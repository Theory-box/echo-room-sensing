# Echo Room Sensing: status and findings (2026-11-14)

Consolidated summary of everything built and learned so far, written for review by another
Claude instance (the one that wrote the original handoff). Repo: `Theory-box/echo-room-sensing`.
Detailed chronological notes: `session-notes/echo-room-sensing.md`.

## 1. Goal (unchanged from the handoff)
Static acoustic room mapping with a Pixel 11 (no LiDAR): a clean room shell (walls/floor/ceiling as
planes → polygon mesh) plus rough furniture boxes. User prefers static capture over handheld.

## 2. What exists now

| Part | Where | State |
|---|---|---|
| Web diagnostic (Chrome) | `diagnostic/index.html`, live on GitHub Pages | Works; showed Chrome is mono-only |
| Shared DSP (sweep/chirp generation, matched filter, analysis) | `diagnostic/dsp.js` | Used by web page and app |
| Native Android app "Echo Room" | `android/` (Java + WebView UI in `app/src/main/assets/native.html`) | Installed on the user's phone |
| App: mic test (5 recording modes) | "Mic test" section | Works |
| App: guided room sweep | "Start sweep" | Works; voice prompts, gyro-tracked turns, raw WAV per stop |
| Offline analysis (Python) | `analysis/sweep_map.py`, `plot_map.py`, `combine_spots.py`, `scan_offset.py` | Runs; results below |
| Results | `results/` | JSON reports, sweep `session.json`, map image |

Raw sweep WAVs (37 MB) are not in git; they're kept on the user's PC.
PC toolchain (user-scope, no admin): JDK 21, Android SDK (platform 35, build-tools 35), Gradle wrapper
8.11.1 / AGP 8.7.3, adb, and `uv` for Python (numpy/scipy/matplotlib). The phone is connected by USB with
debugging authorized. The app can be driven from the PC (adb intent extras + WebView DevTools protocol).

## 3. Hardware findings (high confidence)

