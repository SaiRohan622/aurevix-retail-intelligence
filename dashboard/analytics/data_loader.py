"""
AUREVIX — Universal High-Performance & Secure Data Loader
Parses CSV, XLSX/XLS, Parquet, and JSON with SHA-256 fingerprinting, file validation,
column normalization, and Streamlit caching.
Exposes both load_file() and load_and_fingerprint() for full backward and cross-module compatibility.
"""
import io
import hashlib
from pathlib import Path
from typing import Tuple, Optional, Union, Any
import pandas as pd
import streamlit as st

from dashboard.analytics.security_utils import (
    sanitize_upload_filename,
    validate_file_security,
    sanitize_column_names,
    ALLOWED_EXTENSIONS,
    DANGEROUS_EXTENSIONS
)
from src.common.logger import get_logger

logger = get_logger("aurevix.data_loader")


@st.cache_data(show_spinner=False, max_entries=16)
def _cached_parse_bytes(file_bytes: bytes, filename: str, file_hash: str) -> pd.DataFrame:
    """Deterministic, pure-function in-memory parser cached by file_hash."""
    safe_name = sanitize_upload_filename(filename)
    name_lower = safe_name.lower()
    buf = io.BytesIO(file_bytes)

    if name_lower.endswith(".csv") or not (name_lower.endswith((".xlsx", ".xls", ".parquet", ".json"))):
        df = UniversalDataLoader._load_csv(buf, safe_name)
    elif name_lower.endswith((".xlsx", ".xls")):
        buf.seek(0)
        try:
            df = pd.read_excel(buf)
        except Exception as exc:
            logger.warning(f"Excel read error: {exc}")
            raise ValueError(f"Unable to parse Excel file '{safe_name}'. The workbook may be corrupted or encrypted.")
    elif name_lower.endswith(".parquet"):
        buf.seek(0)
        try:
            df = pd.read_parquet(buf)
        except Exception as exc:
            logger.warning(f"Parquet read error: {exc}")
            raise ValueError(f"Unable to parse Parquet file '{safe_name}'. The file structure is invalid or unsupported.")
    elif name_lower.endswith(".json"):
        df = UniversalDataLoader._load_json(buf, safe_name)
    else:
        raise ValueError(
            f"Unsupported format: '{safe_name}'. "
            "Supported formats: .csv, .xlsx, .xls, .parquet, .json"
        )

    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        raise ValueError(f"'{safe_name}' was loaded but contains no rows of data.")

    if len(df.columns) == 0:
        raise ValueError(f"'{safe_name}' contains no valid data columns.")

    # Clean, strip, and deduplicate column names safely
    df.columns = sanitize_column_names(df.columns)
    return df


class UniversalDataLoader:
    """Loads CSV, XLSX/XLS, Parquet, and JSON with SHA-256 fingerprinting and cache acceleration."""

    @classmethod
    def load_file(
        cls,
        file_obj: Any,
        filename: Optional[str] = None
    ) -> Tuple[pd.DataFrame, str]:
        """
        Primary public ingestion API.
        Accepts Streamlit UploadedFile, file-like BytesIO buffer, or filesystem path.
        Returns (pandas DataFrame, SHA-256 fingerprint string).
        """
        if filename is None:
            if hasattr(file_obj, "name"):
                filename = str(file_obj.name)
            elif isinstance(file_obj, (str, Path)):
                filename = Path(file_obj).name
            else:
                filename = "dataset.csv"

        return cls.load_and_fingerprint(file_obj, filename)

    @classmethod
    def load(
        cls,
        file_obj: Any,
        filename: Optional[str] = None
    ) -> Tuple[pd.DataFrame, str]:
        """Alias for load_file."""
        return cls.load_file(file_obj, filename)

    @classmethod
    def load_dataset(
        cls,
        file_obj: Any,
        filename: Optional[str] = None
    ) -> Tuple[pd.DataFrame, str]:
        """Alias for load_file."""
        return cls.load_file(file_obj, filename)

    @classmethod
    def load_and_fingerprint(
        cls,
        file_obj: Any,
        filename: Optional[str] = None
    ) -> Tuple[pd.DataFrame, str]:
        """
        Loads file content, validates security boundaries, generates SHA-256 fingerprint,
        and parses into a sanitized DataFrame.
        """
        if filename is None:
            if hasattr(file_obj, "name"):
                filename = str(file_obj.name)
            elif isinstance(file_obj, (str, Path)):
                filename = Path(file_obj).name
            else:
                filename = "dataset.csv"

        safe_filename = sanitize_upload_filename(filename)

        if hasattr(file_obj, "read"):
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            file_bytes = file_obj.read()
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
        else:
            with open(file_obj, "rb") as fh:
                file_bytes = fh.read()

        # Enforce Security Validation (Size limit, Allowlist, Magic Bytes, Empty check)
        validate_file_security(file_bytes, safe_filename)

        file_hash = hashlib.sha256(file_bytes).hexdigest()[:16]

        # Load from in-memory cache or parse once
        df = _cached_parse_bytes(file_bytes, safe_filename, file_hash)
        return df, file_hash

    @classmethod
    def _load_csv(cls, buf: io.BytesIO, filename: str) -> pd.DataFrame:
        last_parsed = None
        for encoding in ("utf-8-sig", "utf-8", "latin-1", "cp1252"):
            for sep in (",", ";", "\t", "|"):
                try:
                    buf.seek(0)
                    df = pd.read_csv(
                        buf,
                        sep=sep,
                        encoding=encoding,
                        on_bad_lines="skip",
                        low_memory=False
                    )
                    if len(df.columns) >= 1:
                        if len(df) > 0:
                            return df
                        last_parsed = df
                except Exception:
                    continue
        if last_parsed is not None:
            return last_parsed

        try:
            buf.seek(0)
            df = pd.read_csv(buf, encoding="utf-8", errors="replace")
            return df
        except Exception as exc:
            pass
        raise ValueError(f"Unable to parse CSV file '{filename}'. Please check delimiters and encoding.")

    @classmethod
    def _load_json(cls, buf: io.BytesIO, filename: str) -> pd.DataFrame:
        for orient in ("records", "columns", "index", "values", None):
            try:
                buf.seek(0)
                kwargs = {"orient": orient} if orient else {}
                df = pd.read_json(buf, **kwargs)
                if isinstance(df, pd.DataFrame) and not df.empty and len(df.columns) > 0:
                    return df
            except Exception:
                continue
        raise ValueError(f"Cannot parse '{filename}' as JSON. Ensure it is a valid JSON array or object.")
