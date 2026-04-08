package com.driverdashboard.service

import android.util.Log

/**
 * Phase 2: Regex Utility
 *
 * Converts raw UI text strings into typed numeric values.
 * All methods are null-safe — they return null on parse failure
 * rather than throwing, so the caller can gracefully skip bad reads.
 */
object RideDataParser {

    private const val TAG = "RideDataParser"

    // ─── Fare ─────────────────────────────────────────────────────────────────
    // Matches: "85.00 DH", "MAD 85", "₱ 85.00", "Rp 15,000", "RM12.50", "฿ 85", "$8.40"
    private val FARE_REGEX = Regex(
        """(?:MAD|DH|[₱$฿€£Rp])?\s*([\d,]+(?:\.\d{1,2})?)\s*(?:DH|MAD)?""",
        RegexOption.IGNORE_CASE
    )

    fun parseFare(raw: String): Float? {
        val match = FARE_REGEX.find(raw.trim()) ?: return logNull(TAG, "fare", raw)
        return match.groupValues[1]
            .replace(",", "")
            .toFloatOrNull()
            ?: logNull(TAG, "fare float", raw)
    }

    // ─── Distance ─────────────────────────────────────────────────────────────
    // Matches: "15.2 km", "3.4km", "800 m", "0.8m"
    private val KM_REGEX    = Regex("""([\d.]+)\s*km""",  RegexOption.IGNORE_CASE)
    private val METER_REGEX = Regex("""([\d.]+)\s*m\b""", RegexOption.IGNORE_CASE)

    fun parseDistance(raw: String): Float? {
        KM_REGEX.find(raw)?.let {
            return it.groupValues[1].toFloatOrNull() ?: logNull(TAG, "km float", raw)
        }
        METER_REGEX.find(raw)?.let {
            val meters = it.groupValues[1].toFloatOrNull() ?: return logNull(TAG, "meter float", raw)
            return meters / 1000f  // Convert to km
        }
        return logNull(TAG, "distance", raw)
    }

    // ─── Passenger Rating ─────────────────────────────────────────────────────
    // Matches: "4.85", "4.9 ★", "Rating: 4.7"
    private val RATING_REGEX = Regex("""(\d\.\d{1,2})""")

    fun parseRating(raw: String): Float? {
        val match = RATING_REGEX.find(raw) ?: return logNull(TAG, "rating", raw)
        return match.groupValues[1].toFloatOrNull()
    }

    // ─── Trip Count ───────────────────────────────────────────────────────────
    // Matches: "124 trips", "Trips: 8", "3 completed"
    private val TRIPS_REGEX = Regex("""(\d+)\s*(?:trips?|completed|rides?)""", RegexOption.IGNORE_CASE)

    fun parseTripCount(raw: String): Int? {
        val match = TRIPS_REGEX.find(raw) ?: return logNull(TAG, "trips", raw)
        return match.groupValues[1].toIntOrNull()
    }

    // ─── Helper ───────────────────────────────────────────────────────────────
    private fun <T> logNull(tag: String, field: String, raw: String): T? {
        Log.v(tag, "Could not parse $field from: \"$raw\"")
        return null
    }
}


/**
 * Centralized regex pattern registry.
 * Add app-specific keyword variants here as you test against the real UI.
 */
object NodePattern {

    // Search hint texts — used in findAccessibilityNodeInfosByText()
    val FARE_PATTERNS = listOf(
        Regex("""(?:MAD|DH|[₱$฿€£])?\s*\d+[\.,]\d+(?:\s*(?:DH|MAD))?"""),
        Regex("""Total\s*Fare""", RegexOption.IGNORE_CASE),
        Regex("""Estimated\s*Earning""", RegexOption.IGNORE_CASE)
    )

    val DISTANCE_PATTERNS = listOf(
        Regex("""\d+\.?\d*\s*km""", RegexOption.IGNORE_CASE),
        Regex("""Total\s*Distance""", RegexOption.IGNORE_CASE),
        Regex("""\d+\s*m\b""")
    )

    val RATING_PATTERNS = listOf(
        Regex("""[45]\.\d+\s*★?"""),
        Regex("""Passenger\s*Rating""", RegexOption.IGNORE_CASE)
    )

    val TRIPS_PATTERNS = listOf(
        Regex("""\d+\s*trips?""", RegexOption.IGNORE_CASE),
        Regex("""Completed\s*Rides""", RegexOption.IGNORE_CASE)
    )
}
