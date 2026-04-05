"""PDF report generator service.

Generates volumetry PDF reports using ReportLab based on the example format.
Uses Doctor App brand styles and colors with reference values.
"""

import io
import logging
from datetime import datetime
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.volume_extractor import ReportData, StructureRow, VolumeValue, ReferenceRange
from app.services import reference_values as refs

logger = logging.getLogger(__name__)

# Doctor App Brand Colors
BRAND_BLUE_LIGHT = "#96CBF0"  # RGB(150, 203, 240)
BRAND_BLUE_MEDIUM = "#4F91C7"  # RGB(79, 145, 199)
BRAND_GREEN_MINT = "#6EC899"  # RGB(110, 200, 153)
BRAND_BLUE_SKY = "#81CDF4"  # RGB(129, 205, 244)
BRAND_GREEN_TURQUOISE = "#00C899"  # RGB(0, 200, 153)
BRAND_DARK_TEXT = "#2D3748"  # Dark gray for readability
BRAND_LIGHT_BG = "#F7FAFC"  # Light background
BRAND_ROW_ALT = "#EDF2F7"  # Alternating row color

# Status colors for reference comparison
STATUS_NORMAL = "#48BB78"  # Green - within range
STATUS_WARNING = "#ECC94B"  # Yellow - slightly outside
STATUS_ALERT = "#F56565"  # Red - significantly outside

# Assets paths - works both in Docker (/app/assets) and locally
ASSETS_DIR = Path("/app/assets/doctor-app/3_PNG")
if not ASSETS_DIR.exists():
    # Fallback for local development
    ASSETS_DIR = Path(__file__).parent.parent.parent.parent / "assets" / "doctor-app" / "3_PNG"
LOGO_PATH = ASSETS_DIR / "Logo Doctor App-01.png"

# Page dimensions
PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 1.5 * cm


