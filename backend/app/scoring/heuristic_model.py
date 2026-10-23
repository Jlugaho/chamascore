"""
ChamaScore Heuristic Credit Scoring Engine
Score range: 300 (Poor) to 850 (Excellent)
"""
import numpy as np
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass


@dataclass
class FeatureResult:
    value: float | None
    unit: str
    weight: int
    normalized_score: float
    contribution: float
    rating: str
    available: bool
    availability_note: str | None = None


class HeuristicCreditScorer:

    SCORE_MIN = 300
    SCORE_MAX = 850

    WEIGHTS = {
        "group_longevity_months":   15,
        "contribution_cv":          20,
        "contribution_reliability": 15,
        "repayment_rate":           25,
        "liquidity_ratio":          10,
        "member_stability":          5,
        "attendance_rate":           5,
        "recent_default_rate":       5,
    }

    NORMALIZATION_RANGES = {
        "group_longevity_months":   (0.0, 60.0),
        "contribution_cv":          (0.0, 1.0),
        "contribution_reliability": (0.0, 1.0),
        "repayment_rate":           (0.0, 1.0),
        "liquidity_ratio":          (0.0, 10.0),
        "member_stability":         (0.0, 1.0),
        "attendance_rate":          (0.0, 1.0),
        "recent_default_rate":      (0.0, 0.5),
    }

    INVERSE_FEATURES = {"contribution_cv", "recent_default_rate"}

    FEATURE_META = {
        "group_longevity_months":   ("Group Longevity",          "months"),
        "contribution_cv":          ("Contribution Consistency",  "coefficient"),
        "contribution_reliability": ("Contribution Reliability",  "ratio"),
        "repayment_rate":           ("Loan Repayment Rate",       "ratio"),
        "liquidity_ratio":          ("Liquidity Ratio",           "ratio"),
        "member_stability":         ("Member Stability",          "ratio"),
        "attendance_rate":          ("Meeting Attendance Rate",   "ratio"),
        "recent_default_rate":      ("Recent Default Rate (90d)", "ratio"),
    }

    def _normalize(self, feature: str, value: float) -> float:
        min_val, max_val = self.NORMALIZATION_RANGES[feature]
        if max_val == min_val:
            return 1.0
        normalized = float(np.clip((value - min_val) / (max_val - min_val), 0.0, 1.0))
        if feature in self.INVERSE_FEATURES:
            normalized = 1.0 - normalized
        return normalized

    def _get_rating(self, normalized: float) -> str:
        if normalized >= 0.85: return "excellent"
        elif normalized >= 0.70: return "very_good"
        elif normalized >= 0.55: return "good"
        elif normalized >= 0.40: return "fair"
        else: return "poor"

    def calculate_score(self, features: Dict[str, float | None]) -> Tuple[int, Dict[str, FeatureResult]]:
        total_weighted = 0.0
        breakdown = {}

        for feature, weight in self.WEIGHTS.items():
            raw_value = features.get(feature)
            available = raw_value is not None
            normalized = self._normalize(feature, raw_value) if available else 0.5
            contribution = normalized * weight
            total_weighted += contribution
            _, unit = self.FEATURE_META[feature]
            breakdown[feature] = FeatureResult(
                value=round(raw_value, 4) if available else None,
                unit=unit,
                weight=weight,
                normalized_score=round(normalized, 4),
                contribution=round(contribution, 2),
                rating=self._get_rating(normalized) if available else "insufficient_data",
                available=available,
                availability_note=None if available else "Insufficient recorded data",
            )

        score = int(round(float(np.clip(
            self.SCORE_MIN + (total_weighted / 100.0) * (self.SCORE_MAX - self.SCORE_MIN),
            self.SCORE_MIN, self.SCORE_MAX
        ))))
        return score, breakdown

    def get_score_band(self, score: int) -> str:
        if score >= 750: return "Excellent"
        elif score >= 660: return "Very Good"
        elif score >= 600: return "Good"
        elif score >= 500: return "Fair"
        else: return "Poor"

    def generate_recommendations(self, breakdown: Dict[str, FeatureResult]) -> List[str]:
        recommendations = []
        messages = {
            "contribution_cv": "Improve contribution consistency — ensure all members pay on time every cycle.",
            "repayment_rate": "Address outstanding loan defaults — follow up with members on overdue repayments.",
            "group_longevity_months": "Your group is relatively new — scores improve significantly with a longer track record.",
            "attendance_rate": "Improve meeting attendance — consistent attendance signals group health to lenders.",
            "member_stability": "Reduce member turnover — stable membership signals trustworthiness.",
            "contribution_reliability": "Increase total contributions — close the gap between expected and actual savings.",
            "liquidity_ratio": "Reduce outstanding loans relative to savings to improve your liquidity ratio.",
            "recent_default_rate": "Prioritize repaying recent overdue loans to clear your 90-day default record.",
        }
        for feature, result in breakdown.items():
            if not result.available:
                recommendations.append(
                    f"Record more data for {self.FEATURE_META[feature][0].lower()} to include it in future scores."
                )
            elif result.rating in ("poor", "fair"):
                if feature in messages:
                    recommendations.append(messages[feature])
        if not recommendations:
            recommendations.append("Your group is performing well across all metrics. Keep up the excellent financial discipline!")
        return recommendations

    def generate_calculation_log(self, features: Dict[str, float | None], breakdown: Dict[str, FeatureResult], score: int) -> str:
        lines = ["=" * 55, "CHAMASCORE CREDIT SCORE CALCULATION LOG", "=" * 55, ""]
        total = 0.0
        for feature, result in breakdown.items():
            display_name, _ = self.FEATURE_META[feature]
            if not result.available:
                lines += [
                    f"Feature : {display_name}",
                    f"  Status     : {result.availability_note}",
                    f"  Weight     : {result.weight}%",
                    f"  Contribution: {result.contribution:.2f} pts (neutral)",
                    "",
                ]
                total += result.contribution
                continue
            lines += [
                f"Feature : {display_name}",
                f"  Raw Value  : {result.value} {result.unit}",
                f"  Weight     : {result.weight}%",
                f"  Normalized : {result.normalized_score:.4f}",
                f"  Contribution: {result.contribution:.2f} pts",
                f"  Rating     : {result.rating.upper()}",
                "",
            ]
            total += result.contribution
        lines += [
            f"Total Weighted : {total:.2f} / 100",
            f"Final Score    : {score}",
            f"Band           : {self.get_score_band(score)}",
            "=" * 55,
        ]
        return "\n".join(lines)


