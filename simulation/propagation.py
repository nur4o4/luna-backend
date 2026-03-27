"""
Social graph propagation simulation.

Implements the flywheel described in the takehome:
    1. User gets recommendation → expresses interest
    2. Interest propagates through social graph
    3. Next users see social proof → more likely to act
    4. More engagement → stronger social proof → faster conversion

Key design decisions:
- Initiators (high initiator_score) see content first
- Social proof multiplier increases conversion probability
- Personality traits modulate conversion (Boratto et al. 2024 GRS Survey):
  - Agreeableness boosts base conversion probability
  - Openness affects willingness to engage with unfamiliar venues
  - Energy affects action boldness (skip to GOING)
- Each propagation wave is logged for visualization
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field

from .models import User, EngagementLevel, VENUES, INTEREST_CATEGORIES
from .group_scorer import recommend_group


@dataclass
class PropagationEvent:
    """A single event in the propagation simulation."""
    wave: int
    user_id: str
    venue_id: str
    action: EngagementLevel
    social_proof_count: int   # how many connections were already engaged
    triggered_by: str | None  # user who caused this propagation


@dataclass
class PropagationResult:
    """Full result of a propagation simulation."""
    events: list[PropagationEvent] = field(default_factory=list)
    waves: list[list[str]] = field(default_factory=list)  # user_ids per wave
    venue_id: str = ""
    venue_name: str = ""

    @property
    def total_interested(self) -> int:
        return len({e.user_id for e in self.events if e.action.value >= EngagementLevel.INTERESTED.value})

    @property
    def total_going(self) -> int:
        return len({e.user_id for e in self.events if e.action == EngagementLevel.GOING})


def _social_proof_for_user(user: User, venue_id: str, users: dict[str, User]) -> int:
    """Count how many of this user's connections are engaged with this venue."""
    count = 0
    for fid in user.friends:
        friend = users[fid]
        if venue_id in friend.engagement:
            # Weight by engagement level
            count += friend.engagement[venue_id].value
    return count


def _get_venue_category(venue_id: str) -> str | None:
    """Get the category of a venue by ID."""
    for v in VENUES:
        if v["id"] == venue_id:
            return v.get("category")
    return None


def _get_user_categories(user: User) -> set[str]:
    """Get the interest categories a user's interests fall into."""
    interest_to_cat = {}
    for cat, interests in INTEREST_CATEGORIES.items():
        for interest in interests:
            interest_to_cat[interest] = cat
    return {interest_to_cat[i] for i in user.interests if i in interest_to_cat}


def _conversion_probability(
    user: User,
    venue_id: str,
    social_proof: int,
    wave: int,
) -> tuple[float, EngagementLevel]:
    """
    Calculate probability of user taking action, and what action they'd take.

    Personality-aware conversion (Boratto et al. 2024 GRS Survey):
    - Agreeableness adds to base probability (agreeable people go along with the group)
    - Openness modulates willingness for unfamiliar venue categories
    - Energy affects action boldness (high-energy users skip to GOING)

    Social proof multiplier: each engaged friend increases probability.
    Later waves convert faster (momentum effect).
    """
    agreeableness = user.personality.get('agreeableness', 0.5)
    openness = user.personality.get('openness', 0.5)
    energy = user.personality.get('energy', 0.5)

    # Base probability now includes agreeableness (GRS Survey)
    base_prob = 0.15 + user.initiator_score * 0.2 + agreeableness * 0.08

    # Openness penalty/bonus for unfamiliar venues
    venue_cat = _get_venue_category(venue_id)
    user_cats = _get_user_categories(user)
    if venue_cat and venue_cat not in user_cats:
        # Venue doesn't match user's usual interests — openness determines willingness
        base_prob *= (0.5 + openness * 0.5)

    # Social proof multiplier (diminishing returns)
    sp_multiplier = 1.0 + min(social_proof * 0.25, 2.0)

    # Momentum: later waves convert faster
    wave_bonus = min(wave * 0.08, 0.3)

    final_prob = min(0.95, base_prob * sp_multiplier + wave_bonus)

    # Higher social proof → more likely to skip "interested" and go straight to "invite/going"
    # Energy modulates action boldness: high-energy users jump to GOING more readily
    energy_shift = energy * 0.15  # shifts probability mass toward bolder actions

    if social_proof >= 4:
        action = EngagementLevel.GOING
    elif social_proof >= 2:
        action = random.choices(
            [EngagementLevel.INTERESTED, EngagementLevel.INVITED, EngagementLevel.GOING],
            weights=[max(0.05, 0.2 - energy_shift), 0.5, 0.3 + energy_shift],
        )[0]
    else:
        action = random.choices(
            [EngagementLevel.INTERESTED, EngagementLevel.INVITED],
            weights=[max(0.3, 0.7 - energy_shift), 0.3 + energy_shift],
        )[0]

    return final_prob, action


def simulate_propagation(
    seed_user_id: str,
    venue_id: str,
    users: dict[str, User],
    max_waves: int = 5,
    seed: int = 42,
) -> PropagationResult:
    """
    Simulate how interest propagates through the social graph.

    Wave 0: Seed user expresses interest
    Wave 1+: Friends/FoFs see social proof and decide whether to engage
    """
    random.seed(seed)
    result = PropagationResult(venue_id=venue_id)

    # Find venue name
    for v in VENUES:
        if v["id"] == venue_id:
            result.venue_name = v["name"]
            break

    # Wave 0: Seed user
    users[seed_user_id].engagement[venue_id] = EngagementLevel.INTERESTED
    result.events.append(PropagationEvent(
        wave=0,
        user_id=seed_user_id,
        venue_id=venue_id,
        action=EngagementLevel.INTERESTED,
        social_proof_count=0,
        triggered_by=None,
    ))
    result.waves.append([seed_user_id])

    engaged_users = {seed_user_id}

    for wave in range(1, max_waves + 1):
        wave_users = []

        # Find users adjacent to engaged users who haven't engaged yet
        candidates = set()
        for eid in engaged_users:
            for fid in users[eid].friends:
                if fid not in engaged_users:
                    candidates.add(fid)
                    # Also add FoFs for wider reach
                    for fof_id in users[fid].friends:
                        if fof_id not in engaged_users:
                            candidates.add(fof_id)

        # Sort by initiator score (show to initiators first — per takehome hint)
        candidates = sorted(candidates, key=lambda uid: -users[uid].initiator_score)

        for cid in candidates:
            if cid in engaged_users:
                continue

            social_proof = _social_proof_for_user(users[cid], venue_id, users)
            prob, action = _conversion_probability(users[cid], venue_id, social_proof, wave)

            if random.random() < prob:
                users[cid].engagement[venue_id] = action
                engaged_users.add(cid)
                wave_users.append(cid)

                # Find who triggered this (most engaged friend)
                triggered_by = None
                for fid in users[cid].friends:
                    if fid in engaged_users and fid != cid:
                        triggered_by = fid
                        break

                result.events.append(PropagationEvent(
                    wave=wave,
                    user_id=cid,
                    venue_id=venue_id,
                    action=action,
                    social_proof_count=social_proof,
                    triggered_by=triggered_by,
                ))

        result.waves.append(wave_users)

        if not wave_users:
            break  # No more propagation

    return result
