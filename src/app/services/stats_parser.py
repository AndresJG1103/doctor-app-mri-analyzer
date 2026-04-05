"""FreeSurfer/FastSurfer stats file parser.

Parses various stats files from FreeSurfer/FastSurfer output to extract
volumetric measurements for the PDF report.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StructureVolume:
    """Volume measurement for a brain structure."""

    name: str
    volume_mm3: float
    nvoxels: int = 0
    # For cortical structures
    surface_area: float = 0.0
    thickness_avg: float = 0.0
    thickness_std: float = 0.0


@dataclass
class VolumetryData:
    """All volumetric data extracted from stats files."""

    # Global measures
    etiv: float = 0.0  # Estimated Total Intracranial Volume
    brain_seg_vol: float = 0.0
    brain_seg_vol_no_vent: float = 0.0
    cortex_vol: float = 0.0
    cerebral_wm_vol: float = 0.0
    subcort_gray_vol: float = 0.0
    total_gray_vol: float = 0.0
    supratentorial_vol: float = 0.0
    ventricle_choroid_vol: float = 0.0
    mask_vol: float = 0.0

    # Hemisphere-specific
    lh_cortex_vol: float = 0.0
    rh_cortex_vol: float = 0.0
    lh_cerebral_wm_vol: float = 0.0
    rh_cerebral_wm_vol: float = 0.0

    # Subcortical structures (indexed by structure name)
    subcortical: dict[str, StructureVolume] = field(default_factory=dict)

    # Cerebellar structures
    cerebellar: dict[str, StructureVolume] = field(default_factory=dict)

    # Cortical regions (from aparc stats)
    lh_cortical: dict[str, StructureVolume] = field(default_factory=dict)
    rh_cortical: dict[str, StructureVolume] = field(default_factory=dict)

    # Brainstem
    brainstem_vol: float = 0.0

    # Corpus Callosum segments
    cc_posterior: float = 0.0
    cc_mid_posterior: float = 0.0
    cc_central: float = 0.0
    cc_mid_anterior: float = 0.0
    cc_anterior: float = 0.0


class StatsParser:
    """Parser for FreeSurfer/FastSurfer stats files."""

    # Mapping of structure SegIds to names for aseg.stats
    ASEG_STRUCTURE_IDS: dict[int, str] = {
        4: "Left-Lateral-Ventricle",
        5: "Left-Inf-Lat-Vent",
        7: "Left-Cerebellum-White-Matter",
        8: "Left-Cerebellum-Cortex",
        10: "Left-Thalamus",
        11: "Left-Caudate",
        12: "Left-Putamen",
        13: "Left-Pallidum",
        14: "3rd-Ventricle",
        15: "4th-Ventricle",
        16: "Brain-Stem",
        17: "Left-Hippocampus",
        18: "Left-Amygdala",
        24: "CSF",
        26: "Left-Accumbens-area",
        28: "Left-VentralDC",
        31: "Left-choroid-plexus",
        43: "Right-Lateral-Ventricle",
        44: "Right-Inf-Lat-Vent",
        46: "Right-Cerebellum-White-Matter",
        47: "Right-Cerebellum-Cortex",
        49: "Right-Thalamus",
        50: "Right-Caudate",
        51: "Right-Putamen",
        52: "Right-Pallidum",
        53: "Right-Hippocampus",
        54: "Right-Amygdala",
        58: "Right-Accumbens-area",
        60: "Right-VentralDC",
        63: "Right-choroid-plexus",
        77: "WM-hypointensities",
        251: "CC_Posterior",
        252: "CC_Mid_Posterior",
        253: "CC_Central",
        254: "CC_Mid_Anterior",
        255: "CC_Anterior",
    }

    def __init__(self, stats_dir: str | Path) -> None:
        """Initialize parser with stats directory path."""
        self.stats_dir = Path(stats_dir)

    def parse_measure_line(self, line: str) -> tuple[str, float] | None:
        """Parse a # Measure line from stats file.

        Example: # Measure BrainSeg, BrainSegVol, Brain Segmentation Volume, 1628478.211642, mm^3
        """
        match = re.match(
            r"#\s*Measure\s+(\w+),\s*(\w+),\s*([^,]+),\s*([\d.]+),\s*(\S+)",
            line.strip(),
        )
        if match:
            measure_name = match.group(1)
            value = float(match.group(4))
            return measure_name, value
        return None

    def parse_aseg_stats(self) -> dict[str, Any]:
        """Parse aseg.stats file for global and subcortical volumes."""
        aseg_file = self.stats_dir / "aseg.stats"
        if not aseg_file.exists():
            logger.warning(f"aseg.stats not found at {aseg_file}")
            return {}

        measures: dict[str, float] = {}
        structures: dict[int, dict[str, Any]] = {}

        with open(aseg_file, "r") as f:
            for line in f:
                line = line.strip()

                # Parse measure lines
                if line.startswith("# Measure"):
                    result = self.parse_measure_line(line)
                    if result:
                        measures[result[0]] = result[1]

                # Parse structure data lines (non-comment lines with data)
                elif line and not line.startswith("#"):
                    parts = line.split()
                    if len(parts) >= 5:
                        try:
                            seg_id = int(parts[1])
                            nvoxels = int(parts[2])
                            volume = float(parts[3])
                            name = parts[4]
                            structures[seg_id] = {
                                "name": name,
                                "nvoxels": nvoxels,
                                "volume_mm3": volume,
                            }
                        except (ValueError, IndexError):
                            continue

        return {"measures": measures, "structures": structures}

    def parse_aparc_stats(self, hemisphere: str) -> dict[str, StructureVolume]:
        """Parse aparc.DKTatlas.mapped.stats for cortical regions."""
        filename = f"{hemisphere}.aparc.DKTatlas.mapped.stats"
        stats_file = self.stats_dir / filename

        if not stats_file.exists():
            logger.warning(f"{filename} not found at {stats_file}")
            return {}

        regions: dict[str, StructureVolume] = {}

        with open(stats_file, "r") as f:
            for line in f:
                line = line.strip()

                # Skip comments
                if line.startswith("#") or not line:
                    continue

                # Parse data line
                # Format: StructName NumVert SurfArea GrayVol ThickAvg ThickStd ...
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        name = parts[0]
                        num_vert = int(parts[1])
                        surf_area = float(parts[2])
                        gray_vol = float(parts[3])
                        thick_avg = float(parts[4])
                        thick_std = float(parts[5])

                        regions[name] = StructureVolume(
                            name=name,
                            volume_mm3=gray_vol,
                            nvoxels=num_vert,
                            surface_area=surf_area,
                            thickness_avg=thick_avg,
                            thickness_std=thick_std,
                        )
                    except (ValueError, IndexError):
                        continue

        return regions

    def parse_cerebellum_stats(self) -> dict[str, StructureVolume]:
        """Parse cerebellum.CerebNet.stats for cerebellar volumes."""
        stats_file = self.stats_dir / "cerebellum.CerebNet.stats"

        if not stats_file.exists():
            logger.warning(f"cerebellum.CerebNet.stats not found at {stats_file}")
            return {}

        structures: dict[str, StructureVolume] = {}

        with open(stats_file, "r") as f:
            for line in f:
                line = line.strip()

                if line.startswith("#") or not line:
                    continue

                parts = line.split()
                if len(parts) >= 5:
                    try:
                        _seg_id = int(parts[1])  # noqa: F841
                        nvoxels = int(parts[2])
                        volume = float(parts[3])
                        name = parts[4]

                        structures[name] = StructureVolume(
                            name=name,
                            volume_mm3=volume,
                            nvoxels=nvoxels,
                        )
                    except (ValueError, IndexError):
                        continue

        return structures

    def parse_all(self) -> VolumetryData:
        """Parse all stats files and return VolumetryData."""
        data = VolumetryData()

        # Parse aseg.stats
        aseg = self.parse_aseg_stats()
        if aseg:
            measures = aseg.get("measures", {})
            structures = aseg.get("structures", {})

            # Global measures
            data.etiv = measures.get("EstimatedTotalIntraCranialVol", 0.0)
            data.brain_seg_vol = measures.get("BrainSeg", 0.0)
            data.brain_seg_vol_no_vent = measures.get("BrainSegNotVent", 0.0)
            data.cortex_vol = measures.get("Cortex", 0.0)
            data.cerebral_wm_vol = measures.get("CerebralWhiteMatter", 0.0)
            data.subcort_gray_vol = measures.get("SubCortGray", 0.0)
            data.total_gray_vol = measures.get("TotalGray", 0.0)
            data.supratentorial_vol = measures.get("SupraTentorial", 0.0)
            data.ventricle_choroid_vol = measures.get("VentricleChoroidVol", 0.0)
            data.mask_vol = measures.get("Mask", 0.0)

            # Hemisphere-specific
            data.lh_cortex_vol = measures.get("lhCortex", 0.0)
            data.rh_cortex_vol = measures.get("rhCortex", 0.0)
            data.lh_cerebral_wm_vol = measures.get("lhCerebralWhiteMatter", 0.0)
            data.rh_cerebral_wm_vol = measures.get("rhCerebralWhiteMatter", 0.0)

            # Extract subcortical structures
            subcort_ids = [10, 11, 12, 13, 17, 18, 26, 28, 49, 50, 51, 52, 53, 54, 58, 60]
            for seg_id in subcort_ids:
                if seg_id in structures:
                    s = structures[seg_id]
                    data.subcortical[s["name"]] = StructureVolume(
                        name=s["name"],
                        volume_mm3=s["volume_mm3"],
                        nvoxels=s["nvoxels"],
                    )

            # Cerebellar from aseg (basic)
            for seg_id in [7, 8, 46, 47]:
                if seg_id in structures:
                    s = structures[seg_id]
                    data.cerebellar[s["name"]] = StructureVolume(
                        name=s["name"],
                        volume_mm3=s["volume_mm3"],
                        nvoxels=s["nvoxels"],
                    )

            # Brainstem
            if 16 in structures:
                data.brainstem_vol = structures[16]["volume_mm3"]

            # Corpus Callosum
            if 251 in structures:
                data.cc_posterior = structures[251]["volume_mm3"]
            if 252 in structures:
                data.cc_mid_posterior = structures[252]["volume_mm3"]
            if 253 in structures:
                data.cc_central = structures[253]["volume_mm3"]
            if 254 in structures:
                data.cc_mid_anterior = structures[254]["volume_mm3"]
            if 255 in structures:
                data.cc_anterior = structures[255]["volume_mm3"]

        # Parse cortical stats
        data.lh_cortical = self.parse_aparc_stats("lh")
        data.rh_cortical = self.parse_aparc_stats("rh")

        # Parse detailed cerebellum
        cereb_detailed = self.parse_cerebellum_stats()
        if cereb_detailed:
            # Add vermis if not already present
            if "Cbm_Vermis" in cereb_detailed:
                data.cerebellar["Vermis"] = cereb_detailed["Cbm_Vermis"]

        return data


# Global parser instance creator
def create_stats_parser(subject_dir: str | Path) -> StatsParser:
    """Create a stats parser for a subject directory."""
    return StatsParser(subject_dir)
