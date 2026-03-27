"""
Visualization engine for the Luna social graph simulation.

Produces multi-panel figures showing:
1. Full social graph with the target user highlighted
2. Candidate pool (friends + FoFs)
3. Selected optimal group
4. Propagation waves over time
"""
from __future__ import annotations
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
import numpy as np
from matplotlib.colors import to_rgba

from .models import User, EngagementLevel, GroupRecommendation
from .propagation import PropagationResult
from .graph_generator import get_candidate_pool


# ── Color Palette ──────────────────────────────────────────────────────────

COLORS = {
    "target":      "#FF6B35",  # warm orange — the user
    "friend":      "#4ECDC4",  # teal — direct friends
    "fof":         "#95E1D3",  # light teal — friends of friends
    "selected":    "#F7DC6F",  # gold — selected group members
    "interested":  "#85C1E9",  # light blue
    "invited":     "#F0B27A",  # peach
    "going":       "#82E0AA",  # green
    "inactive":    "#D5D8DC",  # grey
    "edge_normal": "#E8E8E8",
    "edge_friend": "#B0BEC5",
    "edge_group":  "#FF6B35",
    "bg":          "#FAFBFC",
}

ENGAGEMENT_COLORS = {
    EngagementLevel.RECOMMENDED: COLORS["inactive"],
    EngagementLevel.INTERESTED:  COLORS["interested"],
    EngagementLevel.INVITED:     COLORS["invited"],
    EngagementLevel.GOING:       COLORS["going"],
}


def _get_layout(G: nx.Graph, target_id: str) -> dict:
    """Spring layout with target user at center."""
    pos = nx.spring_layout(G, seed=42, k=1.8, iterations=80)
    # Center on target user
    if target_id in pos:
        offset = pos[target_id]
        pos = {k: v - offset for k, v in pos.items()}
    return pos


