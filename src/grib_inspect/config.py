"""Default GRIB key sets. Override per scan with --identity-keys / --keys."""

from __future__ import annotations

# Identity: what makes two messages across different files/products "the same variable".
DEFAULT_IDENTITY_KEYS = ["shortName", "typeOfLevel", "level", "stepRange"]

# Encoding/metadata keys worth reporting on. Not exhaustive by design
# (v1: metadata only, no data values) -- extend with --keys if a comparison needs more.
DEFAULT_METADATA_KEYS = [
    "discipline",
    "parameterCategory",
    "parameterNumber",
    "typeOfStatisticalProcessing",
    "name",
    "units",
    "paramId",
    "editionNumber",
    "centre",
    "subCentre",
    "generatingProcessIdentifier",
    "typeOfGeneratingProcess",
    "dataDate",
    "dataTime",
    "gridType",
    "Ni",
    "Nj",
    "packingType",
    "bitsPerValue",
    "numberOfValues",
    "missingValue",
    "typeOfFirstFixedSurface",
    "typeOfSecondFixedSurface",
    "scaleFactorOfFirstFixedSurface",
    "scaledValueOfFirstFixedSurface",
    "productDefinitionTemplateNumber",
    "stepType",
    "stepUnits",
    "stepRange",
]
