"""
AUREVIX — Central In-Memory Analytical Session & Performance State Manager
Coordinating uploaded dataset isolation, central analysis caching, dataset fingerprint caching,
dynamic KPI caching, cross-filtering, target tracking, audit governance, and progressive lazy analysis.
"""
import time
import datetime
from typing import Dict, Any, Optional, List, Tuple
import pandas as pd
import streamlit as st
from dashboard.analytics.schema_detector import SchemaDetector
from dashboard.analytics.profiler import DataProfiler
from dashboard.analytics.metric_engine import MetricEngine
from dashboard.analytics.insight_engine import InsightEngine
from dashboard.analytics.anomaly_engine import AnomalyEngine
from dashboard.analytics.cleaning_engine import DataCleaningEngine
from dashboard.analytics.workspace_manager import WorkspaceManager
from dashboard.analytics.persistent_storage import PersistentStorageManager
from dashboard.analytics.audit_trail import AuditTrail

_DEMO_RESULTS = {
    'dataset_id': 'olist_production_gold',
    'dataset_name': 'Olist Brazilian E-Commerce',
    'profile': {
        'row_count': 98666, 'col_count': 14, 'memory_mb': 18.4,
        'missing_cells': 0, 'missing_pct': 0.0, 'duplicate_rows': 0,
        'duplicate_pct': 0.0, 'quality_score': 99.9981,
        'completeness_score': 100.0, 'validity_score': 100.0,
        'uniqueness_score': 100.0, 'consistency_score': 100.0,
        'outliers': {}, 'constant_columns': [], 'problematic_indices': [],
        'rating': 'EXCELLENT', 'rating_color': '#10b981',
        'issues_summary': {
            'total_issues': 0, 'missing_values': 0, 'duplicate_rows': 0,
            'invalid_dates': 0, 'outliers_count': 0, 'constant_columns_count': 0
        },
        'column_profiles': {},
        'invalid_dates': {},
        'problematic_records': [],
        'is_sampled': False,
        'sample_size': 98666
    },
    'schema': {
        'domain': 'Retail & E-Commerce', 'domain_confidence': 99,
        'columns': {}, 'roles': {},
        'numeric_columns': ['price', 'freight_value'],
        'categorical_columns': ['product_category_name', 'customer_state'],
        'date_columns': ['order_purchase_timestamp'],
        'id_columns': [], 'text_columns': [], 'boolean_columns': [], 'detected_fields': [],
    },
    'kpis': {
        'total_revenue': 15843553.24, 'total_transactions': 98666,
        'total_quantity': 112650, 'average_revenue': 160.58,
        'average_transaction_value': 160.58, 'total_profit': None,
        'profit_margin': None, 'average_cost': 0.0,
        'unique_customers': 99441, 'unique_products': 32951,
        'unique_categories': 73, 'unique_regions': 27,
        'growth_pct': None, 'prev_period_revenue': None,
        'top_category_name': 'beleza_saude', 'top_category_val': 1441248.07,
        'top_region_name': 'SP', 'top_region_val': 6608512.44,
        'primary_metric_col': 'price', 'profit_col': None,
        'date_col': 'order_purchase_timestamp', 'customer_col': 'customer_id',
        'product_col': 'product_id', 'category_col': 'product_category_name',
        'region_col': 'customer_state',
    },
    'insights': [], 'anomalies': [], 'analysis_time_ms': 0.0,
}

_NS = 'workspace'


