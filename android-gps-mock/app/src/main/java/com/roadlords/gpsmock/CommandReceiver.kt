package com.roadlords.gpsmock

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

/**
 * Prijíma ADB broadcast príkazy a spúšťa GPS Mock Service.
 *
 * Použitie:
 * adb shell am broadcast -a com.roadlords.gpsmock.START -e gpx "/sdcard/route.gpx" -e speed 80
 * adb shell am broadcast -a com.roadlords.gpsmock.STOP
 * adb shell am broadcast -a com.roadlords.gpsmock.SET --ef lat 48.15 --ef lon 17.10
 */
class CommandReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        Log.i("GpsMock", "Received broadcast: ${intent.action}")

        // For Android 12+ (S), we can't start foreground service from broadcast
        // So we use a regular startService() and let the service call startForeground() itself
        val serviceIntent = Intent(context, GpsMockService::class.java).apply {
            action = intent.action
            intent.extras?.let { putExtras(it) }
        }

        try {
            context.startService(serviceIntent)
            Log.i("GpsMock", "Service intent sent successfully")
        } catch (e: Exception) {
            Log.e("GpsMock", "Failed to start service: ${e.message}")
        }
    }
}
