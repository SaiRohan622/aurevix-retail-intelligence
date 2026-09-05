"""
AUREVIX — Universal Schema & Domain Intelligence Engine
Infers column semantics, fine-grained semantic classifications (DATE, DATETIME, NUMERIC, CURRENCY,
PERCENTAGE, INTEGER, FLOAT, CATEGORY, TEXT, ID, BOOLEAN, EMAIL, PHONE, UNKNOWN),
multi-domain classification (Retail, HR, Marketing, Finance, Healthcare, Logistics, Operations),
and confidence scoring.
"""
import re
from typing import Dict, List, Any, Optional, Tuple, Union
import pandas as pd
import numpy as np
from dashboard.analytics.column_mapper import ColumnMapper


class SchemaDetector:
    """Infers column roles, semantic classifications, and domain category with confidence scoring."""

    GEO_PATTERNS = [
        "state", "region", "country", "city", "zip", "postal", "province",
        "territory", "location", "lat", "latitude", "lon", "longitude",
        "customer_state", "customer_city", "seller_state", "seller_city"
    ]

    CURRENCY_PATTERNS = [
        "price", "revenue", "sales", "cost", "salary", "payroll", "amount",
        "spend", "income", "profit", "freight", "fee", "budget", "expense",
        "cogs", "turnover", "billed", "payments", "compensation"
    ]

    PERCENTAGE_PATTERNS = [
        "pct", "percent", "percentage", "ratio", "margin", "share", "discount",
        "rate", "ctr", "roi", "cpa", "conversion_rate", "churn_rate"
    ]

    EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")
    PHONE_REGEX = re.compile(r"^\+?[\d\s\-\(\)]{7,20}$")

    @classmethod
    def _infer_fine_grained_type(cls, col_name: str, series: pd.Series) -> str:
        col_lower = col_name.lower().replace(" ", "_").replace("-", "_")
        non_nulls = series.dropna()

        # 1. Boolean
        if series.dtype == bool or (len(non_nulls) > 0 and non_nulls.isin([0, 1, "0", "1", "True", "False", True, False, "true", "false", "Y", "N", "yes", "no"]).all() and series.nunique() <= 2):
            return "boolean"

        # 2. Email
        if any(term in col_lower for term in ["email", "e_mail", "mail"]):
            return "email"
        if len(non_nulls) > 0 and non_nulls.astype(str).str.contains("@").any():
            sample_matches = sum(bool(cls.EMAIL_REGEX.match(str(x).strip())) for x in non_nulls.head(10))
            if sample_matches >= max(1, int(len(non_nulls.head(10)) * 0.7)):
                return "email"

        # 3. Phone
        if any(term in col_lower for term in ["phone", "tel", "mobile", "cell", "fax"]):
            return "phone"

        # 4. Datetime / Date
        if pd.api.types.is_datetime64_any_dtype(series):
            # Check if time component exists
            if hasattr(series.dt, "time") and not (series.dt.time == pd.Timestamp("00:00:00").time()).all():
                return "datetime"
            return "date"

        # If numeric series with small integer values (like years of experience, age, count), do not treat as date
        is_small_num = pd.api.types.is_numeric_dtype(series) and len(non_nulls) > 0 and (non_nulls.max() < 1000 if pd.api.types.is_numeric_dtype(series) else False)
        
        if not is_small_num and any(p in col_lower for p in ["date", "time", "timestamp", "created_at", "updated_at", "order_date", "joining_date", "hire_date", "dob", "birth_date"]) or (col_lower == "year" and pd.api.types.is_numeric_dtype(series) and len(non_nulls) > 0 and non_nulls.min() > 1900):
            try:
                # Do not convert integers < 1000 into epoch nanosecond datetimes
                if not pd.api.types.is_numeric_dtype(series) or (non_nulls.min() >= 1900 and non_nulls.max() <= 2100):
                    dt_s = pd.to_datetime(non_nulls.head(20), errors="coerce")
                    if dt_s.notnull().sum() >= max(1, int(len(non_nulls.head(20)) * 0.7)):
                        if any("time" in col_lower or ":" in str(x) for x in non_nulls.head(5)):
                            return "datetime"
                        return "date"
            except Exception:
                pass

        # 5. Percentage / Rates
        if any(p in col_lower for p in cls.PERCENTAGE_PATTERNS):
            return "percentage"
        if pd.api.types.is_numeric_dtype(series) and len(non_nulls) > 0:
            if non_nulls.between(0, 1).all() and any(w in col_lower for w in ["rate", "pct", "ratio"]):
                return "percentage"

        # 6. Currency / Price string formats (e.g. "$1,250.00")
        if any(p in col_lower for p in cls.CURRENCY_PATTERNS):
            if pd.api.types.is_numeric_dtype(series):
                return "currency"
            if len(non_nulls) > 0 and any(s in str(non_nulls.iloc[0]) for s in ["$", "€", "£", "¥"]):
                return "currency"

        # 7. Identifiers (UUID, IDs, Keys, Hashes, SKUs)
        if any(p in col_lower for p in ["_id", "id_", "uuid", "guid", "hash", "sku", "code", "key", "token", "ssn", "passport"]):
            if col_lower != "paid":
                return "id"
        if pd.api.types.is_numeric_dtype(series) and any(p in col_lower for p in ["id", "code", "key", "number"]) and series.nunique() > len(series) * 0.8:
            return "id"

        # 8. Numeric measures (Integer vs Float)
        if pd.api.types.is_numeric_dtype(series):
            if pd.api.types.is_integer_dtype(series) or (len(non_nulls) > 0 and (non_nulls % 1 == 0).all()):
                return "integer"
            return "float"

        # 9. Geographic
        if any(p in col_lower for p in cls.GEO_PATTERNS):
            return "geographic"

        # 10. Long Text / Freeform Notes / Descriptions (checked before cardinality)
        if any(p in col_lower for p in ["note", "description", "comment", "summary", "text", "body", "message", "details", "feedback", "review"]):
            return "text"
        if len(non_nulls) > 0 and non_nulls.astype(str).str.len().mean() > 35:
            return "text"

        # 11. Categorical
        uniques = series.nunique(dropna=True)
        if uniques <= 50 or (len(series) > 0 and uniques / len(series) < 0.2):
            return "categorical"

        return "text"

    @classmethod
    def detect_schema(cls, df: pd.DataFrame) -> Dict[str, Any]:
        if df.empty:
            return {
                "columns": {},
                "roles": {},
                "numeric_columns": [],
                "categorical_columns": [],
                "date_columns": [],
                "id_columns": [],
                "text_columns": [],
                "boolean_columns": [],
                "geographic_columns": [],
                "currency_columns": [],
                "percentage_columns": [],
                "email_columns": [],
                "phone_columns": [],
                "candidate_metrics": [],
                "domain": "Enterprise Operations / General Tabular",
                "domain_confidence": 50,
                "detected_fields": []
            }

        col_dict = {}
        numeric_cols = []
        cat_cols = []
        date_cols = []
        id_cols = []
        text_cols = []
        bool_cols = []
        geo_cols = []
        curr_cols = []
        pct_cols = []
        email_cols = []
        phone_cols = []

        total_rows = len(df)

        for col in df.columns:
            s = df[col]
            dtype_str = str(s.dtype)
            sem_type = cls._infer_fine_grained_type(col, s)
            
            nulls = int(s.isnull().sum())
            uniques = int(s.nunique(dropna=True))
            cardinality = "high" if (total_rows > 0 and uniques / total_rows > 0.5) else ("medium" if uniques > 20 else "low")
            samples = [str(x) for x in s.dropna().head(3).tolist()]

            # Determine base role classification
            if sem_type in ["numeric", "currency", "percentage", "integer", "float"]:
                base_type = "numeric"
            elif sem_type in ["date", "datetime"]:
                base_type = "date"
            elif sem_type in ["categorical", "geographic"]:
                base_type = "categorical"
            elif sem_type == "boolean":
                base_type = "boolean"
            elif sem_type == "id":
                base_type = "id"
            else:
                base_type = "text"

            col_dict[col] = {
                "dtype": dtype_str,
                "semantic_type": base_type,
                "fine_type": sem_type,
                "cardinality": cardinality,
                "null_count": nulls,
                "null_pct": (nulls / total_rows * 100.0) if total_rows > 0 else 0.0,
                "unique_count": uniques,
                "samples": samples
            }

            if sem_type in ["numeric", "currency", "percentage", "integer", "float"]:
                numeric_cols.append(col)
                if sem_type == "currency":
                    curr_cols.append(col)
                elif sem_type == "percentage":
                    pct_cols.append(col)
            elif sem_type == "categorical":
                cat_cols.append(col)
            elif sem_type == "geographic":
                geo_cols.append(col)
                cat_cols.append(col)
            elif sem_type in ["date", "datetime"]:
                date_cols.append(col)
            elif sem_type == "id":
                id_cols.append(col)
            elif sem_type == "boolean":
                bool_cols.append(col)
            elif sem_type == "email":
                email_cols.append(col)
                text_cols.append(col)
            elif sem_type == "phone":
                phone_cols.append(col)
                text_cols.append(col)
            else:
                text_cols.append(col)

        # Detect primary business roles
        roles = {
            "revenue": ColumnMapper.match_column(df, ColumnMapper.REVENUE_PATTERNS, require_numeric=True) or (curr_cols[0] if curr_cols else (numeric_cols[0] if numeric_cols else None)),
            "profit": ColumnMapper.match_column(df, ColumnMapper.PROFIT_PATTERNS, require_numeric=True),
            "cost": ColumnMapper.match_column(df, ColumnMapper.COST_PATTERNS, require_numeric=True),
            "quantity": ColumnMapper.match_column(df, ColumnMapper.QUANTITY_PATTERNS, require_numeric=True),
            "date": ColumnMapper.match_column(df, ColumnMapper.DATE_PATTERNS, require_datetime=True) or (date_cols[0] if date_cols else None),
            "customer": ColumnMapper.match_column(df, ColumnMapper.CUSTOMER_PATTERNS, require_numeric=False),
            "product": ColumnMapper.match_column(df, ColumnMapper.PRODUCT_PATTERNS, require_numeric=False),
            "category": ColumnMapper.match_column(df, ColumnMapper.CATEGORY_PATTERNS, require_numeric=False) or (cat_cols[0] if cat_cols else None),
            "region": ColumnMapper.match_column(df, ColumnMapper.REGION_PATTERNS, require_numeric=False) or (geo_cols[0] if geo_cols else None),
            "order_id": ColumnMapper.match_column(df, ColumnMapper.ORDER_ID_PATTERNS, require_numeric=False),
            "status": ColumnMapper.match_column(df, ColumnMapper.STATUS_PATTERNS, require_numeric=False)
        }

        # Domain classification
        domain, confidence, detected_fields = cls._classify_domain(df, roles)

        return {
            "columns": col_dict,
            "roles": roles,
            "numeric_columns": numeric_cols,
            "categorical_columns": cat_cols,
            "date_columns": date_cols,
            "id_columns": id_cols,
            "text_columns": text_cols,
            "boolean_columns": bool_cols,
            "geographic_columns": geo_cols,
            "currency_columns": curr_cols,
            "percentage_columns": pct_cols,
            "email_columns": email_cols,
            "phone_columns": phone_cols,
            "candidate_metrics": numeric_cols,
            "domain": domain,
            "domain_confidence": confidence,
            "detected_fields": detected_fields
        }

    @classmethod
    def _classify_domain(cls, df: pd.DataFrame, roles: Dict[str, Optional[str]]) -> Tuple[str, int, List[str]]:
        cols_lower = [c.lower() for c in df.columns]
        
        # Domain detection rules
        # 1. HR / Workforce
        hr_keywords = ["salary", "employee", "emp_id", "department", "dept", "job_title", "joining_date", "hire_date", "headcount", "performance_rating", "attrition", "tenure"]
        hr_matches = [k for k in hr_keywords if any(k in c for c in cols_lower)]
        if len(hr_matches) >= 2 or any("salary" in c for c in cols_lower) and any("dept" in c or "department" in c for c in cols_lower):
            return "HR / Workforce Analytics", min(98, 60 + len(hr_matches) * 12), hr_matches

        # 2. Marketing / Advertising
        mkt_keywords = ["campaign", "clicks", "impressions", "leads", "conversions", "ad_spend", "spend", "ctr", "cpc", "roi", "cpa", "channel", "ad_group"]
        mkt_matches = [k for k in mkt_keywords if any(k in c for c in cols_lower)]
        if len(mkt_matches) >= 2 or any("campaign" in c for c in cols_lower):
            return "Marketing & Campaigns", min(98, 60 + len(mkt_matches) * 12), mkt_matches

        # 3. Inventory / Logistics / Supply Chain
        inv_keywords = ["stock", "inventory", "warehouse", "sku", "reorder", "quantity_on_hand", "supplier", "freight", "shipment", "carrier", "lead_time"]
        inv_matches = [k for k in inv_keywords if any(k in c for c in cols_lower)]
        if len(inv_matches) >= 2:
            return "Inventory & Supply Chain", min(98, 60 + len(inv_matches) * 12), inv_matches

        # 4. Finance & Banking
        fin_keywords = ["expense", "income", "budget", "ebitda", "cash_flow", "assets", "liabilities", "tax", "payroll", "dividend", "interest_rate", "credit_score", "loan"]
        fin_matches = [k for k in fin_keywords if any(k in c for c in cols_lower)]
        if len(fin_matches) >= 2:
            return "Financial & Banking", min(98, 60 + len(fin_matches) * 12), fin_matches

        # 5. Healthcare / Medical
        hc_keywords = ["patient", "diagnosis", "admission", "discharge", "hospital", "doctor", "physician", "prescription", "dosage", "medical", "treatment"]
        hc_matches = [k for k in hc_keywords if any(k in c for c in cols_lower)]
        if len(hc_matches) >= 2:
            return "Healthcare & Clinical Analytics", min(98, 60 + len(hc_matches) * 12), hc_matches

        # 6. Retail / E-Commerce
        ret_keywords = ["price", "revenue", "product", "order", "sales", "freight", "customer", "category", "item", "quantity", "sku", "store", "cart"]
        ret_matches = [k for k in ret_keywords if any(k in c for c in cols_lower)]
        if len(ret_matches) >= 2:
            return "Retail & E-Commerce", min(98, 60 + len(ret_matches) * 10), ret_matches

        return "Enterprise Operations / General Tabular", 65, []
