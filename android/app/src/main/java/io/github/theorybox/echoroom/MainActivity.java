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
import android.media.AudioTrack;
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

/**
 * Thin native shell: plays the test signal and records all phone mics at the same
 * time (AudioRecord, multi-channel), then hands the raw samples to the web UI
 * (assets/native.html + shared dsp.js) for analysis.
 *
 * adb autorun:  am start -n io.github.theorybox.echoroom/.MainActivity
 *                 --ez autorun true [--es configs "UNPROCESSED:2,CAMCORDER:2"] [--ei delay 10]
 * Report:       run-as io.github.theorybox.echoroom cat files/latest.json
 */
public class MainActivity extends Activity {
    static final String TAG = "EchoRoom";

    private WebView web;
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
        web.addJavascriptInterface(new Bridge(), "Native");
        setContentView(web);
        readExtras(getIntent());
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, 1);
        }
        web.loadUrl("file:///android_asset/native.html");
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
    private void record(String b64, int sr, String source, int channels) {
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

        @JavascriptInterface public String start(String b64, int sr, String source, int channels) {
            if ("running".equals(state)) return "busy";
            if (!hasMicPermission()) return "no mic permission";
            state = "running";
            progress = 0f;
            resultMeta = null;
            resultB64 = null;
            new Thread(() -> record(b64, sr, source, channels), "echo-record").start();
            return "ok";
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
