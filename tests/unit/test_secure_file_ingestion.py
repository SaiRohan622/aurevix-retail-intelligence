import io
import json
import pytest
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path

from dashboard.analytics.data_loader import UniversalDataLoader
from dashboard.analytics.security_utils import (
    sanitize_upload_filename,
    validate_file_security,
    sanitize_column_names,
    sanitize_for_spreadsheet_export,
    is_safe_path,
    MAX_UPLOAD_SIZE_BYTES
)
from dashboard.analytics.persistent_storage import PersistentStorageManager


def test_allowed_csv_upload():
    """Verify standard valid CSV uploads are parsed successfully."""
    csv_bytes = b"customer,revenue,category\nAlice,120.50,Electronics\nBob,85.00,Home"
    buf = io.BytesIO(csv_bytes)
    df, fhash = UniversalDataLoader.load_file(buf, "sales.csv")
    assert len(df) == 2
    assert "revenue" in df.columns
    assert len(fhash) == 16


def test_allowed_xlsx_upload():
    """Verify standard valid Excel uploads are parsed successfully."""
    df_src = pd.DataFrame({"product": ["Widget A", "Widget B"], "price": [10.0, 25.0]})
    excel_buf = io.BytesIO()
    with pd.ExcelWriter(excel_buf, engine="openpyxl") as writer:
        df_src.to_excel(writer, index=False)
    excel_bytes = excel_buf.getvalue()

    df, fhash = UniversalDataLoader.load_file(io.BytesIO(excel_bytes), "products.xlsx")
    assert len(df) == 2
    assert "product" in df.columns
    assert len(fhash) == 16


def test_allowed_json_upload():
    """Verify standard valid JSON uploads are parsed successfully."""
    json_bytes = json.dumps([
        {"id": 1, "status": "active", "score": 95},
        {"id": 2, "status": "pending", "score": 80}
    ]).encode("utf-8")

    df, fhash = UniversalDataLoader.load_file(io.BytesIO(json_bytes), "users.json")
    assert len(df) == 2
    assert "status" in df.columns
    assert len(fhash) == 16


def test_allowed_parquet_upload():
    """Verify standard valid Parquet uploads are parsed successfully."""
    df_src = pd.DataFrame({"region": ["North", "South"], "volume": [500, 750]})
    table = pa.Table.from_pandas(df_src)
    parquet_buf = io.BytesIO()
    pq.write_table(table, parquet_buf)
    parquet_bytes = parquet_buf.getvalue()

    df, fhash = UniversalDataLoader.load_file(io.BytesIO(parquet_bytes), "regions.parquet")
    assert len(df) == 2
    assert "region" in df.columns
    assert len(fhash) == 16


def test_unsupported_executable_extension_rejected():
    """Verify dangerous executable/script extensions are blocked before parsing."""
    dangerous_files = ["malware.exe", "script.bat", "exploit.ps1", "payload.py", "lib.dll", "hook.js"]
    for d_name in dangerous_files:
        with pytest.raises(ValueError, match="executable or unsafe file type"):
            validate_file_security(b"dummy data", d_name)


def test_oversized_file_rejected(monkeypatch):
    """Verify files exceeding MAX_UPLOAD_SIZE_BYTES are rejected."""
    # Create fake oversized buffer exceeding size limit
    fake_huge_bytes = b"x" * (MAX_UPLOAD_SIZE_BYTES + 1024)
    with pytest.raises(ValueError, match="File exceeds the maximum allowed upload size"):
        validate_file_security(fake_huge_bytes, "huge_data.csv")


def test_zero_byte_file_rejected():
    """Verify zero-byte / empty files are rejected."""
    with pytest.raises(ValueError, match="The file.*is empty|uploaded file is empty"):
        UniversalDataLoader.load_file(io.BytesIO(b""), "empty.csv")


def test_malformed_csv_handled_gracefully():
    """Verify corrupt binary CSV content triggers a controlled ValueError without crash."""
    corrupt_bytes = b"\x00\x01\x02\x03\xff\xfe\xaa\xbb"
    with pytest.raises(ValueError, match="Unable to parse CSV file|contains no rows of data"):
        UniversalDataLoader.load_file(io.BytesIO(corrupt_bytes), "corrupt.csv")


def test_malformed_json_handled_gracefully():
    """Verify malformed JSON triggers a controlled error without stack trace."""
    malformed_json = b"{'key': unquoted_value, missing_closing"
    with pytest.raises(ValueError):
        UniversalDataLoader.load_file(io.BytesIO(malformed_json), "bad.json")


def test_malformed_xlsx_handled_gracefully():
    """Verify invalid XLSX payload is rejected."""
    fake_xlsx_bytes = b"NOT_A_ZIP_CONTAINER"
    with pytest.raises(ValueError, match="invalid workbook structure"):
        validate_file_security(fake_xlsx_bytes, "corrupt.xlsx")


def test_malformed_parquet_handled_gracefully():
    """Verify invalid Parquet payload is rejected."""
    fake_parquet_bytes = b"NOT_PARQUET_HEADER_DATA"
    with pytest.raises(ValueError, match="invalid Parquet file signature"):
        validate_file_security(fake_parquet_bytes, "corrupt.parquet")


def test_path_traversal_filename_sanitized():
    """Verify directory traversal patterns (../, ..\\) are stripped."""
    dirty_name = "../../../../../etc/passwd.csv"
    clean_name = sanitize_upload_filename(dirty_name)
    assert "../" not in clean_name
    assert ".." not in clean_name
    assert clean_name.endswith(".csv")


