"""
Group scoring algorithm for optimal group formation.

Research-informed composite formula:
    GroupScore = I × w_i + A × w_a + P × w_p + C × w_c + Ψ × 0.10 + V + E + ε

    where w_i, w_a, w_p, w_c are ADAPTIVE weights (ACGER, Liao et al. 2020)
    and Ψ is personality compatibility using mixed homo/hetero attributes
    (GGA, Krouska et al. 2023)

Key design decisions:
- We score GROUPS, not individuals — the unit of recommendation is a group
- Interest distinctiveness is weighted (jazz clubs >> restaurants)
- Weights adapt to group context, not fixed (ACGER paper)
- Personality uses mixed attribute optimization (GGA paper)
- Members get soft affinity scores, not binary in/out (DDGLM, Busireddy et al. 2026)
- Group emergent preference captures group-level interests beyond individual aggregation (ACGER)
- Controlled randomness for exploration (not purely deterministic)
- Search space pruned by social proximity before scoring
"""
from __future__ import annotations
import math
import random
from itertools import combinations
from collections import Counter

from .models import (
    User, GroupRecommendation, INTEREST_DISTINCTIVENESS,
    INTEREST_CATEGORIES, VENUES, EngagementLevel,
)
from .graph_generator import get_candidate_pool


# ── Scoring Components ─────────────────────────────────────────────────────

def shared_interest_score(users: list[User]) -> float:
    """
    Score based on interests shared across the group.
    Weighted by distinctiveness — niche interests count more.
    """
    if len(users) < 2:
        return 0.0

    interest_counts = Counter()
    for u in users:
        interest_counts.update(u.interests)

    # Interests shared by 2+ members, weighted by distinctiveness
    shared_score = 0.0
    for interest, count in interest_counts.items():
        if count >= 2:
            distinctiveness = INTEREST_DISTINCTIVENESS.get(interest, 1.0)
            # More people sharing = exponentially better (concave reward)
            shared_score += distinctiveness * (count / len(users)) ** 0.5

    # Normalize to 0-1
    max_possible = len(set().union(*(u.interests for u in users))) * 1.0
    return min(1.0, shared_score / max(1.0, max_possible * 0.5))


def availability_overlap_score(users: list[User]) -> tuple[float, str | None]:
    """
    Score based on time slot overlap.
    Returns (score, best_time_slot).
    """
    if not users:
        return 0.0, None

    slot_counts = Counter()
    for u in users:
        slot_counts.update(u.availability)

    if not slot_counts:
        return 0.0, None

    best_slot, best_count = slot_counts.most_common(1)[0]
    overlap_ratio = best_count / len(users)

    # Prefer weekend evening slots (higher energy)
    time_bonus = 1.0
    if "fri" in best_slot or "sat" in best_slot:
        time_bonus = 1.15
    if "7pm" in best_slot or "9pm" in best_slot:
        time_bonus *= 1.1

    return min(1.0, overlap_ratio * time_bonus), best_slot


def past_success_score(users: list[User]) -> float:
    """
    Score based on past co-attendance among group members.
    Groups that have gone out together before are more likely to do it again.
    """
    if len(users) < 2:
        return 0.0

    total_pairs = 0
    successful_pairs = 0
    total_coattendance = 0

    for i, u1 in enumerate(users):
        for u2 in users[i + 1:]:
            total_pairs += 1
            count = u1.past_coattendance.get(u2.id, 0)
            if count > 0:
                successful_pairs += 1
                total_coattendance += count

    if total_pairs == 0:
        return 0.0

    pair_ratio = successful_pairs / total_pairs
    intensity = min(1.0, total_coattendance / (total_pairs * 3))

    return pair_ratio * 0.6 + intensity * 0.4


