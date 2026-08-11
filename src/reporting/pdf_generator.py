"""
PDF Executive Summary Report Generator for TradeGuard.

Produces a 1-Page executive-ready PDF brief using ReportLab.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import PDF_REPORTS_DIR
from src.utils.logger import get_logger

logger = get_logger("PDFReportGenerator")


class PDFReportGenerator:
    """Generates 1-Page PDF Executive Summary Brief for Trade Reconciliation runs."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or PDF_REPORTS_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        run_summary: Dict[str, Any],
        breaks: List[Dict[str, Any]],
        output_filename: Optional[str] = None
    ) -> Path:
        """
        Generates a styled 1-Page PDF Executive Summary report.

        :param run_summary: Dictionary containing run metrics (Run_ID, Match_Percentage, Total_Breaks, etc.).
        :param breaks: List of break dictionaries.
        :param output_filename: Optional custom filename for PDF output.
        :return: Path object to the generated PDF file.
        """
        run_id = run_summary.get("Run_ID", "REC_N/A")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output_filename or f"Trade_Reconciliation_Summary_{timestamp}.pdf"
        target_path = self.output_dir / filename

        logger.info(f"Generating Executive PDF Brief at: {target_path}")

        doc = SimpleDocTemplate(
            str(target_path),
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        # Custom Palette & Styles
        primary_color = colors.HexColor("#1B365D")  # Deep Navy
        secondary_color = colors.HexColor("#0F172A") # Slate Dark
        accent_color = colors.HexColor("#00F2FE")   # Cyan Accent
        border_color = colors.HexColor("#CBD5E1")   # Slate Light

        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=20,
            leading=24,
            textColor=primary_color,
            spaceAfter=2
        )
        subtitle_style = ParagraphStyle(
            'DocSubtitle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#64748B"),
            spaceAfter=10
        )
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=12,
            leading=15,
            textColor=primary_color,
            spaceBefore=10,
            spaceAfter=6
        )
        cell_style = ParagraphStyle(
            'CellText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=secondary_color
        )
        cell_bold = ParagraphStyle(
            'CellBold',
            parent=cell_style,
            fontName='Helvetica-Bold'
        )

        elements = []

        # Header Title Banner
        elements.append(Paragraph("TradeGuard — Executive Reconciliation Brief", title_style))
        elements.append(Paragraph("Product Control & Operational Risk Governance Audit", subtitle_style))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=primary_color, spaceAfter=10))

        # Metadata Bar
        match_pct = float(run_summary.get("Match_Percentage", 0.0))
        status_tag = "HEALTHY" if match_pct >= 90 else ("WARNING" if match_pct >= 80 else "CRITICAL")
        status_bg = "#D1FAE5" if status_tag == "HEALTHY" else ("#FEF3C7" if status_tag == "WARNING" else "#FEE2E2")
        status_fg = "#065F46" if status_tag == "HEALTHY" else ("#92400E" if status_tag == "WARNING" else "#991B1B")

        meta_data = [
            [
                Paragraph(f"<b>Run ID:</b> {run_id}", cell_style),
                Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", cell_style),
                Paragraph(f"<b>Engine Tolerance:</b> ${run_summary.get('Tolerance', 0.01):.2f}", cell_style),
                Paragraph(f"<b>System Status:</b> <font color='{status_fg}'><b>{status_tag}</b></font>", cell_style),
            ]
        ]
        meta_table = Table(meta_data, colWidths=[1.8*inch, 2.2*inch, 1.7*inch, 1.8*inch])
        meta_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ('BOX', (0, 0), (-1, -1), 0.5, border_color),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        elements.append(meta_table)
        elements.append(Spacer(1, 10))

        # Executive KPI Summary Cards Table
        elements.append(Paragraph("1. Executive Summary KPIs", section_style))
        fo_trades = run_summary.get("FO_Trade_Count", 0)
        bo_trades = run_summary.get("BO_Trade_Count", 0)
        matched = run_summary.get("Matched_Trades_Count", 0)
        total_breaks = run_summary.get("Total_Breaks", len(breaks))
        crit_breaks = sum(1 for b in breaks if b.get("Severity") == "CRITICAL")
        exec_time = run_summary.get("Execution_Time", "0.01s")

        kpi_headers = ["Total FO Trades", "Total BO Trades", "Matched Trades", "Match Rate %", "Total Exceptions", "Critical Breaks"]
        kpi_values = [
            f"{fo_trades:,}",
            f"{bo_trades:,}",
            f"{matched:,}",
            f"{match_pct:.2f}%",
            f"{total_breaks:,}",
            f"{crit_breaks:,}"
        ]

        kpi_table_data = [
            [Paragraph(f"<b>{h}</b>", cell_bold) for h in kpi_headers],
            [Paragraph(f"<b>{v}</b>", cell_bold) for v in kpi_values]
        ]
        kpi_table = Table(kpi_table_data, colWidths=[1.25*inch]*6)
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#F1F5F9")),
            ('BOX', (0, 0), (-1, -1), 0.5, primary_color),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 12))

        # Break Severity Breakdown
        elements.append(Paragraph("2. Break Severity & Notional Exposure", section_style))
        sev_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        sev_notional = {"CRITICAL": 0.0, "HIGH": 0.0, "MEDIUM": 0.0, "LOW": 0.0}

        for b in breaks:
            sev = b.get("Severity", "MEDIUM")
            notional = float(b.get("FO_Notional") or b.get("BO_Notional") or 0.0)
            if sev in sev_counts:
                sev_counts[sev] += 1
                sev_notional[sev] += notional

        sev_rows = [["Severity Level", "Exception Count", "% of Total", "Estimated Notional Exposure ($)"]]
        for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
            cnt = sev_counts[sev]
            pct = (cnt / total_breaks * 100) if total_breaks > 0 else 0.0
            notional_str = f"${sev_notional[sev]:,.2f}"
            sev_rows.append([
                Paragraph(f"<b>{sev}</b>", cell_bold),
                Paragraph(str(cnt), cell_style),
                Paragraph(f"{pct:.1f}%", cell_style),
                Paragraph(notional_str, cell_style)
            ])

        sev_table = Table(sev_rows, colWidths=[1.8*inch, 1.8*inch, 1.8*inch, 2.1*inch])
        sev_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#334155")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(sev_table)
        elements.append(Spacer(1, 12))

        # Top Critical Exceptions Table (Up to 8 items)
        elements.append(Paragraph("3. Top Critical Exceptions Sample", section_style))
        crit_items = [b for b in breaks if b.get("Severity") == "CRITICAL"][:8]
        if not crit_items:
            crit_items = breaks[:8]

        crit_rows = [["Trade ID", "Desk", "Counterparty", "Break Category", "Severity", "Status"]]
        for item in crit_items:
            t_id = item.get("Trade_ID", "N/A")
            desk = item.get("Desk", "N/A")
            cp = item.get("Counterparty", "N/A")
            cat = item.get("Break_Type", "N/A")
            sev = item.get("Severity", "N/A")
            res_status = item.get("Resolution_Status", "UNRESOLVED")

            crit_rows.append([
                Paragraph(t_id, cell_bold),
                Paragraph(desk, cell_style),
                Paragraph(cp, cell_style),
                Paragraph(cat, cell_style),
                Paragraph(f"<b>{sev}</b>", cell_bold),
                Paragraph(res_status, cell_style)
            ])

        crit_table = Table(crit_rows, colWidths=[1.2*inch, 1.2*inch, 1.5*inch, 1.6*inch, 1.0*inch, 1.0*inch])
        crit_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), primary_color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, border_color),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(crit_table)

        # Build PDF Document
        doc.build(elements)
        logger.info(f"Successfully created PDF Executive Brief: {target_path}")
        return target_path