def _draw_base_graph(
    ax: plt.Axes,
    G: nx.Graph,
    pos: dict,
    users: dict[str, User],
    node_colors: dict[str, str],
    node_sizes: dict[str, int],
    highlight_edges: set[tuple] | None = None,
    title: str = "",
):
    """Draw the graph with given node colors and sizes."""
    ax.set_facecolor(COLORS["bg"])
    ax.set_title(title, fontsize=13, fontweight="bold", pad=12, color="#2C3E50")

    # Draw edges
    for u, v in G.edges():
        edge_color = COLORS["edge_group"] if highlight_edges and (u, v) in highlight_edges else COLORS["edge_normal"]
        linewidth = 2.0 if highlight_edges and (u, v) in highlight_edges else 0.5
        alpha = 0.8 if highlight_edges and (u, v) in highlight_edges else 0.3
        ax.plot(
            [pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
            color=edge_color, linewidth=linewidth, alpha=alpha, zorder=1,
        )

    # Draw nodes
    for nid in G.nodes():
        color = node_colors.get(nid, COLORS["inactive"])
        size = node_sizes.get(nid, 200)
        ax.scatter(
            pos[nid][0], pos[nid][1],
            s=size, c=color, edgecolors="white", linewidths=1.5, zorder=2,
        )
        ax.annotate(
            users[nid].name, pos[nid],
            fontsize=7, ha="center", va="bottom",
            xytext=(0, 8), textcoords="offset points",
            color="#34495E", fontweight="bold",
        )

    ax.set_xlim(ax.get_xlim()[0] - 0.15, ax.get_xlim()[1] + 0.15)
    ax.set_ylim(ax.get_ylim()[0] - 0.15, ax.get_ylim()[1] + 0.15)
    ax.axis("off")


# ── Public Visualization Functions ─────────────────────────────────────────

def visualize_group_selection(
    target_user_id: str,
    users: dict[str, User],
    G: nx.Graph,
    recommendation: GroupRecommendation,
    save_path: str = "output/group_selection.png",
):
    """
    3-panel figure:
    1. Full graph (user highlighted)
    2. Candidate pool highlighted
    3. Selected group highlighted
    """
    fig, axes = plt.subplots(1, 3, figsize=(22, 7))
    fig.patch.set_facecolor(COLORS["bg"])
    fig.suptitle(
        "Optimal Group Formation Algorithm",
        fontsize=18, fontweight="bold", color="#2C3E50", y=0.98,
    )

    pos = _get_layout(G, target_user_id)
    candidates = set(get_candidate_pool(users[target_user_id], users))
    selected = set(recommendation.members)

    # ── Panel 1: Full Graph ────────────────────────────────────────────
    colors1 = {nid: COLORS["target"] if nid == target_user_id else COLORS["inactive"] for nid in G.nodes()}
    sizes1 = {nid: 500 if nid == target_user_id else 150 for nid in G.nodes()}
    _draw_base_graph(axes[0], G, pos, users, colors1, sizes1,
                     title="1. Social Graph (You)")

    # ── Panel 2: Candidate Pool ────────────────────────────────────────
    colors2 = {}
    sizes2 = {}
    for nid in G.nodes():
        if nid == target_user_id:
            colors2[nid] = COLORS["target"]
            sizes2[nid] = 500
        elif nid in candidates and nid in users[target_user_id].friends:
            colors2[nid] = COLORS["friend"]
            sizes2[nid] = 350
        elif nid in candidates:
            colors2[nid] = COLORS["fof"]
            sizes2[nid] = 250
        else:
            colors2[nid] = COLORS["inactive"]
            sizes2[nid] = 100

    _draw_base_graph(axes[1], G, pos, users, colors2, sizes2,
                     title="2. Candidate Pool (Friends + FoFs)")

    # ── Panel 3: Selected Group ────────────────────────────────────────
    colors3 = {}
    sizes3 = {}
    group_edges = set()
    for nid in G.nodes():
        if nid == target_user_id:
            colors3[nid] = COLORS["target"]
            sizes3[nid] = 500
        elif nid in selected:
            colors3[nid] = COLORS["selected"]
            sizes3[nid] = 450
        else:
            colors3[nid] = COLORS["inactive"]
            sizes3[nid] = 80

    # Highlight edges between group members
    for u in selected:
        for v in selected:
            if u < v and G.has_edge(u, v):
                group_edges.add((u, v))

    _draw_base_graph(axes[2], G, pos, users, colors3, sizes3,
                     highlight_edges=group_edges,
                     title="3. Optimal Group Selected")

    # Add score breakdown to panel 3
    bd = recommendation.breakdown
    score_text = (
        f"Score: {recommendation.score:.2f}\n"
        f"Interests: {bd['shared_interests']:.2f}  |  "
        f"Availability: {bd['availability_overlap']:.2f}\n"
        f"Past success: {bd['past_coattendance']:.2f}  |  "
        f"Cohesion: {bd['social_cohesion']:.2f}\n"
        f"Time: {recommendation.suggested_time}"
    )
    axes[2].text(
        0.02, 0.02, score_text, transform=axes[2].transAxes,
        fontsize=9, verticalalignment="bottom",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="white", alpha=0.9, edgecolor="#BDC3C7"),
        fontfamily="monospace", color="#2C3E50",
    )

    # Legend
    legend_patches = [
        mpatches.Patch(color=COLORS["target"], label="You"),
        mpatches.Patch(color=COLORS["friend"], label="Direct Friend"),
        mpatches.Patch(color=COLORS["fof"], label="Friend of Friend"),
        mpatches.Patch(color=COLORS["selected"], label="Selected Group"),
        mpatches.Patch(color=COLORS["inactive"], label="Other Users"),
    ]
    fig.legend(handles=legend_patches, loc="lower center", ncol=5, fontsize=10,
               frameon=True, fancybox=True, shadow=False, edgecolor="#BDC3C7")

    plt.tight_layout(rect=[0, 0.06, 1, 0.94])
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close()
    print(f"  Saved: {save_path}")


