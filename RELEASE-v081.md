# Riftfall v0.81 — navigation recovery and five-era integration

Includes all v0.80 economy, recruitment, music and v0.79 stability changes.

Changes:
- A unit whose global route search yields to the frame budget retries next frame instead of receiving the two-second unreachable-route cooldown.
- Local traffic detours retain their A* frontier, visited nodes and predecessor map across frame budgets, rather than restarting each time. Their existing visit cap remains in place.
- New movement, attack and gather orders discard obsolete local search jobs. Local jobs also restart when their start, destination or map topology changes. Movement continues through collision-checked substeps.

Verification includes deterministic tests for frame-budget yields, resumable detours, unreachable-path backoff and new-order invalidation. A four-faction integration scenario advances all commanders through Stone, Ancient, Medieval, Industrial and Future using real simulation timers, checks building upgrades and positions, retains early troop equipment, serializes each player's visible state, and verifies future resource deposits and final-era advancement rejection.

The full expansion remains in progress. Browser visual/playability review and the public Render deployment are still outstanding. The four-faction simulation scenario is not a browser-based multiplayer playtest.
