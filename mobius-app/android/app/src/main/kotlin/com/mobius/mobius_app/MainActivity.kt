package com.mobius.mobius_app

import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel
import com.mobius.app.MobiusAccessibilityService

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "com.mobius/device")
            .setMethodCallHandler { call, result ->
                val svc = MobiusAccessibilityService.getInstance()
                if (svc == null) {
                    result.error("SERVICE_UNAVAILABLE", "Enable Accessibility Service first", null)
                    return@setMethodCallHandler
                }
                when (call.method) {
                    "openApp" -> result.success(svc.openApp(call.argument("packageName") ?: ""))
                    "readScreen" -> result.success(svc.readScreen())
                    "tapElement" -> result.success(svc.tapElement(call.argument("contentDesc") ?: ""))
                    else -> result.notImplemented()
                }
            }
    }
}
