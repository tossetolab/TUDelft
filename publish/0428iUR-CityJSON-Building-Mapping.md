# CityGML (PLATEAU + i-UR ADE) to CityJSON Mapping Table for Buildings

**Version:** 2026-05-12Updated

This document defines an official, implementation-oriented mapping table between **CityGML building-related attributes** (including **i-UR ADE**) used in PLATEAU datasets and their corresponding representations in **CityJSON 2.0**.

The mapping is explicitly data-driven: attributes are included only when they are **commonly populated in real PLATEAU CityGML files** and **meaningful in downstream CityJSON / 3DBAG-style usage**.

---

## Mapping Policy

- Mapping is based on **semantic meaning**, not CityGML UML structure.
- CityJSON attributes contain core, frequently queried building properties.
- CityJSON properties.iur contain contextual, regulatory, and urban-planning information.
- Nested structures are expressed explicitly using arrows (→)
- All i-UR ADE class hierarchies are **flattened**.
- Attributes not listed here are intentionally excluded.

---

## 0. Core CityGML Building Attributes (bldg:Building)  

| CityGML attribute | CityJSON target | Notes |
|-------------------|-----------------|-------|
| core:creationDate | creationDate | ISO 8601 string |
| bldg:class | class | Widely populated in PLATEAU |
| bldg:usage | usage | Used when i-UR usage missing |
| bldg:measuredHeight | measuredHeight | CityJSON standard |
| bldg:storeysAboveGround | storeysAboveGround | Frequently populated |
| bldg:storeysBelowGround | storeysBelowGround | Frequently populated |

---

## 1. Building Identifiers (uro:BuildingIDAttribute)

| CityGML attribute | CityJSON target | Notes |
|-------------------------|----------------|-------|
| gml:id | gmlID | gml:ID |
| meshCode | meshcode | Regional grid-code |
| name | name | Building specific name:ja |
| buildingID | buildingID | Municipal unique building ID |
| branchID | branchID | Optional |
| partID | partID | Optional |

---

## 2. Building Details (uro:BuildingDetailAttribute)

| CityGML attribute | CityJSON target | Notes |
|-------------------------|----------------|-------|
| siteArea | siteArea | gml:Measure → number |
| totalFloorArea | totalFloorArea | Core analytical attribute |
| buildingFootprintArea | footprintArea | Optional |
| buildingStructureType | structureType | CodeType → string |
| fireproofStructureType | fireproofType | CodeType → string |
| majorUsage | usage | Promoted to core |
| vacancy | vacancy | Frequently populated |
| buildingCoverageRate | coverageRatio | Ratio |
| floorAreaRate | floorAreaRatio | Ratio |
| buildingHeight | measuredHeight | Harmonized |
| surveyYear | surveyYear | Provenance |

| i-UR attribute | CityJSON target | Notes |
| developmentArea | iur → developmentArea | Planning context |
| orgUsage, detailedUsage* | iur → detailedUsage | Flattened |
| eaveHeight | iur → eaveHeight | Optional |

---

## 3. Urban Planning and Zoning Attributes

| i-UR attribute | CityJSON target | Notes |
|-------------------------|----------------|-------|
| urbanPlanType | urbanPlanType | Contextual |
| areaClassificationType | areaClassificationType | Contextual |
| districtsAndZonesType | districts[] | Multi-valued |
| landUseType | landUseType | Zoning |

---

## 4. Disaster Risk Attributes (uro:BldgDisasterRiskAttribute)

### FloodingRiskAttribute

| i-UR attribute | CityJSON target | Notes |
|-------------------------|----------------|-------|
| description | risk.flood.description | Code value |
| rank | risk.flood.rank | Ordinal |
| depth | risk.flood.depth | meters |
| adminType | risk.flood.adminType | Source authority |
| scale | risk.flood.scale | Assessment scale |

### LandSlideRiskAttribute

| i-UR attribute | CityJSON target | Notes |
|-------------------------|----------------|-------|
| description | risk.landslide.description | Code value |
| areaType | risk.landslide.areaType | Hazard zone type |

---

## 5. Geometry Semantics

| CityGML | CityJSON target |
|--------|----------------|
| bldg:GroundSurface | GroundSurface |
| bldg:WallSurface | WallSurface |
| bldg:OuterFloorSurface | OuterFloorSurface |
| bldg:OuterCeilingSurface | OuterCeilingSurface |
| bldg:ClosureSurface | ClosureSurface |
| bldg:InteriorWallSurface | InteriorWallSurface |
| bldg:FloorSurface | FloorSurface |
| bldg:CeilingSurface | CeilingSurface |
---

## 6. Explicitly Excluded Attributes

The following CityGML / i-UR elements are intentionally not mapped:

- Detailed DataQualityAttribute breakdowns (only summaries recommended)
- CityObjectGroup (floor/group semantics)
- ConstructionEvent and lifecycle histories
- Indoor, facility, and energy ADEs
- Generic key-value extension attributes unless explicitly required

---

## Notes

- This mapping is converter-agnostic and can be implemented independently of PLATEAU-GIS-Converter.
- Attribute selection is empirically aligned with real PLATEAU CityGML data and 3DBAG-style CityJSON usage.
- Designed for CityJSON 2.0 and downstream formats such as FlatCityBuf and 3D Tiles.
- This document was created with the support of **Microsoft 365 Copilot**.
