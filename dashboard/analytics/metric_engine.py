"""
AUREVIX — High-Performance Dynamic Business Metric & Universal KPI Engine
Computes domain-aware business KPIs, growth rates, period-over-period comparisons, entity economics,
and structured KPI summary cards across Retail, HR, Marketing, Finance, Inventory, Healthcare, and Generic datasets.
"""
from typing import Dict, Any, Optional, List
import pandas as pd
import numpy as np


class MetricEngine:
    """Calculates business KPIs and dynamic summary cards tailored to dataset domain."""

    @classmethod
    def calculate_metrics(cls, df: pd.DataFrame, schema_meta: Dict[str, Any]) -> Dict[str, Any]:
        if df.empty:
            return {}

        roles = schema_meta.get("roles", {})
        num_cols = schema_meta.get("numeric_columns", [])
        curr_cols = schema_meta.get("currency_columns", [])
        domain = schema_meta.get("domain", "Enterprise Operations / General Tabular")

        # 1. Primary Metric
        rev_col = roles.get("revenue") or (curr_cols[0] if curr_cols else (num_cols[0] if num_cols else None))
        tot_rev = float(df[rev_col].sum()) if rev_col and rev_col in df.columns else 0.0
        avg_rev = float(df[rev_col].mean()) if rev_col and rev_col in df.columns else 0.0

        # 2. Profit
        profit_col = roles.get("profit")
        tot_profit = float(df[profit_col].sum()) if profit_col and profit_col in df.columns else None
        profit_margin = (tot_profit / tot_rev * 100.0) if (tot_profit is not None and tot_rev > 0) else None

        # 3. Cost / Expense
        cost_col = roles.get("cost")
        avg_cost = float(df[cost_col].mean()) if cost_col and cost_col in df.columns else 0.0

        # 4. Quantity / Volume
        qty_col = roles.get("quantity")
        tot_qty = float(df[qty_col].sum()) if qty_col and qty_col in df.columns else len(df)

        # 5. Transactions / Records
        order_col = roles.get("order_id")
        tot_orders = int(df[order_col].nunique()) if order_col and order_col in df.columns else len(df)

        # 6. Customers / Accounts
        cust_col = roles.get("customer")
        tot_cust = int(df[cust_col].nunique()) if cust_col and cust_col in df.columns else None

        # 7. Products / Items
        prod_col = roles.get("product")
        tot_prod = int(df[prod_col].nunique()) if prod_col and prod_col in df.columns else None

        # 8. Categories / Departments
        cat_col = roles.get("category")
        tot_cat = int(df[cat_col].nunique()) if cat_col and cat_col in df.columns else None

        # 9. Regions / Locations
        reg_col = roles.get("region")
        tot_reg = int(df[reg_col].nunique()) if reg_col and reg_col in df.columns else None

        # 10. Average Value per Transaction
        aov = tot_rev / max(1, tot_orders) if tot_orders > 0 else 0.0

        # 11. Top Category Contributor
        top_cat_name, top_cat_val = None, 0.0
        if cat_col and rev_col and cat_col in df.columns and rev_col in df.columns:
            grp = df.groupby(cat_col)[rev_col].sum().sort_values(ascending=False)
            if not grp.empty:
                top_cat_name = str(grp.index[0])
                top_cat_val = float(grp.iloc[0])

        # 12. Top Region Contributor
        top_reg_name, top_reg_val = None, 0.0
        if reg_col and rev_col and reg_col in df.columns and rev_col in df.columns:
            grp = df.groupby(reg_col)[rev_col].sum().sort_values(ascending=False)
            if not grp.empty:
                top_reg_name = str(grp.index[0])
                top_reg_val = float(grp.iloc[0])

        # 13. Fast Period-over-Period Growth
        date_col = roles.get("date")
        growth_pct, prev_period_rev = None, None
        if date_col and rev_col and date_col in df.columns and rev_col in df.columns:
            try:
                df_dates = pd.to_datetime(df[date_col], errors="coerce")
                valid_mask = df_dates.notnull()
                if valid_mask.sum() >= 4:
                    sorted_idx = df_dates[valid_mask].sort_values().index
                    rev_series = pd.to_numeric(df.loc[sorted_idx, rev_col], errors="coerce").fillna(0.0)
                    half = len(rev_series) // 2
                    if half >= 2:
                        p1 = float(rev_series.iloc[:half].sum())
                        p2 = float(rev_series.iloc[half:].sum())
                        prev_period_rev = p1
                        if p1 > 0:
                            growth_pct = float(((p2 - p1) / p1) * 100.0)
            except Exception:
                pass

        # 14. Build Dynamic Domain-Specific KPI Card Objects
        kpi_cards: List[Dict[str, Any]] = []

        if "HR" in domain or "Workforce" in domain:
            kpi_cards.append({
                "id": "headcount", "label": "Total Headcount", "value": f"{len(df):,}",
                "explanation": "Active workforce records", "source_col": "records", "confidence": 99, "icon": "👥"
            })
            if rev_col and ("salary" in rev_col.lower() or "compensation" in rev_col.lower() or "pay" in rev_col.lower()):
                kpi_cards.append({
                    "id": "avg_salary", "label": "Average Compensation", "value": f"${avg_rev:,.2f}",
                    "explanation": f"Mean annualized compensation from {rev_col}", "source_col": rev_col, "confidence": 95, "icon": "💵"
                })
                kpi_cards.append({
                    "id": "total_payroll", "label": "Total Payroll Commitment", "value": f"${tot_rev:,.2f}",
                    "explanation": f"Sum of {rev_col}", "source_col": rev_col, "confidence": 95, "icon": "💼"
                })
            if tot_cat:
                kpi_cards.append({
                    "id": "departments", "label": "Active Departments", "value": f"{tot_cat}",
                    "explanation": f"Unique divisions in {cat_col}", "source_col": cat_col, "confidence": 90, "icon": "🏢"
                })
        elif "Marketing" in domain:
            if rev_col:
                kpi_cards.append({
                    "id": "total_spend", "label": f"Total {rev_col.replace('_', ' ').title()}", "value": f"${tot_rev:,.2f}",
                    "explanation": f"Aggregate investment in {rev_col}", "source_col": rev_col, "confidence": 95, "icon": "📢"
                })
            kpi_cards.append({
                "id": "campaigns", "label": "Total Records / Campaigns", "value": f"{len(df):,}",
                "explanation": "Campaign tracking volume", "source_col": "records", "confidence": 99, "icon": "🎯"
            })
            if tot_cat:
                kpi_cards.append({
                    "id": "channels", "label": "Marketing Channels", "value": f"{tot_cat}",
                    "explanation": f"Distinct channels in {cat_col}", "source_col": cat_col, "confidence": 90, "icon": "📡"
                })
        elif "Inventory" in domain or "Supply Chain" in domain:
            kpi_cards.append({
                "id": "inventory_units", "label": "Units Monitored", "value": f"{tot_qty:,.0f}",
                "explanation": "Total inventory units recorded", "source_col": qty_col or "records", "confidence": 95, "icon": "📦"
            })
            if rev_col:
                kpi_cards.append({
                    "id": "inventory_value", "label": f"Total {rev_col.replace('_', ' ').title()}", "value": f"${tot_rev:,.2f}",
                    "explanation": f"Gross inventory valuation from {rev_col}", "source_col": rev_col, "confidence": 95, "icon": "🏭"
                })
            if tot_prod:
                kpi_cards.append({
                    "id": "active_skus", "label": "Active SKUs / Items", "value": f"{tot_prod:,}",
                    "explanation": f"Distinct items in {prod_col}", "source_col": prod_col, "confidence": 90, "icon": "🏷️"
                })
            elif tot_cat:
                kpi_cards.append({
                    "id": "warehouses", "label": "Warehouses / Categories", "value": f"{tot_cat:,}",
                    "explanation": f"Storage centers in {cat_col}", "source_col": cat_col, "confidence": 88, "icon": "🏬"
                })
        elif "Financial" in domain or "Banking" in domain:
            if rev_col:
                kpi_cards.append({
                    "id": "financial_volume", "label": f"Total {rev_col.replace('_', ' ').title()}", "value": f"${tot_rev:,.2f}",
                    "explanation": f"Gross financial throughput across {len(df):,} transactions", "source_col": rev_col, "confidence": 95, "icon": "💳"
                })
            if tot_profit is not None:
                kpi_cards.append({
                    "id": "net_profit", "label": "Operating Profit", "value": f"${tot_profit:,.2f}",
                    "delta": f"{profit_margin:.1f}% Margin" if profit_margin else None,
                    "explanation": f"Net operating income from {profit_col}", "source_col": profit_col, "confidence": 94, "icon": "📈"
                })
            kpi_cards.append({
                "id": "transactions", "label": "Ledger Records", "value": f"{len(df):,}",
                "explanation": "Audited transaction count", "source_col": "records", "confidence": 99, "icon": "🧾"
            })
            if tot_cat:
                kpi_cards.append({
                    "id": "accounts", "label": "Account Classifications", "value": f"{tot_cat:,}",
                    "explanation": f"Categories in {cat_col}", "source_col": cat_col, "confidence": 90, "icon": "🏦"
                })
        elif "Healthcare" in domain or "Clinical" in domain:
            kpi_cards.append({
                "id": "patients", "label": "Patients / Records", "value": f"{len(df):,}",
                "explanation": "Clinical encounters recorded", "source_col": "records", "confidence": 99, "icon": "🏥"
            })
            if rev_col:
                kpi_cards.append({
                    "id": "clinical_cost", "label": f"Total {rev_col.replace('_', ' ').title()}", "value": f"${tot_rev:,.2f}",
                    "explanation": f"Aggregate treatment volume from {rev_col}", "source_col": rev_col, "confidence": 95, "icon": "💊"
                })
            if tot_cat:
                kpi_cards.append({
                    "id": "diagnoses", "label": "Diagnoses / Specialties", "value": f"{tot_cat:,}",
                    "explanation": f"Clinical categories in {cat_col}", "source_col": cat_col, "confidence": 90, "icon": "🩺"
                })
        else:
            # Default / Retail / General Tabular
            if rev_col:
                kpi_cards.append({
                    "id": "revenue", "label": f"Total {rev_col.replace('_', ' ').title()}", "value": f"${tot_rev:,.2f}",
                    "delta": f"{'+' if growth_pct >= 0 else ''}{growth_pct:.1f}% vs prev period" if growth_pct is not None else None,
                    "explanation": f"Cumulative volume across {len(df):,} records", "source_col": rev_col, "confidence": 95, "icon": "💰"
                })
                kpi_cards.append({
                    "id": "aov", "label": f"Average {rev_col.replace('_', ' ').title()}", "value": f"${avg_rev:,.2f}",
                    "explanation": f"Mean value per record from {rev_col}", "source_col": rev_col, "confidence": 92, "icon": "📊"
                })
            if tot_profit is not None:
                kpi_cards.append({
                    "id": "profit", "label": "Total Net Profit", "value": f"${tot_profit:,.2f}",
                    "delta": f"{profit_margin:.1f}% Margin" if profit_margin else None,
                    "explanation": f"Net operating profit from {profit_col}", "source_col": profit_col, "confidence": 94, "icon": "📈"
                })
            if tot_cust:
                kpi_cards.append({
                    "id": "customers", "label": "Unique Accounts / Customers", "value": f"{tot_cust:,}",
                    "explanation": f"Distinct entities in {cust_col}", "source_col": cust_col, "confidence": 90, "icon": "👤"
                })
            elif tot_cat:
                kpi_cards.append({
                    "id": "categories", "label": "Unique Categories", "value": f"{tot_cat:,}",
                    "explanation": f"Segments in {cat_col}", "source_col": cat_col, "confidence": 88, "icon": "🏷️"
                })

        return {
            "total_revenue": tot_rev,
            "total_transactions": tot_orders,
            "total_quantity": tot_qty,
            "average_revenue": avg_rev,
            "average_transaction_value": aov,
            "total_profit": tot_profit,
            "profit_margin": profit_margin,
            "average_cost": avg_cost,
            "unique_customers": tot_cust,
            "unique_products": tot_prod,
            "unique_categories": tot_cat,
            "unique_regions": tot_reg,
            "growth_pct": growth_pct,
            "prev_period_revenue": prev_period_rev,
            "top_category_name": top_cat_name,
            "top_category_val": top_cat_val,
            "top_region_name": top_reg_name,
            "top_region_val": top_reg_val,
            "primary_metric_col": rev_col,
            "profit_col": profit_col,
            "date_col": date_col,
            "customer_col": cust_col,
            "product_col": prod_col,
            "category_col": cat_col,
            "region_col": reg_col,
            "kpi_cards": kpi_cards
        }
