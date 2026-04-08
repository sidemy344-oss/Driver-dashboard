package com.driverdashboard.service

import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

/**
 * Minimal launcher activity.
 * Its only job is to ask the user to grant the
 * "Display over other apps" (SYSTEM_ALERT_WINDOW) permission,
 * then start RideObserverService.
 */
class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Simple inline layout — no XML needed for this stub
        val layout = android.widget.LinearLayout(this).apply {
            orientation = android.widget.LinearLayout.VERTICAL
            gravity = android.view.Gravity.CENTER
            setPadding(48, 48, 48, 48)
        }

        val title = TextView(this).apply {
            text = "Driver Dashboard"
            textSize = 22f
            gravity = android.view.Gravity.CENTER
        }

        val status = TextView(this).apply {
            text = if (Settings.canDrawOverlays(this@MainActivity))
                "✓ Overlay permission granted"
            else
                "⚠ Overlay permission required"
            textSize = 14f
            gravity = android.view.Gravity.CENTER
            setPadding(0, 24, 0, 24)
        }

        val btn = Button(this).apply {
            text = if (Settings.canDrawOverlays(this@MainActivity))
                "Start Service"
            else
                "Grant Overlay Permission"

            setOnClickListener {
                if (!Settings.canDrawOverlays(this@MainActivity)) {
                    // Send user to the system permission screen
                    val intent = Intent(
                        Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                        Uri.parse("package:${packageName}")
                    )
                    startActivity(intent)
                } else {
                    // Permission already granted — start the service
                    startForegroundService(
                        Intent(this@MainActivity, RideObserverService::class.java)
                    )
                    status.text = "✓ Service started — you can close this screen"
                }
            }
        }

        layout.addView(title)
        layout.addView(status)
        layout.addView(btn)
        setContentView(layout)
    }

    override fun onResume() {
        super.onResume()
        // Auto-start service if permission was just granted
        if (Settings.canDrawOverlays(this)) {
            startForegroundService(
                Intent(this, RideObserverService::class.java)
            )
        }
    }
}
