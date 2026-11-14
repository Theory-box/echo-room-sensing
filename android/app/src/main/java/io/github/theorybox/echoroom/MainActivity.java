package io.github.theorybox.echoroom;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.media.AudioAttributes;
import android.media.AudioDeviceInfo;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioRecord;
import android.hardware.Sensor;
import android.hardware.SensorEvent;
import android.hardware.SensorEventListener;
import android.hardware.SensorManager;
import android.media.AudioTrack;
import android.media.ToneGenerator;
import android.speech.tts.TextToSpeech;
import android.media.MediaRecorder;
import android.media.MicrophoneInfo;
import android.os.Build;
import android.os.Bundle;
import android.util.Base64;
import android.util.Log;
import android.util.Pair;
import android.view.WindowManager;
import android.webkit.ConsoleMessage;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.FloatBuffer;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Locale;

/**
 * Thin native shell: plays the test signal and records all phone mics at the same
 * time (AudioRecord, multi-channel), then hands the raw samples to the web UI
 * (assets/native.html + shared dsp.js) for analysis.
 *
 * adb autorun:  am start -n io.github.theorybox.echoroom/.MainActivity
 *                 --ez autorun true [--es configs "UNPROCESSED:2,CAMCORDER:2"] [--ei delay 10]
 * Report:       run-as io.github.theorybox.echoroom cat files/latest.json
 */
public class MainActivity extends Activity implements SensorEventListener {
    static final String TAG = "EchoRoom";

    private WebView web;
    private SensorManager sm;
    private TextToSpeech tts;
    private volatile boolean ttsReady = false;
    private final float[] rotMat = new float[9];
    private final float[] orient = new float[3];
    private volatile float yawDeg = 0f;
    private volatile float gyroMag = 0f;
    private final float[] gravity = new float[3];
    private volatile String sessionDir = null;

    // ---------- live sonar: looping ping playback + continuous stereo recording into a ring buffer ----------
    private volatile boolean sonarOn = false;
    private AudioTrack sonarTrack;
    private Thread sonarThread;
    private float[] ring;                 // interleaved stereo
    private long ringFrames = 0;          // total frames written
    private int ringCap = 0;              // capacity in frames
    private final Object ringLock = new Object();

