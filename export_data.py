#!/usr/bin/env python3
"""
Export simulation data to JSON for the interactive web visualization.

Usage:
    python3 export_data.py              # default 25-person graph
    python3 export_data.py --techbro    # 10-person tech bro test scenario
"""
import json
import sys
from simulation.graph_generator import generate_social_graph, get_candidate_pool
from simulation.group_scorer import recommend_group, recommend_group_with_venue
from simulation.propagation import simulate_propagation
from simulation.models import VENUES
from simulation.test_scenarios import tech_bro_scenario


def export_graph(users, G, filename="output/graph_data.json"):
    all_user_data = {}
    all_propagations = {}

    for uid, user in users.items():
        recs = recommend_group_with_venue(uid, users, top_k=5)
        candidates = get_candidate_pool(user, users)

        all_user_data[uid] = {
            "candidates": candidates,
            "recommendations": [
                {
                    "venue": r.venue,
                    "members": r.members,
                    "score": round(r.score, 3),
                    "breakdown": r.breakdown,
                    "suggested_time": r.suggested_time,
                    "member_affinities": r.member_affinities,
                    "adaptive_weights": r.adaptive_weights,
                    "weight_context": r.weight_context,
                }
                for r in recs
            ],
        }

        if recs:
            venue_id = recs[0].venue["id"]
        else:
            venue_id = "v1"

        for u in users.values():
            u.engagement.clear()

        prop = simulate_propagation(uid, venue_id, users, max_waves=5, seed=42)
        all_propagations[uid] = {
            "venue_id": prop.venue_id,
            "venue_name": prop.venue_name,
            "waves": prop.waves,
            "events": [
                {
                    "wave": e.wave,
                    "user_id": e.user_id,
                    "action": e.action.name,
                    "social_proof_count": e.social_proof_count,
                    "triggered_by": e.triggered_by,
                }
                for e in prop.events
            ],
        }

    nodes = []
    for uid, user in users.items():
        nodes.append({
            "id": uid,
            "name": user.name,
            "interests": user.interests,
            "availability": user.availability,
            "friends": user.friends,
            "initiator_score": round(user.initiator_score, 3),
            "past_coattendance": user.past_coattendance,
            "personality": {k: round(v, 2) for k, v in user.personality.items()},
        })

    edges = [{"source": u, "target": v} for u, v in G.edges()]

    data = {
        "nodes": nodes,
        "edges": edges,
        "venues": VENUES,
        "user_data": all_user_data,
        "propagations": all_propagations,
    }

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Exported {len(nodes)} nodes, {len(edges)} edges to {filename}")


def main():
    if "--techbro" in sys.argv:
        print("Loading tech bro scenario (10 users)...")
        users, G = tech_bro_scenario()
        export_graph(users, G)

        # Also print a quick summary of what the algorithm does
        print("\n--- Algorithm Results ---")
        for uid in ["u0", "u4", "u7"]:  # Chad (tech bro), Mia (normie), Omar (loner)
            user = users[uid]
            recs = recommend_group_with_venue(uid, users, top_k=3)
            print(f"\n{user.name}'s top group:")
            if recs:
                r = recs[0]
                names = [users[m].name for m in r.members]
                print(f"  Venue: {r.venue['name']}")
                print(f"  Group: {', '.join(names)}")
                print(f"  Score: {r.score:.3f}")
                print(f"  Breakdown: {r.breakdown}")
                print(f"  Weights: {r.adaptive_weights} ({r.weight_context})")
                print(f"  Affinities: {r.member_affinities}")
                print(f"  Time: {r.suggested_time}")

                # Check: are the tech bros grouped?
                tech_bros = {"u0", "u1", "u2", "u3"}
                group_set = set(r.members)
                tb_in_group = tech_bros & group_set
                print(f"  Tech bros in group: {len(tb_in_group)}/4 ({', '.join(users[t].name for t in tb_in_group)})")
    else:
        print("Loading default scenario (25 users)...")
        users, G = generate_social_graph(n_users=25, avg_friends=4, seed=42)
        export_graph(users, G)


if __name__ == "__main__":
    main()
