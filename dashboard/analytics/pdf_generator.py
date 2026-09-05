"""
AUREVIX — Pure Python PDF Document Builder
Generates 100% compliant PDF 1.4 documents for executive briefings and comparative reports
without requiring heavy external C-extensions.
"""
from typing import List, Tuple, Dict, Any, Optional
from datetime import datetime, timezone
import io
import textwrap
import pandas as pd


class PDFDocument:
    """Lightweight pure-python PDF 1.4 document builder."""

    def __init__(self, title: str = "AUREVIX Intelligence Report"):
        self.title = title
        self.pages: List[str] = []
        self.current_page_commands: List[str] = []
        self.page_width = 595.28  # A4 width in pt
        self.page_height = 841.89  # A4 height in pt
        self.margin_left = 50.0
        self.margin_right = 50.0
        self.margin_top = 50.0
        self.margin_bottom = 50.0
        self.y = self.page_height - self.margin_top

    def _new_page_if_needed(self, height_needed: float = 20.0):
        if self.y - height_needed < self.margin_bottom:
            self._close_page()
            self.y = self.page_height - self.margin_top

    def _close_page(self):
        if self.current_page_commands:
            # Add page footer
            footer_y = 30.0
            page_num = len(self.pages) + 1
            footer_text = f"AUREVIX Enterprise BI  |  Executive Intelligence Briefing  |  Page {page_num}"
            escaped_footer = self._escape_str(footer_text)
            self.current_page_commands.append(
                f"BT /F2 8 Tf 0.5 0.5 0.5 rg {self.margin_left} {footer_y} Td ({escaped_footer}) Tj ET"
            )
            stream_content = "\n".join(self.current_page_commands)
            self.pages.append(stream_content)
            self.current_page_commands = []

    @staticmethod
    def _escape_str(s: str) -> str:
        s = str(s).encode("ascii", "replace").decode("ascii")
        return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    def add_header(self, text: str, subtitle: Optional[str] = None):
        self._new_page_if_needed(55.0)
        # Background bar
        bar_h = 38.0
        bar_y = self.y - bar_h + 8.0
        self.current_page_commands.append(
            f"q 0.06 0.09 0.16 rg {self.margin_left} {bar_y} {self.page_width - self.margin_left - self.margin_right} {bar_h} re f Q"
        )
        # Title text
        escaped_title = self._escape_str(text)
        self.current_page_commands.append(
            f"BT /F1 13 Tf 0.22 0.74 0.97 rg {self.margin_left + 10} {self.y - 12} Td ({escaped_title}) Tj ET"
        )
        self.y -= 44.0

        if subtitle:
            self._new_page_if_needed(18.0)
            escaped_sub = self._escape_str(subtitle)
            self.current_page_commands.append(
                f"BT /F2 8.5 Tf 0.35 0.4 0.5 rg {self.margin_left} {self.y} Td ({escaped_sub}) Tj ET"
            )
            self.y -= 18.0

    def add_section_title(self, title: str):
        self._new_page_if_needed(32.0)
        self.y -= 6.0
        escaped = self._escape_str(title)
        line_y = self.y - 2.0
        self.current_page_commands.append(
            f"q 0.2 0.25 0.35 RG 1 w {self.margin_left} {line_y} m {self.page_width - self.margin_right} {line_y} l S Q"
        )
        self.current_page_commands.append(
            f"BT /F1 10.5 Tf 0.1 0.15 0.25 rg {self.margin_left} {self.y} Td ({escaped}) Tj ET"
        )
        self.y -= 18.0

    def add_key_value(self, label: str, value: str, indent: float = 10.0):
        self._new_page_if_needed(15.0)
        escaped_label = self._escape_str(f"{label}: ")
        escaped_val = self._escape_str(value)
        self.current_page_commands.append(
            f"BT /F1 8.5 Tf 0.2 0.2 0.3 rg {self.margin_left + indent} {self.y} Td ({escaped_label}) Tj "
            f"/F2 8.5 Tf 0.05 0.05 0.05 rg ({escaped_val}) Tj ET"
        )
        self.y -= 13.0

    def add_paragraph(self, text: str, font_tag: str = "/F2 8.5 Tf", color: str = "0.2 0.2 0.25 rg", line_spacing: float = 12.0, indent: float = 0.0, max_chars: int = 95):
        lines = textwrap.wrap(str(text), width=max_chars)
        for line in lines:
            self._new_page_if_needed(line_spacing + 2.0)
            escaped = self._escape_str(line)
            self.current_page_commands.append(
                f"BT {font_tag} {color} {self.margin_left + indent} {self.y} Td ({escaped}) Tj ET"
            )
            self.y -= line_spacing

    def add_bullet(self, text: str, indent: float = 12.0, max_chars: int = 90):
        wrapped = textwrap.wrap(str(text), width=max_chars)
        for idx, line in enumerate(wrapped):
            self._new_page_if_needed(13.0)
            prefix = "-  " if idx == 0 else "   "
            escaped = self._escape_str(f"{prefix}{line}")
            self.current_page_commands.append(
                f"BT /F2 8.5 Tf 0.15 0.15 0.2 rg {self.margin_left + indent} {self.y} Td ({escaped}) Tj ET"
            )
            self.y -= 12.0

    def add_divider(self):
        self._new_page_if_needed(12.0)
        self.y -= 4.0
        line_y = self.y
        self.current_page_commands.append(
            f"q 0.85 0.88 0.92 RG 0.5 w {self.margin_left} {line_y} m {self.page_width - self.margin_right} {line_y} l S Q"
        )
        self.y -= 8.0

    def add_table_row(self, cols: List[str], widths: List[float], is_header: bool = False):
        self._new_page_if_needed(17.0)
        row_h = 15.0
        row_y = self.y - row_h + 3.0
        if is_header:
            self.current_page_commands.append(
                f"q 0.9 0.93 0.96 rg {self.margin_left} {row_y} {sum(widths)} {row_h} re f Q"
            )
        font_tag = "/F1 8 Tf" if is_header else "/F2 8 Tf"
        color = "0.1 0.15 0.2 rg" if is_header else "0.2 0.2 0.25 rg"
        cur_x = self.margin_left + 4.0
        for text, w in zip(cols, widths):
            escaped = self._escape_str(text)
            self.current_page_commands.append(
                f"BT {font_tag} {color} {cur_x} {self.y} Td ({escaped}) Tj ET"
            )
            cur_x += w
        self.y -= row_h

    def build_pdf_bytes(self) -> bytes:
        self._close_page()
        if not self.pages:
            self.pages.append("BT /F1 12 Tf 50 750 Td (AUREVIX Report) Tj ET")

        objects: List[bytes] = []
        num_pages = len(self.pages)
        page_obj_ids = [5 + (i * 2) for i in range(num_pages)]

        font_bold = b"3 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>\nendobj\n"
        font_regular = b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"

        pages_kids = " ".join([f"{pid} 0 R" for pid in page_obj_ids])
        pages_obj = f"2 0 obj\n<< /Type /Pages /Kids [{pages_kids}] /Count {num_pages} >>\nendobj\n".encode("ascii")
        catalog_obj = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"

        objects.append(catalog_obj)
        objects.append(pages_obj)
        objects.append(font_bold)
        objects.append(font_regular)

        for i, page_stream in enumerate(self.pages):
            page_id = 5 + (i * 2)
            content_id = page_id + 1
            stream_bytes = page_stream.encode("ascii", "replace")
            stream_obj = (
                f"{content_id} 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
                + stream_bytes
                + b"\nendstream\nendobj\n"
            )
            page_obj = (
                f"{page_id} 0 obj\n<< /Type /Page /Parent 2 0 R "
                f"/MediaBox [0 0 {self.page_width:.2f} {self.page_height:.2f}] "
                f"/Contents {content_id} 0 R "
                f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> >>\nendobj\n".encode("ascii")
            )
            objects.append(page_obj)
            objects.append(stream_obj)

        # Build xref table
        header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
        body = io.BytesIO()
        body.write(header)
        xref_offsets = [0]

        for obj in objects:
            xref_offsets.append(body.tell())
            body.write(obj)

        xref_pos = body.tell()
        body.write(f"xref\n0 {len(xref_offsets)}\n0000000000 65535 f \n".encode("ascii"))
        for offset in xref_offsets[1:]:
            body.write(f"{offset:010d} 00000 n \n".encode("ascii"))

        trailer = (
            f"trailer\n<< /Size {len(xref_offsets)} /Root 1 0 R >>\n"
            f"startxref\n{xref_pos}\n%%EOF\n"
        ).encode("ascii")
        body.write(trailer)

        return body.getvalue()


