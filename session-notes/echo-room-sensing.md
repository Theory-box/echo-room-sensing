# Session notes: echo room sensing (acoustic room mapping)

Branch: `feature/echo-diagnostic`
App folder: `diagnostic/`

## Status (2026-11-14)
- Stage 1 diagnostic page written and unit-tested with synthetic data; awaiting first run on the user's Pixel 11.
- Hosting: GitHub Pages from `main` once merged (needs "merge to main").

## Goal
Static-capture acoustic mapping on a Pixel 11 → clean room shell (planes → polygon mesh) + rough furniture boxes.

## Next steps
1. User runs the diagnostic, pastes results.
2. Decide web app vs native Android (depends on distinct stereo mics + processing off).
3. Stage 2: rotations + direction finding.

See the full handoff (HANDOFF.md) for design, pipeline, and how to read results.
