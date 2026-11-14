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

## Native app run 2 (2026-11-14 18:24 UTC, quiet room, unplugged, started from the app)
- UNPROCESSED:2 now works (run 1 silence was the locked screen). Bottom mic → ch1, back mic → ch2, both
  direct/raw. Noise floor -74 dBFS, sweep align conf ~5000. Best mode: UNPROCESSED:2 (= ch1+ch2 of UNPROCESSED:3).
- Repeatability: UNPROCESSED:2 vs :3 direct-path delays agree within ~0.1 sample (~1 mm path);
  echo peaks repeat across 4 modes within ±2 mm (e.g. ultrasonic mic1 1.985–1.987 m).
- Ch2 − ch1 direct delay: speaker R +20.8 samples (≈14.9 cm, matches 14.2 cm mic spacing → R = bottom speaker).
  Speaker L only +3.9 samples, and at the bottom mic L arrives just 2.3 samples after R: L does NOT behave like a
  top earpiece ~14 cm away. Speaker layout/routing in portrait is unresolved.
- Back mic is ~48 dB down at 18 kHz vs its 1 kHz level (bottom mic ~13 dB): maybe intrinsic (port design),
  placement unknown. Ultrasonic SNR still 52 dB on ch2.
- UNPROCESSED:3 ch3: not reported as a mic; timing within ~1–3 samples of ch1, different content. Unknown.
- Distances not yet validated against measurements.

## Sweep mode added (2026-11-14)
- Run 2 setup (from user): phone on a coffee container ~10 cm above the stovetop, clutter on the stove,
  back wall ~0.3 m behind, range hood directly above, ceiling ~2 m (guess confirmed by user).
  Rings 0.29–0.37 m (both mics) ≈ back wall; 0.45–0.65 m ≈ hood/clutter; ~1.9–2.0 m ≈ ceiling. Plausible, unmeasured.
- App: guided rotation sweep (8×45° or 12×30°, 1–2 spots ~1 ft apart), voice prompts, duck delay,
  raw WAV per stop + session.json. Capture shortened from ~12 s to ~4.9 s signal.
- Rejected for now: handheld body sweep (body echo + hand motion). Upright stops not needed: with the phone
  flat, echoes with ~zero mic TDOA at every rotation are above/below (ceiling/floor).
- Next: pull a sweep, compute per-echo direction from mic TDOA vs yaw, plot a top-down reflector map.

## First room sweep (2026-11-14 13:41 local, 2 spots × 8 stops)
Data: `results/sweep-20261114-134133/session.json` (+ map); raw WAVs on the user's PC in Documents/echo-room-data/.
- Capture quality excellent: all stops within ~3° of target, gyro max during capture ≤0.016 rad/s, phone level,
  align conf 2600–4700, noise ≈ -75 dBFS, US SNR ~80/45–60 dB. Turned counter-clockwise (azimuth decreasing).
- Mic2−mic1 direct path: median 16.5 samples (≈11.8 cm), stable ±2 samples.
- Analysis (`analysis/sweep_map.py`, `plot_map.py`): sweep deconvolution → analytic IRs, align on direct path,
  subtract per-spot mean across stops (removes phone-fixed energy), back-project 2-mic envelope product on a
  horizontal grid with each stop's yaw, r² spreading gain, per-range contrast.
- Result v1: ranges are crisp (rings), but direction is weak; only partial arcs. Coherent (carrier-phase) cross
  term gave aliasing fringes (14 cm spacing ≫ λ). Needs ground truth from the user to judge arcs.
- Idea: range-only multi-spot trilateration (Dokmanić-style) may beat 2-mic TDOA; needs known spot positions.
- Combining spots (`analysis/combine_spots.py`, Hough over wall lines, spot 2 ≈ 0.30 m right, "same facing"):
  NOT conclusive. Control rotations (90/180/270°) scored as high or higher (contrast 2.86–3.07) than the
  user-described setups (0° 2.74, 44° 2.73–2.89). Cause: per-spot direction is weak (mostly rings), so the
  combination is range-only, and one 30 cm move lets unrelated echo ranges pair up by coincidence (busy kitchen).
- Bug/design flaw: app reset yaw per spot and stored no absolute yaw → spots not in one frame. Fix pending.
- Proposed next: slide sweep along a tape measure (several known positions on two perpendicular lines). A wall's
  range must change linearly with slide position, which coincidences can't fake across 4+ positions.
