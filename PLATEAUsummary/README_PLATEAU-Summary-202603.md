# Process of PLATEAU-Summary-202603

A municipality-level summary of the 3D city models published by Japan's Project PLATEAU (MLIT), compiled as of 31 March 2026. Each row of the `list` sheet represents one municipality (city, ward, town or village) and records which feature types are available, the most detailed LOD for each, the reported LOD1/LOD2 coverage area and building counts, dataset metadata, and census-based contextual indicators.

- **Municipalities:** 304 (45 prefectures)
- **Spec versions covered:** 3.2 – 5.0
- **Data years covered:** FY2020 – FY2025

> ⚠️ **This is not an official dataset.** It was compiled independently for research purposes. Building counts and coverage areas are transcribed from free-text descriptions and have **not** been counted from the CityGML data (see [Limitations](#limitations)).

---

## Data sources

| Source                                                                                                                                                                                          | Used for                                                                                                                            |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| PLATEAU attribute list (`attributedata_2025.zip`), published on the PLATEAU project page, as of 31 March 2026<br>https://gic-plateau.s3.ap-northeast-1.amazonaws.com/doc/attributedata_2025.zip | Feature types and LODs per municipality, texture availability, spec version, data year, LOD1/LOD2 coverage area and building counts |
| PLATEAU API (via an MCP service)                                                                                                                                                                | `zipfile-size-MB`, `feature_types`                                                                                                  |
| 2020 Population Census of Japan (Statistics Bureau)                                                                                                                                             | `city-cat`, `area-km2`, `2020pop`, `pop-density-km2`                                                                                |

---

## How the data were compiled

### 1. Source attribute list

The original attribute list was **manually compiled by the PLATEAU project** from the metadata of each PLATEAU dataset (XML files and, in part, spreadsheets). The list is not generated automatically.

The original list is a complex, multi-sheet spreadsheet. It has a transposed layout, with municipalities as columns, and it uses merged and free-text cells. It was therefore **restructured with Claude Code** so that **each row represents a single municipality**. The transposed source is kept in the `rawSheet` sheet for reference.

### 2. LOD per feature type

For each feature type (buildings, road, urban-planning, landuse, etc.), the column records the **most detailed LOD available in that municipality** (e.g. `LOD2` means LOD1 and LOD2 are available). `texture` is set to `1` when textured models are available. Otherwise it is blank.

### 3. LOD1/LOD2 coverage area and building counts

In the source list, coverage area and building counts appear only as **unstructured text**. For example:

```
LOD1: 62.98km2 646474棟(都市計画基本図整備範囲内全域)
```

Each entry was parsed as follows:

| Text fragment                                     | Column      |
| ------------------------------------------------- | ----------- |
| `62.98km2` (or `㎞2`)                             | `LOD1-km2`  |
| `646474棟` (thousands separators removed)         | `LOD1bldgs` |
| text in parentheses (extent of the modelled area) | `notes`     |

LOD2 entries were processed in the same way (`LOD2-km2`, `LOD2bldgs`, `LOD2note`).

Some processing rules:

- If a municipality has datasets from several years, the values from the **latest version** (`latest-vesion-year`) are used.
- Descriptions in `notes` were partly normalised:
  - "whole municipality" variants → `全域 - all area coveraged`
  - "city planning area" → `都市計画区域 - urban planning area`
  - Shizuoka Prefecture municipalities → `VIRTUALSHIZUOKA点群データ計測範囲` (VIRTUAL SHIZUOKA point-cloud survey area)
- For a few municipalities, the source text gives the area but no building count. In these cases the count was supplemented from other material.

**Why use text-based figures?** Neither the PLATEAU API nor the other metadata contain actual building counts or coverage areas. To check plausibility, counts for several municipalities were computed from the actual CityGML data. They were broadly consistent with the reported figures.

### 4. Supplementary information

- `zipfile-size-MB` and `feature_types` were retrieved from the PLATEAU API (via an MCP service).
- `city-cat`, `area-km2`, `2020pop` and `pop-density-km2` were **added independently** from the 2020 Population Census. These values are **not part of the PLATEAU data**.

---

## Sheet overview

| Sheet            | Description                                                                                                     |
| ---------------- | --------------------------------------------------------------------------------------------------------------- |
| `list`           | Main table: one row per municipality                                                                            |
| `summary`        | Number of municipalities by feature type and maximum LOD                                                        |
| `rawSheet`       | Transposed source attribute list (municipalities as columns), including the original free-text LOD descriptions |
| `census`         | 2020 Census population and area by municipality                                                                 |
| `v3`, `v4`, `v5` | Attribute definitions from the source list, by spec version                                                     |
| `Sheet2`         | Working sheet used to join census values                                                                        |

---

## Column dictionary (`list` sheet)

| Column                                    | Description                                                                                                                                                                                                                                                                          |
| ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `No`                                      | Row number                                                                                                                                                                                                                                                                           |
| `pref-name` / `pref-en` / `prefcode`      | Prefecture name (Japanese / English) and code                                                                                                                                                                                                                                        |
| `city-name` / `city-name-en` / `citycode` | Municipality name (Japanese / English) and 5-digit municipality code                                                                                                                                                                                                                 |
| `city-cat`                                | Municipality category: `designated-cites` (ordinance-designated city), `city`, `ward`, `town`, `village` _(added from census)_                                                                                                                                                       |
| `first_year`                              | First fiscal year in which PLATEAU data were published                                                                                                                                                                                                                               |
| `latest-vesion-year`                      | Fiscal year of the latest published version                                                                                                                                                                                                                                          |
| `spec`                                    | Version of the PLATEAU 3D city model standard specification                                                                                                                                                                                                                          |
| `bldgs`                                   | Most detailed LOD of building models                                                                                                                                                                                                                                                 |
| `texture`                                 | `1` if textured models are available                                                                                                                                                                                                                                                 |
| `road` … `urban-objects`                  | Most detailed LOD per feature type (road, public-transport, walkway, public-square, sea-route, urban-planning, landuse, disaster risk, urban-facilities, vegetation, water, terrain, bridge, tunnel, others, underground-shopping-mall, underground-structures, area, urban-objects) |
| `zipfile-size-MB`                         | Size of the CityGML zip file (MB) _(PLATEAU API)_                                                                                                                                                                                                                                    |
| `feature_types`                           | List of feature-type codes in the dataset, e.g. `bldg`, `tran`, `luse` _(PLATEAU API)_                                                                                                                                                                                               |
| `LOD1-km2` / `LOD1bldgs`                  | LOD1 coverage area (km²) and number of buildings _(parsed from text)_                                                                                                                                                                                                                |
| `notes`                                   | Extent of the LOD1 modelled area                                                                                                                                                                                                                                                     |
| `LOD2-km2` / `LOD2bldgs` / `LOD2note`     | LOD2 coverage area, number of buildings and extent _(parsed from text)_                                                                                                                                                                                                              |
| `LOD3` / `LOD3_note`                      | Number of LOD3 buildings and note                                                                                                                                                                                                                                                    |
| `LOD4` / `LOD4_note`                      | Number of LOD4 buildings and note                                                                                                                                                                                                                                                    |
| `latest_citygml`                          | Download URL of the latest CityGML package                                                                                                                                                                                                                                           |
| `latest_metadata-url`                     | URL of the dataset page on G-Spatial Information Center                                                                                                                                                                                                                              |
| `area-km2`                                | Municipal area (km²) _(added from census)_                                                                                                                                                                                                                                           |
| `2020pop`                                 | Population, 2020 Census _(added from census)_                                                                                                                                                                                                                                        |
| `pop-density-km2`                         | Population density (persons/km²) _(added from census)_                                                                                                                                                                                                                               |

---

## Limitations

- Building counts and coverage areas are **transcribed from manually written text**, not counted from the CityGML data. They should be treated as **approximate** values.
- The source attribute list is itself a manual compilation, so omissions or inconsistencies in the original carry over into this table.
- The modelled area (`notes`) differs between municipalities, e.g. whole municipality, city planning area, or zoning area only. **Coverage area is not the same as municipal area.** Comparisons between municipalities should take this into account.
- Census-derived values refer to whole municipalities, not to the PLATEAU modelled area.
