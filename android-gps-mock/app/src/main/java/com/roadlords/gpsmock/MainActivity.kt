package com.roadlords.gpsmock

import android.app.Activity
import android.os.Bundle
import android.widget.Toast

/**
 * Minimálna aktivita - len zobrazí správu a zatvorí sa.
 * Aplikácia je určená na ovládanie cez ADB, nie cez UI.
 */
class MainActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Toast.makeText(this, "GPS Mock - use ADB commands", Toast.LENGTH_LONG).show()
        finish()  // Okamžite zavrieť
    }
}
