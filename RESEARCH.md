# Related research and ideas for Echo Room (searched 2026-11-14)

Search focus: 2024–2026 work on smartphone/acoustic echo sensing, plus the foundational papers they build on.
Honest note: very little 2025–26 work does exactly "phone-only sonar mapping"; most recent work is neural
room-geometry inference from simulated data, or narrow phone sensing tasks (auth, breathing, soil).

## Most relevant papers
- **Synesthesia — "Can a Phone Hear the Shape of a Room?"** (Shih & Rowe, IPSN 2019). Phone records echoes at many
  positions, phone position from visual-inertial odometry (ARKit/ARCore-style); room geometry still reconstructed
  with ~20 cm position uncertainty. https://wise.ece.cmu.edu/projects/synesthesia.html
- **Room shape + self-localization with one device (co-located mic+speaker) and motion sensors** (Wang, Peng, Chen;
  arXiv 1612.05793). First-order echoes + motion sensors suffice; needs ≥3 non-collinear positions.
  https://arxiv.org/abs/1612.05793
- **EchoSLAM** (Kreković, Dokmanić, Vetterli) — omni source + collocated mic on a moving robot, 2D polygon rooms.
- **ELF-SLAM / Indoor Smartphone SLAM with acoustic echoes** (arXiv 2210.08493; IEEE 2023) — phone echoes + IMU.
  https://arxiv.org/abs/2210.08493
- **EchoScan** (Yeon et al., IEEE/ACM TASLP 2024) — neural network infers floorplan + height maps from echoes,
  incl. walls not directly visible; trained on simulated impulse responses. https://arxiv.org/abs/2310.11728
- **Depth maps from ultrasonic echoes** (Honma, Kimura, Irie; ICIP 2024, arXiv 2409.03336) — inaudible echoes are
  weaker/noisier; using *audible* echoes as auxiliary training data improves ultrasonic-only depth.
  https://arxiv.org/abs/2409.03336
- **AV-Twin: audio-visual digital twins with smartphones** (arXiv 2512.10778, Dec 2025) — phone impulse-response capture
  + camera; surface materials via differentiable acoustic rendering. https://arxiv.org/abs/2512.10778
- **Saranga** (arXiv 2603.24699, 2026) — mW ultrasound navigation on palm-sized drones in fog/dark; a neural network
  trained on synthetic data + a little real noise pulls echoes out of very low SNR. https://arxiv.org/abs/2603.24699
- **Self-interference / direct-path removal on phones**: AIM acoustic imaging (MobiSys 2018) subtracts a
  pre-recorded direct-path signal, then separates background reflections; SCR-Auth (arXiv 2404.15000, TIFS 2025)
  differences against a reference segment containing only direct path + environment. https://arxiv.org/abs/2404.15000
- **FMCW phone sensing** — MilliSonic (~mm tracking via FMCW phase, arXiv 1901.06601); EchoSpot (18–23 kHz FMCW +
  Kalman filter to tame multipath); SoilSound (arXiv 2509.09823, 2025) phone chirps for soil moisture.

## Ideas that fit our app (best value first)
1. **Track echoes over time instead of per click** (Kalman/persistence, as in EchoSpot). Require an echo to persist
   for a few clicks at a consistent distance before drawing it bright. Likely cuts flicker and false echoes.
   Small effort; moderate confidence it's visible.
2. **Subtract the phone's own "direct + body" signal** (AIM, SCR-Auth). Learn the direct-path template (e.g. median of
   the complex response over several headings while turning, or a short calibration with the phone pointed at open
   space) and subtract it before echo picking. Could shrink the ~0.5 m near blind zone. Medium effort; uncertain
   gain (phone grip changes the template).
3. **For walking/room mapping: use ARCore camera tracking for phone position** (Synesthesia). Their result that
   ~20 cm position error is tolerable is encouraging, and is far easier than acoustic odometry. Big effort; the
   strongest path back to actual room outlines.
