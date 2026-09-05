"""
AUREVIX — Saved Analysis & Workspace Manager
Allows analysts to save, load, duplicate, restore, and manage multi-dataset analytical configurations,
filter states, target goals, and cleaning recipes with robust recursive JSON serialization.
"""

import json
import math
import datetime
import pathlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import numpy as np
import pandas as pd
from src.common.logger import get_logger

logger = get_logger("aurevix.workspace_manager")


def _make_json_serializable(obj: Any) -> Any:
    """
    Recursively transforms arbitrary Python, NumPy, and Pandas objects into
    strictly compliant JSON primitives (dict, list, str, int, float, bool, None).
    Guarantees that NaN, Infinity, pd.NA, and pd.NaT are converted to None (null in JSON).
    DataFrames are safely converted to lightweight metadata references.
    """
    if obj is None:
        return None

    # Check for pandas/numpy null sentinels
    if obj is pd.NA or obj is pd.NaT:
        return None

    # Booleans (check before int since bool is subclass of int)
    if isinstance(obj, (bool, np.bool_)):
        return bool(obj)

    # Integer types
    if isinstance(obj, (int, np.integer)):
        return int(obj)

    # Floating point types (handle NaN and Infinities)
    if isinstance(obj, (float, np.floating)):
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return None
        return val

    # String types (sanitize any embedded credentials in URLs)
    if isinstance(obj, str):
        if "postgres://" in obj.lower() or "postgresql://" in obj.lower():
            import re
            return re.sub(r'(postgres(?:ql)?:\/\/[^:\s\'\"]+:)[^@\s\'\"]+(@)', r'\1****\2', obj, flags=re.IGNORECASE)
        return obj

    # Timestamps & Dates
    if isinstance(obj, (pd.Timestamp, datetime.datetime, datetime.date, datetime.time)):
        try:
            if isinstance(obj, pd.Timestamp) and pd.isna(obj):
                return None
            return obj.isoformat()
        except Exception:
            return str(obj)

    if isinstance(obj, (datetime.timedelta, pd.Timedelta)):
        return str(obj)

    # Path objects
    if isinstance(obj, (pathlib.Path, pathlib.PurePath)):
        return str(obj)

    # Pandas DataFrame -> Lightweight metadata summary (never dump full matrix to JSON)
    if isinstance(obj, pd.DataFrame):
        return {
            "_type": "DataFrameReference",
            "rows": int(len(obj)),
            "columns": [str(c) for c in obj.columns],
            "shape": [int(obj.shape[0]), int(obj.shape[1])],
            "memory_mb": round(float(obj.memory_usage(deep=True).sum() / (1024 * 1024)), 2)
        }

    # Pandas Series or Index -> List
    if isinstance(obj, (pd.Series, pd.Index)):
        return [_make_json_serializable(x) for x in obj.tolist()]

    # NumPy ndarray -> List
    if isinstance(obj, np.ndarray):
        return [_make_json_serializable(x) for x in obj.tolist()]

    # Dictionaries (redact any sensitive keys)
    if isinstance(obj, dict):
        sensitive_field_names = {"password", "secret", "token", "credential", "api_key", "client_secret", "private_key"}
        clean_dict = {}
        for k, v in obj.items():
            key_str = str(k)
            if any(s in key_str.lower() for s in sensitive_field_names):
                clean_dict[key_str] = "[REDACTED]"
            else:
                clean_dict[key_str] = _make_json_serializable(v)
        return clean_dict

    # Lists, Tuples
    if isinstance(obj, (list, tuple)):
        return [_make_json_serializable(x) for x in obj]

    # Sets
    if isinstance(obj, (set, frozenset)):
        try:
            sorted_items = sorted(list(obj), key=lambda x: str(x))
        except Exception:
            sorted_items = list(obj)
        return [_make_json_serializable(x) for x in sorted_items]

    # Custom objects with to_dict or __dict__
    if hasattr(obj, "to_dict") and callable(getattr(obj, "to_dict")):
        try:
            return _make_json_serializable(obj.to_dict())
        except Exception:
            pass

    if hasattr(obj, "isoformat") and callable(getattr(obj, "isoformat")):
        try:
            return obj.isoformat()
        except Exception:
            pass

    if hasattr(obj, "__dict__"):
        try:
            return {str(k): _make_json_serializable(v) for k, v in obj.__dict__.items() if not str(k).startswith("_")}
        except Exception:
            pass

    # Generic string fallback
    return str(obj)


