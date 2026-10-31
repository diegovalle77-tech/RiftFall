# Riftfall v0.79 — combat state recovery

Fixed a server crash when fog-of-war visibility evaluated combat fires, craters, and effects without a unit kind. Preserved bridge and building visibility extents.

Missing rooms or invalid tokens return an explicit invalid_session response. Internal state failures return a retryable state_unavailable response rather than falsely invalidating a live session. Server traceback diagnostics remain on the host.

This is an incremental update to the complete v0.78 package. It does not declare the full expansion, new music, or public Render deployment finished.
