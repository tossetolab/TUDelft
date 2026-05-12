# CityGML (PLATEAU + i-UR ADE) to CityJSON Mapping Table for Buildings

**Version:** 2026-05-12Updated

This document defines an official, implementation-oriented mapping table between **CityGML building-related attributes** (including **i-UR ADE**) used in PLATEAU datasets and their corresponding representations in **CityJSON 2.0**.

The mapping is explicitly data-driven: attributes are included only when they are **commonly populated in real PLATEAU CityGML files** and **meaningful in downstream CityJSON / 3DBAG-style usage**.

---

## Mapping Policy

- Mapping is based on **semantic meaning**, not CityGML UML structure.
- CityJSON `attributes` contain core, frequently queried building properties.
- CityJSON `properties.iur` contain contextual, regulatory, and urban-planning information.
- Nested structures are expressed explicitly using arrows (→)
- All i-UR ADE class hierarchies are **flattened**.
- Attributes not listed here are intentionally excluded.

---

## 0. Core CityGML Building Attributes (bldg:Building)  

| CityGML attribute | CityJSON target | Notes |
|-------------------|-----------------|-------|
| `bldg:class` | `class` | Widely populated in PLATEAU |
| `bldg:usage` | `usage` | Used when i-UR usage missing |
| `bldg:measuredHeight` | `measuredHeight` | CityJSON standard |
| `bldg:storeysAboveGround` | `storeysAboveGround` | Frequently populated |
| `bldg:storeysBelowGround` | `storeysBelowGround` | Frequently populated |
| `core:creationDate` | `creationDate` | ISO 8601 string |

---

## 1. Building Identifiers (uro:BuildingIDAttribute)

| CityGML / i-UR attribute | CityJSON target | Notes |
|-------------------------|----------------|-------|
| `gml:id` | `gmlID` | gml:ID |
| `meshCode` | `meshcode` | Regional grid-code |
| `name` | `name` | Building specific name:ja |
| `buildingID` | `buildingID` | Municipal unique building ID |
| `branchID` | `branchID` | Optional |
| `partID` | `partID` | Optional |
| `prefecture` | `prefecture` | Metadata-level |
| `city` | `city` | Metadata-level |

---

## 2. Building Details (uro:BuildingDetailAttribute)

| CityGML / i-UR attribute | CityJSON target | Notes |
|-------------------------|----------------|-------|
| `siteArea` | `siteArea` | gml:Measure → number |
| `totalFloorArea` | `totalFloorArea` | Core analytical attribute |
| `buildingFootprintArea` | `footprintArea` | Optional |
| `developmentArea` | `iur → developmentArea` | Planning context |
| `buildingStructureType` | `structureType` | CodeType → string |
| `fireproofStructureType` | `fireproofType` | CodeType → string |
| `majorUsage` | `usage` | Promoted to core |
| `orgUsage`, `detailedUsage*` | `iur → detailedUsage[]` | Flattened |
| `vacancy` | `vacancy` | Frequently populated |
| `buildingCoverageRate` | `coverageRatio` | Ratio |
| `floorAreaRate` | `floorAreaRatio` | Ratio |
| `buildingHeight` | `measuredHeight` | Harmonized |
| `eaveHeight` | `iur → eaveHeight` | Optional |
| `surveyYear` | `surveyYear` | Provenance |
| `note` | `iur → note` | Free text |

---

## 3. Urban Planning and Zoning Attributes

| CityGML / i-UR attribute | CityJSON target | Notes |
|-------------------------|----------------|-------|
| `urbanPlanType` | `iur → urbanPlanType` | Contextual |
| `areaClassificationType` | `iur → areaClassificationType` | Contextual |
| `districtsAndZonesType` | `iur → districts[]` | Multi-valued |
| `landUseType` | `iur → landUseType` | Zoning |

---

## 4. Disaster Risk Attributes (uro:BldgDisasterRiskAttribute)

### FloodingRiskAttribute

| CityGML / i-UR attribute | CityJSON target | Notes |
|-------------------------|----------------|-------|
| `description` | `iur → risk.flood.description` | Code value |
| `rank` | `iur → risk.flood.rank` | Ordinal |
| `depth` | `iur → risk.flood.depth` | meters |
| `adminType` | `iur → risk.flood.adminType` | Source authority |
| `scale` | `iur → risk.flood.scale` | Assessment scale |

### LandSlideRiskAttribute

| CityGML / i-UR attribute | CityJSON target | Notes |
|-------------------------|----------------|-------|
| `description` | `iur → risk.landslide.description` | Code value |
| `areaType` | `iur → risk.landslide.areaType` | Hazard zone type |

---

## 5. Geometry Semantics

| CityGML | CityJSON target |
|--------|----------------|
| bldg:GroundSurface | geometry → semantics → surfaces → type |
| bldg:WallSurface | geometry → semantics → surfaces → type |
| bldg:RoofSurface | geometry → semantics → surfaces → type |

---

## 6. Explicitly Excluded Attributes

The following CityGML / i-UR elements are intentionally not mapped:

- Detailed `DataQualityAttribute` breakdowns (only summaries recommended)
- `CityObjectGroup` (floor/group semantics)
- `ConstructionEvent` and lifecycle histories
- Indoor, facility, and energy ADEs
- Generic key-value extension attributes unless explicitly required

---

## Notes

- This mapping is converter-agnostic and can be implemented independently of PLATEAU-GIS-Converter.
- Attribute selection is empirically aligned with real PLATEAU CityGML data and 3DBAG-style CityJSON usage.
- Designed for CityJSON 2.0 and downstream formats such as FlatCityBuf and 3D Tiles.
- This document was created with the support of **Microsoft 365 Copilot**.
