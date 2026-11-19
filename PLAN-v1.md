# Plan v1 (2026-11-18): audit + brainstorm consolidation

Two independent audits plus four rounds of brainstorming between two instances, with the disputed ideas tested on the
recorded sessions. Ranked. Functions are in android/app/src/main/assets/sonar.html.

## 1. Bug fixes (from the audits, all verified against the code)
- a. **wyUpdate (moves-with-you):** currently counts "any echo at this distance in any recent reading" -> can hide real
  walls in clutter. Require the same echo (track / nearest chain within 2 cm) to stay put over the >= 20 cm move;
  entries expire. (Dormant today: walking never detected.)
- b. **Push ghosts in the room frame:** store where each ghost was found; apply only within 30 cm of there.
- c. **Straight wall lines in the room frame:** add the tracked position when a region closes.
- d. **Room box toggle:** also clear the map, so position and map never disagree.
- e. **Small fixes:** keep matched-echo support across refits; trim SLM.acc; cap a face-on pass at ~200 readings (an
  O(n^2) close could freeze after minutes held still); wipeRings centred where the ring was painted;
  push-heading window trimming.
- f. **Disable the walking path in v1** (gates widen + recovery jumps; 67-99 cm false jumps if it ever triggers on
  arm sweeps). The tap flow replaces it.

## 2. Freeze the box rotation after lock
slRefit refits rotation every second from drifted headings, so the box follows the drift. After lock: update D only.

## 3. The box vetoes rings
A ring sat on a wall distance in 2 of 20 sessions (1.35 m, 0.81-0.84 m): the near-square room makes walls look like
floor/ceiling. In ringFree/isRing a distance the locked box explains in that sector is not a ring there.

## 4. Per-turn compass (log only)
Each full turn: refit rotation with D fixed. Per-turn rotations agreed within 0.5-1.5 deg when >= ~200 echoes backed
them. Gates: >= 200 explained echoes, |change| <= 8 deg (mod 90), the two halves of the turn within 12 deg (good turns
2-10, bad 16-44; tuned on the same 21 turns -> keep logging, revisit).

## 5-7. Two-spot guided flow (replaces walking detection)
- Full turn -> face each wall once -> push at the amber dots -> arrow to a spot 50-70 cm away and >= 0.8 m from every
  wall -> tap "I moved" -> turn -> result with a confidence per axis.
- After the tap: tracking frozen; the spot-2 turn is buffered (readings per spot) and drawn once the pose is found.
- Relocalisation: a heading search within +-8 deg, then one offset vote per axis against spot 1's echoes. Use both
  walls of an axis when seen, else low confidence + the farthest consistent peak, never beyond the locked width.
  Mirror ambiguity resolved by the move direction at the tap.
- Tests: offline split-half noise floor (expect ~0), fake shifts recovered (incl. one wall deleted); live loop
  closure (spot 1 -> 2 -> 1 within 10 cm) and a taped 60 cm move.

## 8. Log the magnetometer heading (reference only, not an anchor: indoor errors 10-30 deg that change over 1 m)

## Later
- Furniture vs walls: label echoes against the specular wall model, then a furniture layer; plane vs point from two
  spots.
- Openings drawn as gaps (the 4.32 m surface that moved with pushes is a candidate).
- Suggesting the next spot.
- Applying the compass continuously.
- Refining room widths from later spots.

## Rejected (tested on recordings)
- Particle filter against the box (6-87 cm drift standing).
- Echo odometry (creeps ~1 cm/s while turning).
- Corners as landmarks (at chance level in the quiet modes).
- Room-width vote from 2nd-order echoes (1 of 24 axes).
- "Nearest surface is the wall" (shrinks rooms to furniture).
- Echo-based drift correction: mean offset +-5-10; loudness anchors sd 12.8; distance-curve anchors sd 15.7.
- Turn-health ratio (the box explains 16-36% of echoes in every turn).
- Accelerometer calibration (nothing would use it).
- Magnetometer as an anchor.
- Translation updates while standing (creep).
- Tracking while walking (never triggered; risky if it did).
