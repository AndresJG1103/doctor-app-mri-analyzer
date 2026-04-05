"""Reference values for brain volumetry.

These values represent the 95% confidence intervals for normalized
brain volumes based on sex and age. Values are expressed as percentages
of the intracranial volume (ICV).

Based on normative data from brain volumetry studies.
"""

from app.services.volume_extractor import ReferenceRange

# =============================================================================
# TISSUE SEGMENTATION REFERENCES (% of ICV)
# =============================================================================
TISSUE_REFERENCES: dict[str, ReferenceRange] = {
    "White Matter (WM)": ReferenceRange(min_pct=30.0, max_pct=41.0),
    "Normal Appearing White Matter": ReferenceRange(min_pct=30.0, max_pct=41.0),
    "Abnormal Appearing White Matter": ReferenceRange(min_pct=0.0, max_pct=0.5),
    "Grey Matter (GM)": ReferenceRange(min_pct=52.0, max_pct=60.0),
    "Subcortical Grey Matter": ReferenceRange(min_pct=2.9, max_pct=3.7),
    "Cortical Grey Matter": ReferenceRange(min_pct=41.0, max_pct=48.0),
    "Cerebellar Grey Matter": ReferenceRange(min_pct=6.7, max_pct=9.4),
    "Cerebro Spinal Fluid (CSF)": ReferenceRange(min_pct=2.3, max_pct=11.5),
    "Brain (WM+GM)": ReferenceRange(min_pct=87.0, max_pct=96.0),
    "Intracranial Cavity (IC)": ReferenceRange(min_pct=100.0, max_pct=100.0),
}

# =============================================================================
# MACROSTRUCTURE REFERENCES (% of ICV)
# =============================================================================
MACRO_REFERENCES: dict[str, dict[str, ReferenceRange]] = {
    "Cerebrum": {
        "total": ReferenceRange(min_pct=77.0, max_pct=86.0),
        "right": ReferenceRange(min_pct=38.5, max_pct=43.0),
        "left": ReferenceRange(min_pct=38.5, max_pct=43.0),
        "asymmetry": ReferenceRange(min_pct=-2.2, max_pct=1.9),
    },
    "Cerebrum WM": {
        "total": ReferenceRange(min_pct=28.5, max_pct=38.5),
        "right": ReferenceRange(min_pct=14.2, max_pct=19.3),
        "left": ReferenceRange(min_pct=14.2, max_pct=19.3),
        "asymmetry": ReferenceRange(min_pct=-2.4, max_pct=2.5),
    },
    "Cerebrum GM": {
        "total": ReferenceRange(min_pct=44.3, max_pct=51.7),
        "right": ReferenceRange(min_pct=22.1, max_pct=25.9),
        "left": ReferenceRange(min_pct=22.2, max_pct=25.9),
        "asymmetry": ReferenceRange(min_pct=-2.4, max_pct=1.9),
    },
    "Cerebellum": {
        "total": ReferenceRange(min_pct=8.1, max_pct=11.0),
        "right": ReferenceRange(min_pct=4.1, max_pct=5.5),
        "left": ReferenceRange(min_pct=4.0, max_pct=5.5),
        "asymmetry": ReferenceRange(min_pct=-2.8, max_pct=4.1),
    },
    "Cerebellum WM": {
        "total": ReferenceRange(min_pct=1.6, max_pct=2.8),
        "right": ReferenceRange(min_pct=0.8, max_pct=1.4),
        "left": ReferenceRange(min_pct=0.8, max_pct=1.4),
        "asymmetry": ReferenceRange(min_pct=-3.9, max_pct=8.6),
    },
    "Cerebellum GM": {
        "total": ReferenceRange(min_pct=6.7, max_pct=9.4),
        "right": ReferenceRange(min_pct=3.1, max_pct=4.3),
        "left": ReferenceRange(min_pct=3.1, max_pct=4.3),
        "asymmetry": ReferenceRange(min_pct=-4.0, max_pct=4.5),
    },
    "Vermis": {
        "total": ReferenceRange(min_pct=0.5, max_pct=0.8),
    },
    "Brainstem": {
        "total": ReferenceRange(min_pct=1.1, max_pct=1.6),
    },
}