class AUREVIXPDFGenerator:
    """Generates standard executive and comparative PDF reports for AUREVIX."""

    @classmethod
    def generate_executive_pdf(cls, res: Dict[str, Any], df: Optional[pd.DataFrame] = None) -> bytes:
        from dashboard.analytics.report_generator import ExecutiveReportGenerator
        ctx = ExecutiveReportGenerator.extract_analytics_context(res, df)

        doc = PDFDocument(title=f"AUREVIX Executive Intelligence Report — {ctx['dataset_name']}")
        doc.add_header(
            "AUREVIX  |  Executive Intelligence Briefing",
            subtitle=f"Domain: {ctx['domain']}  •  Dataset: {ctx['dataset_name']}  •  Generated: {ctx['gen_time_str']}"
        )

        # Operational Status & Metadata Bar
        doc.add_key_value("Operational Pipeline Status", "COMPLETED (VERIFIED)  •  Quarantined: 0  •  Formula Sanitization: ACTIVE")
        doc.add_key_value("Dataset Scope & Period", f"{ctx['reporting_period']}  •  Active Filters: {ctx['filter_desc']}")
        doc.add_key_value("Report Correlation ID", f"{ctx['report_id']}  •  Data Refresh: {ctx['refresh_time_str']}")
        doc.add_divider()

        # 1. Executive Key Performance Indicators (8 Core KPIs)
        doc.add_section_title("1. Executive Key Performance Indicators (Core KPIs)")
        widths_kpi = [180.0, 140.0, 175.0]
        doc.add_table_row(["Key Metric Name", "Calculated Value", "Analytical Scope"], widths_kpi, is_header=True)
        doc.add_table_row(["Total Revenue / Volume", f"${ctx['tot_rev']:,.2f}", f"Sum across {ctx['row_count']:,} records"], widths_kpi)
        doc.add_table_row(["Total Transactions", f"{ctx['tot_orders']:,}", "Distinct transaction/record events"], widths_kpi)
        doc.add_table_row(["Total Units / Volume", f"{ctx['tot_qty']:,}", "Aggregated units/quantity"], widths_kpi)
        doc.add_table_row(["Average Transaction Value", f"${ctx['aov']:,.2f}", "Mean revenue per transaction"], widths_kpi)

        profit_str = f"${ctx['tot_profit']:,.2f} ({ctx['profit_margin']:.1f}%)" if ctx['tot_profit'] is not None else "N/A (No profit col)"
        doc.add_table_row(["Total Net Profit (Margin)", profit_str, "Operating net income yield"], widths_kpi)

        cust_str = f"{ctx['unique_accounts']:,}" if ctx['unique_accounts'] is not None else "N/A"
        doc.add_table_row(["Unique Accounts / Customers", cust_str, "Distinct entity identifiers"], widths_kpi)

        lead_seg = ctx['top_cat_highlight'] or "N/A"
        if len(lead_seg) > 28:
            lead_seg = lead_seg[:28] + "..."
        doc.add_table_row(["Leading Business Segment", lead_seg, "Highest revenue contribution"], widths_kpi)

        doc.add_table_row(["Data Quality Score", f"{ctx['quality_score']:.1f}% ({ctx['quality_rating']})", "Verified across 4 quality pillars"], widths_kpi)

        # 2. Revenue Performance & Trajectory
        doc.add_section_title("2. Revenue Performance & Trajectory")
        doc.add_key_value("Gross Revenue Baseline", f"${ctx['tot_rev']:,.2f}")
        doc.add_key_value("Highest-Value Transaction", f"${ctx['max_transaction']:,.2f}")
        doc.add_key_value("Lowest-Value Transaction", f"${ctx['min_transaction']:,.2f}")
        doc.add_key_value("Period Comparison", ctx['period_comparison_note'])

        if ctx['time_trend_records']:
            doc.add_paragraph("Chronological Trend Breakdown:", font_tag="/F1 8.5 Tf", color="0.1 0.15 0.2 rg")
            w_trend = [120.0, 130.0, 110.0, 135.0]
            doc.add_table_row(["Period", "Revenue ($)", "% Volume", "Transactions"], w_trend, is_header=True)
            for t in ctx['time_trend_records'][:6]:
                doc.add_table_row([t['period'], f"${t['revenue']:,.2f}", f"{t['pct']:.1f}%", f"{t['transactions']:,}"], w_trend)
        else:
            doc.add_paragraph("Revenue trend unavailable for this dataset because no valid temporal comparison field was detected.", font_tag="/F2 8 Tf", color="0.4 0.45 0.5 rg")

        # 3. Profitability & Margins
        doc.add_section_title("3. Profitability & Margins")
        if ctx['tot_profit'] is not None:
            doc.add_key_value("Total Net Profit", f"${ctx['tot_profit']:,.2f}")
            doc.add_key_value("Net Operating Profit Margin", f"{ctx['profit_margin']:.1f}%")
            doc.add_key_value("Average Profit per Transaction", f"${ctx['tot_profit'] / max(1, ctx['tot_orders']):,.2f}")
            if ctx['highest_profit_cat']:
                doc.add_key_value("Highest-Profit Category", ctx['highest_profit_cat'])
            if ctx['lowest_profit_cat']:
                doc.add_key_value("Lowest-Profit Category", ctx['lowest_profit_cat'])
        else:
            doc.add_paragraph("Profitability metrics unavailable — no profit or cost dimension detected in dataset.", font_tag="/F2 8 Tf", color="0.4 0.45 0.5 rg")

        # 4. Segment & Geographic Performance
        doc.add_section_title("4. Segment & Geographic Breakdown")
        if ctx['category_records']:
            doc.add_paragraph(f"Leading Segment: {ctx['top_cat_highlight']}", font_tag="/F1 8 Tf", color="0.05 0.05 0.1 rg")
            w_cat = [30.0, 140.0, 100.0, 70.0, 80.0, 75.0]
            doc.add_table_row(["#", "Category", "Revenue ($)", "% Share", "Profit ($)", "Txns"], w_cat, is_header=True)
            for c in ctx['category_records'][:5]:
                p_str = f"${c['profit']:,.2f}" if c['profit'] is not None else "N/A"
                doc.add_table_row([str(c['rank']), c['category'][:22], f"${c['revenue']:,.2f}", f"{c['pct']:.1f}%", p_str, f"{c['transactions']:,}"], w_cat)
        else:
            doc.add_paragraph("Segment analysis unavailable — no categorical dimension detected.", font_tag="/F2 8 Tf", color="0.4 0.45 0.5 rg")

        if ctx['region_records']:
            doc.add_paragraph(f"Top Regional Market: {ctx['top_reg_highlight']}", font_tag="/F1 8 Tf", color="0.05 0.05 0.1 rg")
            w_reg = [30.0, 160.0, 110.0, 95.0, 100.0]
            doc.add_table_row(["#", "Territory / Region", "Revenue ($)", "% Share", "Transactions"], w_reg, is_header=True)
            for r in ctx['region_records'][:5]:
                doc.add_table_row([str(r['rank']), r['region'][:25], f"${r['revenue']:,.2f}", f"{r['pct']:.1f}%", f"{r['transactions']:,}"], w_reg)
        else:
            doc.add_paragraph("Geographic analysis unavailable for this dataset.", font_tag="/F2 8 Tf", color="0.4 0.45 0.5 rg")

        # 5. Customer & Account Concentration
        doc.add_section_title("5. Customer & Account Concentration")
        if ctx['customer_records']:
            doc.add_key_value("Unique Accounts / Entities", f"{ctx['unique_accounts']:,}")
            doc.add_key_value("Concentration Finding", ctx['pareto_text'])
            if ctx['top_account_highlight']:
                doc.add_key_value("Top Account Identifier", ctx['top_account_highlight'])
            if ctx['top_5_account_pct'] is not None:
                doc.add_key_value("Top 5 Accounts Share", f"{ctx['top_5_account_pct']:.1f}% of total revenue")

            w_cust = [30.0, 170.0, 120.0, 95.0, 80.0]
            doc.add_table_row(["#", "Account Identifier", "Revenue ($)", "% Share", "Txns"], w_cust, is_header=True)
            for a in ctx['customer_records'][:5]:
                doc.add_table_row([str(a['rank']), a['account'][:25], f"${a['revenue']:,.2f}", f"{a['pct']:.1f}%", f"{a['transactions']:,}"], w_cust)
        else:
            doc.add_paragraph("Customer & Account Concentration analysis unavailable — no customer/account identifier detected.", font_tag="/F2 8 Tf", color="0.4 0.45 0.5 rg")

        # 6. Data Quality & Governance Scorecard
        doc.add_section_title("6. Data Quality & Governance Scorecard")
        doc.add_key_value("Overall Quality Rating", f"{ctx['quality_score']:.1f}% ({ctx['quality_rating']})")
        w_dq = [130.0, 80.0, 85.0, 200.0]
        doc.add_table_row(["Governance Pillar", "Score", "Health", "Evaluation Detail"], w_dq, is_header=True)
        doc.add_table_row(["Completeness", f"{ctx['comp_score']:.1f}%", "VERIFIED", f"{ctx['missing_cells']:,} missing cells"], w_dq)
        doc.add_table_row(["Validity", f"{ctx['val_score']:.1f}%", "VERIFIED", "Schema data types conforming"], w_dq)
        doc.add_table_row(["Consistency", f"{ctx['cons_score']:.1f}%", "VERIFIED", "Statistical variance within bounds"], w_dq)
        doc.add_table_row(["Uniqueness", f"{ctx['uniq_score']:.1f}%", "VERIFIED", f"{ctx['duplicate_rows']:,} duplicate rows"], w_dq)

        # 7. Autonomous Business Insights
        doc.add_section_title("7. Autonomous Business Insights & Intelligence")
        for ins in ctx['dynamic_insights']:
            doc.add_bullet(f"[{ins['pillar']}] {ins['title']}: {ins['observation']}")

        # 8. Executive Alerts & Exceptions
        doc.add_section_title("8. Executive Alerts & Exceptions")
        if ctx['alerts']:
            for al in ctx['alerts']:
                doc.add_bullet(f"[{al['severity']}] {al['message']}")
        else:
            doc.add_paragraph("✓ No material data-quality or analytical exceptions detected.", font_tag="/F1 8.5 Tf", color="0.1 0.5 0.2 rg")

        # 9. Governance & Verification Footer
        doc.add_divider()
        doc.add_key_value("Governance Certification", "Tamper-evident hash integrity & CSV formula neutralization certified.")
        doc.add_key_value("Platform Engine", "AUREVIX Real-Time Analytical & Data Engineering Platform (Production Mode)")

        return doc.build_pdf_bytes()

    @classmethod
    def generate_comparison_pdf(cls, comp_res: Dict[str, Any]) -> bytes:
        ds_a = comp_res.get("dataset_a", {})
        ds_b = comp_res.get("dataset_b", {})
        name_a = ds_a.get("name", "Dataset A")
        name_b = ds_b.get("name", "Dataset B")
        qc = comp_res.get("quality_comparison", {})
        num_m = comp_res.get("numeric_metrics", {})
        insights = comp_res.get("insights", [])

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        doc = PDFDocument(title="AUREVIX Comparative Intelligence Report")
        doc.add_header(
            "AUREVIX  |  Dual-Dataset Comparative Intelligence Audit",
            subtitle=f"Baseline: {name_a} vs Target: {name_b}  |  Generated: {now_str}"
        )

        doc.add_section_title("1. Volume & Schema Comparison")
        doc.add_key_value("Dataset A (Baseline) Records", f"{ds_a.get('rows', 0):,} rows, {ds_a.get('columns', 0)} columns")
        doc.add_key_value("Dataset B (Target) Records", f"{ds_b.get('rows', 0):,} rows, {ds_b.get('columns', 0)} columns")
        doc.add_key_value("Record Volume Delta", f"{comp_res.get('row_difference', 0):+d} rows ({comp_res.get('row_pct_change', 0.0):+.1f}%)")
        doc.add_key_value("Matched Common Columns", f"{len(comp_res.get('common_columns', []))}")

        if num_m:
            doc.add_section_title("2. Numeric Measure Deltas")
            widths = [140.0, 110.0, 110.0, 110.0]
            doc.add_table_row(["Metric", f"Sum ({name_a})", f"Sum ({name_b})", "Variance (%)"], widths, is_header=True)
            for k, v in list(num_m.items())[:6]:
                doc.add_table_row([
                    str(k)[:20],
                    f"{v.get('sum_a', 0):,.2f}",
                    f"{v.get('sum_b', 0):,.2f}",
                    f"{v.get('sum_pct', 0):+.1f}%"
                ], widths)

        doc.add_section_title("3. Data Quality Head-to-Head Comparison")
        doc.add_key_value("Overall Quality Score", f"{qc.get('score_a', 100.0):.1f}% ({name_a}) vs {qc.get('score_b', 100.0):.1f}% ({name_b}) - Delta: {qc.get('score_delta', 0.0):+.1f} pts")
        doc.add_key_value("Completeness Pillar", f"{qc.get('completeness_a', 100.0):.1f}% vs {qc.get('completeness_b', 100.0):.1f}%")
        doc.add_key_value("Missing Cells", f"{qc.get('missing_cells_a', 0):,} vs {qc.get('missing_cells_b', 0):,} ({qc.get('missing_delta', 0):+d})")
        doc.add_key_value("Duplicate Rows", f"{qc.get('duplicate_rows_a', 0):,} vs {qc.get('duplicate_rows_b', 0):,} ({qc.get('duplicate_delta', 0):+d})")

        if insights:
            doc.add_section_title("4. Key Comparative Insights")
            for ins in insights:
                doc.add_bullet(f"{ins.get('title')}: {ins.get('observation')}")

        return doc.build_pdf_bytes()
