"""
Synthetic social graph generator.

Creates a realistic-ish social network where:
- Friends share more interests than strangers
- Friends-of-friends share some interests
- Some users are natural "initiators" (they start plans)
- Past co-attendance correlates with friendship closeness
"""
from __future__ import annotations
import random
import networkx as nx
from .models import User, ALL_INTERESTS, TIME_SLOTS, INTEREST_CATEGORIES

FIRST_NAMES = [
    "Alex", "Jordan", "Sam", "Taylor", "Morgan", "Casey", "Riley", "Quinn",
    "Avery", "Charlie", "Dakota", "Emery", "Finley", "Harper", "Jamie",
    "Kai", "Lennox", "Marley", "Nico", "Oakley", "Peyton", "Reese",
    "Sage", "Tatum", "Val", "Wren", "Zion", "Blake", "Drew", "Eden",
]


def generate_social_graph(
    n_users: int = 25,
    avg_friends: int = 4,
    seed: int = 42,
) -> tuple[dict[str, User], nx.Graph]:
    """Generate a synthetic social graph with correlated interests."""
    random.seed(seed)

    users: dict[str, User] = {}
    G = nx.Graph()

    # ── Step 1: Create users with base interests ───────────────────────
    names = random.sample(FIRST_NAMES, min(n_users, len(FIRST_NAMES)))
    if n_users > len(FIRST_NAMES):
        names += [f"User_{i}" for i in range(len(FIRST_NAMES), n_users)]

    for i in range(n_users):
        uid = f"u{i}"
        # Each user has 2-5 interests, biased toward 1-2 categories
        primary_cat = random.choice(list(INTEREST_CATEGORIES.keys()))
        secondary_cat = random.choice([c for c in INTEREST_CATEGORIES if c != primary_cat])
        interests = (
            random.sample(INTEREST_CATEGORIES[primary_cat], k=random.randint(1, 3)) +
            random.sample(INTEREST_CATEGORIES[secondary_cat], k=random.randint(1, 2))
        )
        # 3-5 available time slots
        availability = random.sample(TIME_SLOTS, k=random.randint(3, 5))

        initiator = random.betavariate(2, 5)  # skewed low — few initiators
        users[uid] = User(
            id=uid,
            name=names[i],
            interests=interests,
            availability=availability,
            initiator_score=initiator,
            personality={
                'openness': random.betavariate(5, 5),       # centered ~0.5
                'agreeableness': random.betavariate(4, 3),   # skewed agreeable
                'energy': min(1.0, initiator + random.gauss(0, 0.15)),  # correlated with initiator
            },
        )
        G.add_node(uid, label=names[i])

    # ── Step 2: Create friendships (preferential attachment + interest bias) ──
    user_ids = list(users.keys())

    # Use Barabasi-Albert-like approach but with interest affinity
    for uid in user_ids:
        n_friends = max(1, int(random.gauss(avg_friends, 1.5)))
        candidates = [c for c in user_ids if c != uid and c not in users[uid].friends]

        # Score candidates by interest overlap (friends tend to share interests)
        scored = []
        for cid in candidates:
            overlap = len(set(users[uid].interests) & set(users[cid].interests))
            # Bias toward interest similarity but allow some random connections
            score = overlap * 2.0 + random.random()
            scored.append((cid, score))

        scored.sort(key=lambda x: -x[1])
        new_friends = [cid for cid, _ in scored[:n_friends]]

        for fid in new_friends:
            if fid not in users[uid].friends:
                users[uid].friends.append(fid)
                users[fid].friends.append(uid)
                G.add_edge(uid, fid)

    # ── Step 3: Generate past co-attendance (correlated with friendship) ──
    for uid, user in users.items():
        for fid in user.friends:
            if fid not in user.past_coattendance:
                # Close friends have gone out more together
                interest_overlap = len(set(user.interests) & set(users[fid].interests))
                count = max(0, int(random.gauss(interest_overlap, 1)))
                if count > 0:
                    user.past_coattendance[fid] = count
                    users[fid].past_coattendance[uid] = count

    # ── Step 4: Add some FoF co-attendance (weaker signal) ──
    for uid, user in users.items():
        fof_ids = set()
        for fid in user.friends:
            fof_ids.update(users[fid].friends)
        fof_ids -= set(user.friends)
        fof_ids.discard(uid)

        for fof_id in random.sample(list(fof_ids), k=min(2, len(fof_ids))):
            if fof_id not in user.past_coattendance and random.random() < 0.3:
                user.past_coattendance[fof_id] = 1
                users[fof_id].past_coattendance[uid] = 1

    return users, G


def get_candidate_pool(user: User, users: dict[str, User], max_candidates: int = 20) -> list[str]:
    """
    Get candidate pool: friends + friends-of-friends.
    Pruned by social proximity and interest similarity (per the "limit search intelligently" hint).
    """
    candidates = set(user.friends)

    # Add friends of friends
    for fid in user.friends:
        for fof_id in users[fid].friends:
            if fof_id != user.id:
                candidates.add(fof_id)

    # Prune by interest similarity if pool is too large
    if len(candidates) > max_candidates:
        scored = []
        for cid in candidates:
            overlap = len(set(user.interests) & set(users[cid].interests))
            is_direct = 1.0 if cid in user.friends else 0.0
            score = overlap + is_direct * 3.0
            scored.append((cid, score))
        scored.sort(key=lambda x: -x[1])
        candidates = {cid for cid, _ in scored[:max_candidates]}

    return list(candidates)
