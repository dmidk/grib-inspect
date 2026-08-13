# GRIB-inspect

A CLI tool to scan GRIB2 files into an appendable SQLite report, and compare
reports to see exactly what changed between two model runs, cycles, or
post-processing tools.

## Install

```bash
uv sync
```

## Usage

Scan a file into a report (`--model` is a free-text label for the source):

```bash
uv run grib-inspect scan fc2026081200+003_sf.grib2 --db-out cy43h.sqlite --model cy43h
```

Append more files to the same report under the same model, e.g. to merge
Cy43h's split SF/ML/PL files into one report comparable to Cy46h's combined
output:

```bash
uv run grib-inspect scan fc2026081200+003_ml.grib2 --db-out cy43h.sqlite --model cy43h
uv run grib-inspect scan fc2026081200+003_pl.grib2 --db-out cy43h.sqlite --model cy43h
```

Scan the other side:

```bash
uv run grib-inspect scan fc2026081200+003.grib2 --db-out cy46h.sqlite --model cy46h
```

Compare the two reports:

```bash
uv run grib-inspect compare cy43h.sqlite cy46h.sqlite
```

Or compare two models stored in the same report db:

```bash
uv run grib-inspect scan other_run.grib2 --db-out combined.sqlite --model cy46h
uv run grib-inspect compare combined.sqlite combined.sqlite --model-a cy43h --model-b cy46h
```

Output shows identical, only-in-A, only-in-B, and differing messages (with
the specific GRIB keys that changed), matched by variable identity
(`shortName`, `typeOfLevel`, `level`, `stepRange` by default).

### Tuning what gets recorded

```bash
# custom identity (what counts as "the same variable")
uv run grib-inspect scan file.grib2 --db-out report.sqlite --model x \
  --identity-keys shortName,typeOfLevel,level

# custom metadata/encoding keys to capture
uv run grib-inspect scan file.grib2 --db-out report.sqlite --model x \
  --keys packingType,bitsPerValue,gridType

# free-form tags, e.g. to record which part of a split run this came from
uv run grib-inspect scan file_sf.grib2 --db-out report.sqlite --model cy43h --tag part=sf
```