def test_absolute_windows_path_sanitized():
    """Verify absolute Windows paths are stripped to safe basename."""
    dirty_name = r"C:\Windows\System32\drivers\etc\hosts.csv"
    clean_name = sanitize_upload_filename(dirty_name)
    assert ":" not in clean_name
    assert "\\" not in clean_name
    assert clean_name.endswith(".csv")


def test_windows_drive_path_sanitized():
    """Verify drive letters and UNC paths are removed."""
    dirty_name = r"D:\Confidential\Financials.xlsx"
    clean_name = sanitize_upload_filename(dirty_name)
    assert "D:" not in clean_name
    assert clean_name == "Financials.xlsx"


def test_null_byte_filename_sanitized():
    """Verify null bytes are stripped from filenames."""
    dirty_name = "report\x00.csv.exe"
    clean_name = sanitize_upload_filename(dirty_name)
    assert "\x00" not in clean_name


def test_windows_reserved_device_names_sanitized():
    """Verify Windows reserved names (CON, PRN, AUX, NUL, COM1) are prefixed safely."""
    for res in ("CON.csv", "PRN.xlsx", "AUX.json", "NUL.parquet", "COM1.csv"):
        clean_name = sanitize_upload_filename(res)
        assert clean_name.startswith("safe_")


def test_duplicate_dataset_fingerprint_detection():
    """Verify exact duplicate file content produces identical SHA-256 fingerprint."""
    data = b"order_id,amount\n101,50.0\n102,75.0"
    _, hash1 = UniversalDataLoader.load_file(io.BytesIO(data), "sales_v1.csv")
    _, hash2 = UniversalDataLoader.load_file(io.BytesIO(data), "sales_v2.csv")
    assert hash1 == hash2


def test_deterministic_fingerprint_calculation():
    """Verify different file content produces different fingerprint."""
    data1 = b"order_id,amount\n101,50.0"
    data2 = b"order_id,amount\n101,999.0"
    _, hash1 = UniversalDataLoader.load_file(io.BytesIO(data1), "a.csv")
    _, hash2 = UniversalDataLoader.load_file(io.BytesIO(data2), "b.csv")
    assert hash1 != hash2


def test_workspace_path_containment():
    """Verify storage manager prevents escaping the workspace directory."""
    base_dir = Path("data/user_workspaces").resolve()
    valid_sub = base_dir / "datasets" / "hash123"
    escape_path = Path("C:/Windows/System32").resolve()

    assert is_safe_path(valid_sub, base_dir) is True
    assert is_safe_path(escape_path, base_dir) is False


def test_macro_enabled_excel_rejected():
    """Verify macro-enabled Excel (.xlsm) is rejected."""
    with pytest.raises(ValueError, match="executable or unsafe file type"):
        validate_file_security(b"dummy macro data", "macro_payload.xlsm")


def test_formula_injection_export_protection():
    """Verify spreadsheet formula injection triggers (=, +, -, @) are neutralized on export."""
    df = pd.DataFrame({
        "username": ["=1+1", "+CMD|' /C calc'!A0", "@SUM(A1:A10)", "-2+3", "normal_user"],
        "revenue": [100.5, 200.0, -50.0, 75.0, 10.0]
    })

    safe_df = sanitize_for_spreadsheet_export(df)

    # Formulas neutralized with leading quote
    assert safe_df["username"].iloc[0] == "'=1+1"
    assert safe_df["username"].iloc[1] == "'+CMD|' /C calc'!A0"
    assert safe_df["username"].iloc[2] == "'@SUM(A1:A10)"
    assert safe_df["username"].iloc[3] == "'-2+3"
    assert safe_df["username"].iloc[4] == "normal_user"

    # Genuine numeric values in revenue column preserved untouched
    assert safe_df["revenue"].iloc[2] == -50.0
    assert safe_df["revenue"].iloc[0] == 100.5


def test_invalid_and_control_character_column_names_sanitized():
    """Verify column names with control characters and nulls are sanitized."""
    raw_cols = ["\x00col_a\x1f", "   ", None, "very_long_" + "x" * 200]
    cleaned = sanitize_column_names(raw_cols)

    assert "\x00" not in cleaned[0]
    assert cleaned[1].startswith("unnamed_column")
    assert cleaned[2].startswith("unnamed_column")
    assert len(cleaned[3]) <= 128


def test_duplicate_column_names_deduplicated():
    """Verify duplicate column names are deterministically deduplicated."""
    raw_cols = ["sales", "sales", "sales", "profit"]
    cleaned = sanitize_column_names(raw_cols)

    assert cleaned == ["sales", "sales_1", "sales_2", "profit"]


def test_empty_dataframe_rejected():
    """Verify DataFrames with 0 rows or 0 columns are rejected."""
    empty_csv = b"col1,col2\n"
    with pytest.raises(ValueError, match="contains no rows of data"):
        UniversalDataLoader.load_file(io.BytesIO(empty_csv), "headers_only.csv")


def test_graceful_parser_failure_no_path_disclosure():
    """Verify error messages do not disclose server filesystem paths."""
    bad_bytes = b"garbage_data_not_json"
    with pytest.raises(ValueError) as exc:
        UniversalDataLoader.load_file(io.BytesIO(bad_bytes), "data.json")

    err_msg = str(exc.value)
    assert "D:\\" not in err_msg
    assert "C:\\" not in err_msg
    assert "/home/" not in err_msg


def test_no_credential_disclosure_on_ingestion_error():
    """Verify error messages on ingestion never disclose database passwords or tokens."""
    bad_bytes = b"bad_data"
    try:
        UniversalDataLoader.load_file(io.BytesIO(bad_bytes), "test.json")
    except ValueError as exc:
        err_msg = str(exc)
        assert "password" not in err_msg.lower()
        assert "secret" not in err_msg.lower()
        assert "postgresql://" not in err_msg.lower()
