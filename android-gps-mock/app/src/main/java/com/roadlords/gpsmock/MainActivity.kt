package com.roadlords.gpsmock

import android.Manifest
import android.app.Activity
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.widget.Toast

/**
 * Minimálna aktivita - spustí GPS Mock service a zatvorí sa.
 * Na Android 13+ najprv požiada o notification permission.
 */
class MainActivity : Activity() {

    companion object {
        private const val REQUEST_NOTIFICATION_PERMISSION = 1
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Android 13+ requires notification permission for foreground services
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), REQUEST_NOTIFICATION_PERMISSION)
                return
            }
        }

        startServiceAndFinish()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)

        if (requestCode == REQUEST_NOTIFICATION_PERMISSION) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                startServiceAndFinish()
            } else {
                Toast.makeText(this, "GPS Mock needs notification permission to run", Toast.LENGTH_LONG).show()
                finish()
            }
        }
    }

    private fun startServiceAndFinish() {
        // Start the GPS Mock foreground service
        val serviceIntent = Intent(this, GpsMockService::class.java).apply {
            action = GpsMockService.ACTION_START
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent)
        } else {
            startService(serviceIntent)
        }

        Toast.makeText(this, "GPS Mock service started", Toast.LENGTH_SHORT).show()
        finish()
    }
}
