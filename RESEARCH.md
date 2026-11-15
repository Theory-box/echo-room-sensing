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
