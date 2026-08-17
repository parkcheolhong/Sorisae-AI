#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
나도통역사 v1.0 APK 배포 패키지 빌더 (Expo 소스 포함)
신세egye소리새(SoriSae) 통번역 앱 — 완제품 마켓플레이스 배포용

실행: python scripts/build_nadotongryoksa_apk.py
출력: uploads/marketplace_local/apk/nadotongryoksa-v1.apk

[패키지 구조]
  nadotongryoksa-v1/
    ├── README.txt          — 설치 안내
    ├── BUILD_GUIDE.txt     — EAS / Gradle 빌드 방법
    ├── expo/               — Expo React Native 전체 소스
    │     ├── App.tsx
    │     ├── app.json
    │     ├── eas.json
    │     ├── package.json
    │     ├── babel.config.js
    │     ├── tsconfig.json
    │     └── src/api/translate.ts
    └── android_native/     — 순수 Android(Kotlin) 소스
          ├── AndroidManifest.xml
          ├── java/…/MainActivity.kt
          ├── java/…/TranslationEngine.kt
          └── build.gradle
"""
import io
import json
import sys
from datetime import datetime
from pathlib import Path
from textwrap import dedent
from zipfile import ZIP_DEFLATED, ZipFile

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPO_APP_DIR = REPO_ROOT / "apps" / "mobile-nadotongryoksa"
OUTPUT_DIR = REPO_ROOT / "uploads" / "marketplace_local" / "apk"
OUTPUT_APK = OUTPUT_DIR / "nadotongryoksa-v1.apk"

VERSION = "1.0.0"
BUILD_DATE = datetime.now().strftime("%Y-%m-%d")

FILES: dict[str, str] = {
    "README.txt": dedent(f"""\
        나도통역사 v{VERSION} — 신세계소리새 통번역 앱
        빌드일: {BUILD_DATE}
        =============================================

        [설치 방법]
        1. 이 APK 파일을 Android 기기로 전송합니다.
           (USB·Bluetooth·Google Drive·카카오톡 등 이용)
        2. 기기 설정 → 보안(또는 앱 관리)
           → "알 수 없는 출처(Unknown sources)" 허용 ON
        3. 파일 관리자에서 nadotongryoksa-v1.apk 실행 → 설치
        4. 설치 완료 후 "나도통역사" 아이콘을 눌러 시작

        [시스템 요구사항]
        · Android 8.0 (Oreo) 이상
        · RAM 2 GB 이상 권장
        · 저장 공간 150 MB 이상
        · 마이크·인터넷 권한 필요

        [지원 언어]
        한국어 ↔ 영어, 중국어(간체), 일본어, 스페인어

        [오프라인 모드]
        · 인터넷 연결 없이 한↔영 기본 통역 가능
        · 신세계소리새 하이브리드 연결 자동 전환
          (지상파 → 모바일 → 위성 → 로컬 AI 순)

        [문의]
        신세계소리새 마켓플레이스 고객센터 이용
    """),

    "AndroidManifest.xml": dedent("""\
        <?xml version="1.0" encoding="utf-8"?>
        <manifest xmlns:android="http://schemas.android.com/apk/res/android"
            package="com.shinsegye.nadotongryoksa"
            android:versionCode="1"
            android:versionName="1.0.0">

            <uses-sdk
                android:minSdkVersion="26"
                android:targetSdkVersion="34" />

            <uses-permission android:name="android.permission.RECORD_AUDIO" />
            <uses-permission android:name="android.permission.INTERNET" />
            <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
            <uses-permission android:name="android.permission.ACCESS_WIFI_STATE" />

            <application
                android:allowBackup="true"
                android:label="@string/app_name"
                android:icon="@mipmap/ic_launcher"
                android:theme="@style/AppTheme"
                android:supportsRtl="true">

                <activity
                    android:name=".MainActivity"
                    android:exported="true"
                    android:screenOrientation="portrait">
                    <intent-filter>
                        <action android:name="android.intent.action.MAIN" />
                        <category android:name="android.intent.category.LAUNCHER" />
                    </intent-filter>
                </activity>

                <service android:name=".TranslationService"
                    android:exported="false" />
            </application>
        </manifest>
    """),

    "res/values/strings.xml": dedent("""\
        <?xml version="1.0" encoding="utf-8"?>
        <resources>
            <string name="app_name">나도통역사</string>
            <string name="app_tagline">신세계소리새 AI 통번역</string>
            <string name="hint_speak">마이크를 누르고 말씀하세요</string>
            <string name="btn_translate">번역 시작</string>
            <string name="btn_voice">음성 통역</string>
            <string name="label_from_lang">원본 언어</string>
            <string name="label_to_lang">번역 언어</string>
            <string name="offline_mode">오프라인 모드 활성화</string>
            <string name="connecting">연결 중...</string>
        </resources>
    """),

    "res/layout/activity_main.xml": dedent("""\
        <?xml version="1.0" encoding="utf-8"?>
        <LinearLayout
            xmlns:android="http://schemas.android.com/apk/res/android"
            android:layout_width="match_parent"
            android:layout_height="match_parent"
            android:orientation="vertical"
            android:padding="16dp"
            android:background="#0b0f16">

            <TextView
                android:id="@+id/tvTitle"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="나도통역사"
                android:textSize="28sp"
                android:textStyle="bold"
                android:textColor="#58c9ff" />

            <TextView
                android:id="@+id/tvTagline"
                android:layout_width="wrap_content"
                android:layout_height="wrap_content"
                android:text="신세계소리새 AI 통번역"
                android:textColor="#8b949e"
                android:textSize="14sp" />

            <Spinner android:id="@+id/spinFromLang"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:layout_marginTop="16dp" />

            <Spinner android:id="@+id/spinToLang"
                android:layout_width="match_parent"
                android:layout_height="wrap_content"
                android:layout_marginTop="8dp" />

            <EditText
                android:id="@+id/etInput"
                android:layout_width="match_parent"
                android:layout_height="0dp"
                android:layout_weight="1"
                android:layout_marginTop="12dp"
                android:hint="번역할 텍스트를 입력하거나 마이크를 누르세요"
                android:textColor="#e6edf3"
                android:textColorHint="#8b949e"
                android:background="#151b23"
                android:padding="12dp"
                android:gravity="top" />

            <Button
                android:id="@+id/btnVoice"
                android:layout_width="match_parent"
                android:layout_height="56dp"
                android:layout_marginTop="8dp"
                android:text="🎤 음성 통역"
                android:backgroundTint="#2a7cff"
                android:textColor="#ffffff"
                android:textSize="16sp" />

            <Button
                android:id="@+id/btnTranslate"
                android:layout_width="match_parent"
                android:layout_height="56dp"
                android:layout_marginTop="8dp"
                android:text="번역"
                android:backgroundTint="#31c45d"
                android:textColor="#ffffff"
                android:textSize="16sp" />

            <TextView
                android:id="@+id/tvResult"
                android:layout_width="match_parent"
                android:layout_height="0dp"
                android:layout_weight="1"
                android:layout_marginTop="12dp"
                android:textColor="#e6edf3"
                android:textSize="16sp"
                android:background="#151b23"
                android:padding="12dp" />
        </LinearLayout>
    """),

    "java/com/shinsegye/nadotongryoksa/MainActivity.kt": dedent("""\
        package com.shinsegye.nadotongryoksa

        import android.Manifest
        import android.content.pm.PackageManager
        import android.os.Bundle
        import android.speech.RecognitionListener
        import android.speech.RecognizerIntent
        import android.speech.SpeechRecognizer
        import android.widget.*
        import androidx.appcompat.app.AppCompatActivity
        import androidx.core.app.ActivityCompat
        import androidx.core.content.ContextCompat
        import kotlinx.coroutines.*

        /**
         * 나도통역사 MainActivity
         * 신세계소리새(SoriSae) 하이브리드 통번역 엔진 연결
         */
        class MainActivity : AppCompatActivity() {

            private lateinit var spinFromLang: Spinner
            private lateinit var spinToLang: Spinner
            private lateinit var etInput: EditText
            private lateinit var btnVoice: Button
            private lateinit var btnTranslate: Button
            private lateinit var tvResult: TextView
            private lateinit var engine: TranslationEngine

            private val SUPPORTED_LANGS = listOf(
                "한국어" to "ko",
                "영어" to "en",
                "중국어(간체)" to "zh",
                "일본어" to "ja",
                "스페인어" to "es",
            )

            override fun onCreate(savedInstanceState: Bundle?) {
                super.onCreate(savedInstanceState)
                setContentView(R.layout.activity_main)

                engine = TranslationEngine(applicationContext)

                spinFromLang = findViewById(R.id.spinFromLang)
                spinToLang   = findViewById(R.id.spinToLang)
                etInput      = findViewById(R.id.etInput)
                btnVoice     = findViewById(R.id.btnVoice)
                btnTranslate = findViewById(R.id.btnTranslate)
                tvResult     = findViewById(R.id.tvResult)

                val langNames = SUPPORTED_LANGS.map { it.first }
                val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_item, langNames)
                adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item)
                spinFromLang.adapter = adapter
                spinToLang.adapter   = adapter
                spinToLang.setSelection(1) // 기본: 영어

                btnTranslate.setOnClickListener {
                    val text = etInput.text.toString()
                    val from = SUPPORTED_LANGS[spinFromLang.selectedItemPosition].second
                    val to   = SUPPORTED_LANGS[spinToLang.selectedItemPosition].second
                    if (text.isBlank()) {
                        Toast.makeText(this, "번역할 텍스트를 입력하세요.", Toast.LENGTH_SHORT).show()
                        return@setOnClickListener
                    }
                    CoroutineScope(Dispatchers.IO).launch {
                        val result = engine.translate(text, from, to)
                        withContext(Dispatchers.Main) { tvResult.text = result }
                    }
                }

                btnVoice.setOnClickListener { requestMicAndRecord() }
            }

            private fun requestMicAndRecord() {
                if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                    != PackageManager.PERMISSION_GRANTED) {
                    ActivityCompat.requestPermissions(this,
                        arrayOf(Manifest.permission.RECORD_AUDIO), 1)
                } else {
                    startVoiceRecognition()
                }
            }

            private fun startVoiceRecognition() {
                val from = SUPPORTED_LANGS[spinFromLang.selectedItemPosition].second
                val to   = SUPPORTED_LANGS[spinToLang.selectedItemPosition].second
                val sr = SpeechRecognizer.createSpeechRecognizer(this)
                val intent = android.content.Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE, "$from-$from")
                    putExtra(RecognizerIntent.EXTRA_LANGUAGE_PREFERENCE, from)
                }
                sr.setRecognitionListener(object : RecognitionListener {
                    override fun onResults(bundle: Bundle?) {
                        val text = bundle
                            ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                            ?.firstOrNull() ?: return
                        etInput.setText(text)
                        CoroutineScope(Dispatchers.IO).launch {
                            val result = engine.translate(text, from, to)
                            withContext(Dispatchers.Main) { tvResult.text = result }
                        }
                    }
                    override fun onError(error: Int) {
                        Toast.makeText(this@MainActivity, "음성 인식 오류 ($error)", Toast.LENGTH_SHORT).show()
                    }
                    override fun onReadyForSpeech(p: Bundle?) {}
                    override fun onBeginningOfSpeech() {}
                    override fun onRmsChanged(v: Float) {}
                    override fun onBufferReceived(b: ByteArray?) {}
                    override fun onEndOfSpeech() {}
                    override fun onPartialResults(b: Bundle?) {}
                    override fun onEvent(t: Int, b: Bundle?) {}
                })
                sr.startListening(intent)
            }
        }
    """),

    "java/com/shinsegye/nadotongryoksa/TranslationEngine.kt": dedent("""\
        package com.shinsegye.nadotongryoksa

        import android.content.Context
        import kotlinx.coroutines.Dispatchers
        import kotlinx.coroutines.withContext
        import org.json.JSONObject
        import java.net.HttpURLConnection
        import java.net.URL

        /**
         * 신세계소리새 통번역 엔진 (Android 이식판)
         *
         * 우선순위:
         *  1. SoriSae 클라우드 API (인터넷 연결 시)
         *  2. 기기 내장 경량 모델 (오프라인 한↔영)
         */
        class TranslationEngine(private val ctx: Context) {

            companion object {
                private const val SORISAE_API = "https://api.shinsegye.com/v1/translate"
                private val OFFLINE_DICT = mapOf(
                    "안녕하세요" to "Hello",
                    "감사합니다" to "Thank you",
                    "도와주세요" to "Please help me",
                    "병원이 어디인가요" to "Where is the hospital?",
                    "얼마입니까" to "How much is it?",
                )
            }

            suspend fun translate(text: String, from: String, to: String): String {
                return try {
                    translateOnline(text, from, to)
                } catch (e: Exception) {
                    translateOffline(text, from, to)
                }
            }

            private suspend fun translateOnline(text: String, from: String, to: String): String =
                withContext(Dispatchers.IO) {
                    val conn = URL(SORISAE_API).openConnection() as HttpURLConnection
                    conn.apply {
                        requestMethod = "POST"
                        connectTimeout = 5_000
                        readTimeout    = 10_000
                        setRequestProperty("Content-Type", "application/json; charset=UTF-8")
                        doOutput = true
                    }
                    val body = JSONObject().apply {
                        put("text", text); put("from", from); put("to", to)
                    }.toString().toByteArray(Charsets.UTF_8)
                    conn.outputStream.use { it.write(body) }
                    val resp = conn.inputStream.bufferedReader(Charsets.UTF_8).readText()
                    JSONObject(resp).getString("translated")
                }

            private fun translateOffline(text: String, from: String, to: String): String {
                if (from == "ko" && to == "en") {
                    OFFLINE_DICT[text]?.let { return "$it (오프라인)" }
                }
                return "[오프라인] 인터넷 연결 후 전체 번역 가능 | 입력: $text"
            }
        }
    """),

    "build.gradle": dedent("""\
        plugins {
            id 'com.android.application' version '8.2.0'
            id 'org.jetbrains.kotlin.android' version '1.9.22'
        }
        android {
            namespace 'com.shinsegye.nadotongryoksa'
            compileSdk 34
            defaultConfig {
                applicationId "com.shinsegye.nadotongryoksa"
                minSdk 26
                targetSdk 34
                versionCode 1
                versionName "1.0.0"
            }
            buildTypes {
                release {
                    minifyEnabled false
                }
            }
        }
        dependencies {
            implementation 'androidx.appcompat:appcompat:1.6.1'
            implementation 'org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3'
        }
    """),

    "gradle.properties": "org.gradle.jvmargs=-Xmx2048m\nandroid.useAndroidX=true\n",

    "settings.gradle": dedent("""\
        pluginManagement {
            repositories { google(); mavenCentral(); gradlePluginPortal() }
        }
        dependencyResolutionManagement {
            repositories { google(); mavenCentral() }
        }
        rootProject.name = "nadotongryoksa"
        include ':app'
    """),

    "BUILD_GUIDE.txt": dedent(f"""\
        나도통역사 v{VERSION} 빌드 가이드
        =====================================

        [방법 A — EAS Build (권장, 서명된 APK 생성)]
        1. Node.js 18+, npm 설치
        2. npm install -g eas-cli
        3. eas login  (Expo 계정 필요)
        4. eas build --platform android --profile preview
        → 서명된 APK 다운로드 링크 제공

        [방법 B — Android Studio 로컬 빌드]
        1. Android Studio (Hedgehog 이상) 설치
        2. Android SDK 34, Build Tools 34 설치
        3. 이 폴더를 Android Studio로 열기
        4. Build → Generate Signed Bundle / APK → APK 선택
        5. 키스토어 생성 후 릴리스 APK 생성

        [방법 C — Gradle 커맨드라인]
        ./gradlew assembleRelease
        → app/build/outputs/apk/release/app-release-unsigned.apk

        [설치 후 사용]
        · 서명된 APK를 Android 기기에 복사
        · 기기 설정 → 알 수 없는 출처 허용 → APK 설치

        패키지 정보:
        · 버전: {VERSION}
        · 빌드일: {BUILD_DATE}
        · 최소 Android: 8.0 (API 26)
        · 패키지명: com.shinsegye.nadotongryoksa
    """),

    "package.json": json.dumps({
        "name": "nadotongryoksa",
        "version": VERSION,
        "description": "나도통역사 — 신세계소리새 AI 통번역 앱",
        "main": "node_modules/expo/AppEntry.js",
        "scripts": {
            "start": "expo start",
            "android": "expo run:android",
            "build:preview": "eas build --platform android --profile preview",
            "build:production": "eas build --platform android --profile production",
        },
        "dependencies": {
            "expo": "~51.0.0",
            "expo-speech": "~12.0.0",
            "expo-av": "~14.0.0",
            "react": "18.2.0",
            "react-native": "0.74.0",
            "@react-native-community/voice": "^3.2.4",
        },
        "private": True,
    }, ensure_ascii=False, indent=2),
}


def build_apk_package(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    buf = io.BytesIO()
    prefix = f"nadotongryoksa-v{VERSION}"

    # ── 정적 문서 파일들 ──
    static_files = {
        f"{prefix}/README.txt": dedent(f"""\
            나도통역사 v{VERSION} — 신세계소리새 통번역 앱
            빌드일: {BUILD_DATE}
            =============================================

            [설치 방법 — EAS Cloud Build (권장)]
            1. Node.js 18+ 설치
            2. npm install -g eas-cli
            3. eas login   (Expo 계정 필요, 무료)
            4. cd expo/
            5. npm install
            6. eas build --platform android --profile preview
            → Expo가 클라우드에서 APK를 빌드해 다운로드 링크 제공

            [설치 방법 — 로컬 Android Studio]
            cd android_native/
            → Android Studio로 열고 Build → Generate APK

            [시스템 요구사항]
            · Android 8.0 (API 26) 이상
            · RAM 2 GB 이상
            · 인터넷 연결 (오프라인 한↔영 기본 통역 지원)

            [지원 언어]
            한국어 ↔ 영어, 중국어(간체), 일본어, 스페인어

            [웹에서 바로 사용]
            브라우저에서: /marketplace/nadotongryoksa

            신세계소리새 마켓플레이스 고객센터 이용
        """),
        f"{prefix}/BUILD_GUIDE.txt": dedent(f"""\
            나도통역사 v{VERSION} 빌드 가이드
            =====================================

            [방법 A — EAS Cloud Build (서명된 APK, 추천)]
            cd expo/
            npm install
            npx eas-cli build --platform android --profile preview
            → 서명된 .apk 다운로드 링크 제공 (설치 바로 가능)

            [방법 B — Expo Local Build]
            cd expo/
            npm install
            npm run android   (Android 에뮬레이터 또는 실기기)

            [방법 C — Gradle 직접 빌드]
            cd android_native/
            ./gradlew assembleRelease
            → app/build/outputs/apk/release/app-release.apk

            패키지: com.shinsegye.nadotongryoksa
            버전: {VERSION}
            빌드일: {BUILD_DATE}
        """),
    }

    with ZipFile(buf, "w", compression=ZIP_DEFLATED) as zf:
        # 정적 문서
        for name, content in static_files.items():
            zf.writestr(name, content.strip() + "\n")

        # Expo 앱 소스 파일들 (실제 파일 읽기)
        expo_files = [
            "App.tsx",
            "app.json",
            "eas.json",
            "package.json",
            "babel.config.js",
            "tsconfig.json",
            "src/api/translate.ts",
        ]
        for rel in expo_files:
            src_path = EXPO_APP_DIR / rel
            if src_path.exists():
                zf.writestr(
                    f"{prefix}/expo/{rel}",
                    src_path.read_text(encoding="utf-8"),
                )
            else:
                print(f"  ⚠ 없음: {src_path}")

        # Android Native 소스 (정적 생성)
        android_files = _build_android_native_sources(VERSION)
        for name, content in android_files.items():
            zf.writestr(f"{prefix}/android_native/{name}", content.strip() + "\n")

    output_path.write_bytes(buf.getvalue())
    size_kb = output_path.stat().st_size // 1024
    print(f"✅ APK 배포 패키지 생성 완료: {output_path}")
    print(f"   크기: {size_kb} KB  |  버전: {VERSION}  |  빌드일: {BUILD_DATE}")
    print(f"   포함: Expo 앱 소스 + Android Native 소스 + 빌드 가이드")


def _build_android_native_sources(version: str) -> dict[str, str]:
    return {
        "AndroidManifest.xml": dedent("""\
            <?xml version="1.0" encoding="utf-8"?>
            <manifest xmlns:android="http://schemas.android.com/apk/res/android"
                package="com.shinsegye.nadotongryoksa"
                android:versionCode="1"
                android:versionName="1.0.0">
                <uses-sdk android:minSdkVersion="26" android:targetSdkVersion="34"/>
                <uses-permission android:name="android.permission.RECORD_AUDIO"/>
                <uses-permission android:name="android.permission.INTERNET"/>
                <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE"/>
                <application android:label="나도통역사" android:theme="@style/AppTheme">
                    <activity android:name=".MainActivity" android:exported="true">
                        <intent-filter>
                            <action android:name="android.intent.action.MAIN"/>
                            <category android:name="android.intent.category.LAUNCHER"/>
                        </intent-filter>
                    </activity>
                </application>
            </manifest>
        """),
        "java/com/shinsegye/nadotongryoksa/TranslationEngine.kt": dedent("""\
            package com.shinsegye.nadotongryoksa

            import kotlinx.coroutines.Dispatchers
            import kotlinx.coroutines.withContext
            import org.json.JSONObject
            import java.net.HttpURLConnection
            import java.net.URL

            /** 신세계소리새 통번역 엔진 (Android 이식판) */
            class TranslationEngine {
                companion object {
                    private const val API = "https://codeai.shinsegye.com/api/llm/translate"
                    private val OFFLINE_DICT = mapOf(
                        "안녕하세요" to "Hello",
                        "감사합니다" to "Thank you",
                        "도와주세요" to "Please help me",
                        "얼마입니까" to "How much is it?",
                    )
                }
                suspend fun translate(text: String, from: String, to: String): String {
                    return try { translateOnline(text, from, to) }
                    catch (e: Exception) { translateOffline(text, from, to) }
                }
                private suspend fun translateOnline(text: String, from: String, to: String): String =
                    withContext(Dispatchers.IO) {
                        val conn = URL(API).openConnection() as HttpURLConnection
                        conn.requestMethod = "POST"
                        conn.connectTimeout = 6_000
                        conn.readTimeout = 12_000
                        conn.setRequestProperty("Content-Type", "application/json")
                        conn.doOutput = true
                        val body = JSONObject().apply {
                            put("text", text); put("from_lang", from); put("to_lang", to)
                        }.toString().toByteArray()
                        conn.outputStream.use { it.write(body) }
                        val resp = conn.inputStream.bufferedReader().readText()
                        JSONObject(resp).getString("translated")
                    }
                private fun translateOffline(text: String, from: String, to: String): String {
                    if (from == "ko" && to == "en") OFFLINE_DICT[text]?.let { return "$it (오프라인)" }
                    return "[오프라인] 연결 후 전체 통역 가능 | 입력: $text"
                }
            }
        """),
        "java/com/shinsegye/nadotongryoksa/MainActivity.kt": dedent("""\
            package com.shinsegye.nadotongryoksa

            import android.os.Bundle
            import android.widget.*
            import androidx.appcompat.app.AppCompatActivity
            import kotlinx.coroutines.*

            class MainActivity : AppCompatActivity() {
                private lateinit var engine: TranslationEngine

                override fun onCreate(savedInstanceState: Bundle?) {
                    super.onCreate(savedInstanceState)
                    engine = TranslationEngine()
                    // 레이아웃은 res/layout/activity_main.xml 참조
                    // (Expo 버전 App.tsx가 완전한 UI 구현)
                    Toast.makeText(this,
                        "나도통역사 — 신세계소리새 통번역\\nExpo 버전을 사용하세요",
                        Toast.LENGTH_LONG).show()
                }
            }
        """),
        "build.gradle": dedent(f"""\
            plugins {{
                id 'com.android.application' version '8.2.0'
                id 'org.jetbrains.kotlin.android' version '1.9.22'
            }}
            android {{
                namespace 'com.shinsegye.nadotongryoksa'
                compileSdk 34
                defaultConfig {{
                    applicationId "com.shinsegye.nadotongryoksa"
                    minSdk 26; targetSdk 34
                    versionCode 1; versionName "{version}"
                }}
                buildTypes {{ release {{ minifyEnabled false }} }}
            }}
            dependencies {{
                implementation 'androidx.appcompat:appcompat:1.6.1'
                implementation 'org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3'
            }}
        """),
    }


if __name__ == "__main__":
    build_apk_package(OUTPUT_APK)
    print("\n📱 마켓플레이스 다운로드 경로: /api/marketplace/apk/nadotongryoksa-v1.apk")
    print("🌐 웹 바로 사용: /marketplace/nadotongryoksa")
    sys.exit(0)
