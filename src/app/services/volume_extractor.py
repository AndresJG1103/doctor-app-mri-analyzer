"""Volume extractor service.

Extracts and computes volumetric measures from parsed stats data,
preparing data structures ready for PDF report generation.
"""

import logging
from dataclasses import dataclass, field

from app.services.stats_parser import VolumetryData

logger = logging.getLogger(__name__)


@dataclass
class VolumeValue:
    """A volume measurement with absolute and relative values."""

    absolute_cm3: float  # Volume in cm³
    relative_pct: float  # Percentage relative to ICV


@dataclass
class ReferenceRange:
    """Reference range for a volume measurement (95% confidence interval)."""

    min_pct: float  # Minimum expected percentage
    max_pct: float  # Maximum expected percentage

    def is_within_range(self, value_pct: float) -> bool:
        """Check if value is within normal range."""
        return self.min_pct <= value_pct <= self.max_pct

    def get_status(self, value_pct: float) -> str:
        """Get status: 'normal', 'low', or 'high'."""
        if value_pct < self.min_pct:
            return "low"
        elif value_pct > self.max_pct:
            return "high"
        return "normal"


@dataclass
class StructureRow:
    """A row in the volumetry table with L/R values and references."""

    name: str
    total: VolumeValue | None = None
    right: VolumeValue | None = None
    left: VolumeValue | None = None
    asymmetry_pct: float | None = None
    # Reference ranges (optional)
    ref_total: ReferenceRange | None = None
    ref_right: ReferenceRange | None = None
    ref_left: ReferenceRange | None = None
    ref_asymmetry: ReferenceRange | None = None


@dataclass
class ReportData:
    """All data needed to generate the PDF report."""

    # Header info
    subject_id: str = ""
    sex: str = "Unknown"
    age: int | None = None
    report_date: str = ""
    image_orientation: str = "neurological"
    scale_factor: float | None = None
    snr: float | None = None

    # Tissue segmentation (Page 1)
    tissue_segmentation: list[StructureRow] = field(default_factory=list)

    # Macrostructures (Page 2)
    macrostructures: list[StructureRow] = field(default_factory=list)

    # Subcortical structures (Page 3)
    subcortical: list[StructureRow] = field(default_factory=list)

    # Cortical structures by lobe (Page 4+)
    cortical_frontal: list[StructureRow] = field(default_factory=list)
    cortical_parietal: list[StructureRow] = field(default_factory=list)
    cortical_temporal: list[StructureRow] = field(default_factory=list)
    cortical_occipital: list[StructureRow] = field(default_factory=list)
    cortical_cingulate: list[StructureRow] = field(default_factory=list)
    cortical_insula: list[StructureRow] = field(default_factory=list)

    # ICV for reference
    icv_cm3: float = 0.0