def social_cohesion_score(group_ids: list[str], users: dict[str, User]) -> float:
    """
    How interconnected is the group? A group where everyone knows everyone
    is more likely to actually go than one with strangers.
    """
    if len(group_ids) < 2:
        return 0.0

    total_pairs = 0
    connected_pairs = 0

    for i, uid1 in enumerate(group_ids):
        for uid2 in group_ids[i + 1:]:
            total_pairs += 1
            if uid2 in users[uid1].friends:
                connected_pairs += 1

    return connected_pairs / max(1, total_pairs)


# ── NEW: Research-Informed Components ──────────────────────────────────────

def personality_compatibility_score(group_users: list[User]) -> float:
    """
    Mixed homogeneous/heterogeneous attribute scoring (GGA, Krouska et al. 2023).

    Key insight from the paper: some attributes should be SIMILAR across the group
    (homogeneous) while others should be DIVERSE (heterogeneous).

    Homogeneous (minimize spread):
        - agreeableness: groups where everyone is similarly agreeable avoid conflict

    Heterogeneous (maximize spread):
        - initiator_score: want 1-2 initiators + followers, not all leaders or all followers
        - openness: mixed openness leads to better group discovery

    Uses standard deviation as the spread metric, inspired by the Euclidean distance
    approach in GGA Equations 3-6.
    """
    if len(group_users) < 2:
        return 0.0

    def _std(values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        return math.sqrt(variance)

    agreeableness_vals = [u.personality.get('agreeableness', 0.5) for u in group_users]
    initiator_vals = [u.initiator_score for u in group_users]
    openness_vals = [u.personality.get('openness', 0.5) for u in group_users]

    # Homogeneous: low spread = high score
    agreeableness_sim = max(0.0, 1.0 - _std(agreeableness_vals) * 3.0)

    # Heterogeneous: high spread = high score (capped at 1.0)
    initiator_diversity = min(1.0, _std(initiator_vals) * 4.0)
    openness_diversity = min(1.0, _std(openness_vals) * 3.0)

    return (
        agreeableness_sim * 0.40 +
        initiator_diversity * 0.35 +
        openness_diversity * 0.25
    )


def compute_adaptive_weights(
    interest: float,
    avail: float,
    past: float,
    cohesion: float,
) -> tuple[dict[str, float], str]:
    """
    Context-dependent weight adaptation (ACGER, Liao et al. 2020).

    Instead of fixed weights, we adapt based on group composition context.
    The ACGER paper uses neural attention to learn dynamic weights per event;
    we approximate this with rule-based context detection from the raw sub-scores.

    Returns (weights_dict, context_label).
    """
    # Defaults (rebalanced from original 0.35/0.35/0.20/0.10 to accommodate personality at 0.10)
    w = {"interests": 0.30, "availability": 0.30, "past": 0.15, "cohesion": 0.05}
    label = "balanced"

    if cohesion > 0.7:
        # Close friend group: they already know each other well, so
        # past success matters more (proven group), interests matter less
        w = {"interests": 0.20, "availability": 0.30, "past": 0.30, "cohesion": 0.05}
        label = "close-knit group → boosted past success"
    elif cohesion < 0.3:
        # Mostly strangers: interests are the primary bridge,
        # past co-attendance is unreliable (they haven't been out together)
        w = {"interests": 0.40, "availability": 0.25, "past": 0.05, "cohesion": 0.10}
        label = "new connections → boosted shared interests"

    if avail < 0.4:
        # Scheduling is the bottleneck — weight it higher
        w["availability"] = max(w["availability"], 0.40)
        # Rebalance others proportionally
        remaining = 1.0 - w["availability"] - 0.10  # reserve 0.10 for personality
        other_sum = sum(v for k, v in w.items() if k != "availability")
        if other_sum > 0:
            for k in w:
                if k != "availability":
                    w[k] = w[k] / other_sum * remaining
        label = "scheduling conflict → boosted availability"

    return w, label


def emergent_preference_score(group_users: list[User], venue: dict | None) -> float:
    """
    Group emergent preference (ACGER, Liao et al. 2020).

    Key finding: ~20-30% of group events don't match any individual member's
    stated preferences. Groups develop emergent preferences beyond member aggregation.

    We detect this by checking if the venue bridges multiple interest categories
    represented in the group. A cocktail bar bridges "nightlife" and "dining" people.
    A comedy club bridges "culture" and "nightlife" people.
    """
    if not venue or len(group_users) < 2:
        return 0.0

    # Map each user's interests back to their categories
    interest_to_cat = {}
    for cat, interests in INTEREST_CATEGORIES.items():
        for interest in interests:
            interest_to_cat[interest] = cat

    # Collect unique categories in the group
    group_categories = set()
    for u in group_users:
        for interest in u.interests:
            if interest in interest_to_cat:
                group_categories.add(interest_to_cat[interest])

    # Collect venue categories (from its tags)
    venue_categories = set()
    for tag in venue.get("tags", []):
        if tag in interest_to_cat:
            venue_categories.add(interest_to_cat[tag])

    # Bonus if venue bridges 2+ group categories
    bridged = group_categories & venue_categories
    if len(bridged) >= 2 and len(group_categories) >= 3:
        return 0.05  # full emergent bonus
    elif len(bridged) >= 2:
        return 0.03
    return 0.0


def compute_member_affinities(
    group_ids: list[str],
    users: dict[str, User],
    venue: dict | None = None,
    temperature: float = 0.5,
) -> dict[str, float]:
    """
    Soft membership affinity (DDGLM, Busireddy et al. 2026).

    Instead of binary group membership, each member gets a continuous
    affinity score using temperature-scaled softmax (DDGLM Equation 2).

    τ < 1 produces sharper distributions (strong fit vs marginal members).
    """
    if len(group_ids) < 2:
        return {uid: 1.0 for uid in group_ids}

    group_users = [users[uid] for uid in group_ids]
    group_interests = set()
    group_availability = Counter()
    for u in group_users:
        group_interests.update(u.interests)
        group_availability.update(u.availability)

    raw_scores = {}
    for uid in group_ids:
        u = users[uid]

        # Interest overlap with rest of group
        others_interests = set()
        for other_uid in group_ids:
            if other_uid != uid:
                others_interests.update(users[other_uid].interests)
        interest_overlap = len(set(u.interests) & others_interests) / max(1, len(u.interests))

        # Availability match with group's best slot
        best_slot = group_availability.most_common(1)[0][0] if group_availability else None
        avail_match = 1.0 if best_slot and best_slot in u.availability else 0.0

        # Social ties to other members
        group_friends = sum(1 for other in group_ids if other != uid and other in u.friends)
        social_ties = group_friends / max(1, len(group_ids) - 1)

        # Venue match
        venue_match = 0.0
        if venue:
            venue_tags = set(venue.get("tags", []))
            venue_match = len(set(u.interests) & venue_tags) / max(1, len(venue_tags))

        raw_scores[uid] = (
            interest_overlap * 0.40 +
            avail_match * 0.30 +
            social_ties * 0.20 +
            venue_match * 0.10
        )

    # Temperature-scaled softmax (DDGLM Eq. 2)
    max_score = max(raw_scores.values()) if raw_scores else 0
    exp_scores = {}
    for uid, score in raw_scores.items():
        exp_scores[uid] = math.exp((score - max_score) / temperature)

    total_exp = sum(exp_scores.values())
    affinities = {}
    for uid, exp_s in exp_scores.items():
        affinities[uid] = round(exp_s / max(total_exp, 1e-10), 3)

    return affinities


# ── Main Group Scoring ─────────────────────────────────────────────────────

def score_group(
    group_ids: list[str],
    users: dict[str, User],
    venue: dict | None = None,
    noise_factor: float = 0.05,
) -> GroupRecommendation:
    """
    Score a candidate group and return a full recommendation.

    Research-informed formula:
        GroupScore = I × w_i + A × w_a + P × w_p + C × w_c + Ψ × 0.10 + V + E + ε

    where weights w_i, w_a, w_p, w_c adapt to group context (ACGER)
    and Ψ is personality compatibility using mixed attributes (GGA).
    """
    group_users = [users[uid] for uid in group_ids]

    # Core sub-scores
    interest = shared_interest_score(group_users)
    avail, best_time = availability_overlap_score(group_users)
    past = past_success_score(group_users)
    cohesion = social_cohesion_score(group_ids, users)

    # NEW: Personality compatibility (GGA, Krouska et al. 2023)
    personality = personality_compatibility_score(group_users)

    # NEW: Adaptive weights (ACGER, Liao et al. 2020)
    weights, weight_context = compute_adaptive_weights(interest, avail, past, cohesion)

    # Venue affinity bonus
    venue_bonus = 0.0
    if venue:
        group_interests = set()
        for u in group_users:
            group_interests.update(u.interests)
        venue_tags = set(venue.get("tags", []))
        venue_bonus = len(group_interests & venue_tags) / max(1, len(venue_tags)) * 0.15

    # NEW: Emergent preference bonus (ACGER)
    emergent = emergent_preference_score(group_users, venue)

    # NEW: Soft membership affinities (DDGLM, Busireddy et al. 2026)
    affinities = compute_member_affinities(group_ids, users, venue)

    # Controlled randomness for exploration
    noise = random.gauss(0, noise_factor)

    total = (
        interest * weights["interests"] +
        avail * weights["availability"] +
        past * weights["past"] +
        cohesion * weights["cohesion"] +
        personality * 0.10 +
        venue_bonus +
        emergent +
        noise
    )

    return GroupRecommendation(
        venue=venue or {},
        members=group_ids,
        score=max(0.0, min(1.0, total)),
        breakdown={
            "shared_interests": round(interest, 3),
            "availability_overlap": round(avail, 3),
            "past_coattendance": round(past, 3),
            "social_cohesion": round(cohesion, 3),
            "personality_compatibility": round(personality, 3),
            "venue_affinity": round(venue_bonus, 3),
            "emergent_preference": round(emergent, 3),
        },
        suggested_time=best_time or "fri_7pm",
        member_affinities=affinities,
        adaptive_weights={k: round(v, 3) for k, v in weights.items()},
        weight_context=weight_context,
    )


# ── Top-level Recommendation Function ─────────────────────────────────────

def recommend_group(
    target_user_id: str,
    users: dict[str, User],
    venue: dict | None = None,
    group_sizes: tuple[int, ...] = (3, 4, 5),
    top_k: int = 3,
) -> list[GroupRecommendation]:
    """
    For a given user and (optionally) a venue, find the best groups of 3-5 people.

    Returns top_k recommendations sorted by score.
    """
    candidates = get_candidate_pool(users[target_user_id], users)

    all_recs: list[GroupRecommendation] = []

    for size in group_sizes:
        if len(candidates) < size - 1:
            continue

        # Generate combinations (target user is always included)
        for combo in combinations(candidates, size - 1):
            group_ids = [target_user_id] + list(combo)
            rec = score_group(group_ids, users, venue)
            all_recs.append(rec)

    all_recs.sort(key=lambda r: -r.score)
    return all_recs[:top_k]


def recommend_group_with_venue(
    target_user_id: str,
    users: dict[str, User],
    venues: list[dict] | None = None,
    top_k: int = 3,
) -> list[GroupRecommendation]:
    """
    Recommend best (venue, group, time) combinations for a user.
    This is the full recommendation: place + people + time.
    """
    if venues is None:
        venues = VENUES

    all_recs: list[GroupRecommendation] = []

    for venue in venues:
        recs = recommend_group(target_user_id, users, venue, top_k=1)
        all_recs.extend(recs)

    all_recs.sort(key=lambda r: -r.score)
    return all_recs[:top_k]
