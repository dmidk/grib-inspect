# GRIB-inspect

A CLI tool to scan GRIB2 files into an appendable SQLite report, and compare
reports to see exactly what changed between two model runs, cycles, or post-processing tools.

## Install

```bash
uv sync
```

## Usage

Scan a file into a report (`--model` is a free-text label for the source):

```bash
uv run grib-inspect scan <grib_file> --db-out out.sqlite --model <model_label>
```

Append more files to the same report under the same model, e.g. to merge
several split output files into one report comparable to a single
combined-file report:

```bash
uv run grib-inspect scan <grib_file_1> --db-out out_1.sqlite --model model_1
uv run grib-inspect scan <grib_file_2> --db-out out_1.sqlite --model model_1
uv run grib-inspect scan <grib_file_3> --db-out out_1.sqlite --model model_1
```

Scan the other side:

```bash
uv run grib-inspect scan <grib_file> --db-out out_2.sqlite --model model_2
```

Compare the two reports:

```bash
uv run grib-inspect compare out_1.sqlite out_2.sqlite
```

Or compare two models stored in the same report db:

```bash
uv run grib-inspect scan <grib_file_1> --db-out combined.sqlite --model model_1
uv run grib-inspect scan <grib_file_2> --db-out combined.sqlite --model model_2
uv run grib-inspect compare combined.sqlite combined.sqlite --model-a model_1 --model-b model_2
```

Output shows identical, only-in-A, only-in-B, and differing messages (with
the specific GRIB keys that changed), matched by variable identity
(`discipline`, `parameterCategory`, `parameterNumber`, `typeOfLevel`,
`level`, `stepRange` by default -- the WMO GRIB2 parameter definition, not
the eccodes-derived `shortName`, which can vary across tools/versions).

Add `--html <report.html>` to also write a self-contained HTML diff table
(identity + changed keys, color-coded by only-in-A / only-in-B / differs):

```bash
uv run grib-inspect compare out_1.sqlite out_2.sqlite --html diff.html
```

### Tuning what gets recorded

```bash
# custom identity (what counts as "the same variable")
uv run grib-inspect scan <grib_file> --db-out out.sqlite --model <model_label> \
  --identity-keys discipline,parameterCategory,parameterNumber,typeOfLevel,level

# custom metadata/encoding keys to capture
uv run grib-inspect scan <grib_file> --db-out out.sqlite --model <model_label> \
  --keys packingType,bitsPerValue,gridType

# free-form tags, e.g. to record which part of a split run this came from
uv run grib-inspect scan <sf_file> --db-out out.sqlite --model model_1 --tag part=sf
```
