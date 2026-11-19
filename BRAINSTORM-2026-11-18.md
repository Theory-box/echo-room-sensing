# Brainstorm 2026-11-18 night: two instances, 4 rounds, ideas checked offline on real logs

## Prior art found
- **BatMapper** (MobiSys 2017, Stony Brook):
  - Phone held **horizontally, across the walking direction**: the top and bottom mics each hear "their" side
    wall, so corridor width and sideways position come in continuously while walking.
  - Audible pulses (8-16 kHz 3 ms + 8-10 kHz 1 ms).
  - 1-2 cm ranging up to ~4 m; doors found as ~10 cm recesses (92% precision); hand sway compensated with the
    accelerometer.
  - Room size from left-right phone gestures.
- **SAMS** (2018): FMCW 11-21 kHz while walking freely; map median error 30 cm, 90th percentile 1 m. Our results
  are in the same league.
- **"Autonomous localization and mapping using a single mobile device"** (arXiv 1612.05793): co-located speaker +
  mic + motion sensors. Echoes are labelled by brute force from 3 measured points. Our turn + gyro labelling is
  stronger.
- **Symmetry paper** (arXiv 2403.00698): with the speaker carried on the moving device, echo-only position
  ambiguities ("which of two mirror spots") can't be broken by any number of mics. Only outside cues can: gyro
  continuity, the measured walk, furniture. This matches our design.
- **Bats** (Science 2017): smooth vertical walls are acoustic mirrors heard only face-on. Same physics as our
  +-30 deg.

## Checked offline (real logs, larger room)
| Idea | Result |
|---|---|
| **2.5 m surface = double bounce (1.05 + 1.45 m)** | **Confirmed**: it appears almost only when both are present (49% vs 1%, 77% vs 5%); its distance tracks their sum per reading (r = 0.62-0.89). A ghost. |
| ~4.95 m surface = bounce? | **No**: it appears when the near pair is *not* both heard (~30% vs ~90%), and it is as strong as walls after distance correction. A real big reflector through an opening, seen past a partial obstruction. |
| Opening = "weaker than distance predicts" | **Rejected**: the far surface isn't weak. |
| Pooled room widths across spots | One axis: consistent 3.74-3.81 m at both spots in all 3 sessions. The other: 3.5 vs 3.9 depending on 1.05 vs 1.45 m (second spot doesn't decide). |
| Opacity rule (two parallel surfaces both heard face-on -> the nearer is partial) | Fits: the 1.05 m one is likely the half wall, 1.45 m the wall -> width ~3.85-3.9 m. Needs the user's confirmation. |
| Furniture fingerprint to pick between 2 candidate spots | Reliable gross-error detector (right area 45-72% vs wrong 22-35%); inconsistent between candidates ~35 cm apart. Use as a veto / tie-break only, never as continuous pull (that is what broke the Kalman / particle filters). |
| Walk as synthetic aperture (curved tracks of side objects) | One plausible side object (44 vs ~20 chance votes) in one walk; near-straight-ahead fits are degenerate. Modest. |
| Blanket "drop sum echoes" filter | Flags ~1-2%, same as chance -> learn bounces per direction instead (co-occurrence + correlated jitter). |

## Ranked next steps
**Build (cheap, low risk):**
1. Opacity + learned-bounce rules for the box: per direction, mark a distance as a ghost when it keeps appearing
   exactly with two other surfaces and tracks their sum; among parallel candidates heard face-on, the farther
   non-ghost one is the wall. Fixes the "room too long / too short" in the larger room.
2. Pooled room widths from later spots, only for axes with one clear candidate per side.
3. Furniture fingerprint as a veto ("can't place this spot confidently, turn again") and a tie-break for
   "2 possible spots"; store furniture points only from confidently placed spots; let them grow with spots.

**Short user tests (no build needed):**
4. Tell us what is ~1.0 m and ~1.45 m from the usual first spot in that direction (half wall? height?).
5. Lift test: facing that direction, hold low (knee) 5 s, lift slowly to head height, hold 5 s; control facing a
   clear wall. A full wall keeps its echo; partial objects fade above their top.
6. One slow walk straight toward that direction from ~2.5 m: echo slopes classify real (1x), bounce (2x) and
   floor/ceiling (0x), and level vs distance separates walls (-6 dB per doubling) from edges (-12 dB).

**Later:**
7. "Crab" walk: phone bottom edge toward a side wall while walking (cross-track continuously, door recesses and
   wall ends along the route, as in BatMapper). Along-track from a quick wrist glance at the wall ahead every
   ~1.5-2 m, or from the curvature of door-frame echoes passed on the side. Inaudible works for one side.
8. Earpiece (top) speaker for the crab's other side: 2-minute bench test first (left-only vs right-only level at
   the bottom mic, 16-22 kHz); drop if > 20 dB down.
9. Guided "step ~0.7 m sideways" for a second spot to test openings by visibility.

**Rejected this session:**
- energy-based opening detection;
- the top speaker in the normal hold (it faces your chest);
- turn-rate heading lag (no effect found);
- continuous furniture matching;
- forward-walk aperture as the sideways tracker;
- audible BatMapper-style chirps (inaudible preferred);
- echo-only symmetry breaking.

## Final refinements (partner's last round)
- **Bounce filter at track level, not per reading.** A steady surface in a sector is a bounce if, over at least 10
  readings, it follows r_a + r_b (or 2·r_a) with residual sd <= 2 cm, correlated jitter (>= 0.5) and appears
  mostly when both parents are present. Never flag a track that fits a locked wall. Where a wall coincides with a
  sum, a walk or a second spot splits them (a bounce moves 2x, a wall 1x).
- **Opacity rule guard.** The farther surface must be heard over >= ~60% of the nearer one's heading span. If it
  is heard only in a narrow window, it is seen through a doorway in the nearer surface: the nearer one stays the
  wall and the far one becomes an opening marker. In the opacity case the nearer surface goes to a "half wall /
  furniture" layer instead of being discarded.
- **Furniture fingerprint = accept/reject gate only.** Reject a placement if its clutter score is < ~10 points
  above offset controls (every good run cleared them by 15-37). A sharper version later: furniture points
  triangulated from 2+ spots.
- **Likely link:** the "2 possible spots ~35 cm apart" alternatives match the 1.05 / 1.45 m gap (0.40 m), so they
  are probably the same wall-choice problem, not a position symmetry. Check offline which surface each spot's vote
  used; fixing the wall choice may remove them.
- **Revised order:**
  1. Bounce filter (track level).
  2. Opacity rule with the guard.
  3. Pooled widths.
  4. Fingerprint gate.
  5. User: what is at 1.05 / 1.45 m + lift test.
  6. One slow walk toward that side.
  7. Sideways second spot.
  8. Crab + wrist-glance walk, earpiece bench test.
