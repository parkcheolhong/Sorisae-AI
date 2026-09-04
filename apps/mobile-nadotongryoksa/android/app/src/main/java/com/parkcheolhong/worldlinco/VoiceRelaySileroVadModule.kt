package com.parkcheolhong.worldlinco

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.WritableMap
import com.facebook.react.modules.core.DeviceEventManagerModule
import java.io.File
import java.io.FileOutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.util.concurrent.atomic.AtomicBoolean
import kotlin.math.log10
import kotlin.math.sqrt

/**
 * VoiceRelaySileroVad 네이티브 모듈 (복구 재구성판).
 *
 * 원본은 silero ONNX 추론 기반이었으나 모듈 소스가 유실되어, 동일한 JS 계약
 * (startMonitor/stopMonitor/beginCapture/endCapture + speech_start/speech_end 이벤트)을
 * RMS 에너지 VAD로 재구현했다. VOICE_COMMUNICATION 소스(AEC 적용) 16kHz mono 16bit.
 *
 * - speech 판정: 프레임 RMS dB가 진입 임계(-40dBFS) 이상이 speechMs 누적 → speech_start
 * - endpoint 판정: 종료 임계(-46dBFS, 히스테리시스) 미만이 silenceMs 지속 → speech_end
 * - capture: beginCapture~endCapture 구간 PCM을 WAV로 기록(peak/rms/duration 산출)
 */
