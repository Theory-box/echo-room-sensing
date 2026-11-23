# Things the user asked to remember / test later (kept as of 2026-11-19)

# Test queue (run in a row when there is time)

Ready now (no app changes needed):
- [ ] **Guided scan check**: one Guided scan in the half-wall room; confirm sound stops at the end, still map + Main
      menu; I check the log for the old unlocked-refit error.
- [ ] **Which hole is which mic**: Record only, tap gently next to each mic hole in turn (bottom edge, top, back),
      ~3 s apart, saying nothing. Needed before the mic-tube test.
- [ ] **Card ears**: card curved around both sides of the phone (fixed, not hands), Guided scan; compare with a plain
      scan: confidence, fewer far echoes behind.
- [ ] **Mic tube (wider triangle)**: aquarium air-line tubing (4-6 mm inside), sealed over one mic, mouth taped ~25 cm
      out to the side on a ruler; Record only, turn slowly in front of a flat wall ~1.5 m away.
- [ ] **Felt-lined speaker tube**: ~10 cm tube lined with felt over the speaker only; Guided scan; compare.
- [ ] **Half-covered opening**: felt over the left half of the box mouth; Record only, turn 45 deg left, centre,
      45 deg right at a wall.
- [ ] **Controlled motion / precision**: phone on a firm surface, slid 5, 10, 25 mm against a ruler with pauses, then a
      visible wobble of the phone itself; Record only.
- [ ] **Extra ring check** (optional): Redo ring check from a second spot in the same room.

Needs a small build first (I do it at the start of that session):
- [ ] **Computer as second device**: install `sounddevice`, speaker check (16-22 kHz from the right speaker), beacon,
      then two-way distance with the USB mic. Tell me where the USB mic sits.
- [ ] **Fan trail**: needs Record only that writes to a file (no 2 min limit); close up, turn, step away in stages,
      fan OFF at the end.
- [ ] **Self-moving phone**: needs a buzz-pattern test button; hard table, log twist / push / sonar.


Tests to run
1. **Computer as the second device** (next session): install `sounddevice`; (a) speaker check: inaudible 16-22 kHz
   sweep from the RIGHT speaker (Realtek) while the phone records nearby (Record only) -> can the speakers make our band;
   (b) computer as a steady inaudible beacon while the phone turns / walks; (c) true distance: the computer also records
   its USB mic ("MIC_TEST") on the same audio clock and hears the phone's pings -> combine both sides' timings. Ask where
   the USB mic sits relative to the right speaker.
2. **Controlled motion / precision test**: phone on a firm surface, slid known distances against a ruler (5, 10, 25 mm,
   with pauses), then a visible wobble of the phone itself; Record only. (The 2026-11-19 table-wobble test was unreliable.)
3. **Fan trail**: close to the fan ~15 s, slow turn, step away in stages pausing ~10 s still at each spot into further
   rooms, end with the fan OFF as the control. Wants one continuous recording -> build a write-to-file Record only first
   (today it keeps only the last 2 min in memory).
4. **Guided scan again** (any time): check the new end screen (sound off, still map, Main menu) and that the
   unlocked-refit error is gone in the log.

Ideas to build / explore
5. Smarter loud checks in Guided: one louder click, check whether it helped, repeat only if needed (not fixed 12 s / 6 s).
6. Room confidence as "+- cm per wall" from the spread of independent measurements; a few reference checks with an AR
   measuring app to catch consistent mistakes. Later an accuracy setting (Quick / Normal / Thorough) that works toward it.
7. Fast light sensor (240 Hz colour/light): light compass for heading / room angle, room ID by light flicker, LED beacons.
8. Temperature sensors (gyro chip, barometer): speed-of-sound correction for sonar; gyro drift correction.
9. Wi-Fi RTT (check whether the router supports it) and Wi-Fi Aware (phone to phone) for room-level anchors.
10. Second phone as a beacon / transponder (levels 1-3, reply by sound with its measured timing).
11. Barometer as infrasound: house-wide door open / close sensing.
12. Learned sounds: fan fingerprint 56.3 Hz (+112.6, 168.9) found in other rooms; beacons, sharp sounds as free pings,
    tuning out steady sounds, backwards simulation to locate sources, silent mapping from the fan's whoosh.
13. Attachments: see ATTACHMENT-IDEAS.md (felt-lined speaker tube first; half-covered opening; inverse-designed printed
    caps if a 3D printer is available).
14. Optional extra ring checks at other spots (compare early decay); wall resonance as a "real wall / what material" label.
15. Room map open items: low-things layer (hard low things only; a quiet knee sweep is not a gap), bounce check should
    ignore lengths matching all-round (ceiling) echoes, the left wall's 3.2 m vs 2.5 m question, multi-room / saved rooms.

17. Deep dives the user wants (curiosity, not urgent): the magnetometer (how sensitive, what it can map: steel door
    hardware, radiators, wiring as landmarks), Wi-Fi sensing (RTT, signal strength), and the broader "what can every
    sensor extract" exploration. First-principles sensor names are in SENSORS.md.
18. Ways to use the microphones' 48 000 samples/s beyond pulsed sonar: continuous coded sonar (thousands of updates per
    second: gait, heartbeat-scale micro-motion), many signals at once in the band (sonar + data + beacons), microsecond
    timing between mics, fast transients.
19. Self-moving phone (the user's idea): the vibration motor nudges the phone on a table (stick-slip; lopsided buzz
    patterns bias direction), stop-and-go (buzz, settle, then record), with feedback from the twist sensor and sonar
    fine tracking. Learn the surface with a few test buzzes; table slope straight from the push sensor (gravity); never
    step toward an unknown edge (sonar sees the drop). Goal: hands-free room sweeps (self-rotation), known tiny steps
    to calibrate the hologram ladder, longer crawls for synthetic aperture. The buzz itself as a probe (surface type,
    contact) or cancelled as a known signal. First test: short buzz patterns on a hard table, log twist / push / sonar:
    does it move or spin, which way, how consistently.
20. Card ears and a tube relocating one mic (probe-tube style) to widen the mic triangle: see the test queue.
21. Doorways from sound leakage (user, 2026-11-19): a room's own sounds (bedroom AC etc.) leak into the next room
    mostly through the doorway (walls cut 30-40 dB; higher-pitched parts most), so loudness, direction and door
    open/closed (10-20 dB drop) point to the opening; combine with sonar blank stretches and where the room
    fingerprint switches while walking through.
22. Whole-floor map (planned): second floor has laundry room - kitchen - loft, and the loft connects to three rooms.
    Plan: map each room (Guided scan + ring check, ideally 2 spots), record both sides of each doorway with the door
    open and closed, note steady sound sources per room (AC, fridge, washer), then offline analysis of what joins up.
    The user tells me which session was which room (or says it at the start of a Record only take).
    Doorways (user, 2026-11-23): just do a Guided scan standing in the doorway, named e.g. "Doorway Kitchen - Loft".
    That scan sees both rooms (expect a long, odd box); later, lining it up with each room's own scans places the
    doorway. No doorway detection from close echoes for now.

Separate project (not Echo Room)
16. Magnetometer stud finder app (phone flat on the wall, slide, meter + beep near screws).
