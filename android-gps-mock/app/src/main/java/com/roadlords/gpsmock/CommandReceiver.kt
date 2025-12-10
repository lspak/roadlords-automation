package com.roadlords.gpsmock

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log

/**
 * Prijíma ADB broadcast príkazy.
 *
 * For Android 12+: Since we can't start service from background broadcast,
 * MainActivity must start the service first, then broadcasts send commands to running service.
 *
 * Použitie:
 * 1. First: adb shell am start -n com.roadlords.gpsmock/.MainActivity  (starts service)
 * 2. Then: adb shell am broadcast -a com.roadlords.gpsmock.SET --ef lat 48.15 --ef lon 17.10
 */
class CommandReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        Log.i("GpsMock", "Received broadcast: ${intent.action}")

        // Try to start service (will work if app is in foreground, e.g., just after MainActivity)
        // If fails due to background restrictions, service should already be running
        val serviceIntent = Intent(context, GpsMockService::class.java).apply {
            action = intent.action
            intent.extras?.let { putExtras(it) }
        }

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(serviceIntent)
            } else {
                context.startService(serviceIntent)
            }
            Log.i("GpsMock", "Service started/command sent successfully")
        } catch (e: Exception) {
            Log.e("GpsMock", "Failed to start service (service should already be running): ${e.message}")
        }
    }
}
