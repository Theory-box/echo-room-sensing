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

## 19. Audit (2026-11-17): own review + independent agent review, fixes applied — built, not yet installed
- From the user's Map-view logs (9.5 min, Quiet (long)): **47% of echoes had a physically impossible mic lag** (|lag| > 21
  samples; max for 14.3 cm is 19.9) — they piled up at the ±24–26 search limit and were then labelled ahead/behind with
  full confidence. Older Mid logs show the same (45%). Cause: plain envelope products let a bigger neighbouring echo in the
  back mic win. Fix: normalized (Pearson) envelope correlation per shift; the direction is trusted only if the back mic
  heard it (≥10 dB), |lag| ≤ 21.9 and shape match ≥ 0.6 and no second shift fits almost as well; otherwise "unsure".
  Synthetic check: 4 of 5 cases correct; the 5th (a 4× louder echo 7 cm away in the back mic) is a real two-mic limit.
  Log entries gain a 6th field (shape match).
- Direct-sound "mic check" lag varies 2–26 samples across sessions (expected constant): likely sound through the phone
  body + grip; treat that check as weak.
- Map: floor/ceiling echoes no longer stop the "seen-through" clearing (both reviews); floor/ceiling evidence is now a
  fading per-sector fraction instead of bits that only accumulate; free-space rays spaced by distance (no skipped cells);
  unconfirmed echoes no longer paint arcs behind you; changing ping/rate/volume keeps the map and start heading.
- Quiet (long) at 15 clicks/s + 7 m: the sweep is shortened so the full range + a noise stretch always fit (range was
  silently cut to 5.7 m and the back-mic noise came from one sample). Back-mic noise falls back like the bottom mic's.
- Android: no start while the app is paused (pause race could leave it pinging in the background); page pause handler
  also stops the native side; headphones/Bluetooth connected mid-session stop the sonar (it previously only checked at
  start); record thread catches errors, can't write into a newer session's buffer; base64 encoding moved out of the lock.
- Not changed (minor/by design): display lags the turn by ~0.2–0.5 s; dead landscape CSS; background JS polling.
- **Follow-up from the user's post-fix session (2026-11-17, Quiet (long), 8 clicks/s):** still 27% impossible lags, and
  the lag of the same echo at the same heading (±3°, frames ≥5 apart so no shared clicks) differs by a median of ~14
  samples (random over ±26 would be ~17). An older Mid session (2026-11-14) gave ~6.6. Consecutive frames looked
  repeatable only because they share folded clicks. Conclusion: at 16–22 kHz the two mics (14 cm ≫ 1.7 cm wavelength)
  hear different mixtures of reflections, so per-click timing carries almost no direction there. Direct-sound lag was
  tight (median 4, IQR 2.8–5.2) → channels are aligned; not a capture bug.
- Change: in Quiet (long) the timing is no longer used — echoes are direction-unknown ('?' in logs), painted normally,
  the distance readout uses all echoes, "Clean (ahead only)" isn't offered, the mic check isn't shown, and the Map uses
  the beam + turning only. Strong/Mid keep the checked timing. Implication for the third mic: in Quiet use its loudness
  (body shadow), not timing.

## 20. Full-sweep test mode (2026-11-17) — built, untested on the phone
- Ping "Full sweep 2–22 kHz (audible, test)": one long linear sweep (half the click period, 10% edge ramps). Distance
  from the whole band (~20 kHz → ~0.9 cm resolution vs ~2.9 cm for Quiet); two-mic timing from the sweep's 2–8 kHz part
  (same start sample, so same indices) where wavelengths are 4–17 cm. Adaptive sensitivity like Quiet.
- Echoes are separated from the still-playing sweep by the matched filter (pulse compression), as Quiet (long) already
  does, so a long sweep is fine.
- Synthetic check (wall 2 m ahead at +15 samples, 3 m behind at −15): distances 1.99/3.01 m, lags ±14.7, labels a/b.
  Open question for the phone: whether the low-band timing is consistent between clicks (Quiet's wasn't).
- Back-burner (user, 2026-11-17): **trace echoes between the mics** (match each echo's arrivals across mics, and later
  the third mic, to clean the data). Only after the current modes are polished.
- **Full sweep now alternates up/down sweeps and self-equalizes** (2026-11-17). Loop = one up + one down sweep; each is
  matched-filtered separately, normalized to its own direct sound and averaged (movement shifts the two in opposite
  directions). At each Start, ~6 clicks of a flat sweep measure the received energy per 2 kHz band (bottom mic, includes
  grip); the sweep then spends time ~1/|H| per band (half-way whitening, capped ×4 / ×0.25), and restarts automatically.
  Weights are saved in the log ("eq"). Synthetic checks: distances/labels correct at 2, 8, 15 clicks/s; flat response →
  only the ramped edge bands boosted; simulated weak highs → highs get up to ~2× more time.
- **Reverted (same day) after the user saw worse results + two audits:** Full sweep is back to a single flat linear
  up-sweep (+ low-band two-mic timing). Findings: (1) independent audit, simulated: a DOWN-sweep moves the speaker's
  harmonic distortion to after the direct sound (k-th harmonic lag ≈ (k−1)(f1/rate − t)), smeared ~2–12 m and timed like
  the direct sound → false far "ahead" echoes; up-sweeps put it before the direct sound (standard in swept-sine
  measurement, Farina). (2) Equalizer: the measured weights spread 16:1 (speaker very weak >16 kHz at the bottom mic);
  any rebalancing cost 2–8 dB of echo energy here, and stepped band weights raised range sidelobes; its edge bands were
  also over-boosted ×1.6 by the taper. (3) clickIdx in the pair path fixed (d % PERIOD). Code kept behind flags
  (updown / eq), off. The user's log of the eq version: weights [2.22,1,.86,.25,.25,.25,.75,4,4,4], 48% of echoes >3 m.
