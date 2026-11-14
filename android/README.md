# Echo Room (Android)

Native shell for the echo diagnostic. Chrome on Android only gives one mic channel,
so this app records the phone's mics **at the same time** with `AudioRecord`
(stereo, or 3 channels via an index mask) and plays the same test signal.
The UI and analysis are the web code: `app/src/main/assets/native.html` plus the
shared `diagnostic/dsp.js` (pulled in as an asset folder by `app/build.gradle`).

It tries several Android recording modes (UNPROCESSED, CAMCORDER, MIC,
VOICE_RECOGNITION, 3-channel UNPROCESSED) and reports which ones give distinct mics.
It also reports the phone's own mic positions (`MicrophoneInfo`).

## Build
JDK 17+ and the Android SDK (platform 35). `./gradlew assembleDebug`

## Run from a PC (adb)
```
adb install -r -g app/build/outputs/apk/debug/app-debug.apk
adb shell am start -n io.github.theorybox.echoroom/.MainActivity --ez autorun true --ei delay 10
adb shell run-as io.github.theorybox.echoroom cat files/latest.json
```
Optional: `--es configs "UNPROCESSED:2,CAMCORDER:2"`.

## Room sweep (stage 2 capture)
"Start sweep" records raw stereo (UNPROCESSED; ch1 = bottom mic, ch2 = back mic) at 8 or 12
rotation stops per spot, 1–2 spots. Spoken prompts guide the turns using the game rotation vector
(gyro + accelerometer). Each stop: ~4.9 s signal (log sweep, 2 chirps per speaker, 8 near-ultrasonic
chirps), saved as 32-bit float WAV. Per-session folder `files/sweep-YYYYMMDD-HHMMSS/` holds the WAVs and
`session.json` (plan, yaw per stop, gravity, gyro during capture, per-stop analysis).

Copy a session to the PC:
```
adb exec-out run-as io.github.theorybox.echoroom tar -cf - files/sweep-XXXX > sweep.tar
```
