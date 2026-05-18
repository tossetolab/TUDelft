# plateau2cityjson

A Python converter from PLATEAU CityGML (Japan's national 3D city model) to CityJSON 1.1 / 2.0.

The converter handles single files, entire folders, and folder merges. It supports CRS reprojection, auto-detects the i-UR namespace version across PLATEAU releases, and emits a companion CityJSON Extension schema (`plateau-iur.ext.json`) that formally declares all PLATEAU / i-UR attributes.

---

## Requirements

| Package | Purpose |
|---|---|
| `lxml` | Fast GML / XML parsing |
| `pyproj` | CRS detection and coordinate reprojection |

```bash
pip install lxml pyproj
```

Python 3.10 or later is required (uses `int | None` union syntax).

---

## Quick Start

```bash
# Single file — keep original CRS (EPSG:6697), CityJSON 2.0
python plateau_citygml2cityjson.py 53394509_bldg_6697_op.gml --cityjson-version 2.0

# Folder batch — reproject to Japan Plane Rectangular IX (Tokyo)
python plateau_citygml2cityjson.py udx/bldg/ --epsg 6677

# Folder merge — all tiles into one file, CityJSON 2.0
python plateau_citygml2cityjson.py udx/bldg/ --merge --cityjson-version 2.0 --epsg 6677
```

---

## Usage

```
python plateau_citygml2cityjson.py <input> [options]
```

`<input>` is either a `.gml` file (single conversion) or a directory (batch conversion).

### Options

| Option | Default | Description |
|---|---|---|
| `-o`, `--output` | auto | Output path. For a file input this is a `.city.json` file; for a directory input this is an output directory (or a merged file when `--merge` is set). |
| `-p`, `--pattern` | `*.gml` | Glob pattern used when scanning a directory for GML files. |
| `--merge` | off | Merge all tiles in a directory into a single `.city.json` file instead of converting each tile separately. |
| `--epsg CODE` | source CRS | EPSG code of the output coordinate system. Common values: `6677` (Japan Plane Rectangular IX — Tokyo), `6676` (VIII), `4326` (WGS 84 geographic). Omit to keep the source CRS (usually EPSG:6697). |
| `--cityjson-version` | `1.1` | CityJSON output version: `1.1` or `2.0`. |
| `--compact` | off | Write a single-line compact JSON (no whitespace). By default, a **hybrid** format is used (see [Output Format](#output-format)). |
| `--no-extension` | off | Skip generation of the `plateau-iur.ext.json` Extension schema and omit the `"extensions"` member from the output. |

---

## Input: PLATEAU CityGML

The converter targets the **building** (`bldg:Building`) layer of PLATEAU CityGML datasets.

- **Supported i-UR versions**: 3.1, 3.2, and any future minor version — the `uro` namespace is detected automatically from each GML file's `nsmap`, so the script does not hard-code a specific release.
- **Supported LODs**: LOD0 (`lod0RoofEdge`), LOD1 (`lod1Solid`), LOD2 (`boundedBy` with surface semantics).
- Files from multiple mesh tiles may be combined with `--merge`.

---

## Output Format

By default the converter writes a **hybrid** JSON format that keeps file size close to fully compact output while remaining human-readable:

```
{                                     ← overall braces
  "type":"CityJSON",                  ┐
  "version":"2.0",                    │ metadata keys are pretty-printed
  "extensions":{...},                 │
  "transform":{...},                  │
  "metadata":{...},                   ┘
  "CityObjects":{
    "bldg_xxx":{...one line per building...},
    "bldg_yyy":{...},
  },
  "vertices":[...]                    ← vertex array on one line
}
```

| Mode | Flag | Typical size (897 buildings) |
|---|---|---|
| Hybrid (default) | *(none)* | ~4.5 MB |
| Compact | `--compact` | ~4.5 MB |
| Full indent (indent=2) | *(removed from default)* | ~17 MB |

Use `--compact` if the output will be processed entirely by machines (e.g., piped into `fcb ser`).

---

## CRS Handling

The source CRS is read from the `srsName` attribute of `gml:Envelope`. PLATEAU datasets are typically in **EPSG:6697** (JGD2011 geographic 3D), which stores coordinates as *(latitude, longitude, height)*. The converter swaps axes to the CityJSON convention *(longitude, latitude, height)* automatically.

When `--epsg` is specified, `pyproj` reprojects every vertex before quantisation.

**Quantisation precision**

| CRS type | X / Y | Z |
|---|---|---|
| Geographic (degrees) | 1 × 10⁻⁷ ° ≈ 11 mm | 1 mm |
| Projected (metres) | 1 mm | 1 mm |

The `transform.scale` and `transform.translate` values in the output reflect these settings.

---

## Geometry

| LOD | CityGML source | CityJSON type | Semantics |
|---|---|---|---|
| 0 | `bldg:lod0RoofEdge` | `MultiSurface` | — |
| 1 | `bldg:lod1Solid` | `Solid` | — |
| 2 | `bldg:boundedBy` | `Solid` | `GroundSurface`, `RoofSurface`, `WallSurface`, etc. |

All available LODs present in the source GML are written to the same CityObject (CityJSON supports multiple geometry entries per object).

---

## Attribute Mapping

All attributes are written flat into `Building.attributes` for direct compatibility with GIS tools such as QGIS.

### §0 — Core CityGML Building attributes

| CityGML | CityJSON key | Notes |
|---|---|---|
| `gml:id` | `gmlID` | Duplicated from the CityObject identifier |
| *(filename)* | `meshCode` | JIS X 0410 mesh code parsed from the filename |
| `gml:name` | `name` | Facility name; present on a subset of buildings |
| `core:creationDate` | `creationDate` | ISO 8601 string |
| `bldg:class` | `class` | |
| `bldg:usage` | `usage` | |
| `bldg:measuredHeight` | `measuredHeight` | |
| `bldg:storeysAboveGround` | `storeysAboveGround` | |
| `bldg:storeysBelowGround` | `storeysBelowGround` | |

### §1 — Building Identifiers (`uro:BuildingIDAttribute`)

| CityGML | CityJSON key |
|---|---|
| `uro:buildingID` | `buildingID` |
| `uro:branchID` | `branchID` |
| `uro:partID` | `partID` |
| `uro:prefecture` | `prefecture` |
| `uro:city` | `city` |

### §2 — Building Details (`uro:BuildingDetailAttribute`)

| CityGML | CityJSON key | Notes |
|---|---|---|
| `uro:buildingFootprintArea` | `footprintArea` | Falls back to `buildingRoofEdgeArea` |
| `uro:totalFloorArea` | `totalFloorArea` | |
| `uro:siteArea` | `siteArea` | |
| `uro:buildingStructureType` | `structureType` | |
| `uro:fireproofStructureType` | `fireproofType` | |
| `uro:majorUsage` | `usage` | Used when `bldg:usage` is absent |
| `uro:vacancy` | `vacancy` | |
| `uro:buildingCoverageRate` | `coverageRatio` | Falls back to `specifiedBuildingCoverageRate` |
| `uro:floorAreaRate` | `floorAreaRatio` | Falls back to `specifiedFloorAreaRate` |
| `uro:buildingHeight` | `measuredHeight` | Used when `bldg:measuredHeight` is absent |
| `uro:surveyYear` | `surveyYear` | |

### §3 — Urban Planning & Zoning

| CityGML | CityJSON key | Notes |
|---|---|---|
| `uro:urbanPlanType` | `urbanPlanType` | |
| `uro:areaClassificationType` | `areaClassificationType` | |
| `uro:landUseType` | `landUseType` | |
| `uro:districtsAndZonesType` | `districts` | Multiple values joined with `\|` |
| `uro:detailedUsage` / `uro:orgUsage` | `detailedUsage` | Deduplicated, joined with `\|` |
| `uro:developmentArea` | `developmentArea` | |
| `uro:eaveHeight` | `eaveHeight` | |
| `uro:note` | `note` | |

### §4 — Disaster Risk (`uro:BldgDisasterRiskAttribute`)

When only **one** risk entry exists for a given hazard type, fields are stored flat:

| Example key | Description |
|---|---|
| `floodRisk_description` | Flooding hazard code |
| `floodRisk_rank` | Flood risk rank |
| `floodRisk_depth` | Inundation depth (m) |
| `floodRisk_adminType` | Administrative authority type |
| `floodRisk_scale` | Assessment scale |
| `landslideRisk_description` | Landslide hazard code |
| `landslideRisk_areaType` | Hazard zone type |
| `highTideRisk_*` | High-tide risk fields |
| `inlandFloodRisk_*` | Inland flooding risk fields |
| `tsunamiRisk_*` | Tsunami risk fields |

When **multiple** entries exist for the same hazard type, they are stored as a JSON-encoded array string under the base key (e.g., `floodRisk`).

### Generic attributes (`gen:*Attribute`)

PLATEAU `gen:stringAttribute`, `gen:intAttribute`, and `gen:doubleAttribute` elements are stored as `gen_<name>` (e.g., `gen_建物利用現況`). A small set of redundant generic attributes (e.g., town-block codes that duplicate standard fields) is excluded.

---

## CityJSON Extension

When `--cityjson-version 2.0` is used (the default when omitted from some pipelines) or any time `--no-extension` is **not** set, the converter:

1. Writes `plateau-iur.ext.json` in the same directory as the output `.city.json`. This file is a valid **CityJSON 2.0 Extension** schema ([spec](https://www.cityjson.org/specs/2.0.2/#extensions)) that formally declares all PLATEAU / i-UR extra attributes for the `Building` type.
2. Adds an `"extensions"` member to the CityJSON root object referencing the schema:

```json
"extensions": {
  "PLATEAU-iUR": {
    "url": "./plateau-iur.ext.json",
    "version": "1.0"
  }
}
```

Use `--no-extension` to suppress both the schema file and the `"extensions"` member (e.g., when ingesting into tools that do not support CityJSON Extensions).

---

## Examples

```bash
# Convert a single tile, keep EPSG:6697, CityJSON 1.1 (default)
python plateau_citygml2cityjson.py 53394509_bldg_6697_op.gml

# Convert a single tile to CityJSON 2.0 with Extension schema
python plateau_citygml2cityjson.py 53394509_bldg_6697_op.gml --cityjson-version 2.0

# Reproject to Japan Plane Rectangular IX (EPSG:6677)
python plateau_citygml2cityjson.py 53394509_bldg_6697_op.gml \
    --cityjson-version 2.0 --epsg 6677

# Batch convert a folder (one output file per tile)
python plateau_citygml2cityjson.py udx/bldg/ --epsg 4326

# Batch convert and merge all tiles into one file
python plateau_citygml2cityjson.py udx/bldg/ --merge \
    --cityjson-version 2.0 --epsg 6677

# Compact output without Extension schema (e.g., for FlatCityBuf pipeline)
python plateau_citygml2cityjson.py udx/bldg/ --merge --compact --no-extension

# Specify a custom output path
python plateau_citygml2cityjson.py 53394509_bldg_6697_op.gml \
    --cityjson-version 2.0 -o output/chiyoda.city.json
```

### Downstream: FlatCityBuf

```bash
fcb ser --input chiyoda_bldg.city.json --output chiyoda_bldg.fcb
```

---

## Output File Structure

```
output_dir/
├── 53394509_bldg_6697_op.city.json   ← CityJSON data
└── plateau-iur.ext.json               ← CityJSON Extension schema (auto-generated)
```

When `--merge` is used, a single merged file is written:

```
udx/
└── bldg_merged.city.json
plateau-iur.ext.json
```

---

## Attribute Mapping Reference

The attribute mapping follows the **iUR-CityJSON-Building-Mapping** specification (`0428iUR-CityJSON-Building-Mapping.md`), which defines a converter-agnostic mapping between PLATEAU CityGML / i-UR ADE attributes and CityJSON 2.0 Building attributes.

---

## Specification References

- [CityJSON 2.0.2 Specification](https://www.cityjson.org/specs/2.0.2/)
- [CityJSON Extensions](https://www.cityjson.org/specs/2.0.2/#extensions)
- [PLATEAU i-UR 3.x (geospatial.jp)](https://www.geospatial.jp/iur/)
- [PLATEAU Open Data (G-Spatial Information Center)](https://www.geospatial.jp/ckan/dataset/plateau)
