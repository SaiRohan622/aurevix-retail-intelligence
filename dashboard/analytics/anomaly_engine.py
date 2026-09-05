"""
AUREVIX — High-Performance Statistical Anomaly Detection Engine
Identifies time-series outliers, sudden metric spikes/drops, and extreme dimension deviations using vectorized Z-scores.
"""
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np


class AnomalyEngine:
    """Detects anomalies and pinpoints potential drivers in active datasets using vectorized math."""

    @classmethod
    def detect_anomalies(cls, df: pd.DataFrame, schema_meta: Dict[str, Any], metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        anomalies = []
        if df.empty:
            return anomalies

        schema_meta = schema_meta or {}
        metrics = metrics or {}
        
        date_cols = schema_meta.get("date_columns") or []
        num_cols = schema_meta.get("numeric_columns") or []
        cat_cols = schema_meta.get("categorical_columns") or []

        rev_col = metrics.get("primary_metric_col") or (num_cols[0] if num_cols else None)
        date_col = metrics.get("date_col") or (date_cols[0] if date_cols else None)
        cat_col = metrics.get("category_col") or (cat_cols[0] if cat_cols else None)

        # 1. Vectorized Time-Series Trend Anomalies (Monthly Spikes / Drops)
        if date_col and rev_col and date_col in df.columns and rev_col in df.columns:
            try:
                dt_series = pd.to_datetime(df[date_col], errors="coerce")
                val_series = pd.to_numeric(df[rev_col], errors="coerce").fillna(0.0)
                
                df_work = pd.DataFrame({"_dt": dt_series, "_val": val_series}).dropna(subset=["_dt"])
                if len(df_work) >= 4:
                    ts = df_work.set_index("_dt")["_val"].resample("MS").sum().reset_index()

                    if len(ts) >= 4:
                        mean_val = float(ts["_val"].mean())
                        std_val = float(ts["_val"].std())
                        if std_val > 0 and mean_val > 0:
                            z_scores = (ts["_val"] - mean_val) / std_val
                            dev_pcts = ((ts["_val"] - mean_val) / mean_val) * 100.0

                            for i, z in enumerate(z_scores):
                                row_dt = ts.iloc[i]["_dt"]
                                row_val = float(ts.iloc[i]["_val"])
                                month_label = row_dt.strftime("%B %Y")

                                if z > 2.0:
                                    anomalies.append({
                                        "type": "spike",
                                        "severity": "HIGH" if z > 2.8 else "MEDIUM",
                                        "title": f"Positive Volume Surge in {month_label}",
                                        "metric": rev_col,
                                        "observed": row_val,
                                        "expected": mean_val,
                                        "deviation_pct": float(dev_pcts.iloc[i]),
                                        "description": f"{month_label} volume was <b>{dev_pcts.iloc[i]:.1f}%</b> above historical average ({z:.2f}σ deviation)."
                                    })
                                elif z < -1.8:
                                    anomalies.append({
                                        "type": "drop",
                                        "severity": "HIGH" if z < -2.5 else "MEDIUM",
                                        "title": f"Volume Contraction in {month_label}",
                                        "metric": rev_col,
                                        "observed": row_val,
                                        "expected": mean_val,
                                        "deviation_pct": float(dev_pcts.iloc[i]),
                                        "description": f"{month_label} volume fell <b>{abs(dev_pcts.iloc[i]):.1f}%</b> below baseline trend ({abs(z):.2f}σ contraction)."
                                    })
            except Exception:
                pass

        # 2. Dimensional Skew / Extreme Dominance
        if cat_col and rev_col and cat_col in df.columns and rev_col in df.columns:
            try:
                cat_grp = df.groupby(cat_col)[rev_col].sum()
                if len(cat_grp) >= 3:
                    tot = cat_grp.sum()
                    if tot > 0:
                        top_share = (cat_grp.max() / tot) * 100.0
                        if top_share > 60.0:
                            anomalies.append({
                                "type": "skew",
                                "severity": "MEDIUM",
                                "title": f"Extreme Segment Concentration in '{cat_grp.idxmax()}'",
                                "metric": cat_col,
                                "observed": float(cat_grp.max()),
                                "expected": float(tot / len(cat_grp)),
                                "deviation_pct": float(top_share),
                                "description": f"Single category <b>{cat_grp.idxmax()}</b> controls <b>{top_share:.1f}%</b> of total {rev_col} volume."
                            })
            except Exception:
                pass

        return anomalies