class PDFGenerator:
    """Generates volumetry PDF reports in Spanish with Doctor App branding."""

    def __init__(self) -> None:
        """Initialize PDF generator with styles."""
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self) -> None:
        """Setup custom paragraph styles with Doctor App brand colors."""
        # Main title style
        self.styles.add(
            ParagraphStyle(
                "ReportTitle",
                parent=self.styles["Heading1"],
                fontSize=18,
                textColor=colors.HexColor(BRAND_BLUE_MEDIUM),
                spaceAfter=8,
                fontName="Helvetica-Bold",
                alignment=TA_LEFT,
            )
        )
        # Section headers
        self.styles.add(
            ParagraphStyle(
                "SectionHeader",
                parent=self.styles["Heading2"],
                fontSize=13,
                textColor=colors.HexColor(BRAND_BLUE_MEDIUM),
                spaceAfter=6,
                spaceBefore=14,
                fontName="Helvetica-Bold",
                borderPadding=(0, 0, 4, 0),
            )
        )
        # Subtitle for patient info
        self.styles.add(
            ParagraphStyle(
                "SubTitle",
                parent=self.styles["Normal"],
                fontSize=10,
                textColor=colors.HexColor(BRAND_DARK_TEXT),
                spaceAfter=4,
                fontName="Helvetica",
            )
        )
        # Footer style
        self.styles.add(
            ParagraphStyle(
                "Footer",
                parent=self.styles["Normal"],
                fontSize=8,
                textColor=colors.HexColor(BRAND_GREEN_MINT),
                alignment=TA_CENTER,
                spaceBefore=12,
            )
        )
        # Notes style
        self.styles.add(
            ParagraphStyle(
                "Note",
                parent=self.styles["Normal"],
                fontSize=8,
                textColor=colors.HexColor("#718096"),
                spaceAfter=3,
                leftIndent=8,
                fontName="Helvetica-Oblique",
            )
        )
        # Legend style
        self.styles.add(
            ParagraphStyle(
                "Legend",
                parent=self.styles["Normal"],
                fontSize=8,
                textColor=colors.HexColor("#4A5568"),
                spaceAfter=2,
                fontName="Helvetica",
            )
        )
        # Disclaimer style
        self.styles.add(
            ParagraphStyle(
                "Disclaimer",
                parent=self.styles["Normal"],
                fontSize=7,
                textColor=colors.HexColor("#A0AEC0"),
                alignment=TA_CENTER,
                spaceBefore=8,
            )
        )

    def _fmt_vol(self, val: VolumeValue | None, show_pct: bool = True) -> str:
        """Format volume value as string."""
        if val is None:
            return "—"
        if show_pct:
            return f"{val.absolute_cm3:.2f} ({val.relative_pct:.2f}%)"
        return f"{val.absolute_cm3:.2f}"

    def _fmt_vol_simple(self, val: VolumeValue | None) -> str:
        """Format volume as simple cm³ value."""
        if val is None:
            return "—"
        return f"{val.absolute_cm3:.2f}"

    def _fmt_pct(self, val: VolumeValue | None) -> str:
        """Format just the percentage."""
        if val is None:
            return "—"
        return f"{val.relative_pct:.2f}%"

    def _fmt_ref(self, ref: ReferenceRange | None) -> str:
        """Format reference range as string."""
        if ref is None:
            return "—"
        return f"[{ref.min_pct:.2f} - {ref.max_pct:.2f}]"

    def _fmt_asym(self, asym: float | None) -> str:
        """Format asymmetry percentage."""
        if asym is None:
            return "—"
        return f"{asym:.2f}%"

    def _get_status_indicator(self, value: float | None, ref: ReferenceRange | None) -> str:
        """Get status indicator emoji/symbol."""
        if value is None or ref is None:
            return ""
        status = ref.get_status(value)
        if status == "normal":
            return "✓"
        elif status == "low":
            return "↓"
        else:
            return "↑"

    def _capitalize_name(self, name: str) -> str:
        """Capitalize structure name properly."""
        return name.title() if name else name

    def _create_header_table(self, data: ReportData) -> Table:
        """Create the patient information table with clean design."""
        # Format sex in Spanish
        sex_display = {"M": "Masculino", "F": "Femenino"}.get(data.sex, data.sex)
        
        header_data = [
            ["Paciente:", data.subject_id, "Orientación:", data.image_orientation or "N/A"],
            ["Sexo:", sex_display, "Factor de escala:", f"{data.scale_factor:.2f}" if data.scale_factor else "N/A"],
            ["Edad:", f"{data.age} años" if data.age else "N/A", "SNR:", f"{data.snr:.1f}" if data.snr else "N/A"],
            ["Fecha:", data.report_date, "", ""],
        ]

        table = Table(header_data, colWidths=[2.8 * cm, 4.5 * cm, 3.2 * cm, 4 * cm])
        table.setStyle(
            TableStyle([
                # General font settings
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                # Labels in bold with brand color
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor(BRAND_BLUE_MEDIUM)),
                ("TEXTCOLOR", (2, 0), (2, -1), colors.HexColor(BRAND_BLUE_MEDIUM)),
                # Values in dark text
                ("TEXTCOLOR", (1, 0), (1, -1), colors.HexColor(BRAND_DARK_TEXT)),
                ("TEXTCOLOR", (3, 0), (3, -1), colors.HexColor(BRAND_DARK_TEXT)),
                # Alignment and padding
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                # Subtle background
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(BRAND_LIGHT_BG)),
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor(BRAND_GREEN_MINT)),
            ])
        )
        return table

    def _create_legend(self) -> Paragraph:
        """Create legend explaining the indicators."""
        legend_text = (
            "<b>Leyenda:</b> "
            "<font color='#48BB78'>✓ Normal</font> | "
            "<font color='#F56565'>↓ Bajo</font> | "
            "<font color='#F56565'>↑ Alto</font> | "
            "Referencia = rango esperado (percentil 95)"
        )
        return Paragraph(legend_text, self.styles["Legend"])

    def _create_tissue_table(self, rows: list[StructureRow]) -> Table:
        """Create tissue segmentation table with reference values."""
        table_data = [["Tejido", "Volumen (cm³)", "% ICV", "Referencia", ""]]

        for row in rows:
            vol = row.total
            ref = refs.get_tissue_reference(row.name)
            pct = vol.relative_pct if vol else None
            status = self._get_status_indicator(pct, ref)
            
            table_data.append([
                self._capitalize_name(row.name),
                f"{vol.absolute_cm3:.2f}" if vol else "—",
                f"{vol.relative_pct:.2f}%" if vol else "—",
                self._fmt_ref(ref),
                status,
            ])

        table = Table(table_data, colWidths=[6 * cm, 2.8 * cm, 2.5 * cm, 3.5 * cm, 0.8 * cm])
        table.setStyle(self._get_table_style_with_status(len(table_data), rows, "tissue"))
        return table

    def _create_structure_table(
        self, rows: list[StructureRow], title: str = "Estructura", ref_type: str = "macro"
    ) -> Table:
        """Create a structure table with L/R columns, asymmetry, and references."""
        table_data = [[title, "Total (cm³)", "% ICV", "Derecho", "Izquierdo", "Asimetría", "Ref.", ""]]

        for row in rows:
            # Get reference based on type
            if ref_type == "macro":
                ref = refs.get_macro_reference(row.name, "total")
            elif ref_type == "subcortical":
                ref = refs.get_subcortical_reference(row.name, "total")
            else:
                ref = refs.get_cortical_reference(row.name, "total")
            
            pct = row.total.relative_pct if row.total else None
            status = self._get_status_indicator(pct, ref)
            
            table_data.append([
                self._capitalize_name(row.name),
                self._fmt_vol_simple(row.total),
                self._fmt_pct(row.total),
                self._fmt_vol_simple(row.right),
                self._fmt_vol_simple(row.left),
                self._fmt_asym(row.asymmetry_pct),
                self._fmt_ref(ref),
                status,
            ])

        col_widths = [3.8 * cm, 2 * cm, 2 * cm, 2 * cm, 2 * cm, 1.8 * cm, 2.8 * cm, 0.6 * cm]
        table = Table(table_data, colWidths=col_widths)
        table.setStyle(self._get_table_style_with_status(len(table_data), rows, ref_type))
        return table

    def _get_table_style_with_status(
        self, num_rows: int, rows: list[StructureRow], ref_type: str
    ) -> TableStyle:
        """Get table style with conditional formatting based on status."""
        style_commands = [
            # Header row styling
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BRAND_BLUE_MEDIUM)),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 9),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            # Data rows styling
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor(BRAND_DARK_TEXT)),
            ("ALIGN", (1, 1), (-2, -1), "CENTER"),
            ("ALIGN", (0, 1), (0, -1), "LEFT"),
            ("ALIGN", (-1, 1), (-1, -1), "CENTER"),
            # Alternating row colors for readability
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            # Clean border style
            ("LINEBELOW", (0, 0), (-1, 0), 2, colors.HexColor(BRAND_GREEN_MINT)),
            ("LINEBELOW", (0, 1), (-1, -2), 0.5, colors.HexColor("#E2E8F0")),
            ("LINEBELOW", (0, -1), (-1, -1), 1, colors.HexColor(BRAND_GREEN_MINT)),
            # Padding for comfortable reading
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]

        # Add alternating row colors
        for i in range(2, num_rows, 2):
            style_commands.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor(BRAND_ROW_ALT)))

        # Add status colors for out-of-range values
        for idx, row in enumerate(rows, start=1):
            vol = row.total
            if vol is None:
                continue
            
            # Get reference
            if ref_type == "tissue":
                ref = refs.get_tissue_reference(row.name)
            elif ref_type == "macro":
                ref = refs.get_macro_reference(row.name, "total")
            elif ref_type == "subcortical":
                ref = refs.get_subcortical_reference(row.name, "total")
            else:
                ref = refs.get_cortical_reference(row.name, "total")
            
            if ref is not None:
                status = ref.get_status(vol.relative_pct)
                if status != "normal":
                    # Highlight the status column
                    style_commands.append(
                        ("TEXTCOLOR", (-1, idx), (-1, idx), colors.HexColor(STATUS_ALERT))
                    )
                    style_commands.append(
                        ("FONTNAME", (-1, idx), (-1, idx), "Helvetica-Bold")
                    )
                else:
                    style_commands.append(
                        ("TEXTCOLOR", (-1, idx), (-1, idx), colors.HexColor(STATUS_NORMAL))
                    )

        return TableStyle(style_commands)

    def _create_logo_header(self) -> Table:
        """Create header with Doctor App logo."""
        logo_cell = []
        if LOGO_PATH.exists():
            try:
                # Logo aspect ratio is ~1.29 (1700x1322), use proportional size
                logo_height = 1.8 * cm
                logo_width = logo_height * 1.29  # Maintain aspect ratio
                logo = Image(str(LOGO_PATH), width=logo_width, height=logo_height)
                logo.hAlign = "LEFT"
                logo_cell.append(logo)
            except Exception as e:
                logger.warning(f"Could not load logo: {e}")
                logo_cell.append(Paragraph("Doctor App", self.styles["ReportTitle"]))
        else:
            logo_cell.append(Paragraph("Doctor App", self.styles["ReportTitle"]))

        title_cell = Paragraph(
            "Reporte de Volumetría Cerebral",
            self.styles["ReportTitle"],
        )

        header_table = Table(
            [[logo_cell[0], title_cell]],
            colWidths=[3.5 * cm, 14 * cm],
        )
        header_table.setStyle(
            TableStyle([
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, 0), "LEFT"),
                ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ])
        )
        return header_table

    def generate(self, data: ReportData) -> bytes:
        """Generate PDF report and return as bytes."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=MARGIN,
            rightMargin=MARGIN,
            topMargin=MARGIN,
            bottomMargin=MARGIN,
        )

        elements: list = []

        # ========== HEADER ==========
        elements.append(self._create_logo_header())
        elements.append(Spacer(1, 0.3 * cm))

        # ========== PATIENT INFO ==========
        elements.append(Paragraph("Información del Paciente", self.styles["SectionHeader"]))
        elements.append(self._create_header_table(data))

        # ========== LEGEND ==========
        elements.append(Spacer(1, 0.4 * cm))
        elements.append(self._create_legend())

        # ========== TISSUE SEGMENTATION ==========
        elements.append(Paragraph("Segmentación de Tejidos", self.styles["SectionHeader"]))
        elements.append(self._create_tissue_table(data.tissue_segmentation))
        elements.append(Spacer(1, 0.2 * cm))
        elements.append(
            Paragraph(
                "* ICV = Volumen Intracraneal. Los porcentajes son relativos al ICV total.",
                self.styles["Note"],
            )
        )

        # ========== MACROSTRUCTURES ==========
        elements.append(Paragraph("Macroestructuras", self.styles["SectionHeader"]))
        elements.append(self._create_structure_table(data.macrostructures, "Estructura", "macro"))
        elements.append(Spacer(1, 0.2 * cm))
        elements.append(
            Paragraph(
                "* Asimetría = (Derecho - Izquierdo) / Promedio × 100. Valores positivos indican mayor volumen derecho.",
                self.styles["Note"],
            )
        )

        # ========== SUBCORTICAL ==========
        elements.append(Paragraph("Estructuras Subcorticales", self.styles["SectionHeader"]))
        elements.append(self._create_structure_table(data.subcortical, "Subcortical", "subcortical"))

        # ========== CORTICAL STRUCTURES ==========
        if data.cortical_frontal:
            elements.append(Paragraph("Estructuras Corticales — Lóbulo Frontal", self.styles["SectionHeader"]))
            elements.append(self._create_structure_table(data.cortical_frontal, "Cortical", "cortical"))

        if data.cortical_parietal:
            elements.append(Paragraph("Estructuras Corticales — Lóbulo Parietal", self.styles["SectionHeader"]))
            elements.append(self._create_structure_table(data.cortical_parietal, "Cortical", "cortical"))

        if data.cortical_temporal:
            elements.append(Paragraph("Estructuras Corticales — Lóbulo Temporal", self.styles["SectionHeader"]))
            elements.append(self._create_structure_table(data.cortical_temporal, "Cortical", "cortical"))

        if data.cortical_occipital:
            elements.append(Paragraph("Estructuras Corticales — Lóbulo Occipital", self.styles["SectionHeader"]))
            elements.append(self._create_structure_table(data.cortical_occipital, "Cortical", "cortical"))

        if data.cortical_cingulate:
            elements.append(Paragraph("Estructuras Corticales — Cíngulo", self.styles["SectionHeader"]))
            elements.append(self._create_structure_table(data.cortical_cingulate, "Cortical", "cortical"))

        if data.cortical_insula:
            elements.append(Paragraph("Estructuras Corticales — Ínsula", self.styles["SectionHeader"]))
            elements.append(self._create_structure_table(data.cortical_insula, "Cortical", "cortical"))

        # ========== FOOTER ==========
        elements.append(Spacer(1, 0.8 * cm))
        elements.append(
            Paragraph(
                f"Generado por Doctor App | {datetime.now().strftime('%d/%m/%Y %H:%M')}",
                self.styles["Footer"],
            )
        )
        elements.append(
            Paragraph(
                "Este reporte es de uso informativo. Los valores de referencia corresponden al percentil 95 de la población. "
                "Consulte a un especialista para interpretación clínica.",
                self.styles["Disclaimer"],
            )
        )

        doc.build(elements)
        return buffer.getvalue()

    def save(self, data: ReportData, output_path: Path) -> None:
        """Generate PDF report and save to file."""
        pdf_bytes = self.generate(data)
        output_path.write_bytes(pdf_bytes)
        logger.info(f"PDF report saved to {output_path}")
