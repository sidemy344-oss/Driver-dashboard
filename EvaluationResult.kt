package com.driverdashboard.service

/**
 * The result produced by ProfitabilityEngine after evaluating a ride.
 *
 * @param pkm            Earnings per kilometre in Moroccan Dirhams (DH/km)
 * @param tier           Profitability classification (HIGH / MEDIUM / LOW)
 * @param isHighRisk     True when the passenger or ride conditions raise a safety flag
 * @param passengerWarning  Optional warning shown in the HUD (e.g. low rating, new user)
 */
data class EvaluationResult(
    val pkm: Float,
    val tier: ProfitTier,
    val isHighRisk: Boolean,
    val passengerWarning: PassengerWarning? = null
)

/**
 * Holds the reason text for a passenger-level warning displayed in the HUD.
 */
data class PassengerWarning(
    val reason: String
)