# =============================================================================
# SUBCORTICAL STRUCTURE REFERENCES (% of ICV)
# =============================================================================
SUBCORTICAL_REFERENCES: dict[str, dict[str, ReferenceRange]] = {
    "Accumbens": {
        "total": ReferenceRange(min_pct=0.034, max_pct=0.066),
        "right": ReferenceRange(min_pct=0.014, max_pct=0.032),
        "left": ReferenceRange(min_pct=0.018, max_pct=0.035),
        "asymmetry": ReferenceRange(min_pct=-42.0, max_pct=10.0),
    },
    "Amygdala": {
        "total": ReferenceRange(min_pct=0.10, max_pct=0.16),
        "right": ReferenceRange(min_pct=0.051, max_pct=0.081),
        "left": ReferenceRange(min_pct=0.047, max_pct=0.080),
        "asymmetry": ReferenceRange(min_pct=-9.0, max_pct=19.0),
    },
    "Caudate": {
        "total": ReferenceRange(min_pct=0.52, max_pct=0.75),
        "right": ReferenceRange(min_pct=0.26, max_pct=0.38),
        "left": ReferenceRange(min_pct=0.25, max_pct=0.38),
        "asymmetry": ReferenceRange(min_pct=-8.6, max_pct=15.0),
    },
    "Hippocampus": {
        "total": ReferenceRange(min_pct=0.46, max_pct=0.66),
        "right": ReferenceRange(min_pct=0.24, max_pct=0.33),
        "left": ReferenceRange(min_pct=0.22, max_pct=0.33),
        "asymmetry": ReferenceRange(min_pct=-6.3, max_pct=15.0),
    },
    "Pallidum": {
        "total": ReferenceRange(min_pct=0.17, max_pct=0.27),
        "right": ReferenceRange(min_pct=0.08, max_pct=0.13),
        "left": ReferenceRange(min_pct=0.09, max_pct=0.14),
        "asymmetry": ReferenceRange(min_pct=-22.0, max_pct=3.2),
    },
    "Putamen": {
        "total": ReferenceRange(min_pct=0.59, max_pct=0.84),
        "right": ReferenceRange(min_pct=0.29, max_pct=0.42),
        "left": ReferenceRange(min_pct=0.30, max_pct=0.42),
        "asymmetry": ReferenceRange(min_pct=-7.6, max_pct=7.3),
    },
    "Thalamus": {
        "total": ReferenceRange(min_pct=0.83, max_pct=1.11),
        "right": ReferenceRange(min_pct=0.41, max_pct=0.54),
        "left": ReferenceRange(min_pct=0.42, max_pct=0.57),
        "asymmetry": ReferenceRange(min_pct=-10.4, max_pct=3.6),
    },
    "Ventral DC": {
        "total": ReferenceRange(min_pct=0.60, max_pct=0.80),
        "right": ReferenceRange(min_pct=0.30, max_pct=0.40),
        "left": ReferenceRange(min_pct=0.30, max_pct=0.41),
        "asymmetry": ReferenceRange(min_pct=-6.6, max_pct=2.2),
    },
}

