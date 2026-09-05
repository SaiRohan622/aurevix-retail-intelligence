"""
AUREVIX — Universal Semantic Column Mapper
Maps column names and data types to semantic business roles across diverse domains (Retail, HR, Finance, Marketing, Logistics, Operations).
"""

from typing import List, Dict, Optional, Tuple, Any
import pandas as pd


class ColumnMapper:
    """Rule-based and heuristic semantic column matcher."""

    REVENUE_PATTERNS = [
        "revenue", "sales", "sales_amount", "amount", "total_sales",
        "total_amount", "price", "net_sales", "gross_sales", "income",
        "turnover", "spend", "monetary", "subtotal", "grand_total",
        "salary", "compensation", "budget", "cost_total", "billed", "payments"
    ]

    PROFIT_PATTERNS = [
        "profit", "net_profit", "gross_profit", "margin", "net_margin",
        "gain", "earnings", "operating_income", "ebitda"
    ]

    COST_PATTERNS = [
        "cost", "freight", "shipping", "shipping_cost", "expense", "fee", "tax",
        "cogs", "unit_cost", "operational_cost"
    ]

    QUANTITY_PATTERNS = [
        "quantity", "qty", "units", "units_sold", "volume", "count",
        "items", "item_count", "pieces", "shares", "headcount", "impressions", "clicks", "conversions"
    ]

    DATE_PATTERNS = [
        "date", "order_date", "transaction_date", "invoice_date", "created_at",
        "timestamp", "purchase_date", "joining_date", "hire_date", "event_time", "day",
        "period", "year_month", "datetime", "closed_at", "shipped_date", "launch_date"
    ]

    CUSTOMER_PATTERNS = [
        "customer", "customer_id", "client", "client_id", "client_name",
        "buyer", "buyer_id", "user_id", "account_id", "member_id", "subscriber_id",
        "patient_id", "lead_id", "contact"
    ]

    PRODUCT_PATTERNS = [
        "product", "product_id", "product_name", "item", "item_name",
        "sku", "stock_code", "service", "article", "good", "part_number",
        "course", "project", "campaign", "campaign_id"
    ]

    CATEGORY_PATTERNS = [
        "category", "product_category", "department", "dept", "genre", "class",
        "segment", "type", "division", "channel", "group", "tier", "role", "designation"
    ]

    REGION_PATTERNS = [
        "region", "state", "city", "country", "location", "territory",
        "province", "zone", "hub", "district", "market", "area", "zip", "postal_code",
        "branch", "office", "site"
    ]

    ORDER_ID_PATTERNS = [
        "order_id", "transaction_id", "invoice", "invoice_id", "trans_id",
        "receipt_id", "bill_id", "ticket_id", "booking_id", "deal_id", "order_no", "order_number"
    ]

    STATUS_PATTERNS = [
        "status", "order_status", "stage", "state_label", "delivery_status", "performance_score", "rating"
    ]

    @classmethod
    def match_column(cls, df: pd.DataFrame, patterns: List[str], require_numeric: bool = False, require_datetime: bool = False) -> Optional[str]:
        """Find the highest confidence column matching a pattern list."""
        if df.empty:
            return None

        cols_clean = {str(c).lower().replace(" ", "_").replace("-", "_"): c for c in df.columns}
        
        # 1. Exact match pass
        for p in patterns:
            for clean_col, orig_col in cols_clean.items():
                if clean_col == p:
                    if require_numeric and not pd.api.types.is_numeric_dtype(df[orig_col]):
                        continue
                    if require_datetime and not (pd.api.types.is_datetime64_any_dtype(df[orig_col]) or cls._is_parseable_date(df[orig_col])):
                        continue
                    return orig_col

        # 2. Substring match pass
        for p in patterns:
            for clean_col, orig_col in cols_clean.items():
                if p in clean_col:
                    if require_numeric and not pd.api.types.is_numeric_dtype(df[orig_col]):
                        continue
                    if require_datetime and not (pd.api.types.is_datetime64_any_dtype(df[orig_col]) or cls._is_parseable_date(df[orig_col])):
                        continue
                    return orig_col

        return None

    @staticmethod
    def _is_parseable_date(series: pd.Series) -> bool:
        sample = series.dropna().head(10)
        if sample.empty:
            return False
        try:
            pd.to_datetime(sample, errors="raise")
            return True
        except Exception:
            return False
