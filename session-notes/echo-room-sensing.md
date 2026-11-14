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

## Diagnostic run 1 (2026-11-14, Pixel 11, Chrome 157; user standing in front of phone)
- Chrome mic: channelCount max 1 → DUPLICATE/mono. No mic-pair direction finding in the browser.
- Processing off (EC/NS/AGC false). Sweep alignment conf 2036. No clipping. Noise floor -57 dBFS.
- Speakers distinct: L vs R direct-path delay differs by ~6.2 samples (~4.4 cm path).
- 18-22 kHz ~18 dB below 1 kHz, but ultrasonic SNR 62.7 dB (excellent). Ticks audible to user.
- Deep dip at 17 kHz (-42.5 dB), single point; unexplained (notch or interference).
- Ultrasonic echoes: 0.45, 0.58, 0.70, 1.03, 1.62, 2.11 m. Near ones likely the user's body. 1.62 m plausibly ceiling (unverified).
- Phone tilted ~15° (gravity x 2.6). Motion 60 Hz, gyro API 59 Hz.
- Decision: stages 2+ need a native Android app for raw multi-mic audio. Next: rerun with user out of the room + tape-measured distances to check range accuracy.