- Back-burner: two speakers (bottom + earpiece) with separable signals (MIMO): ~doubles the ahead/behind baseline, no
  left/right, not for Quiet; earpiece weak.

## 21. Ideas for later (theory discussion 2026-11-17) — nothing built, no tests planned yet
- **Micronavigation = the foundation.** Estimate the phone's tiny movement between clicks from its OWN echoes (as
  synthetic-aperture sonar does with overlapping receivers / "displaced phase centre", plus autofocus), with the gyro
  for rotation and the accelerometer for short moves. Unlocks: (a) correct placement of echoes in today's Map (replaces
  the fixed ARM = 25 cm assumption → less blur from body sway); (b) motion-compensated averaging (align clicks before
  folding → stronger faint echoes); (c) approach speed per echo (collision warning, moving vs still); (d) walking
  odometry (+ step counter, + echo fingerprints to fix drift, cf. BatMapper / ELF-SLAM) → walk-around room maps;
  (e) synthetic-aperture imaging. Needs fast clicks for phase tracking: unambiguous speed ≈ λ/(4·click interval)
  (Quiet 8/s ≈ 3.4 cm/s; 4 kHz part of Full sweep at 15/s ≈ 32 cm/s).
- **Correction (checked with clean click pairs, no clears/room changes):** the Quiet inconsistency is BETWEEN the two mics
  (Quiet ~12–15 samples, Full sweep ~4–5). One mic compared with itself across clicks should stay coherent when the phone
  barely moves — that is what micronavigation / backprojection need. Untested.
- **Backprojection (time-domain, as in SAR/SAS):** grid of the room; for every click and every cell add the click's echo
  value at that cell's round-trip distance from the phone position. Magnitude-only = triangulation (fallback); with
  phase = coherent, sharp to ~λ/aperture. Smooth walls are built only by the clicks that face them.
- **Lazy Susan mode:** phone taped off-centre (bottom edge out), turned freely by hand (pauses / backwards fine), gyro
  gives the angle → known circular aperture (UW 2026 turntable preprint did this with the object rotating). Expect a 360°
  top-down outline from one spot, walls within ~10–30 cm at 2–3 m; up/down still ambiguous; coverage tracking with a
  faint "this direction is done" sound. Odds: sharp ~45–55%, fallback beats today's Map ~75%. Handheld sharp version
  later via micronavigation + autofocus (~20–30%).
- Other parked ideas: echo feature detectors from Full sweep (hard/soft by high-vs-low pitch, smooth/rough by echo
  spread, corners by persistence across headings, small objects by high pitch); continuous ~20 kHz tone as a motion
  layer; Doppler beam sharpening; interference-pattern sampling (one moving mic + fixed reference = virtual array);
  user-supplied mouth clicks as a source (works, ≈ Strong mode). Rejected with reasons: 96 kHz (phone's speaker and mic
  routes are 48 kHz only; speaker weak >20 kHz), system ultrasound path (privileged; same speaker, same 48 kHz route),
  combining speakers/mics for higher rates (anti-alias filters, linear superposition), exotic sound shapes (a still
  room is linear: any full-band sound measures the same response).
- **Log v2 (2026-11-17):** events (start / restart with full settings, stop by user or system + reason, clear,
  every setting change, stalls, errors, eq) with wall-clock times; every frame carries seg (new at each Start and Clear —
  analyse within a segment only), raw yaw, direct-sound level (drift = speaker protection?), noise, threshold, gyro rate,
  tilt (pitch/roll from gravity), processing ms. Long sessions are saved in parts (nothing dropped).
- **Micronavigation step 1 (2026-11-17): per-echo approach speed — logged only.** For each echo, the separate clicks
  inside one reading (2–4) are matched-filtered individually (bottom mic); per click the envelope peak (tracked click to
  click) gives a coarse delay and the phase at the peak the fine one (one carrier period = SR/fc samples; fc 19 kHz
  Quiet, 7 kHz Strong, 12 kHz Mid, 5 kHz = low part of Full sweep); coarse picks the whole periods. Log adds per echo
  [speed cm/s (+ = closer), consistency, source p = phase / e = envelope fallback / x = lost]. Simulated moving wall:
  correct within ~1–5% from 2 to 30 cm/s in every mode, still wall 0; at 60 cm/s (walking) it loses track and says so
  (the folded reading smears; walking needs unfolded tracking later). Not yet used for display or the map.
- Holding the phone: not learned (user decision). Rule of thumb: hold it in front with a relaxed arm; side holds blur
  walls ~10–20% at 2–4 m. Revisit only if micronavigation shows a big gain from knowing the hold.
- **First real test of approach speed (2026-11-17, Quiet, 15 clicks/s, walk toward a wall and back, then a turn):**
  echoes fixed relative to the phone (body/hand 0.34 m, floor ~0.85 m) read 0 at high consistency all session; walking
  toward the wall read +12…+15 cm/s while its distance fell 1.75 → 1.13 m (~18 cm/s), standing still 0, walking back
  −12…−13. Problem: 95% of phase-based speeds sat on multiples of the 13.5 cm/s wrap quantum (Quiet at 15/s), and some
  still walls read ±13.5 → the per-step envelope unwrapping is too noisy in a real room.
