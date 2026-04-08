package com.driverdashboard.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat

/**
 * Foreground service that hosts the HUD overlay.
 *
 * Lifecycle:
 *  onCreate  → show overlay
 *  onDestroy → hide overlay
 *
 * TODO: Wire up your screen-reading / accessibility logic here
 *       and call overlayManager.update(result) whenever new
 *       ride data is available.
 */
class RideObserverService : Service() {

    companion object {
        private const val TAG = "RideObserverService"
        private const val CHANNEL_ID = "driver_dashboard_channel"
        private const val NOTIFICATION_ID = 1
    }

    private lateinit var overlayManager: OverlayManager

    override fun onCreate() {
        super.onCreate()
        Log.d(TAG, "Service created")

        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification())

        overlayManager = OverlayManager(this)
        overlayManager.show()

        // ── Stub: push a default result so the HUD renders immediately ──────
        val defaultResult = EvaluationResult(
            pkm            = 0.0f,
            tier           = ProfitTier.MEDIUM,
            isHighRisk     = false,
            passengerWarning = null
        )
        overlayManager.update(defaultResult)
        // ─────────────────────────────────────────────────────────────────────
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(TAG, "Service started")
        // Return START_STICKY so Android restarts the service if it is killed
        return START_STICKY
    }

    override fun onDestroy() {
        super.onDestroy()
        overlayManager.destroy()
        Log.d(TAG, "Service destroyed")
    }

    // Services don't bind in this app
    override fun onBind(intent: Intent?): IBinder? = null

    // ── Notification helpers ──────────────────────────────────────────────────

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Driver Dashboard",
            NotificationManager.IMPORTANCE_LOW          // Silent — no sound/vibration
        ).apply {
            description = "Shows the earnings HUD overlay while driving"
        }
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(channel)
    }

    private fun buildNotification(): Notification =
        NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Driver Dashboard Active")
            .setContentText("Monitoring ride earnings…")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .setOngoing(true)
            .build()
}
