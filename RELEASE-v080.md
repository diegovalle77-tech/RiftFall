# Riftfall v0.80 — era economy and arcade lobby music

This complete package includes the v0.79 combat state recovery fix.

- Construction and recruitment recipes now follow Stone, Ancient, Medieval, Industrial, and Future equipment. Early available equipment avoids iron and Riftglass. Modern infantry, specialists, harvesters, ships and facilities use industrial materials; future equipment adds Riftglass.
- Displayed cost catalogs and actual payments use the same authoritative recipes. Era cost lookups return independent copies, and insufficient payments remain atomic.
- Production queues retain the era when ordered. Advancing while a gatherer is queued no longer turns a cheap early recruit into industrial machinery. Existing buildings continue their intended automatic era upgrade.
- Three new original synthesized lobby compositions: Neon Foundry (132 BPM), Pixel Rebellion (144 BPM), and Rift Drive (126 BPM). Includes techno rhythms, arcade leads and synthesized rock instrumentation without external samples. New tracks lead the six-track lobby rotation; Next Track and volume controls remain available. The three battle arrangements are retained.

Verification: new era economy and recruitment regressions, historical building/research/production integration tests, audio format/level/uniqueness and HTTP asset tests, and eight JavaScript suites. Browser visual QA and listening review have not been performed.

The expansion is still in progress. A public Render URL and final end-to-end five-era multiplayer/browser verification remain outstanding. This release does not claim the full expansion is finished.