def visualize_propagation(
    users: dict[str, User],
    G: nx.Graph,
    propagation: PropagationResult,
    target_user_id: str,
    save_path: str = "output/propagation.png",
):
    """
    Multi-panel figure showing propagation waves.
    Each panel = one wave of the simulation.
    """
    n_waves = min(len(propagation.waves), 5)
    if n_waves < 2:
        n_waves = 2

    fig, axes = plt.subplots(1, n_waves, figsize=(6 * n_waves, 7))
    fig.patch.set_facecolor(COLORS["bg"])
    fig.suptitle(
        f"Social Propagation: {propagation.venue_name}",
        fontsize=18, fontweight="bold", color="#2C3E50", y=0.98,
    )

    pos = _get_layout(G, target_user_id)

    # Accumulate engaged users across waves
    engaged_so_far: dict[str, EngagementLevel] = {}

    for wave_idx in range(n_waves):
        ax = axes[wave_idx] if n_waves > 1 else axes

        # Update engaged users for this wave
        for event in propagation.events:
            if event.wave <= wave_idx:
                engaged_so_far[event.user_id] = event.action

        # Color nodes
        colors = {}
        sizes = {}
        for nid in G.nodes():
            if nid == target_user_id and wave_idx == 0:
                colors[nid] = COLORS["target"]
                sizes[nid] = 500
            elif nid in engaged_so_far:
                colors[nid] = ENGAGEMENT_COLORS[engaged_so_far[nid]]
                sizes[nid] = 400
            else:
                colors[nid] = COLORS["inactive"]
                sizes[nid] = 100

        # Highlight edges between engaged users
        engaged_edges = set()
        engaged_ids = set(engaged_so_far.keys())
        for u in engaged_ids:
            for v in engaged_ids:
                if u < v and G.has_edge(u, v):
                    engaged_edges.add((u, v))

        wave_users = propagation.waves[wave_idx] if wave_idx < len(propagation.waves) else []
        n_new = len(wave_users)
        n_total = len(engaged_so_far)

        _draw_base_graph(
            ax, G, pos, users, colors, sizes,
            highlight_edges=engaged_edges,
            title=f"Wave {wave_idx} (+{n_new} users, {n_total} total)",
        )

    # Legend
    legend_patches = [
        mpatches.Patch(color=COLORS["target"], label="Seed User"),
        mpatches.Patch(color=COLORS["interested"], label="Interested"),
        mpatches.Patch(color=COLORS["invited"], label="Invited"),
        mpatches.Patch(color=COLORS["going"], label="Going"),
        mpatches.Patch(color=COLORS["inactive"], label="Not Engaged"),
    ]
    fig.legend(handles=legend_patches, loc="lower center", ncol=5, fontsize=10,
               frameon=True, fancybox=True, shadow=False, edgecolor="#BDC3C7")

    plt.tight_layout(rect=[0, 0.06, 1, 0.94])
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close()
    print(f"  Saved: {save_path}")


def visualize_score_comparison(
    recommendations: list[GroupRecommendation],
    users: dict[str, User],
    save_path: str = "output/score_comparison.png",
):
    """
    Bar chart comparing top group recommendations with score breakdowns.
    Shows the tradeoffs between groups (high interest vs high availability, etc.)
    """
    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor(COLORS["bg"])
    ax.set_facecolor(COLORS["bg"])

    n = len(recommendations)
    x = np.arange(n)
    bar_width = 0.15

    components = [
        ("shared_interests", "Shared Interests", "#4ECDC4"),
        ("availability_overlap", "Availability", "#F7DC6F"),
        ("past_coattendance", "Past Success", "#85C1E9"),
        ("social_cohesion", "Cohesion", "#F0B27A"),
        ("venue_affinity", "Venue Fit", "#82E0AA"),
    ]

    for i, (key, label, color) in enumerate(components):
        values = [r.breakdown[key] for r in recommendations]
        bars = ax.bar(x + i * bar_width, values, bar_width, label=label, color=color, edgecolor="white")

    # Group labels
    labels = []
    for r in recommendations:
        names = [users[uid].name for uid in r.members[:4]]
        venue = r.venue.get("name", "Any venue")[:20]
        labels.append(f"{venue}\n{', '.join(names)}\nScore: {r.score:.2f}")

    ax.set_xticks(x + bar_width * 2)
    ax.set_xticklabels(labels, fontsize=8, color="#34495E")
    ax.set_ylabel("Component Score", fontsize=11, color="#2C3E50")
    ax.set_title("Group Recommendation Comparison (Score Breakdown)",
                 fontsize=14, fontweight="bold", color="#2C3E50", pad=15)
    ax.legend(loc="upper right", fontsize=9, frameon=True, fancybox=True)
    ax.set_ylim(0, 1.1)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#BDC3C7")
    ax.spines["bottom"].set_color("#BDC3C7")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close()
    print(f"  Saved: {save_path}")


