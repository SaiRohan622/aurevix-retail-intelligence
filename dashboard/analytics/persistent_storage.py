"""
AUREVIX — Persistent Workspace & Dataset Storage Layer
Guarantees uploaded datasets, active filters, strategic goals, and cleaning recipes
persist across browser refreshes (F5 / Ctrl+R) and Streamlit session reconnections
without losing analytical state or falling back to demo data.
"""

import json
import re
import shutil
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
import pandas as pd
from dashboard.analytics.workspace_manager import _make_json_serializable
from src.common.logger import get_logger

logger = get_logger("aurevix.persistent_storage")


def sanitize_id(id_str: str) -> str:
    """
    Sanitizes an identifier to strictly prevent directory traversal and unsafe characters.
    Rejects or strips '../', '..\\', absolute path components, and non-alphanumeric chars.
    """
    if not id_str:
        return "default_dataset"
    # Remove directory separators and path traversal dots
    cleaned = str(id_str).replace("/", "").replace("\\", "").replace("..", "").strip()
    # Keep only alphanumeric, hyphens, and underscores
    cleaned = re.sub(r"[^a-zA-Z0-9_\-]", "", cleaned).strip("._-")
    return cleaned if cleaned else "default_dataset"


def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a user-provided filename to extract only the safe base name.
    """
    if not filename:
        return "dataset.csv"
    base = Path(filename).name
    # Strip any potential path traversal artifacts
    base = base.replace("/", "").replace("\\", "").replace("..", "")
    cleaned = re.sub(r"[^a-zA-Z0-9._\-]", "_", base).strip("._-")
    return cleaned if cleaned else "dataset.csv"


class PersistentStorageManager:
    """
    Manages disk-based persistence for uploaded datasets, active session checkpoints,
    cleaning recipes, and comparison configurations under data/user_workspaces/.
    """

    STORAGE_DIR = Path("data/user_workspaces")
    DATASETS_DIR = STORAGE_DIR / "datasets"
    ACTIVE_STATE_FILE = STORAGE_DIR / "active_state.json"

    @classmethod
    def _ensure_storage(cls) -> None:
        cls.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        cls.DATASETS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_dataset_dir(cls, dataset_id: str) -> Path:
        from dashboard.analytics.security_utils import is_safe_path
        clean_id = sanitize_id(dataset_id)
        ds_dir = cls.DATASETS_DIR / clean_id
        if not is_safe_path(ds_dir, cls.STORAGE_DIR):
            raise ValueError("Path traversal violation: dataset directory escapes workspace storage.")
        return ds_dir

    @classmethod
    def dataset_exists(cls, dataset_id: str) -> bool:
        ds_dir = cls.get_dataset_dir(dataset_id)
        return (ds_dir / "original.parquet").exists() or (ds_dir / "cleaned.parquet").exists()

    @classmethod
    def save_dataset(
        cls,
        dataset_id: str,
        filename: str,
        df: pd.DataFrame,
        original_df: Optional[pd.DataFrame] = None,
        analysis_results: Optional[Dict[str, Any]] = None,
        cleaning_recipe: Optional[List[Dict[str, Any]]] = None,
        data_source: str = "user_upload"
    ) -> Path:
        """
        Persists an uploaded dataset and its initial analytics metadata to disk using Parquet.
        """
        cls._ensure_storage()
        clean_id = sanitize_id(dataset_id)
        clean_name = sanitize_filename(filename)
        ds_dir = cls.DATASETS_DIR / clean_id
        ds_dir.mkdir(parents=True, exist_ok=True)

        # 1. Save original immutable DataFrame
        orig_to_save = original_df if (original_df is not None and not original_df.empty) else df
        orig_path = ds_dir / "original.parquet"
        try:
            orig_to_save.to_parquet(orig_path, index=False)
        except Exception as exc:
            logger.warning(f"Parquet save error for original: {exc}")

        # 2. Save working/cleaned DataFrame
        cleaned_path = ds_dir / "cleaned.parquet"
        try:
            df.to_parquet(cleaned_path, index=False)
        except Exception as exc:
            logger.warning(f"Parquet save error for cleaned: {exc}")

        # 3. Save metadata & analysis results
        from dashboard.analytics.auth_manager import AuthManager
        owner_id = AuthManager.get_current_user_id()
        now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        meta_payload = {
            "dataset_id": clean_id,
            "owner_user_id": owner_id,
            "filename": clean_name,
            "original_filename": filename,
            "data_source": data_source,
            "rows": int(len(df)),
            "columns": [str(c) for c in df.columns],
            "upload_timestamp": now_str,
            "analysis_results": analysis_results or {}
        }
        meta_clean = _make_json_serializable(meta_payload)
        with open(ds_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(meta_clean, f, indent=2, ensure_ascii=False)

        # 4. Save cleaning recipe
        recipe_clean = _make_json_serializable(cleaning_recipe or [])
        with open(ds_dir / "cleaning_recipe.json", "w", encoding="utf-8") as f:
            json.dump(recipe_clean, f, indent=2, ensure_ascii=False)

        logger.info(f"Dataset '{clean_name}' (ID: {clean_id}) persisted to {ds_dir}")
        try:
            from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
            SecurityAuditLogger.log_event(
                event_type=SecurityEventType.DATASET_UPLOAD,
                severity=SecuritySeverity.INFO,
                outcome="SUCCESS",
                user_id=owner_id,
                dataset_id=clean_id,
                source="persistent_storage",
                reason=f"Dataset '{clean_name}' uploaded and persisted",
                metadata={"filename": clean_name, "rows": len(df), "columns": len(df.columns)}
            )
        except Exception:
            pass
        return ds_dir

    @classmethod
    def update_cleaning_state(
        cls,
        dataset_id: str,
        cleaned_df: pd.DataFrame,
        cleaning_recipe: List[Dict[str, Any]],
        analysis_results: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Updates the working cleaned DataFrame and cleaning recipe without touching original.parquet.
        """
        clean_id = sanitize_id(dataset_id)
        ds_dir = cls.DATASETS_DIR / clean_id
        if not ds_dir.exists():
            ds_dir.mkdir(parents=True, exist_ok=True)
        cleaned_path = ds_dir / "cleaned.parquet"
        try:
            cleaned_df.to_parquet(cleaned_path, index=False)
        except Exception as exc:
            logger.warning(f"Parquet save error in update_cleaning_state: {exc}")

        recipe_clean = _make_json_serializable(cleaning_recipe)
        with open(ds_dir / "cleaning_recipe.json", "w", encoding="utf-8") as f:
            json.dump(recipe_clean, f, indent=2, ensure_ascii=False)

        if analysis_results:
            meta_file = ds_dir / "metadata.json"
            if meta_file.exists():
                try:
                    with open(meta_file, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    meta["analysis_results"] = _make_json_serializable(analysis_results)
                    with open(meta_file, "w", encoding="utf-8") as f:
                        json.dump(meta, f, indent=2, ensure_ascii=False)
                except Exception:
                    pass

    @classmethod
    def load_dataset(cls, dataset_id: str) -> Optional[Dict[str, Any]]:
        """
        Loads a persisted dataset (both original and cleaned DataFrames, plus metadata and recipe).
        """
        clean_id = sanitize_id(dataset_id)
        ds_dir = cls.DATASETS_DIR / clean_id
        if not ds_dir.exists():
            return None

        # 1. Load original DataFrame
        orig_df = None
        if (ds_dir / "original.parquet").exists():
            try:
                orig_df = pd.read_parquet(ds_dir / "original.parquet")
            except Exception:
                pass

        # 2. Load cleaned DataFrame
        cleaned_df = None
        if (ds_dir / "cleaned.parquet").exists():
            try:
                cleaned_df = pd.read_parquet(ds_dir / "cleaned.parquet")
            except Exception:
                pass

        # Fallback cleaned to original if needed
        if cleaned_df is None and orig_df is not None:
            cleaned_df = orig_df.copy()
        elif orig_df is None and cleaned_df is not None:
            orig_df = cleaned_df.copy()

        if cleaned_df is None and orig_df is None:
            return None

        # 3. Load metadata
        metadata = {}
        if (ds_dir / "metadata.json").exists():
            try:
                with open(ds_dir / "metadata.json", "r", encoding="utf-8") as f:
                    metadata = json.load(f)
            except Exception:
                pass

        # Verify dataset ownership
        from dashboard.analytics.auth_manager import AuthManager
        owner = metadata.get("owner_user_id", AuthManager.DEFAULT_TEST_USER_ID)
        current_uid = AuthManager.get_current_user_id()
        is_admin = AuthManager.has_role("ADMIN")
        if not (is_admin or owner == current_uid or owner == AuthManager.DEFAULT_TEST_USER_ID or current_uid == AuthManager.DEFAULT_TEST_USER_ID):
            logger.warning(f"Unauthorized dataset access: user={current_uid} cannot load dataset owned by {owner}")
            try:
                from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
                SecurityAuditLogger.log_event(
                    event_type=SecurityEventType.DATASET_ACCESS_DENIED,
                    severity=SecuritySeverity.HIGH,
                    outcome="DENIED",
                    user_id=current_uid,
                    dataset_id=clean_id,
                    source="persistent_storage",
                    reason=f"Unauthorized access to dataset owned by {owner}"
                )
            except Exception:
                pass
            return None

        try:
            from dashboard.analytics.security_audit import SecurityAuditLogger, SecurityEventType, SecuritySeverity
            SecurityAuditLogger.log_event(
                event_type=SecurityEventType.DATASET_ACCESS,
                severity=SecuritySeverity.INFO,
                outcome="SUCCESS",
                user_id=current_uid,
                dataset_id=clean_id,
                source="persistent_storage",
                reason=f"Dataset '{clean_id}' loaded",
                metadata={"rows": len(cleaned_df), "columns": len(cleaned_df.columns)}
            )
        except Exception:
            pass

        # 4. Load cleaning recipe
        recipe = []
        if (ds_dir / "cleaning_recipe.json").exists():
            try:
                with open(ds_dir / "cleaning_recipe.json", "r", encoding="utf-8") as f:
                    recipe = json.load(f)
            except Exception:
                pass

        return {
            "dataset_id": clean_id,
            "filename": metadata.get("filename") or metadata.get("original_filename", "dataset.csv"),
            "original_raw_df": orig_df,
            "raw_df": cleaned_df,
            "analysis_results": metadata.get("analysis_results", {}),
            "cleaning_recipe": recipe,
            "data_source": metadata.get("data_source", "user_upload"),
            "upload_timestamp": metadata.get("upload_timestamp")
        }

    @classmethod
    def save_active_state(cls, state_dict: Dict[str, Any]) -> None:
        """
        Saves the pointer and configuration for the currently active workspace.
        """
        cls._ensure_storage()
        clean_state = _make_json_serializable(state_dict)
        tmp_file = cls.STORAGE_DIR / "active_state.json.tmp"
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(clean_state, f, indent=2, ensure_ascii=False)
        tmp_file.replace(cls.ACTIVE_STATE_FILE)

    @classmethod
    def load_active_state(cls) -> Optional[Dict[str, Any]]:
        """
        Reads active_state.json and reconstructs the active dataset and workspace state from disk.
        """
        if not cls.ACTIVE_STATE_FILE.exists():
            return None

        try:
            with open(cls.ACTIVE_STATE_FILE, "r", encoding="utf-8") as f:
                state_data = json.load(f)
        except Exception as exc:
            logger.warning(f"Unable to read active_state.json: {exc}")
            return None

        if not isinstance(state_data, dict):
            return None

        has_user_mode = bool(state_data.get("user_mode", False))
        comp = state_data.get("comparison", {})
        has_comparison = bool(
            comp and isinstance(comp, dict) and comp.get("dataset_a_fingerprint") and comp.get("dataset_b_fingerprint")
        )

        if not has_user_mode and not has_comparison:
            return None

        dataset_id = state_data.get("user_dataset_id")
        ds_loaded = cls.load_dataset(dataset_id) if dataset_id else None

        if has_user_mode and not ds_loaded:
            logger.warning(f"Active dataset {dataset_id} not found on disk.")
            if not has_comparison:
                return None

        # Merge persistent state
        result = {
            "user_mode": bool(has_user_mode and ds_loaded is not None),
            "user_dataset_id": dataset_id if ds_loaded else None,
            "user_dataset_name": (state_data.get("user_dataset_name") or ds_loaded["filename"]) if ds_loaded else None,
            "data_source": state_data.get("data_source") or (ds_loaded.get("data_source", "user_upload") if ds_loaded else "none"),
            "original_raw_df": ds_loaded["original_raw_df"] if ds_loaded else None,
            "raw_df": ds_loaded["raw_df"] if ds_loaded else None,
            "filtered_df": None,
            "analysis_results": state_data.get("analysis_results") or (ds_loaded.get("analysis_results", {}) if ds_loaded else {}),
            "cleaning_recipe": state_data.get("cleaning_recipe") or (ds_loaded.get("cleaning_recipe", []) if ds_loaded else []),
            "active_filters": state_data.get("active_filters", {}),
            "user_targets": state_data.get("user_targets", {}),
            "dashboard_layout": state_data.get("dashboard_layout", ["kpis", "target", "trend", "donut", "bar", "story", "anomalies", "quality"]),
            "upload_timestamp": state_data.get("upload_timestamp") or (ds_loaded.get("upload_timestamp") if ds_loaded else None),
            "comparison": comp
        }

        # If comparison state contains dataset fingerprints, load comparison DataFrames
        if comp and isinstance(comp, dict):
            fp_a = comp.get("dataset_a_fingerprint")
            fp_b = comp.get("dataset_b_fingerprint")
            if fp_a:
                ds_a = cls.load_dataset(fp_a)
                if ds_a and ds_a.get("raw_df") is not None:
                    comp["dataset_a"] = ds_a["raw_df"]
            if fp_b:
                ds_b = cls.load_dataset(fp_b)
                if ds_b and ds_b.get("raw_df") is not None:
                    comp["dataset_b"] = ds_b["raw_df"]

        return result

    @classmethod
    def clear_active_state(cls) -> None:
        """
        Clears the active workspace pointer so subsequent refreshes do not restore a cleared session.
        """
        if cls.ACTIVE_STATE_FILE.exists():
            try:
                cls.ACTIVE_STATE_FILE.unlink()
            except Exception as exc:
                logger.warning(f"Failed to unlink active_state.json: {exc}")

    @classmethod
    def delete_dataset(cls, dataset_id: str) -> bool:
        """
        Deletes a specific persisted dataset directory from disk.
        """
        clean_id = sanitize_id(dataset_id)
        ds_dir = cls.DATASETS_DIR / clean_id
        if ds_dir.exists():
            try:
                shutil.rmtree(ds_dir)
                logger.info(f"Dataset {clean_id} deleted from disk.")
                return True
            except Exception as exc:
                logger.error(f"Failed to delete dataset {clean_id}: {exc}")
                return False
        return False

    @classmethod
    def clear_all_user_workspaces(cls) -> None:
        """
        Purges all user uploaded datasets and active state from disk.
        """
        cls.clear_active_state()
        if cls.DATASETS_DIR.exists():
            for child in cls.DATASETS_DIR.iterdir():
                if child.is_dir():
                    try:
                        shutil.rmtree(child)
                    except Exception:
                        pass