def engineer_features_from_raw(raw: Dict[str, Any]) -> Dict[str, float | None]:
    features = {}

    features["group_longevity_months"] = raw.get("group_age_days", 0) / 30.0

    contribution_count = raw.get("contribution_count")
    avg = raw.get("avg_contribution")
    std = raw.get("stddev_contribution")
    if contribution_count is None:
        contribution_count = 0
    features["contribution_cv"] = (
        float(std) / float(avg)
        if contribution_count >= 2 and avg and std is not None
        else None
    )

    active = raw.get("active_members", 0) or 0
    months = max(raw.get("group_age_days", 1) / 30.0, 1)
    contrib_amount = float(raw.get("contribution_amount", 0) or 0)
    expected = active * months * contrib_amount
    actual = float(raw.get("total_contributions", 0) or 0)
    features["contribution_reliability"] = (
        float(np.clip(actual / expected, 0, 1)) if expected > 0 else None
    )

    repaid = float(raw.get("repaid_loans_count", 0) or 0)
    defaulted = float(raw.get("defaulted_loans_count", 0) or 0)
    total_loans = repaid + defaulted
    features["repayment_rate"] = repaid / total_loans if total_loans > 0 else None

    savings = float(raw.get("total_savings", 0) or 0)
    active_loans = float(raw.get("active_loans_total", 0) or 0)
    features["liquidity_ratio"] = (
        float(np.clip(savings / active_loans, 0, 10)) if active_loans > 0 else None
    )

    total_members = raw.get("total_ever_members", 0) or 0
    features["member_stability"] = (
        float(np.clip(active / total_members, 0, 1)) if total_members > 0 else None
    )

    attendance_records = raw.get("attendance_records_30d")
    attended = raw.get("actual_attendance_30d", 0) or 0
    features["attendance_rate"] = (
        float(np.clip(attended / attendance_records, 0, 1))
        if attendance_records and attendance_records > 0 else None
    )

    loans_90d = raw.get("loans_disbursed_90d", 0) or 0
    defaults_90d = raw.get("defaults_90d", 0) or 0
    features["recent_default_rate"] = (
        float(np.clip(defaults_90d / loans_90d, 0, 0.5)) if loans_90d > 0 else None
    )

    return features