4. **Two-band cross-supervision** (Honma 2024): the audible band can teach/calibrate the inaudible band (thresholds,
   or which echoes are real). Fits the earlier "cycle bands" idea. Back burner.
5. **Learned denoising trained on our simulator** (Saranga, EchoScan): our simulator could generate training data.
   Big effort; long-term.

## Third microphone (researched 2026-11-17)
- **Pixel 11 has 3 microphones** (Google spec pages). Placement isn't published in the spec.
- **Google's SpeechCompass (CHI 2025, Best Paper)**, phone-only version on an unmodified **Pixel 6**: three mics at the
  **bottom edge, top edge, and near the rear camera**. The camera mic is only **15 mm** from the top mic — "too small for
  useful delay estimates", so only two pairs were usable and localization stayed **180°** (front/back ambiguity
  unresolved). Mean error 16° (speech) / 23° (environmental sound). The authors note a camera mic placed farther left
  (larger baseline) would have allowed 360°. Their 4-mic phone case got 360° and 11–22° error.
  https://arxiv.org/abs/2502.08848 · https://research.google/blog/making-group-conversations-more-accessible-with-sound-localization/
- **UT Dallas SSPRL "Three Mic DOA" Android app (2020)**: the guide's Android capture uses **two** sources (MIC = bottom,
  CAMCORDER = near camera), stereo max; "Android doesn't guarantee two-channel recording for all phones".
  https://labs.utdallas.edu/ssprl/files/2020/09/Users-Guide-Android-ThreeMicDOA.pdf
- **Android API**: >2 mics need a channel *index* mask (e.g. 0x7) on AudioRecord; whether the HAL exposes 3 distinct mics
  is vendor-dependent. Our app already records 3 channels on the Pixel 11 (UNPROCESSED, mask 0x7); MicrophoneInfo lists
  only "bottom" and "back" with positions; ch3's identity is unknown (timing close to the bottom mic).
