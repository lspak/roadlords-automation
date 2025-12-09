package com.roadlords.gpsmock

import android.app.*
import android.content.Context
import android.content.Intent
import android.location.Criteria
import android.location.Location
import android.location.LocationManager
import android.os.*
import android.util.Log
import java.io.File
import javax.xml.parsers.DocumentBuilderFactory
import kotlin.concurrent.thread
import kotlin.math.*

/**
 * Minimálny GPS Mock Service - bez UI, ovládaný cez ADB.
 *
 * Použitie:
 * adb shell am broadcast -a com.roadlords.gpsmock.START -e gpx "/sdcard/route.gpx" -e speed 80
 * adb shell am broadcast -a com.roadlords.gpsmock.STOP
 * adb shell am broadcast -a com.roadlords.gpsmock.SET -e lat 48.15 -e lon 17.10
 */
class GpsMockService : Service() {

    companion object {
        const val TAG = "GpsMock"
        const val CHANNEL_ID = "gps_mock_channel"
        const val NOTIFICATION_ID = 1

        const val ACTION_START = "com.roadlords.gpsmock.START"
        const val ACTION_STOP = "com.roadlords.gpsmock.STOP"
        const val ACTION_SET = "com.roadlords.gpsmock.SET"
    }

    private lateinit var locationManager: LocationManager
    private var isRunning = false
    private var playbackThread: Thread? = null

    // Pre statickú pozíciu - kontinuálny update
    private var staticLocationThread: Thread? = null
    private var staticLat: Double = 0.0
    private var staticLon: Double = 0.0
    private var isHoldingPosition = false

