# Social Graph Simulation for Optimal Group Formation

Luna Social's core promise is simple: *get real-world connections, not just show you places*. This simulation demonstrates that promise in action and moves beyond just recommending individual users to assembling cohesive groups of 3-5 people most likely to actually go somewhere together.

## Why This Matters

Most social platforms fail at group formation because they recommend *people* to individuals. Luna's insight is different: **recommend optimized *groups*, not individuals**. When three friends see a venue AND each other, the probability they converge on that place increases dramatically.

This simulation proves it by:
1. **Building a synthetic social graph** (a synthetic friend network, interests, and availability)
2. **Computing optimal groups** using a weighted scoring algorithm that balances interests, availability, past co-attendance, and social cohesion
3. **Simulating propagation** showing how a single recommendation triggers a social flywheel through multiple waves
4. **Visualizing the entire process** to make the algorithm's logic transparent

---

## Quick Start (30 seconds)

```bash
# Run the complete simulation
python3 run_simulation.py

# Outputs generated to output/:
#   ✓ group_selection_process.png   — 3-panel algorithm visualization
#   ✓ propagation_waves.png         — 5-wave social spread simulation
#   ✓ score_comparison.png          — Top 5 group recommendations
#   ✓ group_deep_dive.png           — Detailed breakdown of winning group
```

Expected output: **4 high-quality PNG visualizations** showing the algorithm at work.

To validate the algorithm with controlled test cases:
```bash
python3 -m simulation.test_groups
```

---

## The Algorithm: Scoring Groups, Not Individuals

### Core Formula

```
GroupScore = 
    0.35 × SharedInterests         (Why they'd enjoy the same place)
  + 0.35 × AvailabilityOverlap     (Can they actually go at the same time?)
  + 0.20 × PastCoattendance        (Have they successfully gone out before?)
  + 0.10 × SocialCohesion          (Does everyone know each other?)
  + noise(0.05)                     (Controlled randomness for exploration)
```

### Design Decisions

#### 1. **We Score GROUPS, Not Individuals** ⭐

Most recommendation systems ask: *"Which of my friends would like this place?"*

Luna asks: *"What combination of my friends would actually go together AND have a great time?"*

This is fundamentally different:
- 5 individual recommendations = users say "maybe" to each
- 1 group recommendation = users commit together
- Group momentum overcomes individual hesitation

#### 2. **Interest Distinctiveness Weights**

Not all interests are equal:
- "Restaurants" is shared by 80% of users → weight: 0.5 (generic)
- "Jazz clubs" is shared by 12% of users → weight: 1.0 (distinctive)

Why? A group where everyone loves jazz is a *much* stronger signal than everyone liking restaurants. The algorithm weights by distinctiveness (defined in [models.py](simulation/models.py)).

#### 3. **Availability Overlap Equally Weighted with Interests**

Availability (0.35) is weighted the same as shared interests (0.35) because:
- Perfect interests + conflicting schedules = no group forms
- The best group that can actually coordinate wins

The algorithm picks the *best time slot* for overlap and boosts scores for evening/weekend times (higher social energy).

#### 4. **Past Co-Attendance as a Tiebreaker**

Groups that have gone out together before score higher (20% weight). This:
- Favors "experienced" groups over new combinations
- Rewards loyalty and network depth
- Reflects reality: friends who've hung out together are more likely to do it again

#### 5. **Social Cohesion (10% weight)**

A group where everyone knows everyone (all mutual friends) scores higher than a group with a "stranger" member. This small bonus:
- Recognizes that tight-knit groups are more likely to commit
- Doesn't overshadow interest alignment (only 10%)
- Still allows introducing new people to friend groups (if interests align)

#### 6. **Candidate Pool Pruning**

To avoid brute-forcing thousands of combinations, the algorithm:
1. Starts with direct friends
2. Expands to friends-of-friends (FoFs)
3. Prunes by interest similarity if pool exceeds 20 candidates

This is the "limit search intelligently" hint from the takehome—social proximity + interest matching makes the search tractable while preserving quality.

---

## The Propagation Flywheel 🔥

Once a group is recommended, the system simulates how that recommendation propagates through the social network:

```
Wave 0: Seed user (you) sees recommendation
        → Expresses interest or invites friends
        
Wave 1: Users in your social circle see this venue
        + Social proof: "Kai is interested"
        → Higher conversion: skip "interested" → go straight to "inviting"
        
Wave 2: Friends-of-friends see the venue
        + Stronger social proof: "Multiple people going"
        → Momentum builds, more "going" signals
        
Wave 3-4: Extended network joins
        → Venue hits critical mass for social trend
```

This demonstrates the core function:
> "Show them content first → Express interest → Show to network → Next user sees social proof → Faster commit → Confirmed plans are strongest social proof → Flywheel accelerates"

---

## Architecture

### File Structure

```
luna-takehome-backend/
├── simulation/
│   ├── __init__.py
│   ├── models.py              # Data classes: User, GroupRecommendation, EngagementLevel
│   ├── graph_generator.py     # Synthetic graph + candidate pool logic
│   ├── group_scorer.py        # Core algorithm: scoring functions + recommend_group()
│   ├── propagation.py         # Flywheel simulation: waves of engagement
│   ├── visualizer.py          # All visualization functions
│   └── test_groups.py         # Validation test suite
├── run_simulation.py          # Main entry point
├── output/                    # Generated visualizations
│   ├── group_selection_process.png
│   ├── propagation_waves.png
│   ├── score_comparison.png
│   └── group_deep_dive.png
└── README.md                  # This file
```
---

## Dependencies

```
python>=3.10
matplotlib>=3.6
networkx>=3.0
numpy>=1.20
```

Install with:
```bash
pip install -r requirements.txt
```

(Or just `pip install matplotlib networkx numpy` if no requirements.txt exists)

data