- **Implication for the sonar**: if Pixel 11 keeps the Pixel 6-style layout, the third mic adds a ~1.5 cm baseline next
  to the back/top mic → little direction gain. Residual device question (research can't answer): where ch3 is. The
  app's Scratch test answers it in ~30 s.

## Wall vs corner echoes (established room acoustics)
- Image-source model: each reflection's amplitude = product of the wall reflection coefficients × 1/path length. A
  flat wall's first-order (perpendicular) reflection has one bounce and the shortest path → normally the strongest echo.
  A corner between two walls is a second-order path (two bounces, longer) → weaker. Corners/trihedrals matter for
  *directional* sonar/radar because they retroreflect over a wide range of angles, not because they are louder.
  (Our simulator's "corners strongest" referred to accumulated evidence in the wall-fit map across all headings, not raw
  echo amplitude — that wording was misleading.)

## Third microphone — device check on the Pixel 11 (2026-11-17)
- Google's Pixel 11 hardware diagram: 3 mics — top edge, rear (camera bar), bottom edge.
  https://support.google.com/pixelphone/answer/7157629
- Phone audio policy (dumpsys media.audio_policy): built-in mic port supports channel index masks 0x7 and 0xF (3 and 4
  channels); Android's MicrophoneInfo only lists "bottom" and "back".
- Silent 3-channel capture (UNPROCESSED, 0x7, 16–22 kHz sweep from the bottom speaker, phone still): ch1 = bottom mic
  (first); ch2 +10.4 samples; ch3 +14.6 samples; all three carry room echoes and the same noise floor → three real mics.
  ch2/ch3 are the two top-end mics (camera bar and top edge), only ~4 samples apart → ~1.5–3 cm apart (cf. 15 mm on
  Pixel 6 in SpeechCompass). Which of ch2/ch3 is which isn't settled by timing. The 4-channel capture adds a channel
  coincident with ch1.
- (An earlier quick analysis wrongly put ch3 next to the bottom mic — it picked a weak click.)
- Conclusion: the third mic gives a thin triangle (~14 cm × ~1.5–3 cm). Expected sonar gain is small; not worth building
  on before cheaper improvements.

## Phone speakers, mics and distortion (researched 2026-11-17; three parallel searches + checks on the phone)
Device facts (label = model the source is about):
- Pixel 11: stereo = bottom speaker + earpiece (GSMArena review snippet). Amplifier part for Pixel 10/11 not public;
  Pixel 9 Pro XL uses Cirrus CS35L41B (iFixit), Pixel 6 Pro 2× CS35L41B, Pixel 9a a TI class-D. Pixel 6 device tree:
  cs35l41 "Protect Lite" firmware, per-speaker calibration. No published Pixel 9–11 response curves, no >16 kHz data.
- Pixel 11 Pro XL (Bandicoot Lab): 76.6 dBA max, treble-forward; mic response "nearly flat". Pixel 10 Pro XL: distortion
  and chassis vibration near max volume (Mobilissimo).
- Android CDD properties PROPERTY_SUPPORT_SPEAKER/MIC_NEAR_ULTRASOUND (18.5–20 kHz within 40 dB / 15 dB of 2 kHz):
  Pixel values unpublished — readable via AudioManager.getProperty in the app.
- Pixel 11 audio policy has AUDIO_CONTENT_TYPE_ULTRASOUND behind ACCESS_ULTRASOUND (signature|privileged): not usable by
  apps. Related shipped tech: Nest Hub ultrasound presence sensing; Elliptic Labs proximity (Xiaomi).
- Pixel 7 (support page lists 4a 5G–7): Adaptive Sound = mic-driven, time-varying speaker EQ for media; check it's off.
- Known Pixel 7–10 bug: random audio pops when streams start/overlap (software).
Speaker protection (TI/Cirrus docs, generic): excursion limiting is fast (ms look-ahead) and acts mostly near/below
resonance; thermal limiting builds over seconds–minutes and can attenuate any band incl. highs; multiband release can
"pump" ping to ping. Roughly linear/time-invariant at moderate levels.
Distortion (MobiCom'22 "Experience", via D. Li dissertation ch. 5): 15 phones incl. Pixel 4 leak audible products from
18–22 kHz signals at 80% volume; the AMPLIFIER dominates distortion; harmonics alias in the 48 kHz playback chain (20 kHz
→ 4/8/12/16 kHz); above ~40% volume (their amp) extra volume mostly becomes distortion and at 100% the fundamental even
dropped. Chirps leak least; two tones add intermodulation.
Linear vs exponential sweeps: an n-th harmonic of a linear up-chirp smears over negative lags (before the direct sound);
of a down-chirp over positive lags (our false far echoes). Farina/Novak exponential sweeps put each harmonic at a clean
negative time (Δt_n = −L ln n) but move energy to low frequencies (worse resolution with our weak highs).
Using distortion: AliasProbe (unreviewed 2026, iPhone 15 Pro): 16–20 kHz chirp's 2nd harmonic aliases to an 8–16 kHz
down-chirp; stitching gave ~2× narrower single-reflector peaks in 4/12 runs, needs 100% volume; template must be
bandpass(s²). MobiCom'22 suggests those aliases are emitted acoustically (audible). HotNets'22 uses 3rd-order IM for
micro-vibration sensing. Crack detection uses harmonics, but rooms are linear → no use for mapping.
Practice: BatMapper uses Hann-windowed linear up-chirps (8–16 kHz), per-mic band-pass, first peak as time reference.
Ranked for the app: (1) volume/linearity test (find the knee; app currently holds 80% media volume); (2) pulse inversion
(+s/−s pairs, half-difference cancels even harmonics and their aliases) — keeps up-sweeps; (3) log near-ultrasound
properties + direct-path level per ping (detect thermal limiting); (4) Adaptive Sound off; (5) exponential sweep only as
a speaker-distortion diagnostic; (6) AliasProbe stitching — low value. Checked: in our current periodic Full sweep the
next ping's harmonic precursor (~−0.55T) stays outside the echo window and the noise tail (needs nb ≤ P − 0.55T; holds
with fill 0.5 and the range-fit rule).

## Moving through the interference pattern: synthetic aperture / holography (researched 2026-11-17)
- AIM (MobiSys 2018, Samsung S7): phone moved along a path as a virtual array (SAR) → 2D acoustic images of objects.
  Problems named: strong self/background interference, hand jitter off the path, speaker/mic distortion.
  https://sigmobile.org/grav/research-highlight/aim · https://par.nsf.gov/biblio/10063070
- SONDAR (2024): inverse SAR (object moves) on commodity devices for size/shape. https://par.nsf.gov/servlets/purl/10569725
- UW preprint (Mar 2026, unreviewed): unmodified iPhone + motorized turntable rotating the OBJECT = known circular
  aperture → 3D acoustic volume in <30 s; says hand-trajectory estimation is the dominant error in prior phone SAR.
  https://coherent-3d-acoustic-imaging.pages.dev/
- Handheld mmWave SAR (ViSAR, IFNet) also fights handheld motion; ViSAR uses time-domain backprojection for non-linear
  paths. https://cse.sc.edu/~sur/papers/Jackie_UbiComp21_ViSAR.pdf · https://arxiv.org/pdf/2405.02023.pdf
- Holography with ONE moving mic + a fixed reference mic = "virtual phased array" (established in noise-source
  localization; needs a steady sound field). https://acoustics-old.ippt.pan.pl/index.php/aa/article/view/1524
- Room geometry from a moving co-located speaker+mic / robot: first-order echoes, image sources (no interference-pattern
  method found). https://arxiv.org/pdf/1907.01169
- For us: object-scale SAR on phones is proven; room-scale wall imaging this way isn't. The known blocker is the hand's
  path. A lazy Susan (phone at an offset from the centre, rotation from the gyro) gives a known circular aperture — same
  idea as the UW turntable, but rotating the phone.

## Standards checklist (sonar / radar / phone acoustic sensing), researched 2026-11-17
Ranked by value for effort; checked against our code where noted.
1. Coherent integration limit (radar CPI): we fold RAW samples over 2–4 clicks before the matched filter. At Quiet's
   λ≈1.8 cm the echo phase turns once per ~0.9 cm of round-trip-halved motion, so hand/turn motion of 5–15 cm/s
   (0.3–1 cm per click at 15/s) partly CANCELS moving echoes in the fold (walls while turning). Fix: compress each click
   and average envelopes (non-coherent), or coherent only after motion compensation. High / small. [checked: real]
2. Tracker-aided phase unwrapping (LLAP, Strata, weather-radar dealiasing): done 2026-11-17 (per-echo tracks).
3. Velocity-ambiguity resolution: staggered click periods (CRT), up/down pairs (rejected here: harmonics), sub-band
   synthetic wavelength (untested idea).
4. LFM range–Doppler coupling Δτ = f_d·Tp/B: Quiet (50 ms, 6 kHz) at 0.15 m/s ≈ 2–3 cm range bias; correct with tracked speed.
5. Window the matched-filter reference (Hamming/Taylor) to push direct-sound range sidelobes toward −40 dB (cost ~1 dB).
6. Static/direct-path removal (LLAP static vector, Strata CIR differencing, MTI): slow running average of the complex
   response near the phone, subtracted → smaller blind zone. (= earlier back-burner "subtract direct signal".)
7. OS-CFAR along range (Rohling 1983) instead of median+offset; noise from past max range.
8. Track management: gating + nearest-neighbour assignment, confirm 3-of-5, coast, delete; map/show confirmed only.
9. Pre-whitening from the measured response (regularised): we found full rebalancing costs echo energy on this phone;
   regularised/mild only, if ever.
10. Harmonics: exponential sweep or lower drive (see distortion section).
11. Range–Doppler map (FFT over 8–16 clicks per range bin).
12. Doppler ego-motion (Kellner et al. 2013): fit phone velocity to static echoes' radial speeds (RANSAC), movers = outliers.
13. TVG: 1/r for walls (ours), 1/r² for points, + air absorption ~0.3–0.6 dB/m at 20 kHz (uncertain).
14. GCC-PHAT + sub-sample interpolation for the two-mic delay.
15. Sonar occupancy grids (Elfes, Konolige MURIEL, Leonard & Durrant-Whyte RCDs): carve only to the first confirmed
    echo; weak free evidence for missing returns; clamp; regions of constant depth → put the wall at the RCD centre
    (wall normal) instead of smearing the arc.
16. Bistatic offset per mic (bottom mic next to the speaker → negligible for ch1).
17–18. DPCA/PGA synthetic aperture, track-before-detect: later.
Already standard: long LFM + taper, periodic circular processing, direct path = time zero, UNPROCESSED 48 kHz, adaptive
threshold + noise gate, multiples suppression, normalized two-mic correlation, log-odds grid with beam model/carving.
Refs: LLAP https://samsonsjarkal.github.io/KeSun/files/mobicom16_ultrasound.pdf · Strata
https://www.cs.sjtu.edu.cn/~yichao/pmwiki/assets/publications/mobisys17_strata.pdf · Kellner ego-motion
https://unpaywall.org/10.1109%2FITSC.2013.6728341 · radar odometry survey https://arxiv.org/pdf/2307.07861 · acoustic
sensing survey https://arxiv.org/pdf/1901.03450 · Konolige MURIEL https://unpaywall.org/10.1023%2FA%3A1008806422571 ·
staggered PRF https://arxiv.org/pdf/2111.01246 · GCC-PHAT https://speechprocessingbook.aalto.fi/Enhancement/tdoa.html

## Other fields, mapped to our measured problems (researched 2026-11-18)
Checked on the raw wall recording (2026-11-18 11:52) where possible:
- Leading-edge / threshold retracking (radar altimetry, Davis 1997 https://www.osti.gov/biblio/524723): jitter after
  removing the push, 2 bands: peak 1.83 cm, −6 dB edge 1.68, −10 dB edge 1.68, −14 dB edge 1.93; 1 band: no gain.
  Lower thresholds run into the room background (only ~6 dB below the wall hump) — the "10 %" edge stuck to the
  search-window start (artefact). Small gain at best; not built.
- Measured-response template / deconvolution (Kleeman & Kuc 1995 https://ecse.monash.edu/centres/irrc/LKPubs/IJRR95.PDF):
  only helps if the 4–6 cm hump components were speaker/phone ringing. Direct-sound tail: −6 dB at 4.5 cm, −18/−22 at
  7.5–9 cm, −29 at 10.5 cm → no ringing components at 4–6 cm; the components are in the room. Not pursued.
- Still open, ranked: OS-CFAR (Rohling) + agreement across pitch bands for fake echoes (can be judged offline on the
  logged raw profiles `p`); audio/IMU clock alignment with AudioRecord.getTimestamp(TIMEBASE_BOOTTIME) and gain/delay
  calibration of the leaky integrator (explains part of 0.56× / 0.2 s early); two-mic expected-lag test (+20 vs −20
  samples, BatMapper-style path-length check) — less needed since the body blocks echoes from behind (walls behind
  detected 2.6 % vs 26 % ahead); bearing from echo strength vs yaw (Kuc 1997) ≈ what the wall finder's power-weighted
  centre does. Unlikely to transfer: synthetic aperture / Doppler beam sharpening by hand at λ 1.8 cm, MVDR with 2 mics,
  bat spectral-notch cues, full track-before-detect.
