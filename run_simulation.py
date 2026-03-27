#!/usr/bin/env python3
"""
Luna Social — Social Graph Simulation for Optimal Group Formation

This script demonstrates the core algorithm:
1. Generates a synthetic social graph (25 users)
2. Computes optimal groups for a target user
3. Simulates social propagation through the network
4. Produces visualizations showing emergent behavior

Usage:
    python3 run_simulation.py
"""
from simulation.graph_generator import generate_social_graph
from simulation.group_scorer import recommend_group, recommend_group_with_venue
from simulation.propagation import simulate_propagation
from simulation.visualizer import (
    visualize_group_selection,
    visualize_propagation,
    visualize_score_comparison,
    visualize_group_deep_dive,
)
from simulation.models import VENUES


def main():
    print("=" * 60)
    print("  Luna Social — Group Formation Simulation")
    print("=" * 60)

    # ── 1. Generate Social Graph ───────────────────────────────────────
    print("\n[1/4] Generating synthetic social graph...")
    users, G = generate_social_graph(n_users=25, avg_friends=4, seed=42)

    print(f"  Created {len(users)} users with {G.number_of_edges()} connections")

    # Pick a target user (one with moderate connections for interesting results)
    target_id = "u0"
    target = users[target_id]
    print(f"\n  Target user: {target.name} (id={target_id})")
    print(f"  Interests: {', '.join(target.interests)}")
    print(f"  Availability: {', '.join(target.availability)}")
    print(f"  Friends: {[users[f].name for f in target.friends]}")
    print(f"  Initiator score: {target.initiator_score:.2f}")

    # ── 2. Compute Optimal Groups ──────────────────────────────────────
    print("\n[2/4] Computing optimal groups...")

    # Without specific venue (pure group optimization)
    group_recs = recommend_group(target_id, users, top_k=5)
    print(f"\n  Top group (no venue constraint):")
    for i, rec in enumerate(group_recs[:3]):
        names = [users[uid].name for uid in rec.members]
        print(f"    #{i+1} [{rec.score:.3f}] {', '.join(names)} @ {rec.suggested_time}")
        print(f"         {rec.breakdown}")

    # With venue matching (full recommendation: place + people + time)
    full_recs = recommend_group_with_venue(target_id, users, top_k=5)
    print(f"\n  Top recommendations (venue + group + time):")
    for i, rec in enumerate(full_recs[:3]):
        names = [users[uid].name for uid in rec.members]
        venue = rec.venue.get("name", "?")
        print(f"    #{i+1} [{rec.score:.3f}] {venue}")
        print(f"         Group: {', '.join(names)}")
        print(f"         Time: {rec.suggested_time}")
        print(f"         Scores: {rec.breakdown}")

    # ── 3. Simulate Propagation ────────────────────────────────────────
    print("\n[3/4] Simulating social propagation...")

    # Use the top recommended venue
    venue_id = full_recs[0].venue["id"] if full_recs else "v1"
    propagation = simulate_propagation(
        seed_user_id=target_id,
        venue_id=venue_id,
        users=users,
        max_waves=5,
        seed=42,
    )

    print(f"\n  Venue: {propagation.venue_name}")
    print(f"  Waves simulated: {len(propagation.waves)}")
    for i, wave in enumerate(propagation.waves):
        if wave:
            names = [users[uid].name for uid in wave]
            print(f"    Wave {i}: {', '.join(names)}")
    print(f"\n  Total interested: {propagation.total_interested}")
    print(f"  Total going: {propagation.total_going}")

    # Show the flywheel effect
    print("\n  Propagation events:")
    for event in propagation.events:
        user_name = users[event.user_id].name
        trigger = users[event.triggered_by].name if event.triggered_by else "organic"
        print(f"    Wave {event.wave}: {user_name} → {event.action.name} "
              f"(social proof: {event.social_proof_count}, via: {trigger})")

    # ── 4. Generate Visualizations ─────────────────────────────────────
    print("\n[4/4] Generating visualizations...")

    best_rec = group_recs[0]
    visualize_group_selection(target_id, users, G, best_rec)
    visualize_propagation(users, G, propagation, target_id)
    visualize_score_comparison(full_recs[:5], users)
    visualize_group_deep_dive(full_recs[0], users)

    print("\n" + "=" * 60)
    print("  Done! Check the output/ directory for visualizations.")
    print("=" * 60)


if __name__ == "__main__":
    main()