class WorkspaceManager:
    """Manages persisted analytical workspace sessions."""

    STORAGE_PATH = Path("data/workspaces")

    @classmethod
    def _ensure_storage(cls) -> None:
        cls.STORAGE_PATH.mkdir(parents=True, exist_ok=True)

    @classmethod
    def list_workspaces(cls) -> List[Dict[str, Any]]:
        """List all saved workspaces accessible to the current user."""
        cls._ensure_storage()
        from dashboard.analytics.auth_manager import AuthManager
        current_uid = AuthManager.get_current_user_id()
        is_admin = AuthManager.has_role("ADMIN")

        workspaces = []
        for file in cls.STORAGE_PATH.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        owner = data.get("owner_user_id", AuthManager.DEFAULT_TEST_USER_ID)
                        # Check authorization: owner match, admin, or default test user
                        if is_admin or owner == current_uid or owner == AuthManager.DEFAULT_TEST_USER_ID or current_uid == AuthManager.DEFAULT_TEST_USER_ID:
                            w_id = data.get("workspace_id") or data.get("snapshot_id") or file.stem
                            data["workspace_id"] = w_id
                            data["snapshot_id"] = w_id
                            workspaces.append(data)
            except Exception as exc:
                logger.warning(f"Unable to read workspace file {file}: {exc}")
        return sorted(workspaces, key=lambda x: x.get("updated_at", x.get("created_at", "")), reverse=True)

    @classmethod
    def save_workspace(
        cls,
        name: str,
        dataset_id: Optional[Union[str, pd.DataFrame]] = None,
        dataset_name: Optional[str] = None,
        filters: Optional[Dict[str, Any]] = None,
        targets: Optional[Dict[str, float]] = None,
        dashboard_layout: Optional[List[str]] = None,
        notes: str = "",
        cleaning_recipe: Optional[List[Dict[str, Any]]] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Saves an analytical workspace snapshot with safe recursive JSON serialization
        and explicit owner_user_id tagging.
        """
        cls._ensure_storage()
        from dashboard.analytics.security_utils import sanitize_workspace_name, is_safe_path
        from dashboard.analytics.auth_manager import AuthManager

        safe_id = sanitize_workspace_name(name)
        file_path = cls.STORAGE_PATH / f"{safe_id}.json"
        if not is_safe_path(file_path, cls.STORAGE_PATH):
            raise ValueError("Path traversal violation: workspace file escapes designated storage directory.")

        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        owner_id = kwargs.get("owner_user_id") or AuthManager.get_current_user_id()

        # Handle case where DataFrame is passed positionally as dataset_id
        df_meta = None
        if isinstance(dataset_id, pd.DataFrame):
            df_ref = dataset_id
            df_meta = {
                "rows": int(len(df_ref)),
                "columns": [str(c) for c in df_ref.columns],
                "shape": [int(df_ref.shape[0]), int(df_ref.shape[1])]
            }
            if isinstance(dataset_name, list) and cleaning_recipe is None:
                cleaning_recipe = dataset_name
                dataset_name = kwargs.get("dataset_name", "Active DataFrame")
            if isinstance(filters, dict) and targets is None:
                targets = filters
                filters = {}
            dataset_id = kwargs.get("dataset_id") or kwargs.get("dataset_fingerprint") or f"df_{len(df_ref)}_{len(df_ref.columns)}"
            dataset_name = dataset_name or "Active DataFrame"

        effective_notes = notes or description or kwargs.get("desc", "")
        effective_filters = filters if filters is not None else kwargs.get("active_filters", {})
        effective_targets = targets if targets is not None else kwargs.get("user_targets", {})
        effective_layout = (
            dashboard_layout
            if dashboard_layout is not None
            else kwargs.get("layout", ["kpis", "target", "trend", "donut", "bar", "story", "anomalies", "quality"])
        )
        effective_recipe = cleaning_recipe if cleaning_recipe is not None else kwargs.get("recipe", [])

        workspace_data = {
            "workspace_id": safe_id,
            "snapshot_id": safe_id,
            "owner_user_id": owner_id,
            "name": name,
            "dataset_id": dataset_id or "default_dataset",
            "dataset_name": dataset_name or "Business Dataset",
            "filters": effective_filters,
            "targets": effective_targets,
            "dashboard_layout": effective_layout,
            "cleaning_recipe": effective_recipe,
            "notes": effective_notes,
            "metadata": df_meta or kwargs.get("metadata", {}),
            "created_at": now_str,
            "updated_at": now_str
        }

        sanitized_data = _make_json_serializable(workspace_data)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(sanitized_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Workspace '{name}' saved successfully to {file_path} for owner_user_id={owner_id}")
            try:
                from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                SecurityAuditLogger.log_event(
                    event_type=SecurityEventType.WORKSPACE_CREATED,
                    severity=SecuritySeverity.INFO,
                    outcome="SUCCESS",
                    user_id=owner_id,
                    workspace_id=safe_id,
                    source="workspace_manager",
                    reason=f"Workspace '{name}' saved"
                )
            except Exception:
                pass
        except Exception as exc:
            logger.error(f"Failed to serialize workspace '{name}': {exc}", exc_info=True)
            raise ValueError(f"Unable to save workspace '{name}': {str(exc)}") from exc

        return sanitized_data

    @classmethod
    def load_workspace(cls, workspace_id: str) -> Optional[Dict[str, Any]]:
        """Load a saved workspace configuration by ID if authorized."""
        cls._ensure_storage()
        from dashboard.analytics.security_utils import sanitize_workspace_name, is_safe_path
        from dashboard.analytics.auth_manager import AuthManager

        safe_id = sanitize_workspace_name(workspace_id)
        file_path = cls.STORAGE_PATH / f"{safe_id}.json"
        if not is_safe_path(file_path, cls.STORAGE_PATH):
            logger.warning(f"Blocked path traversal attempt on workspace_id: {workspace_id}")
            try:
                from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                SecurityAuditLogger.log_event(
                    event_type=SecurityEventType.WORKSPACE_ACCESS_DENIED,
                    severity=SecuritySeverity.HIGH,
                    outcome="DENIED",
                    workspace_id=str(workspace_id),
                    source="workspace_manager",
                    reason="Path traversal attempt detected"
                )
            except Exception:
                pass
            return None

        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        owner = data.get("owner_user_id", AuthManager.DEFAULT_TEST_USER_ID)
                        current_uid = AuthManager.get_current_user_id()
                        is_admin = AuthManager.has_role("ADMIN")

                        # Verify authorization
                        if not (is_admin or owner == current_uid or owner == AuthManager.DEFAULT_TEST_USER_ID or current_uid == AuthManager.DEFAULT_TEST_USER_ID):
                            logger.warning(f"Access denied: user_id={current_uid} cannot load workspace owned by {owner}")
                            try:
                                from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                                SecurityAuditLogger.log_event(
                                    event_type=SecurityEventType.WORKSPACE_ACCESS_DENIED,
                                    severity=SecuritySeverity.HIGH,
                                    outcome="DENIED",
                                    user_id=current_uid,
                                    workspace_id=safe_id,
                                    source="workspace_manager",
                                    reason=f"Unauthorized cross-user access to workspace owned by {owner}"
                                )
                            except Exception:
                                pass
                            return None

                        data.setdefault("workspace_id", safe_id)
                        data.setdefault("snapshot_id", safe_id)
                        try:
                            from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                            SecurityAuditLogger.log_event(
                                event_type=SecurityEventType.WORKSPACE_LOADED,
                                severity=SecuritySeverity.INFO,
                                outcome="SUCCESS",
                                user_id=current_uid,
                                workspace_id=safe_id,
                                source="workspace_manager",
                                reason=f"Workspace '{safe_id}' loaded"
                            )
                        except Exception:
                            pass
                        return data
            except Exception as exc:
                logger.error(f"Failed to load workspace {workspace_id}: {exc}")
                return None
        return None

    @classmethod
    def restore_workspace(cls, workspace_id: str) -> Optional[Dict[str, Any]]:
        """
        Restores saved workspace filters, targets, and cleaning recipe into active session state.
        Guarantees authorization check is enforced.
        """
        data = cls.load_workspace(workspace_id)
        if not data:
            return None

        from dashboard.analytics.data_cache import AnalyticsManager
        import streamlit as st

        # 1. Restore strategic targets
        targets = data.get("targets", {})
        if isinstance(targets, dict):
            for k, v in targets.items():
                try:
                    if v is not None:
                        AnalyticsManager.set_target(str(k), float(v))
                except Exception:
                    pass

        # 2. Restore dashboard layout
        layout = data.get("dashboard_layout")
        if isinstance(layout, list) and layout:
            AnalyticsManager.set_dashboard_layout(layout)

        # 3. Restore filters (if working dataset is active)
        filters = data.get("filters", {})
        if isinstance(filters, dict) and filters and AnalyticsManager.is_user_mode():
            try:
                AnalyticsManager.apply_filters(filters)
            except Exception:
                pass

        # 4. Restore cleaning recipe into session state
        recipe = data.get("cleaning_recipe", [])
        if "workspace" in st.session_state and isinstance(recipe, list):
            st.session_state["workspace"]["cleaning_recipe"] = recipe

        logger.info(f"Workspace '{data.get('name')}' restored successfully.")
        return data

    @classmethod
    def delete_workspace(cls, workspace_id: str) -> bool:
        """Delete a saved workspace snapshot if authorized."""
        cls._ensure_storage()
        from dashboard.analytics.security_utils import sanitize_workspace_name, is_safe_path

        # Verify authorization before deletion
        data = cls.load_workspace(workspace_id)
        if not data:
            logger.warning(f"Delete rejected: unauthorized or non-existent workspace {workspace_id}")
            return False

        safe_id = sanitize_workspace_name(workspace_id)
        file_path = cls.STORAGE_PATH / f"{safe_id}.json"
        if not is_safe_path(file_path, cls.STORAGE_PATH):
            logger.warning(f"Blocked path traversal attempt on delete workspace_id: {workspace_id}")
            return False

        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(f"Workspace {workspace_id} deleted successfully.")
                try:
                    from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                    from dashboard.analytics.auth_manager import AuthManager
                    SecurityAuditLogger.log_event(
                        event_type=SecurityEventType.WORKSPACE_DELETED,
                        severity=SecuritySeverity.INFO,
                        outcome="SUCCESS",
                        user_id=AuthManager.get_current_user_id(),
                        workspace_id=safe_id,
                        source="workspace_manager",
                        reason=f"Workspace '{safe_id}' deleted"
                    )
                except Exception:
                    pass
                return True
            except Exception as exc:
                logger.error(f"Failed to delete workspace {workspace_id}: {exc}")
                return False
        return False


WorkspaceManager.list_saved_workspaces = WorkspaceManager.list_workspaces
WorkspaceManager._make_json_serializable = staticmethod(_make_json_serializable)
