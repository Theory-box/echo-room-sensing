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

## Native app run 1 (2026-11-14, Pixel 11, phone flat on towel, USB cable attached)
Raw report: `results/2026-11-14_native-run1_flat-on-towel.json`
- **Simultaneous separate mics work natively.** Android reports two built-in mics with positions:
  bottom (2.7, 0.6, 0.8) cm and back (5.5, 14.6, 0.4) cm → ~14.2 cm apart (≈20 samples at 48 kHz).
  Input devices accept 1–4 channels, index masks 3ch/4ch.
- UNPROCESSED:3 = best: raw (noise floor -64.6 dBFS, no clipping, align conf 1431). Ch2 differs from ch1
  by a 18.7-sample geometry swing (≈13 cm), consistent with the bottom↔back mic spacing.
  Ch3 has nearly the same timing as ch1 but different content (corr -0.07); identity unknown.
- Ch2 (likely the back mic) is ~43 dB down at 18 kHz vs its 1 kHz level: back mic faces into the towel
  when the phone lies screen-up. Try face-down or upright placement.
- UNPROCESSED:2 returned digital silence (first run; possibly phone still locked). Needs a retest.
- CAMCORDER:2 is "distinct" but activeMics shows both mics mapped (processed) to each channel → don't
  use it for timing. VOICE_RECOGNITION clipped (9623 samples). MIC:2 used only the bottom mic.
- Summary ranking fixed to prefer raw UNPROCESSED capture.
