"""
CPAverse Agent — PDF Generator with Company Letterhead

Generates professional PDF documents using Josh Mauer CPA letterhead.
All agent-generated documents use this module to maintain consistent
branding and Circular 230 compliance.

Two-Tier System (Circular 230 §10.22 Due Diligence):
    DRAFT — Agent creates PDF with "DRAFT — Pending CPA Review" watermark.
            Saved to client's 2025 folder immediately.
    FINAL — After Josh reviews and approves, agent re-generates clean
            letterhead version without watermark.

Letterhead Elements (from Josh Mauer CPA Google Docs template):
    - Logo: Green checkmark icon + "Josh Mauer" in dark gray
      Subtitle: "CERTIFIED PUBLIC ACCOUNTANT" in smaller gray
    - Gray horizontal separator line
    - Contact line: 7707 West 151st Street Overland Park, KS 66223
                    | 913-815-1550 | www.joshmauercpa.com

File Placement:
    Agent saves PDFs to client folders on the AWS WorkSpace virtual drive
    (mapped to TaxDome document storage). Path pattern:
        {TAXDOME_VIRTUAL_DRIVE}/{client_folder}/2025/{filename}.pdf

Dependencies: reportlab
"""

import os
from datetime import datetime
from typing import Optional, List, Dict

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import (
    HexColor, white, black, gray, lightgrey
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# ── Brand Colors ─────────────────────────────────────────────────
BRAND_GREEN = HexColor("#6EAB2E")       # Checkmark green
BRAND_DARK_GRAY = HexColor("#4A4A4A")   # "Josh Mauer" text
BRAND_LIGHT_GRAY = HexColor("#999999")  # Subtitle & contact info
BRAND_LINE_GRAY = HexColor("#BBBBBB")   # Horizontal separator
BRAND_BLUE = HexColor("#2E6DA4")        # Link color (website)
DRAFT_RED = HexColor("#CC0000")         # Draft watermark color

# ── Firm Info ────────────────────────────────────────────────────
FIRM_NAME = "Josh Mauer"
FIRM_SUBTITLE = "CERTIFIED PUBLIC ACCOUNTANT"
FIRM_ADDRESS = "7707 West 151st Street Overland Park, KS 66223"
FIRM_PHONE = "913-815-1550"
FIRM_WEBSITE = "www.joshmauercpa.com"
FIRM_CONTACT_LINE = f"{FIRM_ADDRESS}  |  {FIRM_PHONE}  |  {FIRM_WEBSITE}"

# ── Page Layout ──────────────────────────────────────────────────
PAGE_WIDTH, PAGE_HEIGHT = letter  # 8.5 x 11 inches
LEFT_MARGIN = 0.75 * inch
RIGHT_MARGIN = 0.75 * inch
TOP_MARGIN = 0.5 * inch
BOTTOM_MARGIN = 0.75 * inch
HEADER_HEIGHT = 1.2 * inch  # Space reserved for letterhead header
CONTENT_TOP = PAGE_HEIGHT - TOP_MARGIN - HEADER_HEIGHT

# ── Disclaimer Text ──────────────────────────────────────────────
STANDARD_DISCLAIMER = (
    "This document was prepared by the CPAverse Tax Prep Agent under the "
    "supervision of Josh Mauer, CPA. It is intended solely for the use of "
    "the named client and should not be distributed to third parties without "
    "written consent. This document does not constitute tax advice and is "
    "subject to review and approval by a licensed CPA."
)

DRAFT_DISCLAIMER = (
    "DRAFT — This document has been prepared by an AI tax preparation agent "
    "and has NOT yet been reviewed or approved by a licensed CPA. Do not rely "
    "on this document for filing purposes. Final review by Josh Mauer, CPA "
    "is required before this document is considered complete."
)

CONFIDENTIALITY_NOTICE = (
    "CONFIDENTIAL: This document contains confidential tax return information "
    "subject to IRC §7216. Unauthorized disclosure is prohibited."
)


class LetterheadPDFGenerator:
    """
    Generates professional PDFs with Josh Mauer CPA letterhead.

    Usage:
        gen = LetterheadPDFGenerator()

        # Create a draft summary PDF
        gen.create_summary_pdf(
            output_path="/path/to/client/2025/Tax_Summary.pdf",
            client_name="John & Jane Smith",
            title="2025 Tax Return Summary",
            sections=[
                {"heading": "Income", "content": "W-2 wages: $85,000\n..."},
                {"heading": "Deductions", "content": "Standard deduction: $29,200"},
            ],
            is_draft=True
        )

        # After Josh approves, create final version
        gen.create_summary_pdf(
            output_path="/path/to/client/2025/Tax_Summary_FINAL.pdf",
            client_name="John & Jane Smith",
            title="2025 Tax Return Summary",
            sections=[...],
            is_draft=False
        )
    """

    def __init__(self, virtual_drive_path: Optional[str] = None):
        self.virtual_drive = virtual_drive_path or os.environ.get(
            "TAXDOME_VIRTUAL_DRIVE", ""
        )
        self._setup_styles()

    def _setup_styles(self):
        """Configure paragraph styles for the letterhead documents."""
        self.styles = getSampleStyleSheet()

        # Document title (below letterhead)
        self.styles.add(ParagraphStyle(
            name="DocTitle",
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            textColor=BRAND_DARK_GRAY,
            spaceAfter=6,
            alignment=TA_LEFT,
        ))

        # Document subtitle / client name
        self.styles.add(ParagraphStyle(
            name="DocSubtitle",
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=BRAND_LIGHT_GRAY,
            spaceAfter=12,
            alignment=TA_LEFT,
        ))

        # Section heading
        self.styles.add(ParagraphStyle(
            name="SectionHeading",
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=BRAND_DARK_GRAY,
            spaceBefore=14,
            spaceAfter=6,
            alignment=TA_LEFT,
        ))

        # Body text
        self.styles.add(ParagraphStyle(
            name="BodyText_LH",
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=black,
            spaceAfter=8,
            alignment=TA_LEFT,
        ))

        # Small text for disclaimers
        self.styles.add(ParagraphStyle(
            name="Disclaimer",
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=BRAND_LIGHT_GRAY,
            spaceBefore=20,
            spaceAfter=4,
            alignment=TA_LEFT,
        ))

        # Table header style
        self.styles.add(ParagraphStyle(
            name="TableHeader",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=12,
            textColor=white,
            alignment=TA_LEFT,
        ))

        # Table body style
        self.styles.add(ParagraphStyle(
            name="TableBody",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=black,
            alignment=TA_LEFT,
        ))

        # Currency amounts (right-aligned)
        self.styles.add(ParagraphStyle(
            name="Currency",
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=black,
            alignment=TA_RIGHT,
        ))

        # Draft watermark notice at top
        self.styles.add(ParagraphStyle(
            name="DraftBanner",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=DRAFT_RED,
            spaceBefore=0,
            spaceAfter=8,
            alignment=TA_CENTER,
        ))

    # ── Letterhead Drawing ───────────────────────────────────────

    def _draw_letterhead(self, canvas_obj, doc, is_draft: bool = False):
        """
        Draw the letterhead header on every page.

        Called by reportlab's SimpleDocTemplate as the onPage callback.
        Draws the logo area, firm name, separator line, and contact info.
        Also draws the draft watermark if is_draft=True.
        """
        canvas_obj.saveState()

        # ── Draw green checkmark circle (simplified as brand element) ──
        # Since we can't embed the exact logo without the image file,
        # we draw a green circle with a white checkmark as an approximation.
        logo_x = LEFT_MARGIN
        logo_y = PAGE_HEIGHT - TOP_MARGIN - 0.15 * inch
        circle_radius = 0.22 * inch

        # Green circle
        canvas_obj.setFillColor(BRAND_GREEN)
        canvas_obj.circle(
            logo_x + circle_radius,
            logo_y - circle_radius,
            circle_radius,
            fill=1, stroke=0
        )

        # White checkmark inside circle
        canvas_obj.setStrokeColor(white)
        canvas_obj.setLineWidth(2.5)
        cx = logo_x + circle_radius
        cy = logo_y - circle_radius
        # Checkmark path: down-left to center-bottom, then up to top-right
        p = canvas_obj.beginPath()
        p.moveTo(cx - 0.10 * inch, cy + 0.02 * inch)
        p.lineTo(cx - 0.02 * inch, cy - 0.10 * inch)
        p.lineTo(cx + 0.14 * inch, cy + 0.12 * inch)
        canvas_obj.drawPath(p, stroke=1, fill=0)

        # ── Firm Name ──
        text_x = logo_x + circle_radius * 2 + 0.12 * inch
        name_y = logo_y - 0.12 * inch

        canvas_obj.setFont("Helvetica-Bold", 22)
        canvas_obj.setFillColor(BRAND_DARK_GRAY)
        canvas_obj.drawString(text_x, name_y, FIRM_NAME)

        # ── Subtitle ──
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(BRAND_LIGHT_GRAY)
        canvas_obj.drawString(text_x, name_y - 14, FIRM_SUBTITLE)

        # ── Gray separator line ──
        line_y = PAGE_HEIGHT - TOP_MARGIN - 0.75 * inch
        canvas_obj.setStrokeColor(BRAND_LINE_GRAY)
        canvas_obj.setLineWidth(1.5)
        canvas_obj.line(
            LEFT_MARGIN, line_y,
            PAGE_WIDTH - RIGHT_MARGIN, line_y
        )

        # ── Contact info line ──
        contact_y = line_y - 12
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(BRAND_LIGHT_GRAY)

        # Build contact line with website in blue
        contact_parts = f"{FIRM_ADDRESS}  |  {FIRM_PHONE}  |  "
        canvas_obj.drawString(LEFT_MARGIN, contact_y, contact_parts)

        # Website in blue
        contact_width = canvas_obj.stringWidth(contact_parts, "Helvetica", 8)
        canvas_obj.setFillColor(BRAND_BLUE)
        canvas_obj.drawString(
            LEFT_MARGIN + contact_width,
            contact_y,
            FIRM_WEBSITE
        )

        # ── Draft Watermark ──
        if is_draft:
            canvas_obj.saveState()
            canvas_obj.setFillColor(HexColor("#FFEEEE"))
            canvas_obj.setFont("Helvetica-Bold", 54)
            canvas_obj.translate(PAGE_WIDTH / 2, PAGE_HEIGHT / 2)
            canvas_obj.rotate(45)
            canvas_obj.setFillAlpha(0.15)
            canvas_obj.drawCentredString(0, 0, "DRAFT")
            canvas_obj.restoreState()

        # ── Page number (bottom center) ──
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.setFillColor(BRAND_LIGHT_GRAY)
        page_num = canvas_obj.getPageNumber()
        canvas_obj.drawCentredString(
            PAGE_WIDTH / 2, 0.5 * inch,
            f"Page {page_num}"
        )

        canvas_obj.restoreState()

    # ── Public Methods ───────────────────────────────────────────

    def create_summary_pdf(
        self,
        output_path: str,
        client_name: str,
        title: str,
        sections: List[Dict[str, str]],
        is_draft: bool = True,
        prepared_date: Optional[str] = None,
        include_disclaimer: bool = True,
    ) -> dict:
        """
        Create a tax summary PDF with letterhead.

        Args:
            output_path: Full path where the PDF will be saved.
            client_name: Client name to display on the document.
            title: Document title (e.g., "2025 Tax Return Summary").
            sections: List of section dicts with "heading" and "content" keys.
                      Content supports \n for line breaks.
            is_draft: If True, adds "DRAFT — Pending CPA Review" watermark.
            prepared_date: Date string for the document. Defaults to today.
            include_disclaimer: Whether to add disclaimer footer text.

        Returns:
            {"success": bool, "path": str, "pages": int, "message": str}
        """
        if not prepared_date:
            prepared_date = datetime.now().strftime("%B %d, %Y")

        try:
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                leftMargin=LEFT_MARGIN,
                rightMargin=RIGHT_MARGIN,
                topMargin=TOP_MARGIN + HEADER_HEIGHT,
                bottomMargin=BOTTOM_MARGIN,
            )

            story = []

            # ── Draft banner ──
            if is_draft:
                story.append(Paragraph(
                    "⚠ DRAFT — PENDING CPA REVIEW ⚠",
                    self.styles["DraftBanner"]
                ))
                story.append(Spacer(1, 4))

            # ── Title ──
            story.append(Paragraph(title, self.styles["DocTitle"]))

            # ── Client name and date ──
            subtitle = f"Prepared for: {client_name}  |  Date: {prepared_date}"
            story.append(Paragraph(subtitle, self.styles["DocSubtitle"]))

            story.append(Spacer(1, 8))

            # ── Sections ──
            for section in sections:
                heading = section.get("heading", "")
                content = section.get("content", "")

                if heading:
                    story.append(Paragraph(heading, self.styles["SectionHeading"]))

                # Handle multi-line content
                for line in content.split("\n"):
                    line = line.strip()
                    if line:
                        story.append(Paragraph(line, self.styles["BodyText_LH"]))

                story.append(Spacer(1, 4))

            # ── Disclaimers ──
            if include_disclaimer:
                story.append(Spacer(1, 20))

                # Thin separator
                story.append(HRFlowable(
                    width="100%", thickness=0.5,
                    color=BRAND_LINE_GRAY, spaceAfter=8
                ))

                if is_draft:
                    story.append(Paragraph(
                        DRAFT_DISCLAIMER, self.styles["Disclaimer"]
                    ))

                story.append(Paragraph(
                    STANDARD_DISCLAIMER, self.styles["Disclaimer"]
                ))
                story.append(Paragraph(
                    CONFIDENTIALITY_NOTICE, self.styles["Disclaimer"]
                ))

            # ── Build with letterhead on every page ──
            def on_page(canvas_obj, doc_obj):
                self._draw_letterhead(canvas_obj, doc_obj, is_draft=is_draft)

            doc.build(story, onFirstPage=on_page, onLaterPages=on_page)

            return {
                "success": True,
                "path": output_path,
                "pages": doc.page,
                "is_draft": is_draft,
                "message": f"PDF created: {os.path.basename(output_path)}",
            }

        except Exception as e:
            return {
                "success": False,
                "path": output_path,
                "pages": 0,
                "is_draft": is_draft,
                "message": f"PDF generation failed: {str(e)}",
            }

    def create_document_checklist_pdf(
        self,
        output_path: str,
        client_name: str,
        documents: List[Dict[str, str]],
        missing: List[str],
        is_draft: bool = True,
    ) -> dict:
        """
        Create a document checklist PDF showing received vs. missing items.

        Used when the agent identifies what documents have been uploaded
        and what's still needed for a complete return.

        Args:
            output_path: Full path for the PDF.
            client_name: Client name.
            documents: List of received doc dicts: {"type": "w2", "filename": "W-2_Employer.pdf"}
            missing: List of still-needed document descriptions.
            is_draft: Whether to apply draft watermark.

        Returns:
            {"success": bool, "path": str, "pages": int, "message": str}
        """
        sections = []

        # Received documents
        received_lines = []
        for doc in documents:
            doc_type = doc.get("type", "other").upper().replace("_", "-")
            filename = doc.get("filename", "Unknown")
            received_lines.append(f"✓  {doc_type}: {filename}")

        sections.append({
            "heading": "Documents Received",
            "content": "\n".join(received_lines) if received_lines else "No documents received yet.",
        })

        # Missing documents
        if missing:
            missing_lines = [f"✗  {item}" for item in missing]
            sections.append({
                "heading": "Documents Still Needed",
                "content": "\n".join(missing_lines),
            })

        # Summary
        total = len(documents) + len(missing)
        sections.append({
            "heading": "Summary",
            "content": (
                f"Received: {len(documents)} of {total} expected documents\n"
                f"Missing: {len(missing)} documents\n"
                f"Completeness: {len(documents) / max(total, 1) * 100:.0f}%"
            ),
        })

        return self.create_summary_pdf(
            output_path=output_path,
            client_name=client_name,
            title="2025 Document Checklist",
            sections=sections,
            is_draft=is_draft,
        )

    def create_data_entry_summary_pdf(
        self,
        output_path: str,
        client_name: str,
        return_type: str,
        entries: List[Dict[str, str]],
        flags: List[str],
        is_draft: bool = True,
    ) -> dict:
        """
        Create a data entry summary PDF after processing a return in Drake.

        Documents what the agent entered, any flags raised, and items
        requiring CPA review.

        Args:
            output_path: Full path for the PDF.
            client_name: Client name.
            return_type: e.g., "1040", "1040-SR", "1065"
            entries: List of entry dicts: {"form": "W-2", "field": "Wages", "value": "$85,000"}
            flags: List of flag descriptions requiring CPA attention.
            is_draft: Whether to apply draft watermark.

        Returns:
            {"success": bool, "path": str, "pages": int, "message": str}
        """
        sections = []

        # Return info
        sections.append({
            "heading": "Return Information",
            "content": (
                f"Return Type: {return_type}\n"
                f"Tax Year: 2025\n"
                f"Prepared by: CPAverse Tax Prep Agent\n"
                f"Status: {'Draft — Pending CPA Review' if is_draft else 'CPA Reviewed & Approved'}"
            ),
        })

        # Data entries
        entry_lines = []
        for entry in entries:
            form = entry.get("form", "")
            field = entry.get("field", "")
            value = entry.get("value", "")
            entry_lines.append(f"{form} — {field}: {value}")

        sections.append({
            "heading": "Data Entered",
            "content": "\n".join(entry_lines) if entry_lines else "No entries recorded.",
        })

        # Flags
        if flags:
            flag_lines = [f"⚑  {flag}" for flag in flags]
            sections.append({
                "heading": "Flags for CPA Review",
                "content": "\n".join(flag_lines),
            })
        else:
            sections.append({
                "heading": "Flags for CPA Review",
                "content": "No flags raised. All entries within expected parameters.",
            })

        return self.create_summary_pdf(
            output_path=output_path,
            client_name=client_name,
            title=f"2025 {return_type} — Data Entry Summary",
            sections=sections,
            is_draft=is_draft,
        )

    # ── Virtual Drive Helpers ────────────────────────────────────

    def get_client_pdf_path(
        self,
        client_folder: str,
        filename: str,
        tax_year: str = "2025",
    ) -> str:
        """
        Build the full path for a client PDF on the virtual drive.

        Args:
            client_folder: Client folder name on the drive.
            filename: PDF filename (e.g., "Tax_Summary.pdf").
            tax_year: Tax year subfolder (default "2025").

        Returns:
            Full path: {virtual_drive}/{client_folder}/{tax_year}/{filename}
        """
        if not self.virtual_drive:
            # Fallback to a local temp path
            return os.path.join("/tmp", "cpaverse", client_folder, tax_year, filename)

        return os.path.join(self.virtual_drive, client_folder, tax_year, filename)

    def promote_draft_to_final(
        self,
        draft_path: str,
        client_name: str,
        title: str,
        sections: List[Dict[str, str]],
    ) -> dict:
        """
        Re-generate a draft PDF as a clean final version (no watermark).

        Called after Josh reviews and approves the draft.

        Args:
            draft_path: Path to the existing draft PDF.
            client_name: Client name.
            title: Document title.
            sections: Same section data used for the draft.

        Returns:
            {"success": bool, "draft_path": str, "final_path": str, "message": str}
        """
        # Generate final path by replacing _DRAFT suffix or adding _FINAL
        base, ext = os.path.splitext(draft_path)
        if base.endswith("_DRAFT"):
            final_path = base.replace("_DRAFT", "_FINAL") + ext
        else:
            final_path = base + "_FINAL" + ext

        result = self.create_summary_pdf(
            output_path=final_path,
            client_name=client_name,
            title=title,
            sections=sections,
            is_draft=False,
        )

        if result["success"]:
            return {
                "success": True,
                "draft_path": draft_path,
                "final_path": final_path,
                "message": f"Final version created: {os.path.basename(final_path)}",
            }
        else:
            return {
                "success": False,
                "draft_path": draft_path,
                "final_path": final_path,
                "message": result["message"],
            }