class VoiceRelaySileroVadModule(private val reactContext: ReactApplicationContext) :
    ReactContextBaseJavaModule(reactContext) {

    companion object {
        const val NAME = "VoiceRelaySileroVad"
        private const val TAG = "VoiceRelaySileroVad"
        private const val EVENT_NAME = "VoiceRelaySileroVadEvent"

        private const val SAMPLE_RATE = 16_000
        private const val FRAME_MS = 20
        private const val FRAME_SAMPLES = SAMPLE_RATE * FRAME_MS / 1000 // 320
        private const val FRAME_BYTES = FRAME_SAMPLES * 2

        /** 진입/종료 임계(dBFS) — 히스테리시스로 플리커 방지. */
        private const val SPEECH_ENTER_DB = -40.0
        private const val SPEECH_EXIT_DB = -46.0
        private const val FULL_SCALE = 32768.0
    }

    private var audioRecord: AudioRecord? = null
    private var monitorThread: Thread? = null
    private val monitorRunning = AtomicBoolean(false)
    private val captureActive = AtomicBoolean(false)

    // VAD 상태
    private var inSpeech = false
    private var speechRunMs = 0
    private var silenceRunMs = 0
    private var speechDurationMs = 0L
    private var silenceDurationMs = 0L

    // 캡처 버퍼
    private val captureBuffer = java.util.concurrent.ConcurrentLinkedQueue<ByteArray>()
    private var captureBytes = 0L

    // 설정
    private var silenceMsConfig = 1_400.0
    private var speechMsConfig = 120.0

    override fun getName(): String = NAME

    private fun hasMicPermission(): Boolean =
        reactContext.checkSelfPermission(android.Manifest.permission.RECORD_AUDIO) ==
            android.content.pm.PackageManager.PERMISSION_GRANTED

    @ReactMethod
    fun isSupported(promise: Promise) {
        // 마이크 권한은 startMonitor 시점에 판정한다(앱 시작 프롭이 권한 허가 전에 와도
        // false로 캐시되는 문제 방지). 모듈이 로드됐다는 것 자체가 지원 가능 신호.
        promise.resolve(true)
    }

    @ReactMethod
    fun startMonitor(silenceMs: Double, speechMs: Double, promise: Promise) {
        if (!hasMicPermission()) {
            promise.resolve(false)
            return
        }
        if (monitorRunning.get()) {
            // 이미 동작 중 — 설정만 갱신하고 성공.
            silenceMsConfig = silenceMs
            speechMsConfig = speechMs
            promise.resolve(true)
            return
        }
        val started = startAudioStream(silenceMs, speechMs)
        promise.resolve(started)
    }

    /** AudioRecord + 모니터 스레드 기동 (startMonitor/beginCapture 공용). */
    private fun startAudioStream(silenceMs: Double, speechMs: Double): Boolean {
        return try {
            val minBuf = AudioRecord.getMinBufferSize(
                SAMPLE_RATE, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT
            )
            val record = AudioRecord(
                MediaRecorder.AudioSource.VOICE_COMMUNICATION,
                SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                maxOf(minBuf, FRAME_BYTES * 10)
            )
            if (record.state != AudioRecord.STATE_INITIALIZED) {
                record.release()
                return false
            }
            audioRecord = record
            silenceMsConfig = silenceMs
            speechMsConfig = speechMs
            resetVadState()
            record.startRecording()
            monitorRunning.set(true)
            monitorThread = Thread {
                val pcm = ByteArray(FRAME_BYTES)
                while (monitorRunning.get()) {
                    val read = try {
                        audioRecord?.read(pcm, 0, FRAME_BYTES) ?: -1
                    } catch (e: Exception) {
                        Log.w(TAG, "audio read failed", e)
                        -1
                    }
                    if (read <= 0) {
                        continue
                    }
                    processFrame(pcm, read)
                }
            }.also { it.start() }
            true
        } catch (e: Exception) {
            Log.w(TAG, "startAudioStream failed", e)
            cleanupAudio()
            false
        }
    }

    @ReactMethod
    fun stopMonitor(promise: Promise) {
        try {
            monitorRunning.set(false)
            monitorThread?.join(300)
            monitorThread = null
            cleanupAudio()
            if (inSpeech) {
                emitEvent("speech_end")
            }
            resetVadState()
            promise.resolve(true)
        } catch (e: Exception) {
            Log.w(TAG, "stopMonitor failed", e)
            promise.resolve(false)
        }
    }

    @ReactMethod
    fun beginCapture(promise: Promise) {
        if (!hasMicPermission()) {
            promise.resolve(false)
            return
        }
        // 모니터가 꺼져 있으면 캡처용으로 스트림을 띄운다(기본 경계값으로 VAD도 병행).
        if (!monitorRunning.get()) {
            val started = startAudioStream(silenceMsConfig, speechMsConfig)
            if (!started) {
                promise.resolve(false)
                return
            }
        }
        captureBuffer.clear()
        captureBytes = 0L
        captureActive.set(true)
        promise.resolve(true)
    }

    @ReactMethod
    fun endCapture(outputPath: String, promise: Promise) {
        captureActive.set(false)
        val chunks = mutableListOf<ByteArray>()
        var total = 0L
        while (true) {
            val chunk = captureBuffer.poll() ?: break
            chunks.add(chunk)
            total += chunk.size
        }
        captureBuffer.clear()
        captureBytes = 0L
        if (chunks.isEmpty()) {
            promise.resolve(null)
            return
        }
        try {
            val out = File(outputPath)
            out.parentFile?.mkdirs()
            FileOutputStream(out).use { fos ->
                writeWavHeader(fos, total)
                for (chunk in chunks) fos.write(chunk)
            }
            promise.resolve(buildCaptureResult(out.absolutePath, chunks))
        } catch (e: Exception) {
            Log.w(TAG, "endCapture failed", e)
            promise.resolve(null)
        }
    }

    @ReactMethod
    fun addListener(eventName: String) {
        // NativeEventEmitter 호환용 no-op (이벤트는 DeviceEventManagerModule로 발송)
    }

    @ReactMethod
    fun removeListeners(count: Int) {
        // no-op
    }

    override fun invalidate() {
        monitorRunning.set(false)
        captureActive.set(false)
        monitorThread = null
        cleanupAudio()
        super.invalidate()
    }

    // ── 내부 ────────────────────────────────────────────────────────────────

    private fun resetVadState() {
        inSpeech = false
        speechRunMs = 0
        silenceRunMs = 0
        speechDurationMs = 0
        silenceDurationMs = 0
    }

    private fun cleanupAudio() {
        try {
            audioRecord?.let {
                if (it.state == AudioRecord.STATE_INITIALIZED) {
                    it.stop()
                }
                it.release()
            }
        } catch (_: Exception) {
        }
        audioRecord = null
    }

    private fun processFrame(pcm: ByteArray, len: Int) {
        if (captureActive.get()) {
            val copy = pcm.copyOf(len)
            captureBuffer.add(copy)
            captureBytes += len
        }
        val rmsDb = computeRmsDb(pcm, len)
        val isVoicedEnter = rmsDb >= SPEECH_ENTER_DB
        val isVoicedStay = rmsDb >= SPEECH_EXIT_DB

        if (!inSpeech) {
            if (isVoicedEnter) {
                speechRunMs += FRAME_MS
                silenceRunMs = 0
                if (speechRunMs >= speechMsConfig) {
                    inSpeech = true
                    speechDurationMs = speechRunMs.toLong()
                    silenceDurationMs = 0
                    emitEvent("speech_start")
                }
            } else {
                speechRunMs = 0
                silenceDurationMs += FRAME_MS
            }
        } else {
            if (isVoicedStay) {
                speechDurationMs += FRAME_MS
                silenceRunMs = 0
                silenceDurationMs = 0
            } else {
                silenceRunMs += FRAME_MS
                silenceDurationMs += FRAME_MS
                if (silenceRunMs >= silenceMsConfig) {
                    inSpeech = false
                    speechRunMs = 0
                    emitEvent("speech_end")
                }
            }
        }
    }

    private fun computeRmsDb(pcm: ByteArray, len: Int): Double {
        val samples = len / 2
        if (samples == 0) return -96.0
        val buf = ByteBuffer.wrap(pcm, 0, len).order(ByteOrder.LITTLE_ENDIAN)
        var sumSq = 0.0
        repeat(samples) {
            val s = buf.short.toDouble()
            sumSq += s * s
        }
        val rms = sqrt(sumSq / samples)
        if (rms <= 0.0) return -96.0
        return 20.0 * log10(rms / FULL_SCALE).coerceAtLeast(1e-6)
    }

    private fun emitEvent(event: String) {
        try {
            val params: WritableMap = Arguments.createMap().apply {
                putString("event", event)
                putDouble("timestampMs", System.currentTimeMillis().toDouble())
                putBoolean("isSpeech", event == "speech_start")
                putDouble("silenceDurationMs", silenceDurationMs.toDouble())
                putDouble("speechDurationMs", speechDurationMs.toDouble())
            }
            reactContext
                .getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java)
                ?.emit(EVENT_NAME, params)
        } catch (e: Exception) {
            Log.w(TAG, "emitEvent failed", e)
        }
    }

    private fun buildCaptureResult(path: String, chunks: List<ByteArray>): WritableMap {
        var peak = 0.0
        var sumSq = 0.0
        var sampleCount = 0L
        for (chunk in chunks) {
            val buf = ByteBuffer.wrap(chunk).order(ByteOrder.LITTLE_ENDIAN)
            while (buf.remaining() >= 2) {
                val s = buf.short.toDouble()
                val abs = kotlin.math.abs(s)
                if (abs > peak) peak = abs
                sumSq += s * s
                sampleCount++
            }
        }
        val rms = if (sampleCount > 0) sqrt(sumSq / sampleCount) else 0.0
        val peakDb = if (peak > 0) 20.0 * log10(peak / FULL_SCALE) else -96.0
        val rmsDb = if (rms > 0) 20.0 * log10(rms / FULL_SCALE) else -96.0
        val byteCount = chunks.sumOf { it.size }.toLong()
        return Arguments.createMap().apply {
            putString("path", path)
            putDouble("byteCount", byteCount.toDouble())
            putDouble("sampleCount", sampleCount.toDouble())
            putDouble("durationMs", sampleCount * 1000.0 / SAMPLE_RATE)
            putDouble("peakDb", peakDb)
            putDouble("rmsDb", rmsDb)
        }
    }

    private fun writeWavHeader(fos: FileOutputStream, dataLen: Long) {
        val totalLen = dataLen + 36
        val header = ByteBuffer.allocate(44).order(ByteOrder.LITTLE_ENDIAN)
        header.put("RIFF".toByteArray())
        header.putInt(totalLen.toInt())
        header.put("WAVE".toByteArray())
        header.put("fmt ".toByteArray())
        header.putInt(16)
        header.putShort(1) // PCM
        header.putShort(1) // mono
        header.putInt(SAMPLE_RATE)
        header.putInt(SAMPLE_RATE * 2) // byte rate
        header.putShort(2) // block align
        header.putShort(16) // bits
        header.put("data".toByteArray())
        header.putInt(dataLen.toInt())
        fos.write(header.array())
    }
}