- **Fix:** whole-turn choice from (1) the echo's recent track (matched within 6 cm, < 0.6 s; dropped if the envelope slope
  disagrees by a full turn) else (2) the least-squares envelope slope over all clicks in the reading; phase steps taken
  within half a turn of that prediction. Log source 't' = turn from the track. Harsher simulation (moving clutter next to
  the wall, more noise): new version correct for 0, ±15, 25, 6, 5 cm/s (Quiet) and 30 (Full sweep); the old version
  failed 25 cm/s completely and partly −15. The exact real symptom wasn't reproduced in simulation → needs a real retest.
- Click rate: wrap quantum = λ/2 per click → lower rates make speed MORE ambiguous (Quiet 3.6 cm/s at 4/s, 13.5 at 15/s;
  Full sweep low part 14 at 4/s, 54 at 15/s). Use 15/s for motion work.
- **Second real speed test (2026-11-17 22:03, Quiet 15/s, 77 s):** still snapped to multiples of 13.5 cm/s. Root cause
  (= standards item 1): the app folded RAW clicks before the matched filter, so an echo survived only if it moved a
  whole wavelength-step between clicks (0, 13.5, 27 cm/s…) — a stroboscopic filter on what gets detected at all.
- **Fix: non-coherent averaging.** Each click is compressed separately (complex correlation in one FFT pass, template
  spectrum cached) for both mics (and the low band for Full sweep), and the ENVELOPES are averaged. The fold is kept only
  for the direct sound (time zero) and the mic self-check. Fast turning now keeps 2 clicks (was 1) so speeds still work.
  Simulation (Quiet 15/s, moving wall): detected in 46/46 frames at 0, 6.75, 10, −20 cm/s (old: 46, 6, 34, 28 of 46) with
  correct speeds; Full sweep 30 cm/s and Strong fine. Cost: noise averages less than with the coherent fold (static
  echoes may be ~2–3 dB weaker in noise-limited cases). Needs a real retest.
- **Third real speed test (22:11, after non-coherent averaging, 164 s, two clears):** walking toward the wall the echo went
  2.44 → 1.21 m (~25 cm/s) and speeds spread +18…+35; still = solid 0; walking back −14…−28. Snapping to 13.5 multiples
  among moving readings fell 80–84% → 46% (chance ≈ 22%). Leftovers: some ±13.5 jumps on still walls, a few wild values
  (−568) from echo mix-ups → echo tracking (next). ~28 ms/frame at 15/s. User: "seems to work pretty well".
- **Near-zone static removal (2026-11-17):** per click, complex response ÷ its own direct sound; running average (mean
  for the first clicks, then α 0.04 ≈ 25 clicks) per mic within 0.6 m, fading to nothing by 0.75 m; residual envelope
  replaces the plain one there. Reset on start/restart/clear. New "Hide closer than 0.15 m" option. Frames log bg = 1 when
  active. Simulation: still body echo 0.34 m removed in Quiet/Full/Strong; moving hand ~0.45 m detected 28/31 (was 14/31)
  Quiet, 16/16 (was 8/16) Strong, 31/31 (was 13/31) Full; still wall 2 m and moving wall unaffected. Expected side effect:
  after a grip change, ~1–2 s of near-zone junk while it relearns.
