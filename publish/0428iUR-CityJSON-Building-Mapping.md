# CityGML (PLATEAU + i-UR ADE) to CityJSON Mapping Table for Buildings

**Version:** 2026-05-04Updated

This document defines an official, implementation-oriented mapping table between **CityGML building-related attributes** (including **i-UR ADE**) used in PLATEAU datasets and their corresponding representations in **CityJSON 2.0**.

The mapping is explicitly data-driven: attributes are included only when they are **commonly populated in real PLATEAU CityGML files** and **meaningful in downstream CityJSON / 3DBAG-style usage**.

---

## Mapping Policy

- Mapping is based on **semantic meaning**, not CityGML UML structure.
- CityJSON `attributes` contain core, frequently queried building properties.
- CityJSON `properties.iur` contain contextual, regulatory, and urban-planning information.
- All i-UR ADE class hierarchies are **flattened**.
- Attributes not listed here are intentionally excluded.

---

## 0. Core CityGML Building Attributes (bldg:Building)  **[ADDED]**

| CityGML attribute | CityJSON target | Notes |
|-------------------|-----------------|-------|
| `bldg:class` | `attributes.class` | Widely populated in PLATEAU |
| `bldg:usage` | `attributes.usage` | Used when i-UR usage missing |
| `bldg:measuredHeight` | `attributes.measuredHeight` | CityJSON standard |
| `bldg:storeysAboveGround` | `attributes.storeysAboveGround` | Frequently populated |
| `bldg:storeysBelowGround` | `attributes.storeysBelowGround` | Frequently populated |
| `core:creationDate` | `attributes.creationDate` | ISO 8601 string |

---

## 1. Building Identifiers (uro:BuildingIDAttribute)

| CityGML / i-UR attribute | CityJSON target | Notes |
|-------------------------|----------------|-------|
| `buildingID` | `attributes.buildingID` | Municipal unique building ID |
| `branchID` | `attributes.branchID` | Optional |
| `partID` | `attributes.partID` | Optional |
| `prefecture` | `metadata.address.prefecture` | Metadata-level |
| `city` | `metadata.address.city` | Metadata-level |

---

## 2. Building Details (uro:BuildingDetailAttribute)

| CityGML / i-UR attribute | CityJSON target | Notes |
|-------------------------|----------------|-------|
| `siteArea` | `attributes.siteArea` | gml:Measure → number |
| `totalFloorArea` | `attributes.totalFloorArea` | Core analytical attribute |
| `buildingFootprintArea` | `attributes.footprintArea` | Optional |
| `developmentArea` | `properties.iur.developmentArea` | Planning context |
| `buildingStructureType` | `attributes.structureType` | CodeType → string |
| `fireproofStructureType` | `attributes.fireproofType` | CodeType → string |
| `majorUsage` | `attributes.usage` | Promoted to core |
| `orgUsage`, `detailedUsage*` | `properties.iur.detailedUsage[]` | Flattened |
| `vacancy` | `attributes.vacancy` | Frequently populated |
| `buildingCoverageRate` | `attributes.coverageRatio` | Ratio |
| `floorAreaRate` | `attributes.floorAreaRatio` | Ratio |
| `buildingHeight` | `attributes.measuredHeight` | Harmonized |
| `eaveHeight` | `properties.iur.eaveHeight` | Optional |
| `surveyYear` | `attributes.surveyYear` | Provenance |
| `note` | `properties.iur.note` | Free text |

---

## 3. Urban Planning and Zoning Attributes

| CityGML / i-UR attribute | CityJSON target | Notes |
|-------------------------|----------------|-------|
| `urbanPlanType` | `properties.iur.urbanPlanType` | Contextual |
| `areaClassificationType` | `properties.iur.areaClassificationType` | Contextual |
| `districtsAndZonesType` | `properties.iur.districts[]` | Multi-valued |
| `landUseType` | `properties.iur.landUseType` | Zoning |

---

## 4. Disaster Risk Attributes (uro:BldgDisasterRiskAttribute)  **[EXTENDED]**

### FloodingRiskAttribute

| CityGML / i-UR attribute | CityJSON target | Notes |
|-------------------------|----------------|-------|
| `description` | `properties.iur.risk.flood.description` | Code value |
| `rank` | `properties.iur.risk.flood.rank` | Ordinal |
| `depth` | `properties.iur.risk.flood.depth` | meters |
| `adminType` | `properties.iur.risk.flood.adminType` | Source authority |
| `scale` | `properties.iur.risk.flood.scale` | Assessment scale |

### LandSlideRiskAttribute

| CityGML / i-UR attribute | CityJSON target | Notes |
|-------------------------|----------------|-------|
| `description` | `properties.iur.risk.landslide.description` | Code value |
| `areaType` | `properties.iur.risk.landslide.areaType` | Hazard zone type |

---

## 5. Geometry Semantics  **[ADDED]**

The following CityGML boundary surface types are preserved and converted into
CityJSON geometry semantics when present:

- `bldg:GroundSurface`
- `bldg:WallSurface`
- `bldg:RoofSurface`

These are mapped to `geometry.semantics.surfaces` with corresponding index arrays.

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
