package com.roadlords.gpsmock

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log

/**
 * Prijíma ADB broadcast príkazy a spúšťa GPS Mock Service.
 *
 * Použitie:
 * adb shell am broadcast -a com.roadlords.gpsmock.START -e gpx "/sdcard/route.gpx" -e speed 80
 * adb shell am broadcast -a com.roadlords.gpsmock.STOP
 * adb shell am broadcast -a com.roadlords.gpsmock.SET -e lat 48.15 -e lon 17.10
 */
class CommandReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        Log.i("GpsMock", "Received: ${intent.action}")

        val serviceIntent = Intent(context, GpsMockService::class.java).apply {
            action = intent.action
            intent.extras?.let { putExtras(it) }
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(serviceIntent)
        } else {
            context.startService(serviceIntent)
        }
    }
}