class VolumeExtractor:
    """Extracts and computes report-ready volume data."""

    # DKTatlas region to lobe mapping
    FRONTAL_REGIONS = [
        "superiorfrontal",
        "rostralmiddlefrontal",
        "caudalmiddlefrontal",
        "parsopercularis",
        "parstriangularis",
        "parsorbitalis",
        "lateralorbitofrontal",
        "medialorbitofrontal",
        "precentral",
        "paracentral",
        "frontalpole",
    ]

    PARIETAL_REGIONS = [
        "superiorparietal",
        "inferiorparietal",
        "supramarginal",
        "postcentral",
        "precuneus",
    ]

    TEMPORAL_REGIONS = [
        "superiortemporal",
        "middletemporal",
        "inferiortemporal",
        "bankssts",
        "fusiform",
        "transversetemporal",
        "entorhinal",
        "temporalpole",
        "parahippocampal",
    ]

    OCCIPITAL_REGIONS = [
        "lateraloccipital",
        "lingual",
        "cuneus",
        "pericalcarine",
    ]

    CINGULATE_REGIONS = [
        "rostralanteriorcingulate",
        "caudalanteriorcingulate",
        "posteriorcingulate",
        "isthmuscingulate",
    ]

    INSULA_REGIONS = ["insula"]

    def __init__(self, volumetry_data: VolumetryData) -> None:
        """Initialize with parsed volumetry data."""
        self.data = volumetry_data
        self.icv = volumetry_data.etiv / 1000.0  # Convert mm³ to cm³

    def _mm3_to_cm3(self, mm3: float) -> float:
        """Convert mm³ to cm³."""
        return mm3 / 1000.0

    def _calc_relative(self, vol_cm3: float) -> float:
        """Calculate percentage relative to ICV."""
        if self.icv <= 0:
            return 0.0
        return (vol_cm3 / self.icv) * 100.0

    def _calc_asymmetry(self, right: float, left: float) -> float:
        """Calculate asymmetry index as percentage."""
        mean_vol = (right + left) / 2.0
        if mean_vol <= 0:
            return 0.0
        return ((right - left) / mean_vol) * 100.0

    def _make_volume_value(self, mm3: float) -> VolumeValue:
        """Create VolumeValue from mm³."""
        cm3 = self._mm3_to_cm3(mm3)
        return VolumeValue(absolute_cm3=cm3, relative_pct=self._calc_relative(cm3))

    def _get_subcort_pair(self, left_name: str, right_name: str) -> StructureRow:
        """Get subcortical structure with L/R values."""
        left_vol = 0.0
        right_vol = 0.0

        if left_name in self.data.subcortical:
            left_vol = self.data.subcortical[left_name].volume_mm3
        if right_name in self.data.subcortical:
            right_vol = self.data.subcortical[right_name].volume_mm3

        total = left_vol + right_vol
        base_name = left_name.replace("Left-", "")

        return StructureRow(
            name=base_name,
            total=self._make_volume_value(total),
            right=self._make_volume_value(right_vol),
            left=self._make_volume_value(left_vol),
            asymmetry_pct=self._calc_asymmetry(right_vol, left_vol),
        )

    def _get_cortical_pair(
        self, region_name: str, display_name: str | None = None
    ) -> StructureRow | None:
        """Get cortical region with L/R values."""
        lh_vol = 0.0
        rh_vol = 0.0

        if region_name in self.data.lh_cortical:
            lh_vol = self.data.lh_cortical[region_name].volume_mm3
        if region_name in self.data.rh_cortical:
            rh_vol = self.data.rh_cortical[region_name].volume_mm3

        if lh_vol == 0 and rh_vol == 0:
            return None

        total = lh_vol + rh_vol

        return StructureRow(
            name=display_name or region_name,
            total=self._make_volume_value(total),
            right=self._make_volume_value(rh_vol),
            left=self._make_volume_value(lh_vol),
            asymmetry_pct=self._calc_asymmetry(rh_vol, lh_vol),
        )

    def extract_tissue_segmentation(self) -> list[StructureRow]:
        """Extract tissue segmentation data for Page 1."""
        rows = []

        # White Matter
        wm_total = self.data.cerebral_wm_vol
        rows.append(
            StructureRow(
                name="White Matter (WM)",
                total=self._make_volume_value(wm_total),
            )
        )

        # Normal Appearing WM (same as WM - no lesion segmentation)
        rows.append(
            StructureRow(
                name="Normal Appearing White Matter",
                total=self._make_volume_value(wm_total),
            )
        )

        # Abnormal Appearing WM (not available)
        rows.append(
            StructureRow(
                name="Abnormal Appearing White Matter",
                total=VolumeValue(absolute_cm3=0.0, relative_pct=0.0),
            )
        )

        # Grey Matter
        gm_total = self.data.total_gray_vol
        rows.append(
            StructureRow(
                name="Grey Matter (GM)",
                total=self._make_volume_value(gm_total),
            )
        )

        # Subcortical Grey Matter
        rows.append(
            StructureRow(
                name="Subcortical Grey Matter",
                total=self._make_volume_value(self.data.subcort_gray_vol),
            )
        )

        # Cortical Grey Matter
        rows.append(
            StructureRow(
                name="Cortical Grey Matter",
                total=self._make_volume_value(self.data.cortex_vol),
            )
        )

        # Cerebellar Grey Matter
        cereb_gm = 0.0
        if "Left-Cerebellum-Cortex" in self.data.cerebellar:
            cereb_gm += self.data.cerebellar["Left-Cerebellum-Cortex"].volume_mm3
        if "Right-Cerebellum-Cortex" in self.data.cerebellar:
            cereb_gm += self.data.cerebellar["Right-Cerebellum-Cortex"].volume_mm3
        rows.append(
            StructureRow(
                name="Cerebellar Grey Matter",
                total=self._make_volume_value(cereb_gm),
            )
        )

        # CSF / Ventricles
        rows.append(
            StructureRow(
                name="Cerebro Spinal Fluid (CSF)",
                total=self._make_volume_value(self.data.ventricle_choroid_vol),
            )
        )

        # Brain (WM + GM)
        brain_total = wm_total + gm_total
        rows.append(
            StructureRow(
                name="Brain (WM+GM)",
                total=self._make_volume_value(brain_total),
            )
        )

        # Intracranial Cavity (ICV = eTIV)
        rows.append(
            StructureRow(
                name="Intracranial Cavity (IC)",
                total=VolumeValue(absolute_cm3=self.icv, relative_pct=100.0),
            )
        )

        return rows

    def extract_macrostructures(self) -> list[StructureRow]:
        """Extract macrostructure data for Page 2."""
        rows = []

        # Cerebrum (total cortical + subcortical + WM excluding cerebellum)
        lh_cerebrum = self.data.lh_cortex_vol + self.data.lh_cerebral_wm_vol
        rh_cerebrum = self.data.rh_cortex_vol + self.data.rh_cerebral_wm_vol
        cerebrum_total = lh_cerebrum + rh_cerebrum

        rows.append(
            StructureRow(
                name="Cerebrum",
                total=self._make_volume_value(cerebrum_total),
                right=self._make_volume_value(rh_cerebrum),
                left=self._make_volume_value(lh_cerebrum),
                asymmetry_pct=self._calc_asymmetry(rh_cerebrum, lh_cerebrum),
            )
        )

        # Cerebrum WM
        rows.append(
            StructureRow(
                name="Cerebrum WM",
                total=self._make_volume_value(self.data.cerebral_wm_vol),
                right=self._make_volume_value(self.data.rh_cerebral_wm_vol),
                left=self._make_volume_value(self.data.lh_cerebral_wm_vol),
                asymmetry_pct=self._calc_asymmetry(
                    self.data.rh_cerebral_wm_vol, self.data.lh_cerebral_wm_vol
                ),
            )
        )

        # Cerebrum GM
        rows.append(
            StructureRow(
                name="Cerebrum GM",
                total=self._make_volume_value(self.data.cortex_vol),
                right=self._make_volume_value(self.data.rh_cortex_vol),
                left=self._make_volume_value(self.data.lh_cortex_vol),
                asymmetry_pct=self._calc_asymmetry(
                    self.data.rh_cortex_vol, self.data.lh_cortex_vol
                ),
            )
        )

        # Cerebellum
        lh_cereb = 0.0
        rh_cereb = 0.0
        lh_cereb_wm = 0.0
        rh_cereb_wm = 0.0

        if "Left-Cerebellum-Cortex" in self.data.cerebellar:
            lh_cereb = self.data.cerebellar["Left-Cerebellum-Cortex"].volume_mm3
        if "Right-Cerebellum-Cortex" in self.data.cerebellar:
            rh_cereb = self.data.cerebellar["Right-Cerebellum-Cortex"].volume_mm3
        if "Left-Cerebellum-White-Matter" in self.data.cerebellar:
            lh_cereb_wm = self.data.cerebellar["Left-Cerebellum-White-Matter"].volume_mm3
        if "Right-Cerebellum-White-Matter" in self.data.cerebellar:
            rh_cereb_wm = self.data.cerebellar["Right-Cerebellum-White-Matter"].volume_mm3

        lh_cereb_total = lh_cereb + lh_cereb_wm
        rh_cereb_total = rh_cereb + rh_cereb_wm
        cereb_total = lh_cereb_total + rh_cereb_total

        rows.append(
            StructureRow(
                name="Cerebellum",
                total=self._make_volume_value(cereb_total),
                right=self._make_volume_value(rh_cereb_total),
                left=self._make_volume_value(lh_cereb_total),
                asymmetry_pct=self._calc_asymmetry(rh_cereb_total, lh_cereb_total),
            )
        )

        # Cerebellum WM
        cereb_wm_total = lh_cereb_wm + rh_cereb_wm
        rows.append(
            StructureRow(
                name="Cerebellum WM",
                total=self._make_volume_value(cereb_wm_total),
                right=self._make_volume_value(rh_cereb_wm),
                left=self._make_volume_value(lh_cereb_wm),
                asymmetry_pct=self._calc_asymmetry(rh_cereb_wm, lh_cereb_wm),
            )
        )

        # Cerebellum GM
        cereb_gm_total = lh_cereb + rh_cereb
        rows.append(
            StructureRow(
                name="Cerebellum GM",
                total=self._make_volume_value(cereb_gm_total),
                right=self._make_volume_value(rh_cereb),
                left=self._make_volume_value(lh_cereb),
                asymmetry_pct=self._calc_asymmetry(rh_cereb, lh_cereb),
            )
        )

        # Vermis
        vermis_vol = 0.0
        if "Vermis" in self.data.cerebellar:
            vermis_vol = self.data.cerebellar["Vermis"].volume_mm3
        rows.append(
            StructureRow(
                name="Vermis",
                total=self._make_volume_value(vermis_vol),
            )
        )

        # Brainstem
        rows.append(
            StructureRow(
                name="Brainstem",
                total=self._make_volume_value(self.data.brainstem_vol),
            )
        )

        return rows

    def extract_subcortical(self) -> list[StructureRow]:
        """Extract subcortical structure data for Page 3."""
        rows = []

        structure_pairs = [
            ("Left-Accumbens-area", "Right-Accumbens-area", "Accumbens"),
            ("Left-Amygdala", "Right-Amygdala", "Amygdala"),
            ("Left-Caudate", "Right-Caudate", "Caudate"),
            ("Left-Hippocampus", "Right-Hippocampus", "Hippocampus"),
            ("Left-Pallidum", "Right-Pallidum", "Pallidum"),
            ("Left-Putamen", "Right-Putamen", "Putamen"),
            ("Left-Thalamus", "Right-Thalamus", "Thalamus"),
            ("Left-VentralDC", "Right-VentralDC", "Ventral DC"),
        ]

        for left_name, right_name, display_name in structure_pairs:
            row = self._get_subcort_pair(left_name, right_name)
            row.name = display_name
            rows.append(row)

        return rows

    def extract_cortical_by_lobe(
        self, regions: list[str], display_names: dict[str, str] | None = None
    ) -> list[StructureRow]:
        """Extract cortical regions for a specific lobe."""
        rows = []
        display_names = display_names or {}

        for region in regions:
            display = display_names.get(region, region)
            row = self._get_cortical_pair(region, display)
            if row:
                rows.append(row)

        return rows

    def extract_all(self, subject_id: str = "", report_date: str = "") -> ReportData:
        """Extract all data needed for the PDF report."""
        report = ReportData(
            subject_id=subject_id,
            report_date=report_date,
            icv_cm3=self.icv,
        )

        report.tissue_segmentation = self.extract_tissue_segmentation()
        report.macrostructures = self.extract_macrostructures()
        report.subcortical = self.extract_subcortical()

        # Cortical regions by lobe
        report.cortical_frontal = self.extract_cortical_by_lobe(self.FRONTAL_REGIONS)
        report.cortical_parietal = self.extract_cortical_by_lobe(self.PARIETAL_REGIONS)
        report.cortical_temporal = self.extract_cortical_by_lobe(self.TEMPORAL_REGIONS)
        report.cortical_occipital = self.extract_cortical_by_lobe(self.OCCIPITAL_REGIONS)
        report.cortical_cingulate = self.extract_cortical_by_lobe(self.CINGULATE_REGIONS)
        report.cortical_insula = self.extract_cortical_by_lobe(self.INSULA_REGIONS)

        return report