- **Chrome on Android gives one mic channel only** (`channelCount` max 1). The original web-app plan is dead
  for direction finding; native is required (the handoff's own fallback).
- **Native raw stereo works:** `AudioRecord`, source `UNPROCESSED`, `CHANNEL_IN_STEREO`, float, 48 kHz.
  ch1 = bottom mic, ch2 = back mic, both mapped "direct" (unprocessed). Noise floor ≈ -74 to -77 dBFS, no AGC/NS/EC.
  (The first attempt returned digital silence because the phone was still locked.)
- **Mic geometry (from Android `MicrophoneInfo`, cm):** bottom (2.69, 0.58, 0.79), back (5.46, 14.56, 0.41).
  ≈14.3 cm apart, mostly along the phone's long axis. Measured direct-path offset mic2−mic1:
  median 16.5 samples (≈11.8 cm of path), stable ±2 samples across 16 stops.
- **Repeatability is excellent:** direct-path delays agree within ~0.1 sample between runs, and echo peaks
  repeat within ±2 mm (e.g. 1.985–1.987 m across 4 modes).
- **Signal:** near-ultrasonic (18–22 kHz) SNR ≈ 80 dB on the bottom mic, 45–60 dB on the back mic. The back mic
  is ~45–48 dB down at 18 kHz relative to its 1 kHz level (bottom mic ~13 dB), even with the phone raised, so this
  is probably intrinsic to that mic port. 18–22 kHz is audible to the user ("ticks").
- **Other modes:** CAMCORDER mixes both mics into each channel ("processed", bad for timing). VOICE_RECOGNITION
  clips. MIC uses only the bottom mic. A 3-channel index-mask capture works; ch1/ch2 match the stereo capture,
  ch3 is unidentified (timing within 1–3 samples of ch1, different content, not reported as a mic).
- **Speakers:** the "L" channel does not behave like a top earpiece 14 cm away. At the bottom mic, L arrives only
  ~2.3 samples after R, and at the back mic only +3.9 vs +20.8 samples. In portrait, both channels seem to come
  mostly from the bottom speaker. Unresolved; limits any 2-speaker × 2-mic direction gain.
- **Sensors:** game rotation vector, gyro and gravity all available (~60 Hz in Chrome, fine natively).
  Rotation tracking during sweeps was accurate (stops within ~3° of target).

## 4. Echo/range results

- Single-spot echo ranges are crisp and repeatable. In the kitchen test (phone ~10 cm above the stovetop on a coffee
  container, wall ~0.3 m behind, range hood above, ceiling ~2 m), the ranges matched plausibly: 0.29–0.37 m ≈ back
  wall (seen by both mics), 0.45–0.65 m ≈ hood/clutter, ~1.9–2.0 m ≈ ceiling. Distances unmeasured, so plausible
  but not verified.

> **Correction (2026-11-14, late):** the 2-spot sweep (`sweep-20261114-134133`) was recorded in the user's
> **living room** (less clutter), not the kitchen. Only the earlier single mic test (run 2) was on the stove.
> Everywhere below/above that calls the sweep "kitchen" means the living room. The "stove nook isn't a rectangle"
> explanation for inconsistent distances is therefore wrong.

## 5. Direction / mapping results (the open problem)

**First room sweep** (kitchen again, 2 spots × 8 stops at 45°, rotate in place; spot 2 = slid ~1 ft to the user's
right, not rotated, so its frame = spot 1's end orientation, ≈ +44° clockwise). Capture quality: excellent (all
stops on target, gyro ≤0.016 rad/s during capture, phone level, sweep align conf 2600–4700).

Analysis pipeline (`analysis/sweep_map.py`):
1. Log-sweep deconvolution → broadband IR per mic (300 Hz–16 kHz), analytic, ×4 upsampled.
2. Align every IR on its direct path; subtract the per-spot mean IR across stops. This removes anything
   rotation-invariant: direct path, phone body, stand, and largely ceiling/floor.
3. Back-project onto a horizontal grid using each stop's yaw and the mic/speaker geometry; r² spreading gain.

Results:
- Coherent cross term `Re(a1·conj(a2))` → aliasing fringes (14 cm spacing ≫ λ at kHz). Not usable.
- Envelope product `|a1|·|a2|` + per-range contrast → **crisp rings, weak direction** (only partial arcs).
  Rotating in place leaves every range unchanged, so direction comes only from the ≤±20-sample inter-mic delay,
  blurred by envelope width and a front/back (mirror) ambiguity.
- **Combining spots** (`combine_spots.py`, Hough voting over wall lines (φ, ρ), using that a wall's
  perpendicular distance changes by n·Δc when the phone moves): **inconclusive.** Control rotations
  (90/180/270°) scored as high or higher than the true setups. The best-fitting slide direction
  (`scan_offset.py`) was toward the phone's *left* (240–315°), but the user reports the phone's top pointed away
  from them, so their "right" = the phone's right (≈90°), which was among the *worst* fits. The hint was chance.
- Interpretation: with weak per-spot direction, combining is effectively range-only. With one ~30 cm move in a
  cluttered kitchen, unrelated echo ranges pair up by coincidence.

## 6. Why direction is hard here (physics)
Direction precision scales with the spread of the listening positions (the aperture). The phone gives 14 cm.
Rotating in place keeps the aperture at ~14 cm and doesn't change any echo's range. Separate tones from both
speakers don't add independent information: the speakers are ≤14 cm apart and seem to share the bottom
speaker; interference between two close sources gives aliased lobes, the same information as TDOA.
Bigger effective aperture = moving the phone to **known** positions (synthetic aperture).

## 7. Options going forward (my estimates)

| Option | Effort for user | Est. chance of a recognizable wall layout |
|---|---|---|
| A. Slide sweep: tape measure, ~8 known positions on an L path, 1 rotation each | High (user finds it too tedious) | ~60% |
| B. **Orbit sweep:** phone on the rim of a rotating base (lazy Susan, or a board pivoting on one point), radius 20–30 cm. Positions follow from gyro yaw + known radius, no tape. 12–16 stops = a 40–60 cm circular aperture | Low (same as current sweep + one setup) | ~50–55% |
| C. Fewer slide positions (4 on one line + 2 perpendicular) | Medium | ~45% |
| D. Keep rotate-in-place; improve processing (per-echo GCC-PHAT, ultrasonic phase tracking, 3rd channel) | None | ~30–40% |
| E. Range-only + user-supplied layout hints (e.g. "room is a rectangle") | Low | ~50% for a rectangular shell, poor for furniture |

My recommendation: **B (orbit sweep)**. It keeps the user's preferred static, guided workflow, needs no
measuring, and enlarges the aperture 3–4×. Also do the first validation in a sparse room with tape-measured
wall distances, not the kitchen. The handoff's 55% for a clean shell still seems about right, conditional on
a bigger aperture.

## 8. Known issues / to-dos
- App resets its yaw at each spot and stores no absolute yaw, so spots aren't in one frame. Must fix before any
  multi-position capture (store the raw game-rotation yaw continuously; record the commanded move).
- Speaker routing (is "L" really the earpiece?) unresolved. Could test with a one-speaker-at-a-time capture
  while the phone is in landscape, or via `AudioDeviceInfo` / routing APIs.
- ch3 of the 3-channel capture unidentified.
- Ultrasonic band is audible to the user (fine for static capture, but don't rely on "inaudible").
- Analysis assumes the speaker sits at the phone's bottom edge (~1 cm uncertainty) and rotation about the phone
  centre (hand rotation can shift ~1 cm).
- Leftover: an unneeded branch `feature/echo-diagnostic` in the user's Claude-Relay repo (pushed before the
  project moved to its own repo). Safe to delete when the user OKs it.

## 9. Process notes (mistakes and fixes, for transparency)
- An early commit to the Claude-Relay feature branch swept in 40 LFS pointer files (no git-lfs on the PC).
  Rewritten within a minute; `main` was never touched.
- The app's first "best mode" summary picked CAMCORDER (processed). Fixed to prefer raw UNPROCESSED.
- I briefly advised placing the phone face-down; corrected (that muffles the earpiece speaker), raise it instead.
- The sweep design didn't keep spots in one frame, though combining them was the point of the 2-spot test.

## 10. User preferences observed
Wants autonomy in this dedicated repo (push to main to make things testable, no per-step permission asks).
Prefers static capture. Often on the phone: keep replies lean. Not comfortable with device/dev setup, so do it
for them where possible. Wants honest confidence estimates.

## 11. Update after review (same day): simulator + rectangle wall fit

Acted on the reviewing instance's suggestions (sections 7–8 above are partly superseded):

- **Yaw frame fixed in the app** (not yet installed; phone was unplugged): yaw is tracked once per session, so all
  spots share one frame (`yawSessionDeg`, signed, clockwise-positive; `yawRawDeg`; yaw change during each move).
  The move prompt now says "slide without turning". Session format `echo-room-sweep v2`.
- **Scratch test** added (app → "Scratch test"): records 3 channels while the user scratches the top edge, bottom
  edge, camera bump and middle of the back, then reports which channel is loudest for each. Identifies ch3.
- **Simulator** (`analysis/simulate.py`): rectangular room, image sources to 2nd order + floor/ceiling, real
  mic/speaker geometry, phone-fixed body/stand taps, back-mic low-pass, noise, point-scatterer clutter, yaw and pivot
  jitter. Writes the app's exact session format, so the real pipeline runs unchanged.
- **Wall fit** (`analysis/fit_walls.py`): image-source model per stop and per mic (uses both the inter-mic delay
  and each mic's ±7 cm range swing; the reviewer's point 1), scored on IR envelopes, per-distance contrast to
  remove ceiling/floor rings. **Right-angle rectangle model:** orientation + 4 distances, scored on 4 wall echoes
  **plus 4 corner echoes**. Corners turned out to be the strongest returns (retroreflectors) and fooled the first
  per-direction version, which is why they're now part of the model.
- **Simulation results** (one spot, rotate in place, 8 stops, yaw jitter 3°, pivot jitter 1.5 cm):

  | Case | Orientation error | Distance error |
  |---|---|---|
  | Clean room | 1° | ≤0.5 cm |
  | + 5 / 12 / 20 point scatterers | 2–4° | ≤2 cm |
  | Room B (3.0×3.4 m, rotated 63°) | 5° | ≤0.5 cm |
  | Room C (4.5×5.5 m, far wall 4.1 m) | 2° | ≤1 cm (after raising the search limit to 5 m) |
  | 12 stops | 2° | ≤0.5 cm |

  Controls: a flipped yaw sign or mirrored mic frame still gives the right distances but a **mirror-image /
  rotated** layout, with ~18% lower score (8917 vs 7556). So the score can check the sign on real data.
- **Real kitchen sweep:** inconclusive, as expected. Spots disagree; normal vs flipped yaw within 4%; orientation
  sharpness 1.2–1.8 SD (sim 2.2–2.6); the known back wall at ~0.3 m is at the edge of the search range, inside the
  phone's own near-field. The stove nook isn't a rectangle around the phone.
- **Simulator limits:** no frequency-dependent absorption, furniture only as points (not planes/edges), no
  table/counter surface under the phone, no speaker directivity. Real rooms will be harder than the sim.

**Revised estimate:** rotate-in-place + rectangle fit in a sparse rectangular room: ~55–60% for correct room
dimensions, ~45–50% for correct orientation too. **Next:** one 8-stop sweep in a sparse room with tape-measured
distances to all 4 walls, plus the scratch test. Orbit sweep only if orientation fails.

## 12. Second review: two speakers (confirmed as a real error)

The reviewing instance found that the sweep plays from **both speakers**, while the fitter and simulator assumed
one. Checked here:

- **Simulator** now models the L channel as a second source at the top earpiece (`--earpiece <gain>`).
  Same room as before (12 scatterers, jitter):

  | L/earpiece gain | Orientation error, both-speaker sweep | Orientation error, R chirps only |
  |---|---|---|
  | 0 (one speaker) | 2° | 2° |
  | 0.5 | 8° | 2° |
  | 0.7 | 12° | 2° |
  | 1.0 | 12°; bottom-mic-only fit permutes the walls | 2° |

  Distances survive; **orientation** is what the second speaker damages.
- **Fitter:** `--source R|L` builds IRs from that speaker's 1–18 kHz chirps only (2 per stop, averaged);
  `--mics 1` = bottom mic only.
- **Kitchen data, R chirps only:** spot 1 and spot 2 **independently give orientation 3°** (walls square to the
  phone's starting direction). Flipped yaw: 8° vs 57° (disagree). Control: shuffled yaw-to-recording assignments
  (5 shuffles × 2 spots) give 12, 66, 26, 32, 68, 19, 83, 29, 70, 89°: no bias toward 0/45°, never agreeing. Chance
  of a ≤1° agreement ≈ 3%. So orientation appears recovered on real data for the first time, and the yaw sign is
  probably right. Distances still disagree between spots (stove nook ≠ closed rectangle; the back wall at ~0.3 m is
  inside the excluded near-field).
- **App (built, not yet installed):** sweep + ultrasonic now play from R (bottom speaker) only; the L/R 1–18 kHz
  chirps are unchanged. Session format `echo-room-sweep v3`.
- Note: there was no "new room" dataset yet when the review was written; the sparse-room test hasn't been run.

Still open from the review: back-mic first-arrival jumps (the median re-anchoring helps; raise the phone),
pivot drift (sim assumes 1.5 cm; a pin-through-cardboard pivot would help), and checking ranges against the
tape measure before orientation in the sparse-room test.

## 13. Third pass: retraction, timing jump, calibrated simulator, pivot drift

- **Retraction:** the §12 result "both spots independently give orientation 3°" is **withdrawn**. The R-chirp
  IR windows were misplaced: on the real recordings every chirp arrives **~1502 samples (31 ms) earlier** than the
  sweep-based timeline predicts. The shift is constant across all 16 stops and the chirps' spacing is exact, so it's
  a fixed jump in the phone's playback/record path between the sweep and the chirps (not clock drift). The simulator
  has no such jump, which is why the R-chirp method looked fine there. `chirp_irs` now locates each chirp with a matched
  filter (±80 ms search). The app should log AudioTrack underruns / timestamps to find the jump's cause.
- **Second speaker, measured with located chirps** (matches the reviewer): bottom mic: earpiece direct −18.9 dB vs
  bottom speaker, echo energy 0.10×; back mic: echo energy 0.40× (0.22–0.64), direct about equal (+1.1 dB). Back mic's
  earliest arrival varies 98–120 samples between stops (airborne ≈113): through-the-body/early paths, so
  `--anchor 16.5` pins it to bottom-mic direct + 16.5 samples.
- **Calibrated simulator:** `--earpiece 0.32,0.63 --chassis` (per-mic earpiece gains from the measured echo energy, plus
  body paths). With 3 cm pivot drift, the both-speaker sweep reproduces the real symptoms (sharpness 1.24, flipped gap
  −3%).
- **Pivot drift is the dominant factor** (`analysis/pivot_grid.py`, 4 seeds per cell, 8 scatterers, 3° yaw jitter,
  calibrated two-speaker sim; "correct" = orientation ≤6° and every wall ≤6 cm):

  | Pivot drift | Both-speaker sweep | R chirps + anchored back mic |
  |---|---|---|
  | 0.5 cm | 4/4 (≤2°) | 4/4 (≤2°) |
  | 1.5 cm | 1/4 | 2/4 |
  | 3.0 cm | 2/4 | 2/4 |

  The second speaker matters much less than keeping the rotation centre fixed to within ~0.5 cm.
- **Real sweep with corrected chirps + anchoring:** still inconclusive (spot 1 9°, spot 2 66°; flipped ≈ normal).
  Consistent with hand-turning drift of ≥1.5 cm.
- **Next capture must use a fixed pivot** (e.g. a pin/thumbtack through cardboard under the phone's centre, or the phone
  taped to a plate that turns on a pin) **and the bottom-speaker-only sweep** (app v3, built, not yet installed). Then
  check the ranges against the tape measure first, orientation second.

## 14. Lazy Susan support (in progress, stopped by user)
- Simulator `--pivot ox,oy`: phone centre offset from a turntable axis. Fitter `--pivot ox,oy|auto`: automatic pivot search
  (peakiness shortlist, then the rectangle score with local refinement); no measuring needed.
- With the true pivot, all simulated lazy-Susan setups (centred, 18 cm off-centre, diagonal) fit exactly (20°, walls exact).
  First auto-search (peakiness only) was biased 1.5–4.5 cm; switched to the rectangle score: case "18 cm off-centre"
  then found the pivot within 1 cm, orientation within 4°. Full validation (`analysis/lazy_susan_check.py`) was stopped
  before finishing.
- App (built, not installed): "Turning with: Lazy Susan" mode (default; 1 spot, 12 stops), full-screen centre cross,
  lazy-Susan voice prompt. No inputs to fill in.
- Realistic ceiling of this approach: a plain rectangle (dimensions within a few cm, orientation within a few degrees),
  ~55–65% odds in the living room after another round or two of fixes; furniture unlikely.

## 15. Live sonar radar (app)
- "Sonar radar (live)" screen (`android/app/src/main/assets/sonar.html` + native ping loop in `MainActivity`):
  looping static AudioTrack ping (R/bottom speaker) every 3200 samples (15/s), continuous UNPROCESSED stereo recording
  into a 2 s ring buffer, JS reads the latest 4 periods, averages 3 pings, matched filter, direct path = time zero.
- Display: radar circle painted along the gyro heading (±10° wedge, ~3 s fade), nearest-echo readout + bar.
  Settings: ping (Strong 2–12 kHz audible / Quiet 16–22 kHz), sensitivity (−34/−38/−42 dB re direct, 1/r-compensated),
  range 3/5/7 m, hide-closer-than 0.3/0.5/0.8 m. Volume held at 80% while running; stops on app pause.
- Lessons from the on-device check: the near-ultrasonic ping was ~−51 dBFS at the mic (speaker weak above 16 kHz), so
  "Strong" (2–12 kHz, +34 dB) is the default; r² gain was wrong for amplitude (now 1/r); "smart" detection hid echoes in
  clutter, so it's a plain threshold like a real sonar. WebView needed a WebViewClient for in-app navigation.
- Verified on device: runs ~12–20 ms/frame, paints echoes, nearest-echo readings 1.4–2.4 m by a desk. Not yet judged by
  the user in real use.

## 16. Related research
See [RESEARCH.md](RESEARCH.md) (2024–2026 papers and ideas ranked for this app).

## 17. Back-burner ideas (user's brainstorming, 2026-11-14) — not started
- **Per-direction learning with confidence** (~65% it noticeably steadies the radar, ~1 h): keep a running average per
  ~10° heading slice instead of fading each click; the longer you point somewhere the cleaner it gets; show a confidence
  number/shading per direction; learned picture also makes changes (door, person) stand out. Needs reset on moving.
  Runs alongside the clicks, not as a separate pass.
- **Ambient-noise learning/subtraction** (fans, hum): small gain in normal rooms — noise is already 80–93 dB below the
  click vs echoes at 40–50 dB, and Quiet (long) is above most fan noise. Could matter in noisy rooms / Strong mode
  (per-direction CFAR threshold, spectral weighting). Low priority.
- **Funnel / horn on the bottom edge** (~60% visible gain in Quiet (long)): paper test first. Protocol: stand ~2 m from a
  wall, Quiet (long), Start, slow full turn (~20–30 s), Stop; repeat with the funnel; compare logs (angular width of the
  wall echo, floor/ceiling rings, consistency). Funnel taped to the phone's edges, extending past the bottom, screen and
  back mic uncovered. With a funnel, the back-mic ahead/behind check should probably be switched off.
- **Cycling ping bands** (frequency diversity): cross-confirm echoes seen in several bands; an inaudible variant would
  cycle within 16–22 kHz.
- From RESEARCH.md: track echoes over time; subtract the phone's own direct/body signal; ARCore pose for room mapping.
- **Three-mic experiment** (2026-11-17 discussion): phone held flat, bottom edge forward (upright/on-edge rejected).
  Third (camera-bar, downward-facing) mic adds: floor/ceiling vs wall labelling from the body shadow (~55–65%, untested),
  3-mic combined signal (~2–4 dB), three-pair timing consistency check to mark bad echoes "unsure". Little left/right
  (only ~1.5–3 cm off the long axis); turning resolves left/right mirror ghosts instead. Grip: normal hold, fingers off the
  camera bar (a small hold diagram). Waits until the two-mic Map view is judged.

## 18. Map view (2026-11-17) — built, untested on the phone
- View → **Map**: occupancy grid (Moravec & Elfes 1985) in the room frame, 5 cm cells, ±7.6 m. Each echo adds evidence
  on its distance arc, weighted by the click beam (strong ahead) and by how well each direction fits the two-mic timing
  (mirror directions fit equally; turning sorts them out); each click removes a little evidence along its beam (±24°)
  closer than the nearest echo. Echoes at the same distance in ≥85% of headings turned through (0.6–2.2 m, not timed as
  ahead) are treated as floor/ceiling and kept off. Phone assumed 25 cm in front of the turning axis.
- Smooth walls echo at their perpendicular distance from many headings, so walls build up where you pointed straight at
  them (blurred near corners). Simulated room (4 walls, floor echo, 30% junk echoes, 2 turns): all four walls at the
  right distances, floor ring removed, some arc ghosts at corners. Real-world result unknown.
- App now opens straight on the sonar; the old test screen is behind the "Tools" button (also used for adb autorun).