# =============================================================================
# CORTICAL LOBE REFERENCES (% of ICV)
# =============================================================================
CORTICAL_REFERENCES: dict[str, dict[str, ReferenceRange]] = {
    # Frontal Lobe
    "Frontal lobe": {
        "total": ReferenceRange(min_pct=14.5, max_pct=17.3),
        "asymmetry": ReferenceRange(min_pct=-5.2, max_pct=4.5),
    },
    "superiorfrontal": {
        "total": ReferenceRange(min_pct=2.3, max_pct=3.0),
        "asymmetry": ReferenceRange(min_pct=-15.5, max_pct=21.0),
    },
    "rostralmiddlefrontal": {
        "total": ReferenceRange(min_pct=1.5, max_pct=2.0),
        "asymmetry": ReferenceRange(min_pct=-14.0, max_pct=14.0),
    },
    "caudalmiddlefrontal": {
        "total": ReferenceRange(min_pct=0.5, max_pct=0.8),
        "asymmetry": ReferenceRange(min_pct=-15.0, max_pct=15.0),
    },
    "precentral": {
        "total": ReferenceRange(min_pct=1.9, max_pct=2.5),
        "asymmetry": ReferenceRange(min_pct=-15.0, max_pct=14.0),
    },
    # Parietal Lobe
    "superiorparietal": {
        "total": ReferenceRange(min_pct=1.5, max_pct=2.0),
        "asymmetry": ReferenceRange(min_pct=-10.0, max_pct=10.0),
    },
    "inferiorparietal": {
        "total": ReferenceRange(min_pct=1.3, max_pct=1.8),
        "asymmetry": ReferenceRange(min_pct=-10.0, max_pct=10.0),
    },
    "postcentral": {
        "total": ReferenceRange(min_pct=1.0, max_pct=1.4),
        "asymmetry": ReferenceRange(min_pct=-12.0, max_pct=12.0),
    },
    "precuneus": {
        "total": ReferenceRange(min_pct=1.0, max_pct=1.4),
        "asymmetry": ReferenceRange(min_pct=-10.0, max_pct=10.0),
    },
    # Temporal Lobe
    "superiortemporal": {
        "total": ReferenceRange(min_pct=1.1, max_pct=1.5),
        "asymmetry": ReferenceRange(min_pct=-10.0, max_pct=15.0),
    },
    "middletemporal": {
        "total": ReferenceRange(min_pct=1.0, max_pct=1.4),
        "asymmetry": ReferenceRange(min_pct=-10.0, max_pct=10.0),
    },
    "inferiortemporal": {
        "total": ReferenceRange(min_pct=0.8, max_pct=1.2),
        "asymmetry": ReferenceRange(min_pct=-10.0, max_pct=10.0),
    },
    "fusiform": {
        "total": ReferenceRange(min_pct=0.8, max_pct=1.1),
        "asymmetry": ReferenceRange(min_pct=-10.0, max_pct=10.0),
    },
    "hippocampus": {
        "total": ReferenceRange(min_pct=0.46, max_pct=0.66),
        "asymmetry": ReferenceRange(min_pct=-6.3, max_pct=15.0),
    },
    # Occipital Lobe
    "lateraloccipital": {
        "total": ReferenceRange(min_pct=1.2, max_pct=1.6),
        "asymmetry": ReferenceRange(min_pct=-10.0, max_pct=10.0),
    },
    "lingual": {
        "total": ReferenceRange(min_pct=0.7, max_pct=1.0),
        "asymmetry": ReferenceRange(min_pct=-10.0, max_pct=10.0),
    },
    "cuneus": {
        "total": ReferenceRange(min_pct=0.4, max_pct=0.6),
        "asymmetry": ReferenceRange(min_pct=-15.0, max_pct=15.0),
    },
    # Insula
    "insula": {
        "total": ReferenceRange(min_pct=0.8, max_pct=1.1),
        "asymmetry": ReferenceRange(min_pct=-10.0, max_pct=10.0),
    },
}


def get_tissue_reference(structure_name: str) -> ReferenceRange | None:
    """Get reference range for a tissue structure."""
    return TISSUE_REFERENCES.get(structure_name)


def get_macro_reference(structure_name: str, field: str = "total") -> ReferenceRange | None:
    """Get reference range for a macrostructure."""
    refs = MACRO_REFERENCES.get(structure_name, {})
    return refs.get(field)


def get_subcortical_reference(structure_name: str, field: str = "total") -> ReferenceRange | None:
    """Get reference range for a subcortical structure."""
    refs = SUBCORTICAL_REFERENCES.get(structure_name, {})
    return refs.get(field)


def get_cortical_reference(region_name: str, field: str = "total") -> ReferenceRange | None:
    """Get reference range for a cortical region."""
    refs = CORTICAL_REFERENCES.get(region_name, {})
    return refs.get(field)