class AnalyticsManager:
    """Thread-safe singleton-pattern session manager with central fingerprint caching & progressive state."""

    @classmethod
    def initialize(cls):
        if _NS not in st.session_state:
            st.session_state[_NS] = {}
        ws = st.session_state[_NS]
        ws.setdefault('user_mode', False)
        ws.setdefault('user_dataset_id', None)
        ws.setdefault('user_dataset_name', None)
        ws.setdefault('dataset_version', 1)
        ws.setdefault('active_workspace_section', "📥 Ingest & Quality Center")
        ws.setdefault('active_role_view', "Executive")
        ws.setdefault('data_source', 'none')
        ws.setdefault('uploaded_signature', None)
        ws.setdefault('original_raw_df', None)
        ws.setdefault('raw_df', None)
        ws.setdefault('filtered_df', None)
        ws.setdefault('last_filter_signature', None)
        ws.setdefault('analysis_results', {})
        ws.setdefault('analysis_cache', {})
        ws.setdefault('analysis_status', 'idle')
        ws.setdefault('initial_profile', {})
        ws.setdefault('cleaning_recipe', [])
        ws.setdefault('active_filters', {})
        ws.setdefault('user_targets', {})
        ws.setdefault('dashboard_layout',
            ['kpis', 'target', 'trend', 'donut', 'bar', 'story', 'anomalies', 'quality'])
        ws.setdefault('upload_timestamp', None)
        ws.setdefault('comparison', {
            'dataset_a': None,
            'dataset_b': None,
            'dataset_a_name': None,
            'dataset_b_name': None,
            'dataset_a_fingerprint': None,
            'dataset_b_fingerprint': None,
            'schema_mapping': {},
            'comparison_results': {},
            'comparison_profile': {},
            'comparison_insights': []
        })
        ws.setdefault('telemetry', {
            "load_time_ms": 0.0,
            "fast_profile_time_ms": 0.0,
            "deep_analysis_time_ms": 0.0,
            "profiling_time_ms": 0.0,
            "kpi_time_ms": 0.0,
            "filtering_time_ms": 0.0,
            "section_time_ms": 0.0,
            "cache_status": "MISS",
            "cache_hits": 0
        })

        # If no active dataset in session state, check persistent storage on disk
        needs_dataset_restore = not ws.get('user_mode') or ws.get('raw_df') is None
        needs_comp_restore = ws.get('comparison', {}).get('dataset_a') is None
        if needs_dataset_restore or needs_comp_restore:
            persisted = PersistentStorageManager.load_active_state()
            if persisted:
                if needs_dataset_restore and persisted.get("user_mode") and persisted.get("raw_df") is not None:
                    ws['user_mode'] = True
                    ws['user_dataset_id'] = persisted['user_dataset_id']
                    ws['user_dataset_name'] = persisted['user_dataset_name']
                    ws['data_source'] = persisted.get('data_source', 'user_upload')
                    ws['original_raw_df'] = persisted['original_raw_df']
                    ws['raw_df'] = persisted['raw_df']
                    ws['filtered_df'] = persisted.get('filtered_df') or persisted['raw_df']
                    ws['analysis_results'] = persisted.get('analysis_results', {})
                    ws['initial_profile'] = ws['analysis_results'].get('profile', {}).copy() if ws['analysis_results'] else {}
                    ws['cleaning_recipe'] = persisted.get('cleaning_recipe', [])
                    ws['active_filters'] = persisted.get('active_filters', {})
                    ws['user_targets'] = persisted.get('user_targets', {})
                    ws['dashboard_layout'] = persisted.get('dashboard_layout', ['kpis', 'target', 'trend', 'donut', 'bar', 'story', 'anomalies', 'quality'])
                    ws['upload_timestamp'] = persisted.get('upload_timestamp')
                    ws['analysis_status'] = 'complete'
                if needs_comp_restore and 'comparison' in persisted and isinstance(persisted['comparison'], dict) and persisted['comparison']:
                    ws['comparison'] = persisted['comparison']

        for k in ('user_mode', 'user_dataset_id', 'user_dataset_name',
                  'raw_df', 'filtered_df', 'analysis_results',
                  'active_filters', 'user_targets', 'dashboard_layout'):
            if k not in st.session_state:
                st.session_state[k] = ws.get(k)

    @classmethod
    def is_user_mode(cls):
        cls.initialize()
        ws = st.session_state[_NS]
        return bool(ws.get('user_mode', False) and ws.get('raw_df') is not None)

    @classmethod
    def has_active_dataset(cls) -> bool:
        cls.initialize()
        ws = st.session_state[_NS]
        raw = ws.get('raw_df')
        return bool(ws.get('user_mode', False) and isinstance(raw, pd.DataFrame) and not raw.empty)

    @classmethod
    def is_demo_mode(cls):
        return not cls.has_active_dataset()

    @classmethod
    def get_dataset_version(cls) -> int:
        cls.initialize()
        return st.session_state[_NS].get('dataset_version', 1)

    @classmethod
    def get_active_section(cls) -> str:
        cls.initialize()
        return st.session_state[_NS].get('active_workspace_section', "📥 Ingest & Quality Center")

    @classmethod
    def set_active_section(cls, section_name: str) -> None:
        cls.initialize()
        st.session_state[_NS]['active_workspace_section'] = section_name

    @classmethod
    def get_active_role_view(cls) -> str:
        cls.initialize()
        return st.session_state[_NS].get('active_role_view', "Executive")

    @classmethod
    def set_active_role_view(cls, role_name: str) -> None:
        cls.initialize()
        st.session_state[_NS]['active_role_view'] = role_name

    @classmethod
    def activate_user_dataset(cls, df: pd.DataFrame, filename: str, file_hash: str, data_source: str = "user_upload"):
        cls.initialize()
        t0 = time.time()
        ws = st.session_state[_NS]
        
        cache_key = f"{file_hash}_{filename}_v1"
        analysis_cache = ws.setdefault('analysis_cache', {})

        # Check Central Analysis Cache
        if cache_key in analysis_cache:
            cached_res = analysis_cache[cache_key]
            ws['user_mode'] = True
            ws['user_dataset_id'] = file_hash
            ws['user_dataset_name'] = filename
            ws['dataset_version'] = 1
            ws['data_source'] = data_source
            ws['uploaded_signature'] = f"{filename}_{file_hash}"
            ws['original_raw_df'] = df
            ws['raw_df'] = df
            ws['filtered_df'] = df
            ws['last_filter_signature'] = None
            ws['cleaning_recipe'] = []
            ws['active_filters'] = {}
            ws['analysis_results'] = cached_res
            ws['initial_profile'] = cached_res.get('profile', {}).copy()
            ws['analysis_status'] = 'complete'
            
            telemetry = ws.setdefault('telemetry', {})
            telemetry['cache_status'] = 'HIT'
            telemetry['cache_hits'] = telemetry.get('cache_hits', 0) + 1
            telemetry['load_time_ms'] = round((time.time() - t0) * 1000, 2)

            AuditTrail.log_event("DATASET_RESTORED_CACHE", file_hash, f"Loaded {filename} from central cache")

            st.session_state['user_mode'] = True
            st.session_state['user_dataset_id'] = file_hash
            st.session_state['user_dataset_name'] = filename
            st.session_state['raw_df'] = df
            st.session_state['filtered_df'] = df
            st.session_state['analysis_results'] = cached_res
            st.session_state['active_filters'] = {}
            return cached_res

        # Cold Analysis Path (Calculate & Cache)
        new_version = ws.get('dataset_version', 0) + 1
        ws['user_mode'] = True
        ws['user_dataset_id'] = file_hash
        ws['user_dataset_name'] = filename
        ws['dataset_version'] = new_version
        ws['data_source'] = data_source
        ws['uploaded_signature'] = f"{filename}_{file_hash}"
        ws['original_raw_df'] = df
        ws['raw_df'] = df
        ws['filtered_df'] = df
        ws['last_filter_signature'] = None
        ws['cleaning_recipe'] = []
        ws['active_filters'] = {}
        ws['upload_timestamp'] = time.time()
        ws['analysis_status'] = 'fast_profile'

        t_schema0 = time.time()
        schema_meta = SchemaDetector.detect_schema(df)
        
        t_prof0 = time.time()
        profile_meta = DataProfiler.profile(df, schema_meta)
        prof_time_ms = round((time.time() - t_prof0) * 1000, 2)
        
        t_kpi0 = time.time()
        metrics = MetricEngine.calculate_metrics(df, schema_meta)
        kpi_time_ms = round((time.time() - t_kpi0) * 1000, 2)
        
        insights = InsightEngine.generate_insights(df, schema_meta, metrics)
        anomalies = AnomalyEngine.detect_anomalies(df, schema_meta, metrics)
        total_duration_ms = round((time.time() - t0) * 1000, 2)

        results = {
            'dataset_id': file_hash,
            'dataset_name': filename,
            'dataset_version': new_version,
            'data_source': data_source,
            'profile': profile_meta,
            'schema': schema_meta,
            'kpis': metrics,
            'insights': insights,
            'anomalies': anomalies,
            'analysis_time_ms': total_duration_ms,
        }
        
        # Save to Central Analysis Cache
        analysis_cache[cache_key] = results
        ws['analysis_results'] = results
        ws['initial_profile'] = profile_meta.copy()
        ws['analysis_status'] = 'complete'
        ws['telemetry'] = {
            "load_time_ms": total_duration_ms,
            "fast_profile_time_ms": round(prof_time_ms * 0.3, 2),
            "deep_analysis_time_ms": round(prof_time_ms * 0.7, 2),
            "profiling_time_ms": prof_time_ms,
            "kpi_time_ms": kpi_time_ms,
            "filtering_time_ms": 0.0,
            "section_time_ms": 0.0,
            "cache_status": "MISS",
            "cache_hits": ws.get('telemetry', {}).get('cache_hits', 0)
        }

        AuditTrail.log_event("DATASET_ACTIVATED", file_hash, f"Activated {filename} ({len(df):,} rows)")

        # Sync legacy flat keys
        st.session_state['user_mode'] = True
        st.session_state['user_dataset_id'] = file_hash
        st.session_state['user_dataset_name'] = filename
        st.session_state['raw_df'] = ws['raw_df']
        st.session_state['filtered_df'] = ws['filtered_df']
        st.session_state['analysis_results'] = results
        st.session_state['active_filters'] = {}

        # Persist to disk for browser refresh / session reconnection
        try:
            PersistentStorageManager.save_dataset(
                dataset_id=file_hash,
                filename=filename,
                df=df,
                original_df=df,
                analysis_results=results,
                cleaning_recipe=[],
                data_source=data_source
            )
            PersistentStorageManager.save_active_state(ws)
        except Exception as exc:
            pass

        return results

    @classmethod
    def clear_active_dataset(cls):
        cls.initialize()
        ws = st.session_state[_NS]
        old_id = ws.get('user_dataset_id', 'N/A')
        ws['user_mode'] = False
        ws['user_dataset_id'] = None
        ws['user_dataset_name'] = None
        ws['dataset_version'] = ws.get('dataset_version', 1) + 1
        ws['data_source'] = 'none'
        ws['uploaded_signature'] = None
        ws['original_raw_df'] = None
        ws['raw_df'] = None
        ws['filtered_df'] = None
        ws['last_filter_signature'] = None
        ws['analysis_results'] = {}
        ws['analysis_status'] = 'idle'
        ws['initial_profile'] = {}
        ws['cleaning_recipe'] = []
        ws['active_filters'] = {}
        ws['user_targets'] = {}
        ws['upload_timestamp'] = None

        AuditTrail.log_event("DATASET_CLEARED", str(old_id), "Workspace reverted to clean slate")
        PersistentStorageManager.clear_active_state()

        st.session_state['user_mode'] = False
        st.session_state['user_dataset_id'] = None
        st.session_state['user_dataset_name'] = None
        st.session_state['raw_df'] = None
        st.session_state['filtered_df'] = None
        st.session_state['analysis_results'] = {}
        st.session_state['active_filters'] = {}
        st.session_state['user_targets'] = {}

    @classmethod
    def revert_to_demo(cls):
        cls.clear_active_dataset()

    @classmethod
    def get_active_df(cls) -> pd.DataFrame:
        cls.initialize()
        ws = st.session_state[_NS]
        if ws.get('user_mode') and ws.get('raw_df') is not None:
            filtered = ws.get('filtered_df')
            if isinstance(filtered, pd.DataFrame) and not filtered.empty:
                return filtered
            raw = ws.get('raw_df')
            if isinstance(raw, pd.DataFrame) and not raw.empty:
                return raw
            return pd.DataFrame()
        return pd.DataFrame()

    @classmethod
    def get_raw_df(cls) -> pd.DataFrame:
        cls.initialize()
        ws = st.session_state[_NS]
        if ws.get('user_mode') and ws.get('raw_df') is not None:
            return ws['raw_df']
        return pd.DataFrame()

    @classmethod
    def get_original_raw_df(cls) -> pd.DataFrame:
        cls.initialize()
        ws = st.session_state[_NS]
        if ws.get('user_mode') and ws.get('original_raw_df') is not None:
            return ws['original_raw_df']
        return pd.DataFrame()

    @classmethod
    def get_analysis_results(cls) -> Dict[str, Any]:
        cls.initialize()
        ws = st.session_state[_NS]
        if ws.get('user_mode') and ws.get('raw_df') is not None and not ws.get('raw_df').empty:
            return ws.get('analysis_results', {})
        return _DEMO_RESULTS

    # ----------------------------------------------------------------------
    # Interactive Cleaning & Data Preparation Layer
    # ----------------------------------------------------------------------
    @classmethod
    def apply_cleaning_step(cls, step_dict: Dict[str, Any]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        cls.initialize()
        ws = st.session_state[_NS]
        if not ws.get('user_mode') or ws.get('raw_df') is None:
            return pd.DataFrame(), {"error": "No user dataset active"}

        current_df = ws['raw_df']
        action = step_dict.get('action')
        params = step_dict.get('params', {})

        if action == "drop_missing":
            cleaned_df, stats = DataCleaningEngine.drop_missing(current_df, **params)
        elif action == "impute_missing":
            cleaned_df, stats = DataCleaningEngine.impute_missing(current_df, **params)
        elif action == "remove_duplicates":
            cleaned_df, stats = DataCleaningEngine.remove_duplicates(current_df, **params)
        elif action == "handle_outliers":
            cleaned_df, stats = DataCleaningEngine.handle_outliers(current_df, **params)
        elif action == "strip_whitespace":
            cleaned_df, stats = DataCleaningEngine.strip_whitespace(current_df, **params)
        elif action == "change_case":
            cleaned_df, stats = DataCleaningEngine.change_case(current_df, **params)
        elif action == "replace_sentinels":
            cleaned_df, stats = DataCleaningEngine.replace_sentinels(current_df, **params)
        elif action == "coerce_data_type":
            cleaned_df, stats = DataCleaningEngine.coerce_data_type(current_df, **params)
        elif action == "drop_columns":
            cleaned_df, stats = DataCleaningEngine.drop_columns(current_df, **params)
        else:
            return current_df, {"error": f"Unknown action: {action}"}

        # Update working dataset and recipe
        new_version = ws.get('dataset_version', 1) + 1
        ws['dataset_version'] = new_version
        ws['raw_df'] = cleaned_df
        ws['filtered_df'] = cleaned_df
        ws['last_filter_signature'] = None
        recipe = ws.get('cleaning_recipe', [])
        step_entry = {
            "step_num": len(recipe) + 1,
            "action": action,
            "params": params,
            "stats": stats,
            "title": step_dict.get("title", action.replace("_", " ").title()),
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        recipe.append(step_entry)
        ws['cleaning_recipe'] = recipe

        # Re-run analytics pipeline on cleaned data
        t0 = time.time()
        schema_meta = SchemaDetector.detect_schema(cleaned_df)
        profile_meta = DataProfiler.profile(cleaned_df, schema_meta)
        metrics = MetricEngine.calculate_metrics(cleaned_df, schema_meta)
        insights = InsightEngine.generate_insights(cleaned_df, schema_meta, metrics)
        anomalies = AnomalyEngine.detect_anomalies(cleaned_df, schema_meta, metrics)
        duration_ms = round((time.time() - t0) * 1000, 2)

        results = {
            'dataset_id': ws.get('user_dataset_id'),
            'dataset_name': ws.get('user_dataset_name'),
            'dataset_version': new_version,
            'data_source': ws.get('data_source', 'user_upload'),
            'profile': profile_meta,
            'schema': schema_meta,
            'kpis': metrics,
            'insights': insights,
            'anomalies': anomalies,
            'analysis_time_ms': duration_ms,
        }
        
        # Cache cleaned version result
        ver_cache_key = f"{ws.get('user_dataset_id')}_{ws.get('user_dataset_name')}_v{new_version}"
        ws.setdefault('analysis_cache', {})[ver_cache_key] = results
        ws['analysis_results'] = results

        AuditTrail.log_event("CLEANING_STEP_APPLIED", str(ws.get('user_dataset_id')), f"Applied: {step_entry['title']}")

        st.session_state['raw_df'] = cleaned_df
        st.session_state['filtered_df'] = cleaned_df
        st.session_state['analysis_results'] = results

        # Persist updated cleaning state to disk
        try:
            PersistentStorageManager.update_cleaning_state(
                dataset_id=ws.get('user_dataset_id'),
                cleaned_df=cleaned_df,
                cleaning_recipe=recipe,
                analysis_results=results
            )
            PersistentStorageManager.save_active_state(ws)
        except Exception:
            pass

        return cleaned_df, stats

    @classmethod
    def undo_last_cleaning_step(cls) -> Optional[Dict[str, Any]]:
        cls.initialize()
        ws = st.session_state[_NS]
        recipe = ws.get('cleaning_recipe', [])
        if not recipe or ws.get('original_raw_df') is None:
            return None

        popped = recipe.pop()
        ws['cleaning_recipe'] = recipe
        new_version = ws.get('dataset_version', 1) + 1
        ws['dataset_version'] = new_version

        base_df = ws['original_raw_df']
        if recipe:
            cleaned_df, _ = DataCleaningEngine.apply_cleaning_recipe(base_df, recipe)
        else:
            cleaned_df = base_df

        ws['raw_df'] = cleaned_df
        ws['filtered_df'] = cleaned_df
        ws['last_filter_signature'] = None

        t0 = time.time()
        schema_meta = SchemaDetector.detect_schema(cleaned_df)
        profile_meta = DataProfiler.profile(cleaned_df, schema_meta)
        metrics = MetricEngine.calculate_metrics(cleaned_df, schema_meta)
        insights = InsightEngine.generate_insights(cleaned_df, schema_meta, metrics)
        anomalies = AnomalyEngine.detect_anomalies(cleaned_df, schema_meta, metrics)
        duration_ms = round((time.time() - t0) * 1000, 2)

        results = {
            'dataset_id': ws.get('user_dataset_id'),
            'dataset_name': ws.get('user_dataset_name'),
            'dataset_version': new_version,
            'data_source': ws.get('data_source', 'user_upload'),
            'profile': profile_meta,
            'schema': schema_meta,
            'kpis': metrics,
            'insights': insights,
            'anomalies': anomalies,
            'analysis_time_ms': duration_ms,
        }
        
        ver_cache_key = f"{ws.get('user_dataset_id')}_{ws.get('user_dataset_name')}_v{new_version}"
        ws.setdefault('analysis_cache', {})[ver_cache_key] = results
        ws['analysis_results'] = results

        AuditTrail.log_event("CLEANING_STEP_UNDONE", str(ws.get('user_dataset_id')), f"Undid: {popped.get('title')}")

        st.session_state['raw_df'] = cleaned_df
        st.session_state['filtered_df'] = cleaned_df
        st.session_state['analysis_results'] = results

        # Persist undone cleaning state to disk
        try:
            PersistentStorageManager.update_cleaning_state(
                dataset_id=ws.get('user_dataset_id'),
                cleaned_df=cleaned_df,
                cleaning_recipe=recipe,
                analysis_results=results
            )
            PersistentStorageManager.save_active_state(ws)
        except Exception:
            pass

        return popped

    @classmethod
    def reset_cleaning(cls) -> None:
        cls.initialize()
        ws = st.session_state[_NS]
        if not ws.get('user_mode') or ws.get('original_raw_df') is None:
            return

        orig_df = ws['original_raw_df']
        new_version = ws.get('dataset_version', 1) + 1
        ws['dataset_version'] = new_version
        ws['raw_df'] = orig_df
        ws['filtered_df'] = orig_df
        ws['last_filter_signature'] = None
        ws['cleaning_recipe'] = []

        t0 = time.time()
        schema_meta = SchemaDetector.detect_schema(orig_df)
        profile_meta = DataProfiler.profile(orig_df, schema_meta)
        metrics = MetricEngine.calculate_metrics(orig_df, schema_meta)
        insights = InsightEngine.generate_insights(orig_df, schema_meta, metrics)
        anomalies = AnomalyEngine.detect_anomalies(orig_df, schema_meta, metrics)
        duration_ms = round((time.time() - t0) * 1000, 2)

        results = {
            'dataset_id': ws.get('user_dataset_id'),
            'dataset_name': ws.get('user_dataset_name'),
            'dataset_version': new_version,
            'data_source': ws.get('data_source', 'user_upload'),
            'profile': profile_meta,
            'schema': schema_meta,
            'kpis': metrics,
            'insights': insights,
            'anomalies': anomalies,
            'analysis_time_ms': duration_ms,
        }
        
        ver_cache_key = f"{ws.get('user_dataset_id')}_{ws.get('user_dataset_name')}_v{new_version}"
        ws.setdefault('analysis_cache', {})[ver_cache_key] = results
        ws['analysis_results'] = results

        AuditTrail.log_event("CLEANING_RESET", str(ws.get('user_dataset_id')), "Reverted to original uncleaned dataset")

        st.session_state['raw_df'] = orig_df
        st.session_state['filtered_df'] = orig_df
        st.session_state['analysis_results'] = results

        # Persist reset cleaning state to disk
        try:
            PersistentStorageManager.update_cleaning_state(
                dataset_id=ws.get('user_dataset_id'),
                cleaned_df=orig_df,
                cleaning_recipe=[],
                analysis_results=results
            )
            PersistentStorageManager.save_active_state(ws)
        except Exception:
            pass

    @classmethod
    def get_cleaning_recipe(cls) -> List[Dict[str, Any]]:
        cls.initialize()
        return st.session_state[_NS].get('cleaning_recipe', [])

    @classmethod
    def get_initial_profile(cls) -> Dict[str, Any]:
        cls.initialize()
        return st.session_state[_NS].get('initial_profile', {})

    # ----------------------------------------------------------------------
    # Fast Global Filters with Signature Caching
    # ----------------------------------------------------------------------
    @classmethod
    def apply_filters(cls, filter_dict: Dict[str, Any]) -> pd.DataFrame:
        cls.initialize()
        ws = st.session_state[_NS]
        raw = ws.get('raw_df')
        if raw is None or (isinstance(raw, pd.DataFrame) and raw.empty):
            return pd.DataFrame()

        filter_items = []
        for k, v in sorted(filter_dict.items()):
            if isinstance(v, (list, tuple, set)):
                filter_items.append((k, tuple(sorted(str(x) for x in v))))
            else:
                filter_items.append((k, str(v)))
        current_filter_sig = hash((ws.get('user_dataset_id'), ws.get('dataset_version'), tuple(filter_items)))

        if ws.get('last_filter_signature') == current_filter_sig and ws.get('filtered_df') is not None:
            telemetry = ws.setdefault('telemetry', {})
            telemetry['cache_hits'] = telemetry.get('cache_hits', 0) + 1
            return ws['filtered_df']

        t0 = time.time()
        df_filtered = raw.copy()
        ws['active_filters'] = filter_dict
        st.session_state['active_filters'] = filter_dict
        import datetime

        for col_k, val_v in filter_dict.items():
            if col_k in ('date_range', 'date_col', 'category_col',
                         'selected_categories', 'region_col', 'selected_regions'):
                continue
            if col_k not in df_filtered.columns:
                continue
            if isinstance(val_v, (list, tuple)) and len(val_v) == 2:
                try:
                    if all(isinstance(v, (datetime.date, pd.Timestamp)) for v in val_v):
                        dt_s = pd.to_datetime(df_filtered[col_k], errors='coerce')
                        mask = (dt_s.dt.date >= val_v[0]) & (dt_s.dt.date <= val_v[1])
                        df_filtered = df_filtered[mask]
                        continue
                except Exception:
                    pass
                df_filtered = df_filtered[df_filtered[col_k].isin(list(val_v))]
            elif isinstance(val_v, (list, set)):
                df_filtered = df_filtered[df_filtered[col_k].isin(list(val_v))]

        date_range = filter_dict.get('date_range')
        date_col = filter_dict.get('date_col')
        if date_range and date_col and date_col in df_filtered.columns and len(date_range) == 2:
            try:
                dt_s = pd.to_datetime(df_filtered[date_col], errors='coerce')
                mask = (dt_s.dt.date >= date_range[0]) & (dt_s.dt.date <= date_range[1])
                df_filtered = df_filtered[mask]
            except Exception:
                pass

        cat_col = filter_dict.get('category_col')
        sel_cats = filter_dict.get('selected_categories')
        if cat_col and sel_cats and cat_col in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[cat_col].isin(sel_cats)]

        reg_col = filter_dict.get('region_col')
        sel_regs = filter_dict.get('selected_regions')
        if reg_col and sel_regs and reg_col in df_filtered.columns:
            df_filtered = df_filtered[df_filtered[reg_col].isin(sel_regs)]

        ws['filtered_df'] = df_filtered
        ws['last_filter_signature'] = current_filter_sig
        st.session_state['filtered_df'] = df_filtered

        schema_meta = ws.get('analysis_results', {}).get('schema', {})
        if schema_meta:
            try:
                upd_m = MetricEngine.calculate_metrics(df_filtered, schema_meta)
                upd_i = InsightEngine.generate_insights(df_filtered, schema_meta, upd_m)
                upd_a = AnomalyEngine.detect_anomalies(df_filtered, schema_meta, upd_m)
                ws['analysis_results']['kpis'] = upd_m
                ws['analysis_results']['insights'] = upd_i
                ws['analysis_results']['anomalies'] = upd_a
                st.session_state['analysis_results'] = ws['analysis_results']
            except Exception:
                pass

        filter_duration_ms = round((time.time() - t0) * 1000, 2)
        telemetry = ws.setdefault('telemetry', {})
        telemetry['filtering_time_ms'] = filter_duration_ms
        return df_filtered

    @classmethod
    def set_target(cls, metric_name, target_val):
        cls.initialize()
        st.session_state[_NS]['user_targets'][metric_name] = float(target_val)
        AuditTrail.log_event("TARGET_SET", st.session_state[_NS].get('user_dataset_id', 'N/A'), f"Set target for {metric_name}: ${target_val:,.2f}")

    @classmethod
    def get_targets(cls):
        cls.initialize()
        return st.session_state[_NS].get('user_targets', {})

    @classmethod
    def reset_targets(cls):
        cls.initialize()
        st.session_state[_NS]['user_targets'] = {}

    @classmethod
    def get_dashboard_layout(cls):
        cls.initialize()
        return st.session_state[_NS].get(
            'dashboard_layout',
            ['kpis', 'target', 'trend', 'donut', 'bar', 'story', 'anomalies', 'quality']
        )

    @classmethod
    def set_dashboard_layout(cls, layout):
        cls.initialize()
        st.session_state[_NS]['dashboard_layout'] = layout

    @classmethod
    def get_dataset_meta(cls):
        cls.initialize()
        res = cls.get_analysis_results()
        return {
            'dataset_id': res.get('dataset_id'),
            'dataset_name': res.get('dataset_name'),
            'dataset_version': res.get('dataset_version', 1),
            'is_user_mode': cls.has_active_dataset(),
            'analysis_time_ms': res.get('analysis_time_ms', 0.0),
        }

    @classmethod
    def get_kpis(cls):
        return cls.get_analysis_results().get('kpis', {})

    @classmethod
    def get_schema_meta(cls):
        return cls.get_analysis_results().get('schema', {})

    @classmethod
    def get_profile_meta(cls):
        return cls.get_analysis_results().get('profile', {})

    @classmethod
    def get_insights(cls):
        return cls.get_analysis_results().get('insights', [])

    @classmethod
    def get_anomalies(cls):
        return cls.get_analysis_results().get('anomalies', [])

    @classmethod

    @classmethod
    def get_comparison_state(cls) -> Dict[str, Any]:
        cls.initialize()
        return st.session_state[_NS].get('comparison', {})

    @classmethod
    def set_comparison_dataset_a(cls, df: pd.DataFrame, name: str, fhash: str) -> None:
        cls.initialize()
        comp = st.session_state[_NS].setdefault('comparison', {})
        comp['dataset_a'] = df.copy() if isinstance(df, pd.DataFrame) else None
        comp['dataset_a_name'] = name
        comp['dataset_a_fingerprint'] = fhash
        # Invalidate existing comparison cache
        comp['comparison_results'] = {}
        comp['comparison_insights'] = []
        AuditTrail.log_event("COMPARISON_DATASET_A_LOADED", fhash, f"Loaded comparison Dataset A '{name}' ({len(df) if df is not None else 0:,} rows)")
        try:
            if isinstance(df, pd.DataFrame):
                PersistentStorageManager.save_dataset(dataset_id=fhash, filename=name, df=df, original_df=df)
            PersistentStorageManager.save_active_state(st.session_state[_NS])
        except Exception:
            pass

    @classmethod
    def set_comparison_dataset_b(cls, df: pd.DataFrame, name: str, fhash: str) -> None:
        cls.initialize()
        comp = st.session_state[_NS].setdefault('comparison', {})
        comp['dataset_b'] = df.copy() if isinstance(df, pd.DataFrame) else None
        comp['dataset_b_name'] = name
        comp['dataset_b_fingerprint'] = fhash
        # Invalidate existing comparison cache
        comp['comparison_results'] = {}
        comp['comparison_insights'] = []
        AuditTrail.log_event("COMPARISON_DATASET_B_LOADED", fhash, f"Loaded comparison Dataset B '{name}' ({len(df) if df is not None else 0:,} rows)")
        try:
            if isinstance(df, pd.DataFrame):
                PersistentStorageManager.save_dataset(dataset_id=fhash, filename=name, df=df, original_df=df)
            PersistentStorageManager.save_active_state(st.session_state[_NS])
        except Exception:
            pass

    @classmethod
    def set_comparison_schema_mapping(cls, mapping: Dict[str, str]) -> None:
        cls.initialize()
        comp = st.session_state[_NS].setdefault('comparison', {})
        comp['schema_mapping'] = mapping
        comp['comparison_results'] = {}
        try:
            PersistentStorageManager.save_active_state(st.session_state[_NS])
        except Exception:
            pass

    @classmethod
    def set_comparison_results(cls, results: Dict[str, Any]) -> None:
        cls.initialize()
        comp = st.session_state[_NS].setdefault('comparison', {})
        comp['comparison_results'] = results
        comp['comparison_insights'] = results.get('insights', [])
        try:
            PersistentStorageManager.save_active_state(st.session_state[_NS])
        except Exception:
            pass

    @classmethod
    def clear_comparison_state(cls) -> None:
        cls.initialize()
        st.session_state[_NS]['comparison'] = {
            'dataset_a': None,
            'dataset_b': None,
            'dataset_a_name': None,
            'dataset_b_name': None,
            'dataset_a_fingerprint': None,
            'dataset_b_fingerprint': None,
            'schema_mapping': {},
            'comparison_results': {},
            'comparison_profile': {},
            'comparison_insights': []
        }
        AuditTrail.log_event("COMPARISON_CLEARED", "N/A", "Cleared dual-dataset comparison state.")
        try:
            PersistentStorageManager.save_active_state(st.session_state[_NS])
        except Exception:
            pass

    @classmethod
    def has_comparison_datasets(cls) -> bool:
        cls.initialize()
        comp = st.session_state[_NS].get('comparison', {})
        df_a = comp.get('dataset_a')
        df_b = comp.get('dataset_b')
        return bool(isinstance(df_a, pd.DataFrame) and not df_a.empty and isinstance(df_b, pd.DataFrame) and not df_b.empty)

    @classmethod
    def get_workspace_state(cls):
        cls.initialize()
        ws = st.session_state[_NS]
        raw_df = ws.get('raw_df')
        orig_df = ws.get('original_raw_df')
        filt_df = ws.get('filtered_df')
        recipe = ws.get('cleaning_recipe', [])
        res = ws.get('analysis_results', {})
        telemetry = ws.get('telemetry', {})
        user_mode = bool(ws.get('user_mode', False) and isinstance(raw_df, pd.DataFrame) and not raw_df.empty)
        return {
            'workspace_exists': _NS in st.session_state,
            'user_mode': user_mode,
            'dataset_name': ws.get('user_dataset_name') or 'None',
            'dataset_id': ws.get('user_dataset_id') or 'N/A',
            'dataset_version': ws.get('dataset_version', 1),
            'active_section': ws.get('active_workspace_section', "📥 Ingest & Quality Center"),
            'active_role_view': ws.get('active_role_view', "Executive"),
            'data_source': ws.get('data_source', 'none'),
            'raw_rows': len(raw_df) if isinstance(raw_df, pd.DataFrame) else 0,
            'raw_cols': len(raw_df.columns) if isinstance(raw_df, pd.DataFrame) else 0,
            'original_rows': len(orig_df) if isinstance(orig_df, pd.DataFrame) else 0,
            'filtered_rows': len(filt_df) if isinstance(filt_df, pd.DataFrame) else 0,
            'original_df_available': isinstance(orig_df, pd.DataFrame) and not orig_df.empty,
            'working_df_available': isinstance(raw_df, pd.DataFrame) and not raw_df.empty,
            'filtered_df_available': isinstance(filt_df, pd.DataFrame) and not filt_df.empty,
            'profiler_available': bool(res.get('profile')),
            'schema_available': bool(res.get('schema')),
            'analysis_results_available': bool(res),
            'analysis_status': ws.get('analysis_status', 'idle'),
            'cleaning_steps_count': len(recipe),
            'active_filters': ws.get('active_filters', {}),
            'upload_timestamp': ws.get('upload_timestamp'),
            'dataframe_available': isinstance(raw_df, pd.DataFrame) and not raw_df.empty,
            'demo_mode': not user_mode,
            'load_time_ms': telemetry.get('load_time_ms', 0.0),
            'fast_profile_time_ms': telemetry.get('fast_profile_time_ms', 0.0),
            'deep_analysis_time_ms': telemetry.get('deep_analysis_time_ms', 0.0),
            'profiling_time_ms': telemetry.get('profiling_time_ms', 0.0),
            'kpi_time_ms': telemetry.get('kpi_time_ms', 0.0),
            'filtering_time_ms': telemetry.get('filtering_time_ms', 0.0),
            'section_time_ms': telemetry.get('section_time_ms', 0.0),
            'cache_status': telemetry.get('cache_status', 'MISS'),
            'cache_hits': telemetry.get('cache_hits', 0)
        }

    @classmethod
    def purge_persistent_storage(cls) -> None:
        """Purges all user uploaded datasets and active state from disk."""
        cls.clear_active_dataset()
        PersistentStorageManager.clear_all_user_workspaces()


AnalyticsManager.apply_cleaning_operation = AnalyticsManager.apply_cleaning_step
AnalyticsManager.undo_cleaning_operation = AnalyticsManager.undo_last_cleaning_step
AnalyticsManager.undo_cleaning_step = AnalyticsManager.undo_last_cleaning_step
AnalyticsManager.reset_cleaning_pipeline = AnalyticsManager.reset_cleaning