    private String startSonar(String pingB64, int periodFrames, int sr) {
        stopSonar();
        try {
            byte[] pb = Base64.decode(pingB64, Base64.DEFAULT);
            FloatBuffer fb = ByteBuffer.wrap(pb).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer();
            float[] ping = new float[fb.remaining()];
            fb.get(ping);
            float[] stereo = new float[periodFrames * 2];
            for (int i = 0; i < ping.length && i < periodFrames; i++) stereo[2 * i + 1] = ping[i];   // R = bottom speaker
            AudioManager am = getSystemService(AudioManager.class);
            int mx = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
            am.setStreamVolume(AudioManager.STREAM_MUSIC, Math.round(mx * 0.8f), 0);
            sonarTrack = new AudioTrack.Builder()
                    .setAudioAttributes(new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_MEDIA)
                            .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build())
                    .setAudioFormat(new AudioFormat.Builder().setEncoding(AudioFormat.ENCODING_PCM_FLOAT)
                            .setSampleRate(sr).setChannelMask(AudioFormat.CHANNEL_OUT_STEREO).build())
                    .setTransferMode(AudioTrack.MODE_STATIC)
                    .setBufferSizeInBytes(stereo.length * 4)
                    .build();
            sonarTrack.write(stereo, 0, stereo.length, AudioTrack.WRITE_BLOCKING);
            sonarTrack.setLoopPoints(0, periodFrames, -1);
            final AudioRecord rec = new AudioRecord.Builder()
                    .setAudioSource(MediaRecorder.AudioSource.UNPROCESSED)
                    .setAudioFormat(new AudioFormat.Builder().setEncoding(AudioFormat.ENCODING_PCM_FLOAT)
                            .setSampleRate(sr).setChannelMask(AudioFormat.CHANNEL_IN_STEREO).build())
                    .setBufferSizeInBytes(sr * 2 * 4)
                    .build();
            if (rec.getState() != AudioRecord.STATE_INITIALIZED) throw new IllegalStateException("AudioRecord not initialized");
            synchronized (ringLock) {
                ringCap = sr * 2;
                ring = new float[ringCap * 2];
                ringFrames = 0;
            }
            sonarOn = true;
            rec.startRecording();
            sonarTrack.play();
            sonarThread = new Thread(() -> {
                float[] buf = new float[1024 * 2];
                long lastVol = 0;
                try {
                    while (sonarOn) {
                        long now = System.currentTimeMillis();
                        if (now - lastVol > 500) {          // hold media volume at 80% while the radar runs
                            lastVol = now;
                            AudioManager amv = getSystemService(AudioManager.class);
                            int target = Math.round(amv.getStreamMaxVolume(AudioManager.STREAM_MUSIC) * 0.8f);
                            if (amv.getStreamVolume(AudioManager.STREAM_MUSIC) != target)
                                amv.setStreamVolume(AudioManager.STREAM_MUSIC, target, 0);
                        }
                        int n = rec.read(buf, 0, buf.length, AudioRecord.READ_BLOCKING);
                        if (n <= 0) continue;
                        synchronized (ringLock) {
                            int frames = n / 2;
                            for (int f = 0; f < frames; f++) {
                                int pos = (int) ((ringFrames + f) % ringCap);
                                ring[2 * pos] = buf[2 * f];
                                ring[2 * pos + 1] = buf[2 * f + 1];
                            }
                            ringFrames += frames;
                        }
                    }
                } finally {
                    rec.stop();
                    rec.release();
                }
            }, "sonar-record");
            sonarThread.start();
            return "ok";
        } catch (Throwable t) {
            Log.e(TAG, "sonar start failed", t);
            stopSonar();
            return "error: " + t;
        }
    }

    private void stopSonar() {
        sonarOn = false;
        if (sonarThread != null) {
            try { sonarThread.join(500); } catch (InterruptedException ignored) { }
            sonarThread = null;
        }
        if (sonarTrack != null) {
            try { sonarTrack.stop(); } catch (Throwable ignored) { }
            sonarTrack.release();
            sonarTrack = null;
        }
    }

    /** Latest `frames` stereo frames (both mics, same instant) as base64 interleaved float32, prefixed "totalFrames|". */
    private String getSonarBoth(int frames) {
        synchronized (ringLock) {
            if (ring == null || ringFrames < frames) return "0|";
            float[] out = new float[frames * 2];
            long start = ringFrames - frames;
            for (int i = 0; i < frames; i++) {
                int pos = (int) ((start + i) % ringCap);
                out[2 * i] = ring[2 * pos];
                out[2 * i + 1] = ring[2 * pos + 1];
            }
            ByteBuffer bb = ByteBuffer.allocate(out.length * 4).order(ByteOrder.LITTLE_ENDIAN);
            bb.asFloatBuffer().put(out);
            return ringFrames + "|" + Base64.encodeToString(bb.array(), Base64.NO_WRAP);
        }
    }

    /** Latest `frames` samples of one channel (0 = bottom mic, 1 = back mic) as base64 float32, prefixed "totalFrames|". */
    private String getSonar(int frames, int ch) {
        synchronized (ringLock) {
            if (ring == null || ringFrames < frames) return "0|";
            float[] out = new float[frames];
            long start = ringFrames - frames;
            for (int i = 0; i < frames; i++) out[i] = ring[2 * (int) ((start + i) % ringCap) + ch];
            ByteBuffer bb = ByteBuffer.allocate(frames * 4).order(ByteOrder.LITTLE_ENDIAN);
            bb.asFloatBuffer().put(out);
            return ringFrames + "|" + Base64.encodeToString(bb.array(), Base64.NO_WRAP);
        }
    }
    private volatile String extrasJson = "{}";
    private volatile String state = "idle";
    private volatile float progress = 0f;
    private volatile String resultMeta = null;
    private volatile String resultB64 = null;

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        WebView.setWebContentsDebuggingEnabled(true);
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setAllowFileAccess(true);
        s.setDomStorageEnabled(true);
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onConsoleMessage(ConsoleMessage m) {
                Log.i(TAG, "js: " + m.message() + " @" + m.lineNumber());
                return true;
            }
        });
        web.setWebViewClient(new android.webkit.WebViewClient());   // keep page navigation (e.g. sonar.html) inside the app
        web.addJavascriptInterface(new Bridge(), "Native");
        setContentView(web);
        readExtras(getIntent());
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 1);
        }
        sm = getSystemService(SensorManager.class);
        tts = new TextToSpeech(this, status -> {
            ttsReady = status == TextToSpeech.SUCCESS;
            if (ttsReady) tts.setLanguage(Locale.US);
        });
        web.loadUrl("file:///android_asset/native.html");
    }

    @Override
    protected void onResume() {
        super.onResume();
        int[] types = {Sensor.TYPE_GAME_ROTATION_VECTOR, Sensor.TYPE_GYROSCOPE, Sensor.TYPE_GRAVITY};
        for (int t : types) {
            Sensor s = sm.getDefaultSensor(t);
            if (s != null) sm.registerListener(this, s, SensorManager.SENSOR_DELAY_GAME);
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        sm.unregisterListener(this);
        stopSonar();   // never keep pinging in the background
        if (web != null) web.evaluateJavascript("window.onSonarStopped && onSonarStopped()", null);
    }

    @Override
    protected void onDestroy() {
        if (tts != null) tts.shutdown();
        super.onDestroy();
    }

    @Override
    public void onSensorChanged(SensorEvent e) {
        switch (e.sensor.getType()) {
            case Sensor.TYPE_GAME_ROTATION_VECTOR:
                SensorManager.getRotationMatrixFromVector(rotMat, e.values);
                SensorManager.getOrientation(rotMat, orient);
                yawDeg = (float) Math.toDegrees(orient[0]);
                break;
            case Sensor.TYPE_GYROSCOPE:
                gyroMag = (float) Math.sqrt(e.values[0] * e.values[0] + e.values[1] * e.values[1] + e.values[2] * e.values[2]);
                break;
            case Sensor.TYPE_GRAVITY:
                System.arraycopy(e.values, 0, gravity, 0, 3);
                break;
        }
    }

    @Override
    public void onAccuracyChanged(Sensor s, int a) {
    }

    /** 32-bit float WAV (format tag 3), interleaved. */
    private static void writeWav(File f, float[] data, int n, int channels, int sr) throws IOException {
        int dataBytes = n * 4;
        ByteBuffer h = ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN);
        h.put("RIFF".getBytes(StandardCharsets.US_ASCII)).putInt(36 + dataBytes)
                .put("WAVE".getBytes(StandardCharsets.US_ASCII))
                .put("fmt ".getBytes(StandardCharsets.US_ASCII)).putInt(16)
                .putShort((short) 3).putShort((short) channels).putInt(sr)
                .putInt(sr * channels * 4).putShort((short) (channels * 4)).putShort((short) 32)
                .put("data".getBytes(StandardCharsets.US_ASCII)).putInt(dataBytes);
        ByteBuffer b = ByteBuffer.allocate(dataBytes).order(ByteOrder.LITTLE_ENDIAN);
        b.asFloatBuffer().put(data, 0, n);
        try (FileOutputStream o = new FileOutputStream(f)) {
            o.write(h.array());
            o.write(b.array());
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        readExtras(intent);
        web.evaluateJavascript("window.onIntent && onIntent()", null);
    }

    private void readExtras(Intent i) {
        try {
            JSONObject o = new JSONObject();
            o.put("autorun", i.getBooleanExtra("autorun", false));
            String c = i.getStringExtra("configs");
            if (c != null) o.put("configs", c);
            o.put("delay", i.getIntExtra("delay", 0));
            extrasJson = o.toString();
        } catch (JSONException ignored) {
        }
    }

    // ---------- helpers ----------
    private static Object num(float v) {
        return (Float.isNaN(v) || Float.isInfinite(v) || v <= -3e38f) ? JSONObject.NULL : (Object) (double) v;
    }

    private static JSONArray coord(MicrophoneInfo.Coordinate3F c) {
        JSONArray a = new JSONArray();
        a.put(num(c.x)).put(num(c.y)).put(num(c.z));
        return a;
    }

    private static JSONObject micJson(MicrophoneInfo m) throws JSONException {
        JSONObject j = new JSONObject();
        j.put("id", m.getId());
        j.put("desc", m.getDescription());
        j.put("type", m.getType());
        j.put("address", m.getAddress());
        j.put("location", m.getLocation());
        j.put("group", m.getGroup());
        j.put("indexInGroup", m.getIndexInTheGroup());
        j.put("position_m", coord(m.getPosition()));
        j.put("orientation", coord(m.getOrientation()));
        j.put("directionality", m.getDirectionality());
        j.put("sensitivity_dBFS", num(m.getSensitivity()));
        j.put("maxSpl", num(m.getMaxSpl()));
        JSONArray cm = new JSONArray();
        for (Pair<Integer, Integer> p : m.getChannelMapping()) cm.put(p.first + ":" + p.second);
        j.put("channelMapping", cm);
        return j;
    }

    private static int sourceId(String name) {
        switch (name) {
            case "MIC": return MediaRecorder.AudioSource.MIC;
            case "CAMCORDER": return MediaRecorder.AudioSource.CAMCORDER;
            case "VOICE_RECOGNITION": return MediaRecorder.AudioSource.VOICE_RECOGNITION;
            case "VOICE_COMMUNICATION": return MediaRecorder.AudioSource.VOICE_COMMUNICATION;
            case "VOICE_PERFORMANCE": return MediaRecorder.AudioSource.VOICE_PERFORMANCE;
            case "DEFAULT": return MediaRecorder.AudioSource.DEFAULT;
            case "UNPROCESSED":
            default: return MediaRecorder.AudioSource.UNPROCESSED;
        }
    }

    // ---------- record + play ----------
    private void record(String b64, int sr, String source, int channels, String saveRel) {
        JSONObject out = new JSONObject();
        AudioRecord rec = null;
        AudioTrack trk = null;
        String data = null;
        try {
            out.put("source", source);
            out.put("requestedChannels", channels);

            byte[] pb = Base64.decode(b64, Base64.DEFAULT);
            FloatBuffer fb = ByteBuffer.wrap(pb).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer();
            final float[] play = new float[fb.remaining()];
            fb.get(play);
            int playFrames = play.length / 2;

            AudioManager am = getSystemService(AudioManager.class);
            int mx = am.getStreamMaxVolume(AudioManager.STREAM_MUSIC);
            int vol = Math.round(mx * 0.8f);
            am.setStreamVolume(AudioManager.STREAM_MUSIC, vol, 0);
            out.put("volume", vol + "/" + mx);

            AudioFormat.Builder fbld = new AudioFormat.Builder()
                    .setEncoding(AudioFormat.ENCODING_PCM_FLOAT).setSampleRate(sr);
            if (channels == 1) fbld.setChannelMask(AudioFormat.CHANNEL_IN_MONO);
            else if (channels == 2) fbld.setChannelMask(AudioFormat.CHANNEL_IN_STEREO);
            else fbld.setChannelIndexMask((1 << channels) - 1);
            int minBuf = AudioRecord.getMinBufferSize(sr,
                    channels == 1 ? AudioFormat.CHANNEL_IN_MONO : AudioFormat.CHANNEL_IN_STEREO,
                    AudioFormat.ENCODING_PCM_FLOAT);
            rec = new AudioRecord.Builder()
                    .setAudioSource(sourceId(source))
                    .setAudioFormat(fbld.build())
                    .setBufferSizeInBytes(Math.max(minBuf * 4, sr * channels * 4))
                    .build();
            if (rec.getState() != AudioRecord.STATE_INITIALIZED)
                throw new IllegalStateException("AudioRecord not initialized");
            final int C = rec.getChannelCount();
            out.put("channels", C);
            out.put("sampleRate", rec.getSampleRate());
            out.put("format", String.valueOf(rec.getFormat()));

            int outMin = AudioTrack.getMinBufferSize(sr, AudioFormat.CHANNEL_OUT_STEREO, AudioFormat.ENCODING_PCM_FLOAT);
            trk = new AudioTrack.Builder()
                    .setAudioAttributes(new AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_MEDIA)
                            .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC).build())
                    .setAudioFormat(new AudioFormat.Builder()
                            .setEncoding(AudioFormat.ENCODING_PCM_FLOAT).setSampleRate(sr)
                            .setChannelMask(AudioFormat.CHANNEL_OUT_STEREO).build())
                    .setTransferMode(AudioTrack.MODE_STREAM)
                    .setBufferSizeInBytes(Math.max(outMin * 4, sr * 2 * 4 / 4))
                    .build();
            final AudioTrack track = trk;

            int pre = (int) (0.4 * sr), post = (int) (0.8 * sr), total = pre + playFrames + post;
            float[] buf = new float[total * C];
            int got = 0;
            boolean started = false;
            Thread writer = null;
            rec.startRecording();
            try {
                JSONArray act = new JSONArray();
                for (MicrophoneInfo m : rec.getActiveMicrophones()) act.put(micJson(m));
                out.put("activeMics", act);
            } catch (IOException e) {
                out.put("activeMicsError", e.toString());
            }
            int chunk = 1024 * C;
            while (got < buf.length) {
                int n = rec.read(buf, got, Math.min(chunk, buf.length - got), AudioRecord.READ_BLOCKING);
                if (n < 0) throw new IllegalStateException("AudioRecord.read error " + n);
                got += n;
                if (!started && got >= pre * C) {
                    started = true;
                    track.play();
                    writer = new Thread(() -> track.write(play, 0, play.length, AudioTrack.WRITE_BLOCKING));
                    writer.start();
                }
                progress = (float) got / buf.length;
            }
            rec.stop();
            if (writer != null) writer.join(3000);
            trk.stop();

            if (saveRel != null && !saveRel.isEmpty() && sessionDir != null) {
                File wav = new File(new File(getFilesDir(), sessionDir), saveRel + ".wav");
                writeWav(wav, buf, got, C, sr);
                out.put("file", sessionDir + "/" + wav.getName());
            }
            ByteBuffer bb = ByteBuffer.allocate(got * 4).order(ByteOrder.LITTLE_ENDIAN);
            bb.asFloatBuffer().put(buf, 0, got);
            data = Base64.encodeToString(bb.array(), Base64.NO_WRAP);
            out.put("frames", got / C);
        } catch (Throwable t) {
            Log.e(TAG, "record failed", t);
            try { out.put("error", t.toString()); } catch (JSONException ignored) { }
        } finally {
            if (rec != null) rec.release();
            if (trk != null) trk.release();
        }
        resultB64 = data;
        resultMeta = out.toString();
        state = "done";
    }

    // ---------- JS bridge ----------
    class Bridge {
        @JavascriptInterface public String extras() { return extrasJson; }

        @JavascriptInterface public void consumeExtras() { extrasJson = "{}"; }

        @JavascriptInterface public boolean hasMicPermission() {
            return checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED;
        }

        @JavascriptInterface public String info() {
            JSONObject o = new JSONObject();
            try {
                o.put("manufacturer", Build.MANUFACTURER);
                o.put("model", Build.MODEL);
                o.put("android", Build.VERSION.RELEASE);
                o.put("sdk", Build.VERSION.SDK_INT);
                AudioManager am = getSystemService(AudioManager.class);
                o.put("outputSampleRate", am.getProperty(AudioManager.PROPERTY_OUTPUT_SAMPLE_RATE));
                o.put("unprocessedSupported", am.getProperty(AudioManager.PROPERTY_SUPPORT_AUDIO_SOURCE_UNPROCESSED));
                JSONArray mics = new JSONArray();
                try {
                    for (MicrophoneInfo m : am.getMicrophones()) mics.put(micJson(m));
                } catch (IOException e) {
                    o.put("micsError", e.toString());
                }
                o.put("microphones", mics);
                JSONArray ins = new JSONArray();
                for (AudioDeviceInfo d : am.getDevices(AudioManager.GET_DEVICES_INPUTS)) {
                    JSONObject j = new JSONObject();
                    j.put("id", d.getId());
                    j.put("type", d.getType());
                    j.put("address", d.getAddress());
                    JSONArray cc = new JSONArray();
                    for (int c : d.getChannelCounts()) cc.put(c);
                    j.put("channelCounts", cc);
                    JSONArray im = new JSONArray();
                    for (int c : d.getChannelIndexMasks()) im.put(c);
                    j.put("channelIndexMasks", im);
                    ins.put(j);
                }
                o.put("inputDevices", ins);
            } catch (Exception e) {
                try { o.put("infoError", e.toString()); } catch (JSONException ignored) { }
            }
            return o.toString();
        }

        @JavascriptInterface public String start(String b64, int sr, String source, int channels, String saveRel) {
            if ("running".equals(state)) return "busy";
            if (!hasMicPermission()) return "no mic permission";
            state = "running";
            progress = 0f;
            resultMeta = null;
            resultB64 = null;
            new Thread(() -> record(b64, sr, source, channels, saveRel), "echo-record").start();
            return "ok";
        }

        /** Yaw (deg, game rotation vector, no magnetometer), gyro magnitude (rad/s), gravity (m/s^2). */
        @JavascriptInterface public String orientation() {
            return "{\"yaw\":" + yawDeg + ",\"gyro\":" + gyroMag
                    + ",\"g\":[" + gravity[0] + "," + gravity[1] + "," + gravity[2] + "]}";
        }

        @JavascriptInterface public boolean say(String text) {
            if (!ttsReady) return false;
            tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "echo");
            return true;
        }

        @JavascriptInterface public boolean speaking() { return ttsReady && tts.isSpeaking(); }

        @JavascriptInterface public void beep() {
            ToneGenerator tg = new ToneGenerator(AudioManager.STREAM_MUSIC, 80);
            tg.startTone(ToneGenerator.TONE_PROP_BEEP2, 300);
            new android.os.Handler(android.os.Looper.getMainLooper()).postDelayed(tg::release, 500);
        }

        @JavascriptInterface public String sonarStart(String pingB64, int periodFrames, int sr) {
            if (!hasMicPermission()) return "no mic permission";
            return startSonar(pingB64, periodFrames, sr);
        }

        @JavascriptInterface public void sonarStop() { stopSonar(); }

        /** 'portrait' | 'reverse' (bottom edge forward) | 'landscape' (upright, bottom edge on the right). */
        @JavascriptInterface public void setOrient(String mode) {
            final int o = "reverse".equals(mode) ? android.content.pm.ActivityInfo.SCREEN_ORIENTATION_REVERSE_PORTRAIT
                    : "landscape".equals(mode) ? android.content.pm.ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
                    : android.content.pm.ActivityInfo.SCREEN_ORIENTATION_PORTRAIT;
            runOnUiThread(() -> setRequestedOrientation(o));
        }

        /** Sonar screen is used with the phone held bottom-edge forward: show the UI rotated 180 degrees. */
        @JavascriptInterface public void setReversed(boolean reversed) {
            runOnUiThread(() -> setRequestedOrientation(reversed
                    ? android.content.pm.ActivityInfo.SCREEN_ORIENTATION_REVERSE_PORTRAIT
                    : android.content.pm.ActivityInfo.SCREEN_ORIENTATION_PORTRAIT));
        }

        @JavascriptInterface public String sonarRead(int frames, int ch) { return getSonar(frames, ch); }

        @JavascriptInterface public String sonarReadBoth(int frames) { return getSonarBoth(frames); }

        @JavascriptInterface public String newSession() {
            String name = "sweep-" + new java.text.SimpleDateFormat("yyyyMMdd-HHmmss", Locale.US).format(new java.util.Date());
            File d = new File(getFilesDir(), name);
            if (!d.mkdirs() && !d.isDirectory()) return "";
            sessionDir = name;
            return name;
        }

        @JavascriptInterface public String saveSessionText(String fileName, String text) {
            if (sessionDir == null) return "no session";
            try (FileOutputStream f = new FileOutputStream(new File(new File(getFilesDir(), sessionDir), fileName))) {
                f.write(text.getBytes(StandardCharsets.UTF_8));
                return sessionDir + "/" + fileName;
            } catch (IOException e) {
                return "save failed: " + e;
            }
        }

        @JavascriptInterface public String poll() { return state + "|" + progress; }

        @JavascriptInterface public String result() {
            String r = resultMeta;
            resultMeta = null;
            state = "idle";
            return r;
        }

        @JavascriptInterface public String resultB64() {
            String r = resultB64;
            resultB64 = null;
            return r;
        }

        @JavascriptInterface public String save(String json) {
            try {
                byte[] b = json.getBytes(StandardCharsets.UTF_8);
                File dir = getFilesDir();
                try (FileOutputStream f = new FileOutputStream(new File(dir, "latest.json"))) { f.write(b); }
                File stamped = new File(dir, "report-" + System.currentTimeMillis() + ".json");
                try (FileOutputStream f = new FileOutputStream(stamped)) { f.write(b); }
                Log.i(TAG, "report saved: " + stamped.getName());
                return stamped.getName();
            } catch (IOException e) {
                return "save failed: " + e;
            }
        }
    }
}
