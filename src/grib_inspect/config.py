"""Default GRIB key sets. Override per scan with --identity-keys / --keys."""

from __future__ import annotations

# Identity: what makes two messages across different files/products "the same variable".
# discipline+parameterCategory+parameterNumber is the WMO GRIB2 parameter definition
# (Table 4.2) -- the actual, tool-independent identity of a field. shortName is an
# eccodes-derived alias layered on top of that and is deliberately excluded here: it
# can vary across eccodes/definitions versions even when the underlying parameter is
# identical (kept in DEFAULT_METADATA_KEYS below for display).
DEFAULT_IDENTITY_KEYS = [
    "discipline",
    "parameterCategory",
    "parameterNumber",
    "typeOfLevel",
    "level",
    "stepRange",
    "typeOfStatisticalProcessing",
]

# Encoding/metadata keys worth reporting on. Not exhaustive by design
# (v1: metadata only, no data values) -- extend with --keys if a comparison needs more.
DEFAULT_METADATA_KEYS = [
    "shortName",
    "name",
    "units",
    "paramId",
    "editionNumber",
    "centre",
    "subCentre",
    "generatingProcessIdentifier",
    "typeOfGeneratingProcess",
    "gridType",
    "gridDefinitionTemplateNumber",
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
]