def visualize_group_deep_dive(
    recommendation: GroupRecommendation,
    users: dict[str, User],
    save_path: str = "output/group_deep_dive.png",
):
    """
    Detailed breakdown of a single recommended group.
    Shows:
    1. Group members and their key attributes
    2. Score component visualization (radar chart or stacked bar)
    3. Interest overlap visualization
    4. Availability overlap heatmap
    """
    fig = plt.figure(figsize=(16, 10))
    fig.patch.set_facecolor(COLORS["bg"])
    gs = fig.add_gridspec(2, 3, hspace=0.35, wspace=0.3)

    # ── Title ──
    group_names = [users[uid].name for uid in recommendation.members]
    venue_name = recommendation.venue.get("name", "Any Venue")
    fig.suptitle(
        f"Optimal Group Deep-Dive: {venue_name}",
        fontsize=18, fontweight="bold", color="#2C3E50", y=0.98,
    )

    # ── Panel 1: Group Members Profile ──
    ax1 = fig.add_subplot(gs[0, :2])
    ax1.axis("off")
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, len(recommendation.members) * 1.5)

    member_y = len(recommendation.members) * 1.5
    for i, uid in enumerate(recommendation.members):
        user = users[uid]
        member_y -= 1.4

        # Member box
        rect = mpatches.FancyBboxPatch(
            (0.1, member_y - 0.4), 9.8, 1.2,
            boxstyle="round,pad=0.05", edgecolor="#BDC3C7", facecolor="white", linewidth=1.5
        )
        ax1.add_patch(rect)

        # Name (large)
        ax1.text(0.5, member_y + 0.45, user.name, fontsize=12, fontweight="bold", color="#2C3E50")

        # Interests
        interests_str = ", ".join(user.interests[:2]) + ("..." if len(user.interests) > 2 else "")
        ax1.text(0.5, member_y + 0.1, f"🎯 {interests_str}", fontsize=9, color="#34495E")

        # Availability
        avail_str = ", ".join(user.availability[:2]) + ("..." if len(user.availability) > 2 else "")
        ax1.text(0.5, member_y - 0.25, f"📅 {avail_str}", fontsize=9, color="#34495E")

        # Initiator score
        init_bar_width = user.initiator_score * 3.0
        ax1.barh(member_y - 0.5, init_bar_width, height=0.15, left=6.5, color="#FF6B35", alpha=0.7)
        ax1.text(6.3, member_y - 0.5, "Init:", fontsize=8, color="#2C3E50", ha="right", va="center")

    ax1.set_title("Group Members", fontsize=13, fontweight="bold", pad=10, color="#2C3E50", loc="left")

    # ── Panel 2: Score Breakdown (Gauge/Bar) ──
    ax2 = fig.add_subplot(gs[0, 2])
    ax2.set_xlim(0, 1.5)
    ax2.set_ylim(0, 5.5)
    ax2.axis("off")

    # Score components as horizontal bars
    components_data = [
        ("Shared Interests", recommendation.breakdown["shared_interests"], COLORS["friend"]),
        ("Availability", recommendation.breakdown["availability_overlap"], COLORS["selected"]),
        ("Past Success", recommendation.breakdown["past_coattendance"], COLORS["interested"]),
        ("Cohesion", recommendation.breakdown["social_cohesion"], COLORS["invited"]),
        ("Venue Fit", recommendation.breakdown["venue_affinity"], COLORS["going"]),
    ]

    y_pos = 5.0
    for label, value, color in components_data:
        # Background bar (light)
        ax2.barh(y_pos, 1.0, height=0.35, color="#E8E8E8", edgecolor="#BDC3C7")
        # Actual value bar
        ax2.barh(y_pos, value, height=0.35, color=color, edgecolor=color, linewidth=1)
        # Label and value
        ax2.text(-0.05, y_pos, label, fontsize=9, color="#2C3E50", ha="right", va="center")
        ax2.text(1.05, y_pos, f"{value:.2f}", fontsize=9, color="#2C3E50", ha="left", va="center", fontweight="bold")
        y_pos -= 0.9

    # Total score box
    total_score = recommendation.score
    ax2.add_patch(mpatches.FancyBboxPatch(
        (0.05, -0.3), 0.9, 0.5,
        boxstyle="round,pad=0.05", edgecolor="#FF6B35", facecolor="#FFE8D6", linewidth=2
    ))
    ax2.text(0.5, 0.15, f"Total\n{total_score:.3f}", fontsize=10, fontweight="bold",
             color="#FF6B35", ha="center", va="center")

    ax2.set_title("Score Components", fontsize=11, fontweight="bold", pad=10, color="#2C3E50", loc="left")

    # ── Panel 3: Shared Interests Matrix ──
    ax3 = fig.add_subplot(gs[1, 0])
    group_users = [users[uid] for uid in recommendation.members]
    n_members = len(group_users)
    n_interests = 6  # Show top 6

    # Collect all interests
    all_interests = set()
    for user in group_users:
        all_interests.update(user.interests)
    top_interests = sorted(list(all_interests), key=lambda x: sum(
        1 for user in group_users if x in user.interests
    ), reverse=True)[:n_interests]

    # Interest matrix
    matrix = np.zeros((len(top_interests), n_members))
    for i, interest in enumerate(top_interests):
        for j, user in enumerate(group_users):
            matrix[i, j] = 1 if interest in user.interests else 0

    im = ax3.imshow(matrix, cmap="YlGn", aspect="auto", vmin=0, vmax=1)
    ax3.set_xticks(range(n_members))
    ax3.set_yticks(range(len(top_interests)))
    ax3.set_xticklabels([u.name for u in group_users], fontsize=9, color="#34495E")
    ax3.set_yticklabels([i[:15] for i in top_interests], fontsize=8, color="#34495E")
    ax3.set_title("Interest Overlap", fontsize=11, fontweight="bold", pad=10, color="#2C3E50", loc="left")

    # Add checkmarks
    for i in range(len(top_interests)):
        for j in range(n_members):
            if matrix[i, j] > 0:
                ax3.text(j, i, "✓", ha="center", va="center", color="#27AE60", fontweight="bold", fontsize=11)

    # ── Panel 4: Availability Overlap Heatmap ──
    ax4 = fig.add_subplot(gs[1, 1])

    # Get all time slots mentioned across the group
    all_slots = set()
    for user in group_users:
        all_slots.update(user.availability)
    all_slots = sorted(list(all_slots))

    # Availability matrix
    avail_matrix = np.zeros((len(all_slots), n_members))
    for i, slot in enumerate(all_slots):
        for j, user in enumerate(group_users):
            avail_matrix[i, j] = 1 if slot in user.availability else 0

    im2 = ax4.imshow(avail_matrix, cmap="Blues", aspect="auto", vmin=0, vmax=1)
    ax4.set_xticks(range(n_members))
    ax4.set_yticks(range(len(all_slots)))
    ax4.set_xticklabels([u.name for u in group_users], fontsize=9, color="#34495E")
    ax4.set_yticklabels([s[:10] for s in all_slots], fontsize=8, color="#34495E")
    ax4.set_title("Availability Overlap", fontsize=11, fontweight="bold", pad=10, color="#2C3E50", loc="left")

    # Add checkmarks
    for i in range(len(all_slots)):
        for j in range(n_members):
            if avail_matrix[i, j] > 0:
                ax4.text(j, i, "✓", ha="center", va="center", color="#3498DB", fontweight="bold", fontsize=11)

    # Highlight best slot
    best_slot = recommendation.suggested_time
    if best_slot in all_slots:
        best_idx = all_slots.index(best_slot)
        ax4.add_patch(mpatches.Rectangle((n_members - 0.5, best_idx - 0.5), 1, 1,
                                         linewidth=2.5, edgecolor="#E74C3C", facecolor="none"))
        ax4.text(n_members * 0.5, -0.7, f"⭐ Best slot: {best_slot}", fontsize=9, color="#E74C3C", ha="center")

    # ── Panel 5: Explanation ──
    ax5 = fig.add_subplot(gs[1, 2])
    ax5.axis("off")

    # Compute values outside f-string
    all_interests_count = len(set().union(*(u.interests for u in group_users)))

    explanation = f"""
ALGORITHM INSIGHT

Why This Group?

✓ Shared Interests: {recommendation.breakdown['shared_interests']:.2f}
   {all_interests_count} total interest categories

✓ Availability: {recommendation.breakdown['availability_overlap']:.2f}
   {recommendation.suggested_time} works for all

✓ Past Success: {recommendation.breakdown['past_coattendance']:.2f}
   History of going out together

✓ Cohesion: {recommendation.breakdown['social_cohesion']:.2f}
   Interconnected friend group

✓ Venue Fit: {recommendation.breakdown['venue_affinity']:.2f}
   Matches group interests
"""

    ax5.text(0.05, 0.95, explanation, transform=ax5.transAxes,
             fontsize=9, verticalalignment="top", fontfamily="monospace",
             bbox=dict(boxstyle="round,pad=0.8", facecolor="white", alpha=0.95, edgecolor="#BDC3C7"),
             color="#2C3E50")

    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=COLORS["bg"])
    plt.close()
    print(f"  Saved: {save_path}")
