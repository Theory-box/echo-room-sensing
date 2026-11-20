# Attachment ideas (parked, 2026-11-19)

Brainstormed with the user; none built. Ranked roughly by promise. All untested.

## Measured so far
- Straight cardboard box (phone inside, bottom edge out): walls not louder, beam not narrower; ceiling/floor echo -6..-7 dB
  (panels shield); self-noise +9..14 dB within 0.5 m only.
- Paper towel roll (squeezed): rang, +10 dB all-round halo 0.6-1.35 m; room box locked on the halo (wrong, half size).

## Physics notes
- A hand-sized opening only becomes directional when several wavelengths wide (16-22 kHz: ~1.7 cm). A 4 cm mouth hears
  roughly the whole front half: a small opening samples pressure, and pressure has no direction.
- Hard tube walls are mirrors to sound: a bare tube guides side sound to the mic and rings. Lining with felt/fabric
  makes it a collimator (side sound dies on the walls), limit ~25 deg for a 4 cm mouth, quieter, much less ringing.
- A tube relocates the listening (or sending) point to its mouth, with a fixed delay.
- Learned fingerprints (record a slow turn in front of a wall once per attachment) beat calculating from dimensions.
- Steady self-echo / ringing of an attachment can be learned and subtracted (extend near-zone removal beyond 0.6 m),
  but what it masked is not recovered, and it needs refreshing if the attachment flexes.

## Ideas, best first
1. Tube over the SPEAKER only (~10 cm, felt-lined, pointing forward): source leaves ahead of the mic, tube body shields
   the mic -> less direct blast (smaller blind zone), cleaner beam, no ringing. Separate tubes for speaker and mic =
   cleanest (two-way trimming). App must correct the fixed source offset (detectable from the mouth reflection).
2. Asymmetric opening (half open, half felt or foil): breaks the left/right mirror; each angle gets its own pitch
   fingerprint (learned). Like the outer ear. Cheap test: felt over the left half, turn 45 L / 45 R at a wall.
3. Two openings apart (e.g. 10 cm side by side) merged into one mic with a known extra delay: a sideways two-ear pair
   (the phone's own mics are front-to-back when held bottom-edge forward). Same ambiguity as two mics (> half a
   wavelength apart): coarse timing must pick the fine solution.
4. Tags per entrance: which mic (route paths to different mics: cleanest), timing (path length), colour (felt dims
   highs; tuned notch pocket ~4.5 mm), resonator "lingering pitch" (must be inside the chirp band; foil too floppy),
   chopping (cover/uncover or flip the attachment to learn one path's contribution).
5. Foil half-cover also gives a built-in ruler: its fixed echo detects the attachment, checks speed of sound
   (temperature), anchors timing.
6. Row of vertical slits (~3-5 mm wide, ~2.5 cm apart): pitch-dependent side beams (direction from pitch). Hard: uneven
   feeding from an off-centre speaker, cavity modes, ringing, leaks (screen window), flex. Too ambitious for now.
7. Small steady barrier (foam / Blu Tack) between speaker and mic on the bottom edge: a few dB less airborne leak; most
   leak goes through the phone body. A finger is too unsteady and reflects.
8. Card "ears" curved around the phone's sides (open, no ringing): maybe +3-6 dB from the front, 6-10 dB less from
   behind and from the body; mainly reduces front/back ghosts. Hands work for a try but move.
9. Tube relocating one mic (like audiologists' probe-tube mics): thin tubing (< 8 mm, e.g. 4-6 mm air-line), 20-40 cm,
   sealed over the mic, mouth fixed on a stick -> a wide mic triangle (left-right and up-down clues), less speaker
   blast at that mic. Fixed delay and colour need a one-time measurement; fine timing more ambiguous at 16-22 kHz.
Not useful: single small hole (omni + ringing), one opening split into two paths (same delay for every direction).
