package com.driverdashboard.service

/**
 * Phase 3: Mathematical Engine
 * Implements the 11-Tier PKM threshold system.
 */
class ProfitabilityEngine {

    fun evaluate(data: RideData): EvaluationResult {
        val pkm       = data.fare / data.distanceKm
        val threshold = getThreshold(data.distanceKm)
        val tier      = classifyTier(pkm, threshold)
        val warning   = checkPassengerQuality(data.rating, data.tripCount)
        return EvaluationResult(
            pkm              = pkm,
            tier             = tier,
            isHighRisk       = warning != null,
            passengerWarning = warning
        )
    }

    private val tiers = listOf(
        1f  to 8.0f,
        2f  to 6.0f,
        3f  to 4.5f,
        4f  to 3.5f,
        5f  to 3.2f,
        6f  to 3.0f,
        7f  to 2.9f,
        8f  to 2.8f,
        9f  to 2.7f,
        10f to 2.6f,
        Float.MAX_VALUE to 2.5f
    )

    private fun getThreshold(distanceKm: Float): Float =
        tiers.first { distanceKm <= it.first }.second

    private fun classifyTier(pkm: Float, threshold: Float): ProfitTier = when {
        pkm >= threshold * 1.15f -> ProfitTier.HIGH
        pkm >= threshold         -> ProfitTier.MEDIUM
        else                     -> ProfitTier.LOW
    }

    private fun checkPassengerQuality(rating: Float?, tripCount: Int?): PassengerWarning? {
        val lowRating = rating != null && rating < 4.6f
        val newUser   = tripCount != null && tripCount < 5
        return when {
            lowRating && newUser -> PassengerWarning("Low rating ($rating) · New user ($tripCount trips)")
            lowRating            -> PassengerWarning("Low rating: $rating ★")
            newUser              -> PassengerWarning("New user: only $tripCount trips")
            else                 -> null
        }
    }
}

/**
 * Immutable snapshot of a parsed ride request card.
 */
data class RideData(
    val fare:       Float,
    val distanceKm: Float,
    val rating:     Float? = null,
    val tripCount:  Int?   = null
)
