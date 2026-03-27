"""
Data models for the Luna social graph simulation.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum


# ── Interest & Venue Catalogs ──────────────────────────────────────────────

INTEREST_CATEGORIES = {
    "nightlife":   ["jazz clubs", "cocktail bars", "rooftop bars", "live music venues", "dance clubs"],
    "dining":      ["sushi restaurants", "italian trattorias", "taco joints", "brunch spots", "fine dining"],
    "outdoors":    ["hiking trails", "rock climbing gyms", "kayaking spots", "bike paths", "surf beaches"],
    "culture":     ["art galleries", "indie cinemas", "comedy clubs", "bookshop cafes", "poetry readings"],
    "wellness":    ["yoga studios", "hot springs", "meditation centers", "boxing gyms", "sauna clubs"],
    "tech":        ["hackathons", "startup meetups", "crypto talks", "sauna clubs", "cold plunge"],
}

ALL_INTERESTS = [i for cat in INTEREST_CATEGORIES.values() for i in cat]

# Niche interests are weighted higher for matching (the "jazz clubs > restaurants" insight)
INTEREST_DISTINCTIVENESS = {interest: 1.0 for interest in ALL_INTERESTS}
# Broad categories get lower weight
for cat, items in INTEREST_CATEGORIES.items():
    for item in items[:2]:  # first 2 in each category are "more common"
        INTEREST_DISTINCTIVENESS[item] = 0.5

TIME_SLOTS = [
    "fri_7pm", "fri_9pm",
    "sat_12pm", "sat_3pm", "sat_7pm", "sat_9pm",
    "sun_11am", "sun_3pm", "sun_7pm",
    "wed_7pm", "thu_7pm",
]

VENUES = [
    {"id": "v1",  "name": "Blue Note Jazz Club",     "category": "nightlife", "tags": ["jazz clubs", "cocktail bars"]},
    {"id": "v2",  "name": "Sunset Rooftop Bar",      "category": "nightlife", "tags": ["rooftop bars", "live music venues"]},
    {"id": "v3",  "name": "Omotenashi Sushi",        "category": "dining",    "tags": ["sushi restaurants", "fine dining"]},
    {"id": "v4",  "name": "Nonna's Trattoria",       "category": "dining",    "tags": ["italian trattorias", "brunch spots"]},
    {"id": "v5",  "name": "Runyon Canyon Trail",     "category": "outdoors",  "tags": ["hiking trails", "bike paths"]},
    {"id": "v6",  "name": "The Laugh Factory",       "category": "culture",   "tags": ["comedy clubs", "live music venues"]},
    {"id": "v7",  "name": "Golden Hour Gallery",     "category": "culture",   "tags": ["art galleries", "bookshop cafes"]},
    {"id": "v8",  "name": "Taqueria El Sol",         "category": "dining",    "tags": ["taco joints", "brunch spots"]},
    {"id": "v9",  "name": "Summit Climbing Gym",     "category": "outdoors",  "tags": ["rock climbing gyms", "boxing gyms"]},
    {"id": "v10", "name": "Bodhi Yoga Studio",       "category": "wellness",  "tags": ["yoga studios", "meditation centers"]},
    {"id": "v11", "name": "Founders House Co-work",  "category": "tech",      "tags": ["startup meetups", "hackathons"]},
    {"id": "v12", "name": "Bathhouse Williamsburg",  "category": "tech",      "tags": ["sauna clubs", "cold plunge"]},
]


# ── Engagement levels (social proof tiers) ─────────────────────────────────

class EngagementLevel(Enum):
    """Each level is progressively stronger social proof (per takehome spec)."""
    RECOMMENDED = 1   # AI suggested, no user action yet
    INTERESTED  = 2   # user saved / expressed interest
    INVITED     = 3   # user was explicitly invited
    GOING       = 4   # confirmed attendance


# ── Core data classes ──────────────────────────────────────────────────────

@dataclass
class User:
    id: str
    name: str
    interests: list[str]
    availability: list[str]
    friends: list[str] = field(default_factory=list)
    past_coattendance: dict[str, int] = field(default_factory=dict)  # user_id → count
    initiator_score: float = 0.5  # 0-1, how likely to initiate plans

    # Personality traits (simplified Big Five — per Boratto et al. 2024 GRS Survey)
    personality: dict[str, float] = field(default_factory=lambda: {
        'openness': 0.5,       # willingness to try unfamiliar venues/groups
        'agreeableness': 0.5,  # tendency to go along with group decisions
        'energy': 0.5,         # extraversion proxy — affects group size, time preferences
    })

    # Simulation state
    engagement: dict[str, EngagementLevel] = field(default_factory=dict)  # venue_id → level


@dataclass
class GroupRecommendation:
    venue: dict
    members: list[str]       # user IDs
    score: float
    breakdown: dict          # score components
    suggested_time: str
    member_affinities: dict[str, float] = field(default_factory=dict)  # uid → 0-1 affinity (DDGLM)
    adaptive_weights: dict[str, float] = field(default_factory=dict)   # component → adapted weight (ACGER)
    weight_context: str = ""  # label explaining why weights were adapted
