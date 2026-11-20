# Things the user asked to remember / test later (kept as of 2026-11-19)

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

Separate project (not Echo Room)
16. Magnetometer stud finder app (phone flat on the wall, slide, meter + beep near screws).