    override fun onCreate() {
        super.onCreate()
        locationManager = getSystemService(Context.LOCATION_SERVICE) as LocationManager
        createNotificationChannel()
        setupMockProvider()
        Log.i(TAG, "GPS Mock Service created")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(NOTIFICATION_ID, createNotification("GPS Mock ready"))

        when (intent?.action) {
            ACTION_START -> {
                val gpxPath = intent.getStringExtra("gpx") ?: ""
                val speed = intent.getFloatExtra("speed", 80f)
                if (gpxPath.isNotEmpty()) {
                    startPlayback(gpxPath, speed)
                }
            }
            ACTION_STOP -> {
                stopPlayback()
            }
            ACTION_SET -> {
                val lat = intent.getFloatExtra("lat", 0f).toDouble()
                val lon = intent.getFloatExtra("lon", 0f).toDouble()
                Log.i(TAG, "SET command received: lat=$lat, lon=$lon")
                if (lat != 0.0 && lon != 0.0) {
                    startHoldingPosition(lat, lon)
                } else {
                    Log.e(TAG, "Invalid coordinates: lat=$lat, lon=$lon")
                }
            }
        }

        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun setupMockProvider() {
        try {
            locationManager.removeTestProvider(LocationManager.GPS_PROVIDER)
        } catch (e: Exception) { }

        try {
            locationManager.addTestProvider(
                LocationManager.GPS_PROVIDER,
                false, false, false, false,
                true, true, true,
                Criteria.POWER_LOW, Criteria.ACCURACY_FINE
            )
            locationManager.setTestProviderEnabled(LocationManager.GPS_PROVIDER, true)
            Log.i(TAG, "Mock provider setup complete")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to setup mock provider: ${e.message}")
        }
    }

    private fun setLocation(lat: Double, lon: Double, speed: Float, bearing: Float) {
        val location = Location(LocationManager.GPS_PROVIDER).apply {
            latitude = lat
            longitude = lon
            altitude = 150.0
            accuracy = 3f
            this.speed = speed
            this.bearing = bearing
            time = System.currentTimeMillis()
            elapsedRealtimeNanos = SystemClock.elapsedRealtimeNanos()
        }

        try {
            locationManager.setTestProviderLocation(LocationManager.GPS_PROVIDER, location)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to set location: ${e.message}")
        }
    }

    private fun startPlayback(gpxPath: String, speedKmh: Float) {
        stopPlayback()

        val points = parseGpx(gpxPath)
        if (points.isEmpty()) {
            Log.e(TAG, "No points in GPX file")
            return
        }

        Log.i(TAG, "Starting playback: ${points.size} points at $speedKmh km/h")
        isRunning = true
        updateNotification("Playing: ${points.size} points")

        playbackThread = thread {
            val speedMs = speedKmh / 3.6f  // km/h to m/s
            var currentIndex = 0

            while (isRunning && currentIndex < points.size - 1) {
                val from = points[currentIndex]
                val to = points[currentIndex + 1]

                val distance = haversineDistance(from.first, from.second, to.first, to.second)
                val bearing = calculateBearing(from.first, from.second, to.first, to.second)
                val travelTime = (distance / speedMs * 1000).toLong()  // ms

                // Interpolate between points
                val steps = maxOf(1, (travelTime / 100).toInt())  // Update every 100ms
                val stepTime = travelTime / steps

                for (step in 0 until steps) {
                    if (!isRunning) break

                    val fraction = step.toFloat() / steps
                    val lat = from.first + (to.first - from.first) * fraction
                    val lon = from.second + (to.second - from.second) * fraction

                    setLocation(lat, lon, speedMs, bearing)
                    Thread.sleep(stepTime)
                }

                currentIndex++
            }

            if (isRunning && points.isNotEmpty()) {
                // Set final position
                val last = points.last()
                setLocation(last.first, last.second, 0f, 0f)
            }

            Log.i(TAG, "Playback finished")
            updateNotification("Playback finished")
        }
    }

    private fun startHoldingPosition(lat: Double, lon: Double) {
        // Zastav akékoľvek prebiehajúce playback
        stopPlayback()

        staticLat = lat
        staticLon = lon
        isHoldingPosition = true

        Log.i(TAG, "Starting to hold position at: $lat, $lon")
        updateNotification("Holding: ${"%.4f".format(lat)}, ${"%.4f".format(lon)}")

        staticLocationThread = thread {
            while (isHoldingPosition) {
                try {
                    setLocation(staticLat, staticLon, 0f, 0f)
                    Thread.sleep(500)  // Update každých 500ms
                } catch (e: InterruptedException) {
                    break
                }
            }
            Log.i(TAG, "Stopped holding position")
        }
    }

    private fun stopHoldingPosition() {
        isHoldingPosition = false
        staticLocationThread?.interrupt()
        staticLocationThread = null
    }

    private fun stopPlayback() {
        isRunning = false
        isHoldingPosition = false
        playbackThread?.interrupt()
        playbackThread = null
        staticLocationThread?.interrupt()
        staticLocationThread = null
        Log.i(TAG, "Playback stopped")
        updateNotification("Stopped")
    }

    private fun parseGpx(path: String): List<Pair<Double, Double>> {
        val points = mutableListOf<Pair<Double, Double>>()
        try {
            val file = File(path)
            val doc = DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(file)
            val trkpts = doc.getElementsByTagName("trkpt")

            for (i in 0 until trkpts.length) {
                val node = trkpts.item(i)
                val lat = node.attributes.getNamedItem("lat").nodeValue.toDouble()
                val lon = node.attributes.getNamedItem("lon").nodeValue.toDouble()
                points.add(Pair(lat, lon))
            }
            Log.i(TAG, "Parsed ${points.size} points from GPX")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to parse GPX: ${e.message}")
        }
        return points
    }

    private fun haversineDistance(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Float {
        val r = 6371000.0  // Earth radius in meters
        val dLat = Math.toRadians(lat2 - lat1)
        val dLon = Math.toRadians(lon2 - lon1)
        val a = sin(dLat / 2).pow(2) + cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) * sin(dLon / 2).pow(2)
        val c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return (r * c).toFloat()
    }

    private fun calculateBearing(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Float {
        val dLon = Math.toRadians(lon2 - lon1)
        val y = sin(dLon) * cos(Math.toRadians(lat2))
        val x = cos(Math.toRadians(lat1)) * sin(Math.toRadians(lat2)) -
                sin(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) * cos(dLon)
        return ((Math.toDegrees(atan2(y, x)) + 360) % 360).toFloat()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID, "GPS Mock", NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    private fun createNotification(text: String): Notification {
        return Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("GPS Mock")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .build()
    }

    private fun updateNotification(text: String) {
        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(NOTIFICATION_ID, createNotification(text))
    }

    override fun onDestroy() {
        stopPlayback()
        try {
            locationManager.removeTestProvider(LocationManager.GPS_PROVIDER)
        } catch (e: Exception) { }
        super.onDestroy()
    }
}
