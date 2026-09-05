"""
AUREVIX — Enterprise Goal & Target Tracking Engine
Tracks user-defined business goals across Revenue, Profit, Customers, Quantity, or Custom metrics
with status classification (EXCEEDED, ON TRACK, AT RISK, BEHIND) and required growth run-rates.
"""
from typing import Dict, Any, Optional, List


class TargetEngine:
    """Evaluates target attainment, variance deltas, run-rate requirements, and status badges."""

    @classmethod
    def evaluate_target(cls, actual_val: float, target_val: float, metric_label: str = "Revenue") -> Dict[str, Any]:
        if target_val <= 0:
            return {"has_target": False, "status": "NO TARGET", "attainment_pct": 0.0}

        attainment = (actual_val / target_val) * 100.0
        remaining = max(0.0, target_val - actual_val)
        required_growth = ((target_val - actual_val) / actual_val * 100.0) if actual_val > 0 else 100.0

        if actual_val >= target_val:
            status = "EXCEEDED"
            status_color = "#10b981"
        elif attainment >= 80.0:
            status = "ON TRACK"
            status_color = "#38bdf8"
        elif attainment >= 50.0:
            status = "AT RISK"
            status_color = "#f59e0b"
        else:
            status = "BEHIND"
            status_color = "#ef4444"

        return {
            "has_target": True,
            "metric_label": metric_label,
            "actual": actual_val,
            "target": target_val,
            "attainment_pct": round(attainment, 2),
            "remaining": round(remaining, 2),
            "gap": round(target_val - actual_val, 2),
            "required_growth": round(max(0.0, required_growth), 1),
            "status": status,
            "status_color": status_color,
            "summary": f"Target of **${target_val:,.2f}** is **{attainment:.1f}%** achieved (${remaining:,.2f} remaining to reach 100%)."
        }