- **Audit round (2026-11-17, mine + independent agent with its own simulation harness) — fixed:**
  1. each click was processed/learned ~3× (overlapping readings) → per-click results cached by absolute sample number:
     compressed once, taught to the near-zone background once (also ~3× less FFT work);
  2. time zero re-picked every reading could flip by one sample (direct sound near half a sample) → misaligned near-zone
     background → false near echoes (Full sweep: 29/30 frames) → time zero locked to the sample-locked click loop
     (median of first readings, re-learn only if off > 2 samples for 10 readings), background reset when it changes;
  3. speed "fully reliable" with only 2 clicks (4/s, fast turns) → one step = unverified (below the 0.5 bar);
  4. echo leaving the ±8-sample click-to-click search, or > 6 samples/click → 'lost' instead of confident-wrong speeds
     (search centre now follows the track's expected shift);
  5. near-zone speeds now use the background-removed response;
  6. heading timestamp used the wrong click centre (off by half a click);
  7. log: setting change now recorded before the restart it causes; a failed save keeps the data and says so;
  8. Java: non-finite sensor values sent as 0 (invalid JSON would break every frame).
  Harness results after fixes: no false near echoes at integer/half-sample offsets in Strong/Full/Quiet; walls intact;
  speeds correct where trackable; confident-wrong speeds: 4/s Full sweep 24 → 0, Strong 4/s 20 → 0, walking (1 m/s, Full
  sweep 15/s) 12 → 5 of 36 (mostly 'lost'; walking needs another method). Not changed: at 2 clicks/s there is one click per
  reading (no speeds); restarts don't start a new segment (split analysis on 'restart' events).
- Later: compare against open-source projects (LLAP Android code; pyroomacoustics for simulated rooms).
- **Hand/desk test of near-zone removal (22:29, 12.6 s, Quiet 15/s, hide 0.15 m):** no constant near junk 0.2–0.8 m
  (previous logs always had ~0.34 m body/hand and often ~0.85 m); real objects at ~0.97 m and 1.4–1.75 m kept; a few
  0.16–0.20 m hits (hand very close, or a residue at the direct-sound edge) — inconclusive. Default "hide closer than"
  left at 0.5 m pending a deliberate hand check (proposal: 0.3 m).
- **Echo tracking (2026-11-17):** tracks with id, alpha-beta distance + speed (phase speed when reliable), gate 6 cm +
  expected movement, nearest-first assignment. Confirmation = ≥ 3 hits spread over more than J+1 readings (readings
  overlap by J clicks, so a one-off junk click appears in exactly J back-to-back readings); coast up to 4 missed
  readings (faded). Radar + distance readout use confirmed tracks; the Map, distance graph and log keep all detections
  (the Map is its own temporal filter). Log per echo: track id, confirmed, track speed; per frame nt, co.
  Simulation (two walls, one moving 15 cm/s, junk echo in 40% of clicks, 10% wall dropouts): junk shown per frame
  Strong 0.63 → 0, Full sweep 0.94 → 0.13; walls 52/52 kept; Quiet (faint, detected in only 30–50% of readings in this
  simulation) keeps ~60–75% of wall frames — a first "seen 3 of 5" rule had hidden them completely (rejected).
- **Echo tracking — real tests (2026-11-17 23:44–23:48, 6 sessions, ~4.5 min, Quiet 15/8 per s + Full sweep):** radar
  set changes per frame 0.65–0.87 (raw) → 0.12–0.19 (shown), nearest-distance jumps > 20 cm 14–24 % → 4–7 %; 25–35 %
  of raw detections never confirmed (mostly junk; some faint real far echoes near the range edge); readout present
  slightly less often (e.g. 90 → 86 % of frames). A 0.16 m echo (just past the 0.15 m mask) shows only in the first
  3–7 s after Start. User: "works better than it used to".
- **Straight walls in Map view (2026-11-18), setting "Walls: Straighten / As heard (arcs)", Map view only, all pings:**
  regions of constant depth (Leonard & Durrant-Whyte 1991). Detections grouped by distance (not track id: faint walls'
  tracks break up) with the arm-offset dip allowed (ARM·(1−cos)); region ends after 15° of turning (or 3 s) without
  it; needs ≥ 5 detections (≥ 3 confirmed), span 12–150°, and its first edge must have been looked past (a wall faced
  at Start is cut off). Direction = echo-power-weighted mean heading; D = mean(r + ARM·cos(h − mid)). Same wall again
  (≤ 15° & 12 cm, or ≤ 30° & 6 cm) merged. Floor/ceiling hidden: map ring check, a region > 150°, or ≥ 3 regions at
  the same distance (± 5 cm, 0.6–2.2 m) pointing into 3+ different 45° sectors. Line length is a guess (from span,
  capped 1.2 m half-length). Log: nw per frame, rcd = ended regions. Simulation (4 walls, floor echo, junk in 40 %
  of clicks, 20 % dropouts, 9 cases incl. 8/15 per s, Strong/Quiet/Full, turning 20–60°/s both ways): 33/36 walls
  found, direction error median 1.8°, worst 5.6°, distance ±2 cm; span midpoint instead of power weighting was
  3.0° / 20°. ~1 false wall per case remains (sim multipath at fixed distances). A harness bug (heading reference)
  first looked like a 5–7° lag; it wasn't the app. Untested on the phone.
- **Straight walls — audit (2026-11-18), own + independent agent:** fixed (1) walls drawn rotated when the map is
  cleared mid-session (e.g. switching to Map view while running): the unwrapped heading now restarts at the current
  heading; (2) the "cut off at Start" rule could accept a region with one fake edge: now both edges must have been
  looked past by ≥ 5°; (3) a region's samples are thinned when standing still (bounded memory); (4) the region's
  nearest distance can't creep down beyond what the arm explains; (5) floor lists deduped/capped; (6) long-log part
  save moved after the Map fields are written. Not changed (nits): open regions aren't logged at Clear/Stop; merging
  takes the first matching wall; toggling Walls while stopped redraws only on the next reading. Simulation unchanged
  (33/36, median 1.8°, worst 5.6°); map cleared mid-turn: walls still correct.
- **Wall test (2026-11-18 00:24–00:35, Quiet 15/s, one spot per segment, Clear/Stop between spots):** same wall
  re-found on later passes within 5–8° typically (90 %: 12–15°); no turn-direction bias (opposite-turn pairs −0.5°
  mean), no heading drift (−1.2°/min). So the misalignment is random (hold/sway, uneven beam, clutter), not timing.
  User: "seems to work very well, especially for quiet… definitely not perfectly aligned, but decently happy".
- **"Fewer fake echoes" (reference windowing / noise CFAR) — investigated, NOT built (2026-11-18).** Ideal range
  sidelobes: Quiet/Strong/Mid (Hann-tapered pings) already < −48 dB beyond 10 cm; only Full sweep (10 % Tukey) has
  −23/−40 dB sidelobes (a receive Hann window would cut them ~20 dB). Real logs (all since 23:44): unconfirmed
  detections (likely fakes) are mostly > 1 m from any stronger echo, only ~2 dB weaker when close (sidelobes would be
  20+ dB weaker), echo-of-echo ~1 %, and sit 14–20 dB above the measured noise floor (confirmed: 17–25) — i.e. real
  but non-repeating reflections (clutter, reverberation, glancing surfaces), not sidelobes or noise. A noise-based
  CFAR at 14 dB would keep 90 % of them (and 98 % of confirmed). Tracking already handles this kind on the radar.
  Revisit only with raw profiles (CA/OS-CFAR against local reverberation) — can't be judged from current logs.
- **Regression sim, all pings × click rates (2026-11-18):** Quiet 2/4/8/15, Strong 2/4/15, Mid 4/8/15, Full 4/8 —
  no errors; walls 47/48 found, direction median 2.6°, worst 10.6° (Quiet 4/s); wall echo present in 59–96 % of frames.
- **Raw echo profile in the log (2026-11-18, build "raw profile").** Every frame now carries `p`: the main mic's
  level for each 3 cm distance step, whole dB re the direct sound, before threshold / 1/r compensation, floored at
  −99 (~0.7 KB/frame, ~0.6 MB/min at 15/s). Purpose: judge an adaptive threshold (CA/OS-CFAR against local
  reverberation) offline against the tracker's confirmed echoes before building it. Sim: present in every frame,
  wall results unchanged (47/48, median 2.6°).

## Foundation review (2026-11-18)
Baselines from the real logs (since 2026-11-17 21:55):
- Distances were the CENTRE of a 3 cm step (every logged value on the grid) → up to ±1.5 cm (0.87 cm rms) before any
  other error; a still echo never changed step.
- Two-mic lag of echoes (Strong/Full sweep, back mic heard > 10 dB): almost flat over −24…+24 samples; class flips
  between consecutive readings of the same track 17 %; even the direct sound's own lag (should be constant) spreads
  8–23 samples (10–90 %). Front/back as built is close to uninformative. Quiet doesn't use it at all.
- Real beam (Quiet, 142 accepted walls): a wall faced squarely is detected in 48 % of readings, 24 % at ±20°,
  ~10 % beyond ±40° (clutter at the same distance).
Independent code audit (synthetic checks with the app's own functions) — bugs:
1. Linear-sweep range–Doppler error v·fc·T/B: Quiet long 4 cm per 10 cm/s at 4/s, 1.2 cm at 15/s; approaching = closer.
2. Distance at the bin centre although the peak sample is known.
3. removeStatic memory is ~25 CLICKS (1.7 s at 15/s, 6 s at 4/s, 12 s at 2/s) → ghosts of near objects after turning.
4. micLag window ±18 samples too wide for Strong/Full (a −3 dB echo 12 samples away flips ahead → side).
5. Full-sweep low-band timing envelopes skip the near-zone background removal; low-band template ends abruptly.
6. Noise gate 3× noise: passes 4 % of noise at 1 click/reading, costs 1.6 dB at 3.
7. Possible phantom at R + ~0.25 m (wall → body → phone), unchecked.
Literature (BatMapper, MobiSys'17): 1–2 cm (80th pct) to large perpendicular walls at 0.5–3.5 m with the same
matched-filter + envelope approach; two collinear mics give only the angle to the phone's axis (a cone) — every
published fix for the mirror ambiguity moves the device (rotation/slide = synthetic array) or adds a sensor.
- **Build "fine distance":** distance from the peak refined between samples (parabola) + the sweep's motion error
  corrected with the echo's phase-measured approach speed (capped ±15 cm; logged as e[12]); distances logged to 1 mm;
  every frame logs `fr` (recording sample counter); on Stop the last 20 s of both mics are saved as raw_audio.wav
  (float32 stereo) next to the log (ring buffer 2 s → 20 s). Sim (all pings × rates): echo distance error median
  0.1–0.8 cm, 90 % ≤ 1.7 cm; walls unchanged (47/48, median 2.6°). Not yet tested on the phone.
- **Build "motion direction" (2026-11-18): front/back from short-range phone motion — logged only, not drawn.**
  Prior art: Swadloon (2013) — phone shaking/walking + Doppler + accelerometer/gyro → direction (~2° to a source).
  Native: TYPE_LINEAR_ACCELERATION rotated into the room frame with the game-rotation-vector matrix, buffered with
  timestamps (`Native.motion()`). Page: phone velocity = leaky-integrated acceleration (fast part, τ 0.7 s, 3 s offset
  removal) + turning-on-the-spot model ARM·dψ/dt (slow part), complementary. Per tracked echo, least squares over
  1.5 s of (phase-measured approach speed, phone velocity over the same clicks): rho = v·u → u's forward/right parts and
  z-scores (|z| > 2.5 = sure). Forward = heading + 180 (bottom edge). Logged as e[13] + frame pv/na.
  Sim (true velocity + 2 cm/s noise + 1 cm/s bias; wall ahead 1.5 m, wall behind 2.2 m): a 1–2 cm forward/back push
  at 1–1.5 Hz → 100 % of echoes ahead/behind called correctly (Quiet 15/s, Strong 15/s; Quiet 8/s 63 % called, rest
  unsure); sideways push, no motion, or turning only → no wrong calls (unsure). Not tested: the real acceleration-based
  velocity (sensor latency/scale), timing alignment, moving people. Sim note: a near-noiseless sim puts Quiet's Auto
  threshold too high (needs real room clutter) — the motion sim uses High sensitivity.
- **First real test of "motion direction" (2026-11-18 11:39, Quiet long 15/s, High, 190 s of free sweeping with
  natural hand motion; not the structured wall test).** Accelerometer stream OK (~100 samples/s). Motion verdicts on
  21 % of echoes (rest unsure/no phase speed). Against walls the app found (echo at the wall's distance while facing
  it = truth "ahead"): 402 called ahead vs 158 called behind (72 % right when sure) — not usable yet. Diagnosis:
  echo approach speed vs phone forward speed correlate only 0.14 (one reading) … 0.24 (1 s smoothing), regression
  slope ~0.4 at every window; wall echoes' distance jitters 1–2 cm between readings (~±10 cm/s apparent speed; 5–95 %
  ±20 cm/s) against ~4 cm/s rms real forward hand motion; ~1 in 10 phase speeds slip one carrier turn (13.5 cm/s at
  15/s). Likely both sides noisy: echo jitter (mixed reflections / speckle at λ 1.8 cm, sway) and the
  acceleration-based velocity (tilt error leaking gravity during rotation: 1° ≈ 0.17 m/s²). Wall-distance
  repeatability across regions: median 3 cm before and after "fine distance" (different rooms) — the 1.5 cm rounding
  was not the dominant real error.
- **Controlled wall test (2026-11-18 11:52, Quiet long 15/s, High; one 56 s recording: wall ahead ~0.9 m, ~24 s still,
  then ~30 s of forward/back pushes at ~0.6–0.7 Hz; no "wall behind" part). Raw audio = last 20 s (pushing).**
  - Log: still, the wall echo distance spreads 9.4 cm (5–95 %, sd 3 cm) although consecutive readings change only
    0.3 cm. The wall is a broad hump 0.87–0.96 m (−3 dB; expected mainlobe ~3 cm) with 2–3 components ~4–6 cm apart.
  - Phone velocity from the accelerometer during pushes: same frequency as the echo (0.61 Hz), right sign and timing
    within ~0.2 s (sensor leads 221 ms), amplitude 0.56× the echo-implied speed → calibratable.
  - Raw audio, single clicks: wall echo 25 dB over noise (not noise-limited), yet click-to-click distance jumps ~3 cm
    (loudest point, −6 dB front edge and hump centre alike) and the hump shape correlates only 0.5 between
    consecutive clicks → speckle: overlapping reflections re-mix with mm motion at λ 1.8 cm. 1 s averages still wander
    86–95 cm. Carrier-phase tracking moves only 0.2 cm/click but loses track when the dominant component switches.
  - Two-mic timing of the wall straight ahead: lag spread −20…+21 samples (40 % ≥ +10, 26 % ≤ −10) with envelope shape
    match 0.96 — broad smooth humps correlate well at many lags, and the mics (14 cm = 8 λ) hear different speckle.
    Direct-sound lag is stable at 7–10 samples (recording fine). Loudness difference back−bottom: −24 dB for this
    wall vs −13…−18 for others, but in the free-sweep session walls ahead/behind gave −15.0 / −14.6 dB → no cue.
  - Offline frequency compounding (split the sweep into K pitch bands = time pieces, sum band envelopes in power):
    leftover jitter after removing the push sinusoid 3.9 cm (app: full band, 3 clicks) → 1.8–2.0 cm (K=2) →
    1.55 cm (K=4, hump centre, 3 clicks). Cost: coarser resolution (K=4 → ~11 cm). Scripts: analysis/raw_wall_test.py,
    analysis/raw_compounding.py. One recording, one wall — needs confirming.
- **Build "pitch bands" (2026-11-18): frequency compounding, setting "Pitch bands" 1 / 2 (default) / 4.** Each band =
  a time piece of the sweep (own Hann taper, zero elsewhere, so delays line up); bottom-mic envelopes beyond the near
  zone = power sum over bands, scaled to the full band at the direct sound. Near zone (static removal), back mic,
  speed/phase and two-mic timing stay full band. Raw wall recording: jitter 3.9 → ~1.8 cm (2 bands); wall stands out
  18.1 / 19.0 / 14.3 dB above the profile median with 1 / 2 / 4 bands; bumps over median+7 dB per reading 7 / 3 / 2.
  Sim (clean single reflectors, no speckle → only the cost shows): fewer threshold crossings in Quiet (−25…30 %), walls
  47 / 43 / 42 of 48, distance error still ≤ 1 cm median. Installed; not yet tested on the phone.
- **Pitch bands on the phone (2026-11-18 12:09–12:16, same spot, Quiet long 15/s, High, full turns; 2 / 4 / 1 bands,
  127 / 115 / 164 s).** Echoes per reading 3.83 / 1.95 / 2.42 (2 / 4 / 1 bands); confirmed share 70 / 70 / 62 %;
  same-track step between readings median 0.40 / 0.60 / 0.60 cm (90 %: 2.0 / 2.6 / 2.6); 1-s wobble sd median
  1.29 / 1.47 / 1.66 cm; walls per minute 32 / 22 / 34. → 2 bands best on every measure except walls/min (≈ 1 band);
  default stays 2.
- **OS-CFAR vs the current median threshold, offline on the logged raw profiles (same sessions).** Proxy: a detection
  is "persistent" if it reappears within ±6 cm in ≥ 3 of the 8 neighbouring readings. At matched persistent rates the
  OS-CFAR (±10 cells, 2 guard, 75th percentile) lets through more non-persistent detections: 2 bands 24 % vs
  13–18 % (median +5…+7 dB); 1 band 25–26 % vs 18 %. Reason: walls are 10–15 cm humps, so the local reference
  window measures the wall's own hump. Not built. Also: at median +7 dB, 2 bands give 2.04 persistent / 13 %
  non-persistent per reading vs 1.85 / 18 % with 1 band.
- **Build "sensor timing" (2026-11-18).** (1) Click capture time from AudioRecord.getTimestamp(TIMEBASE_BOOTTIME)
  (frame number ↔ capture time, same clock as sensor events) via `Native.sonarClock()`; falls back to the old
  "buffer end + 40 ms" estimate if unavailable or > 400 ms off; logged `tc` (page-clock capture time) + `cs` (c/g).
  (2) Heading samples stamped with the rotation-vector event time (`ya` = age) instead of the poll time.
  (3) Leaky-integrator crossover 0.7 → 1.2 s (0.6 Hz: gain ~0.92 → ~0.97, lead ~100 → ~60 ms). (4) Raw horizontal
  acceleration logged per reading (`ac`), so gain/delay can be fitted offline against echo-derived motion.
  Sims unchanged (walls 43/48 at 2 bands; motion cases 0 wrong). Installed; not yet tested on the phone.
- **Phone test of "sensor timing" (2026-11-18 12:37 push test 30 s, 12:38 sweep 54 s; both Quiet long 15/s, High,
  1 pitch band — left over from the comparison).** Capture clock used on every reading (`cs` = c); clicks are
  168–226 ms old when processed (median 197). Push test too gentle/irregular to calibrate: forward acceleration rms
  0.10 m/s² (peak 0.43; a 5 cm push at 1 Hz peaks ~2 m/s²) → accel-derived motion 0.15 cm rms vs wall-echo jitter
  1.2 cm; no clear rhythm; cross-correlation 0.22 at the edge of the lag range → gain/delay not determined.
  Still part: wall echo steady to 0.2–0.3 cm. Sweep vs the 12:14 1-band sweep (same spot): step between readings
  median 0.40 vs 0.60 cm, 1-s wobble 1.26 vs 1.66 cm, walls/min 45 vs 34 — better, but a short single session.
- **Motion calibration redone (2026-11-18).** My earlier "1–2 mm" was an analysis error: the band 0.4–2.5 Hz removed the
  real pushes (~0.3 Hz). With 0.15–1 Hz: accelerometer-derived vs wall-echo motion correlate 0.69–0.77, scale
  0.9–1.2×; acceleration double-integrated ≈ 4.6 cm peak-to-peak. The app's leaky-integrator velocity is the weak link
  for slow motion (0.6×, ~0.3 s extra lead).
- **Build "rough motion" (2026-11-18): front/back v2, logged only (e[14]).** Per confirmed echo, last 3 s: history by
  distance (nearest detection within 4 cm per reading, following drift); fit r(t) = c0 + c1 t + c2 t² − u·x(t), x =
  acceleration integrated twice from the window start (start velocity/offset absorbed by the line/parabola),
  acceleration timeline 120 ms earlier than the clicks; verdict only with ≥ 3 mm forward/back movement left after the
  parabola and |z| ≥ 2.5. On the two sessions it was tuned on (so optimistic): push test wall ahead 48 ahead / 2 behind;
  sweep, echoes from found walls ahead 37 / 6 (old method: coin flip), other echoes 4 / 2; most echoes "unsure".
  Replay of both logs through the app's JS reproduces it (48/1, 38/6). Needs a fresh session to confirm.
- **Fresh sessions with "rough motion" (2026-11-18 12:50–12:54, Quiet long 15/s, High; 2 / 1 / 4 bands Map 74 / 44 /
  73 s, then 4 bands Full view 92 s).** Front/back v2 on echoes from found walls ahead (fresh data, not tuned on):
  2 bands 364 ahead / 15 behind (96 % right, 36 % of them got a verdict); 1 band 55 / 30 (65 %); 4 bands 85 / 24 (78 %).
  No usable "behind" truth (walls behind are hardly heard; echoes at wall+0.5 m with your back to it were called ahead
  44 / 0 — probably other things ahead at that distance). Other echoes: mostly called ahead (2 bands 152 / 20).
  Band comparison vs the 12:09–12:14 sessions: echoes per reading 3.8 (2 bands) vs 2.3–2.4 (1) vs 1.4–2.0 (4) and
  confirmed share 68–70 vs 60–62 % — consistent; walls/min 76 / 53 / 21 (new) and 32 / 34 / 22 (old); but 1-s wobble
  1.81 / 1.63 / 1.43 cm (new) vs 1.29 / 1.66 / 1.47 (old) — session-to-session variation is as large as the band
  effect, so the steadiness gain on the phone is NOT established; the detection gain is.
- **Build "ghost walls" (2026-11-18): far walls drawn instead of the real near wall — fixed in the wall finder.**
  Cause (replay of 4 sessions through the app's own map + wall finder): the floor/ceiling rule (regions at the same
  distance ±5 cm in 3+ of 8 directions, over all regions of the session) marked nearly every distance 0.8–2.1 m as
  "floor-like" in real rooms, so real near walls were rejected/hidden, while their repeat echoes (often exactly 2× the
  near distance) beyond 2.2 m were exempt and drawn. Real sessions show no strong floor ring (best candidates in only
  33–67 % of directions). Fix: floor rule ±3 cm; plus walls aren't see-through — a wall is hidden if a nearer drawn wall
  faces the same way (±20°) or it sits at 2–4× a nearer region in the same direction. Replay: near walls accepted
  19 / 50 / 30 / 21 (was 14 / 26 / 18 / 14); drawn walls per session 6–10, mostly 0.8–2 m (was 20–29, many 2.4–4.5 m).
  Sim: walls 39 / 48 (was 43), false walls 5 (was 6) — the sim's floor reflector is far stronger than real floors and
  pieces of it occlude real walls. Installed; not yet tested on the phone.
- **Hum ("hologram") experiment (2026-11-18).** New ping "Hum (experiment: records only)": 16 steady tones
  17.0–20.75 kHz in 250 Hz steps (every tone repeats exactly every 192 samples), fixed pseudo-random phases, looped
  every 0.1 s; no echo processing, a light log every 0.1 s (heading, motion, recording counter, capture time), and the
  last 40 s of raw audio saved on Stop (ring buffer 20 → 40 s). Idea: every reflection arrives as a steady wave whose
  phase is measured continuously (250 values/s per tone, never losing count of cycles), so the phone's movement
  relative to each surface can be tracked to sub-mm. Closest prior work: LLAP (MobiCom'16, still phone tracking a hand,
  3.5 mm); no prior work found for a phone tracking ITSELF against the room. Offline analysis
  analysis/hum_hologram.py, on simulated audio: one dominant wall → path change tracked to 0.3 mm rms over 9 cm of
  motion; with surfaces ahead + behind of similar strength, a per-distance profile (inverse FFT across tones, 4.3 cm
  steps, repeats every 0.69 m) tracks each separately with the right sign (behind 0.09 mm, ahead 5 mm, side 8 mm).
  Not yet tried on real audio (speckle could spoil it as it did for clicks).
- **First real hum recording (2026-11-18 13:34, 33 s: facing a wall ~1 m, ~5 s still, ~20 s of natural movement,
  slow part-turn −18…+96°).** All 16 tones present, 71–83 dB over the background. The changing part of the sound is
  dominated by the phone's own direct sound (hand/grip shifting), ~34 dB below the static part. Away from the
  direct-sound slot (±6 of 64 slots), each slot's unwrapped hum phase follows the motion sensor's forward movement:
  correlation −0.6…−0.82 (strongest ~1.07 m mod 0.686 m ≈ the wall), path rms ~2 cm vs sensor 2.0 cm; negative sign =
  surfaces ahead (paths shorten moving forward). Median over slots: correlation −0.81, scale 0.64× the sensor, hum
  328 ms later than the acceleration (consistent with the ~0.12–0.3 s offset found earlier). While still: hum wobble
  0.4–1.2 mm sd (range 2.7–4.8 mm) vs the sensor's 2.3–11 mm → the hum is the steadier motion measure at rest.
  Individual slots slip (disagree ~4 cm from the median); the median is robust. One recording; the sensor is not a
  precise truth. Script: analysis/hum_real_test.py.
- **Build "hybrid hum" (2026-11-18): ping "Quiet + hum (experiment)".** Clicks 18.5–22 kHz (amplitude 0.6, pitch
  bands as set) + 8 steady tones 16.32–18.0 kHz, 240 Hz apart (whole cycles every 200 samples; every click period at
  2/4/8/15 per s is a multiple of 200 → seamless loop; amplitude 0.3). Treated as Quiet everywhere (name starts with
  "quiet"). Map runs on the clicks; raw audio saved for 40 s; hum analysed offline (analysis/hum_track.py, needs a
  band filter 16.0–18.25 kHz first: without it the clicks leak into the tones and tracking fails completely).
  Sim: map 39/48 walls, 4 false (plain Quiet 39/5), directions slightly rougher at 8/s; hum track with clicks on 1.3 mm
  rms over 9 cm (corr 0.998). Costs: click band 3.5 vs 6 kHz (~5 vs ~3 cm detail) and shared speaker power; the real
  speaker is weaker at 18.5–22 kHz than the sim assumes. Installed; not yet tried on the phone.
- **Hybrid on the phone (2026-11-18 13:46–13:48; Quiet + hum 59 s, plain Quiet 49 s, hum only 36 s; all 15/s, High,
  4 pitch bands, same room).** Map: echoes per reading 0.82 (hybrid) vs 1.85 (Quiet), confirmed 57 vs 75 %, walls/min
  7 vs 20, noise re the click −58.9 vs −62.4 dB → the hybrid roughly halves detections (quieter clicks, weaker speaker
  at 18.5–22 kHz, hum raising the floor). Hum: hum-only reproduced (second recording: correlation with the sensor's
  forward movement −0.74, hum 392 ms later; first: −0.81, 328 ms) → not a fluke. In the hybrid the hum fails (+0.22):
  its tones flicker at the click rate (15 Hz component 10.5 dB above the movement band, vs −12 dB in hum-only) even
  after band filtering → the clicks modulate the hum in the phone itself (speaker protection / limiter pumping, or
  intermodulation). Removing a common per-block gain or the per-click repeating pattern offline didn't fix it. That
  session also had less forward movement (1.1 cm rms vs 2–2.6). Hybrid as built: worse on both counts.
- **Build "quiet tones" (2026-11-18): all-tone sonar, ping "Quiet tones (experiment)"; the click+hum hybrid is
  removed (Hum records-only kept).** 256 steady tones 16.0–22.0 kHz, 23.44 Hz apart (= a signal repeating every
  2048 samples, 42.7 ms; echoes beyond 7.3 m wrap around), flat with raised-cosine edges, Schroeder phases (low peak),
  played continuously. Each 2048-sample stretch → per tone received/played → Hann across tones → inverse FFT =
  complex distance profile (2 samples per point, ~3 cm detail as Quiet); 3 stretches averaged per reading, a reading
  every ~85 ms; direct sound = strongest point = distance 0; then the normal Quiet pipeline (threshold, tracking, map,
  walls). Pitch-bands and click-rate settings don't apply. Raw audio 40 s saved. Sim (harness clock fixed for this
  mode): echoes per reading 2.7–2.9 vs ~1.0 for Quiet, wall echo present in 88–96 % of readings vs 43–68 %,
  distance error median 0.25–0.4 cm (same), walls 12/16 both, worst direction 4.6° vs 9.9°. The sim speaker is ideal;
  not yet tried on the phone. Next if it holds: hum-phase motion → front/back (replacing the accelerometer).
- **Quiet tones on the phone (2026-11-18 14:03–14:05, same spot; Quiet 4 bands 33 s, Quiet tones 47 s, Quiet tones
  short hold/push 12 s, Quiet 1 band 40 s).** Map: echoes per second 25.1 / 34.2 / 34.1 (Quiet 4 bands / tones /
  Quiet 1 band), confirmed per second 17.7 / 23.4 / 22.3, walls/min 27 / 21 / 24, noise re direct −62.5 / −71.0 /
  −71.7 dB, processing 28 / 15 / 24 ms per reading → tones ≈ plain Quiet at its better setting; not clearly better.
  Motion from the tones' phase: NOT reproduced so far. Fine 3 cm slots (echoes slide out of their slot as the hand
  moves), single tones (each 1/256 of the power, ~12 dB weaker than in the 16-tone hum — too faint) and groups of
  16/32 neighbouring tones all gave scale 0.01–0.16 of the sensor (hum-only: 0.38–0.64) and correlation ≤ 0.6 at
  the edge of the lag range. The hum worked because 16 tones each carried much more power. Possible fix: a few
  stronger "pilot" tones inside the comb (as OFDM does for channel tracking), at some cost to the map.
