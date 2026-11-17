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
