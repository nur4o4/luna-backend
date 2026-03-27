"""
Hand-crafted test scenarios for demonstrating algorithm behavior.
"""
from __future__ import annotations
import networkx as nx
from .models import User


def tech_bro_scenario() -> tuple[dict[str, User], nx.Graph]:
    """
    10 people: 4 tech bros, 6 normies.

    Tech bros share: hackathons, startup meetups, crypto talks, cold plunge, sauna clubs
    They also share availability (weeknight evenings) and have co-attendance history.
    Personality: high energy, moderate openness, moderate agreeableness.

    The question: does the algorithm naturally cluster the tech bros?

    Network structure:
        Chad ── Bryce ── Jared ── Kyle     (tech bro chain, all connected)
          |       |                  |
        Mia ── Sofia ── Lena        Omar   (normies with some cross-connections)
                  |       |
                Priya ── James
    """
    users = {}

    # ── Tech Bros ──────────────────────────────────────────────────────
    # High energy, moderate openness, moderate agreeableness
    users["u0"] = User(
        id="u0", name="Chad",
        interests=["hackathons", "startup meetups", "cold plunge", "rooftop bars"],
        availability=["wed_7pm", "thu_7pm", "fri_9pm", "sat_9pm"],
        friends=["u1", "u2", "u3", "u4"],
        past_coattendance={"u1": 5, "u2": 3, "u3": 4},
        initiator_score=0.85,
        personality={"openness": 0.55, "agreeableness": 0.50, "energy": 0.90},
    )
    users["u1"] = User(
        id="u1", name="Bryce",
        interests=["hackathons", "crypto talks", "cold plunge", "startup meetups"],
        availability=["wed_7pm", "thu_7pm", "fri_9pm", "sat_7pm"],
        friends=["u0", "u2", "u3", "u5"],
        past_coattendance={"u0": 5, "u2": 4, "u3": 3},
        initiator_score=0.7,
        personality={"openness": 0.45, "agreeableness": 0.55, "energy": 0.80},
    )
    users["u2"] = User(
        id="u2", name="Jared",
        interests=["startup meetups", "hackathons", "sauna clubs", "rock climbing gyms"],
        availability=["wed_7pm", "thu_7pm", "sat_9pm", "fri_7pm"],
        friends=["u0", "u1", "u3"],
        past_coattendance={"u0": 3, "u1": 4, "u3": 2},
        initiator_score=0.6,
        personality={"openness": 0.60, "agreeableness": 0.50, "energy": 0.70},
    )
    users["u3"] = User(
        id="u3", name="Kyle",
        interests=["crypto talks", "cold plunge", "hackathons", "cocktail bars"],
        availability=["wed_7pm", "thu_7pm", "fri_9pm", "sat_9pm"],
        friends=["u0", "u1", "u2", "u7"],
        past_coattendance={"u0": 4, "u1": 3, "u2": 2},
        initiator_score=0.55,
        personality={"openness": 0.50, "agreeableness": 0.45, "energy": 0.75},
    )

    # ── Normies ────────────────────────────────────────────────────────
    users["u4"] = User(
        id="u4", name="Mia",
        interests=["art galleries", "indie cinemas", "brunch spots", "yoga studios"],
        availability=["sat_12pm", "sun_11am", "sun_3pm", "fri_7pm"],
        friends=["u0", "u5"],
        past_coattendance={"u5": 3},
        initiator_score=0.4,
        personality={"openness": 0.80, "agreeableness": 0.75, "energy": 0.40},
    )
    users["u5"] = User(
        id="u5", name="Sofia",
        interests=["yoga studios", "brunch spots", "bookshop cafes", "hiking trails"],
        availability=["sat_12pm", "sun_11am", "sun_3pm", "sat_3pm"],
        friends=["u1", "u4", "u6", "u8"],
        past_coattendance={"u4": 3, "u6": 4, "u8": 2},
        initiator_score=0.65,
        personality={"openness": 0.70, "agreeableness": 0.80, "energy": 0.55},
    )
    users["u6"] = User(
        id="u6", name="Lena",
        interests=["poetry readings", "bookshop cafes", "italian trattorias", "meditation centers"],
        availability=["sun_11am", "sun_3pm", "sat_3pm", "sat_7pm"],
        friends=["u5", "u9"],
        past_coattendance={"u5": 4, "u9": 2},
        initiator_score=0.3,
        personality={"openness": 0.85, "agreeableness": 0.90, "energy": 0.25},
    )
    users["u7"] = User(
        id="u7", name="Omar",
        interests=["boxing gyms", "taco joints", "live music venues", "dance clubs"],
        availability=["fri_7pm", "fri_9pm", "sat_9pm", "thu_7pm"],
        friends=["u3"],
        past_coattendance={"u3": 1},
        initiator_score=0.45,
        personality={"openness": 0.35, "agreeableness": 0.30, "energy": 0.80},  # lone wolf
    )
    users["u8"] = User(
        id="u8", name="Priya",
        interests=["hiking trails", "yoga studios", "art galleries", "comedy clubs"],
        availability=["sat_12pm", "sat_3pm", "sun_11am", "sun_3pm"],
        friends=["u5", "u9"],
        past_coattendance={"u5": 2, "u9": 3},
        initiator_score=0.35,
        personality={"openness": 0.65, "agreeableness": 0.70, "energy": 0.35},
    )
    users["u9"] = User(
        id="u9", name="James",
        interests=["comedy clubs", "live music venues", "taco joints", "hiking trails"],
        availability=["fri_7pm", "sat_7pm", "sat_9pm", "sun_3pm"],
        friends=["u6", "u8"],
        past_coattendance={"u6": 2, "u8": 3},
        initiator_score=0.5,
        personality={"openness": 0.50, "agreeableness": 0.60, "energy": 0.55},
    )

    # Build graph
    G = nx.Graph()
    for uid, user in users.items():
        G.add_node(uid, label=user.name)
    for uid, user in users.items():
        for fid in user.friends:
            G.add_edge(uid, fid)

    return users, G
