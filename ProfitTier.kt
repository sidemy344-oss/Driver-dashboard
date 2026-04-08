package com.driverdashboard.service

/**
 * Represents the profitability tier of a ride.
 * Used by EvaluationResult and displayed in the HUD overlay.
 */
enum class ProfitTier(val label: String) {
    HIGH("EXCELLENT"),
    MEDIUM("AVERAGE"),
    LOW("POOR")
}
