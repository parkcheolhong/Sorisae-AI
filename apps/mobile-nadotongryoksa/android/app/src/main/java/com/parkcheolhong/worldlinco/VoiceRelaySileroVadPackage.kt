package com.parkcheolhong.worldlinco

import com.facebook.react.ReactPackage
import com.facebook.react.bridge.NativeModule
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.uimanager.ViewManager

/**
 * VoiceRelaySileroVad 수동 등록 패키지 — 에너지 VAD 재구성판(autolink 대상 아님).
 */
class VoiceRelaySileroVadPackage : ReactPackage {
    override fun createNativeModules(
        reactContext: ReactApplicationContext
    ): List<NativeModule> = listOf(VoiceRelaySileroVadModule(reactContext))

    override fun createViewManagers(
        reactContext: ReactApplicationContext
    ): List<ViewManager<*, *>> = emptyList()
}
