# CityGML (PLATEAU + i-UR ADE) to CityJSON Mapping Table for Buildings

This document defines an official, implementation-oriented mapping table between **CityGML building-related attributes** (including **i-UR ADE**) used in PLATEAU datasets and their corresponding representations in **CityJSON 2.0**. The goal is to preserve semantic value while avoiding direct transplantation of the full i-UR ADE structure into CityJSON.

The mapping is designed for practical use cases such as data distribution, visualization, web services, and lightweight analysis.

---

## Mapping Policy

- CityGML / i-UR attributes are mapped **by semantic meaning**, not by UML structure.
- CityJSON `attributes` are used for core, frequently queried building properties.
- CityJSON `properties.iur` is used for urban-planning, regulatory, and contextual information.
- i-UR ADE class hierarchies are **flattened**.
- Attributes not listed here are intentionally excluded.

---

## 1. Building Identifiers (uro:BuildingIDAttribute)

| CityGML / i-UR ADE attribute | CityJSON target | Notes |
|-----------------------------|----------------|-------|
| `uro:buildingIDAttribute/buildingID` | `attributes.buildingID` | Municipal unique building ID |
| `uro:buildingIDAttribute/branchID` | `attributes.branchID` | Optional branch identifier |
| `uro:buildingIDAttribute/partID` | `attributes.partID` | Optional part identifier |
| `uro:buildingIDAttribute/prefecture` | `metadata.address.prefecture` | Stored as metadata |
| `uro:buildingIDAttribute/city` | `metadata.address.city` | Stored as metadata |

---

## 2. Building Details (uro:BuildingDetailAttribute)

| CityGML / i-UR ADE attribute | CityJSON target | Notes |
|-----------------------------|----------------|-------|
| `siteArea` | `attributes.siteArea` | Unit normalized to number |
| `totalFloorArea` | `attributes.totalFloorArea` | Core analytical attribute |
| `buildingFootprintArea` | `attributes.footprintArea` | Optional |
| `developmentArea` | `properties.iur.developmentArea` | Planning context |
| `buildingStructureType` | `attributes.structureType` | CodeType → string |
| `fireproofStructureType` | `attributes.fireproofType` | CodeType → string |
| `majorUsage` | `attributes.usage` | Promoted to core attribute |
| `orgUsage`, `detailedUsage*` | `properties.iur.detailedUsage[]` | Flattened array |
| `vacancy` | `attributes.vacancy` | Frequently reused |
| `buildingCoverageRate` | `attributes.coverageRatio` | Ratio value |
| `floorAreaRate` | `attributes.floorAreaRatio` | Ratio value |
| `buildingHeight` | `attributes.measuredHeight` | CityJSON standard |
| `eaveHeight` | `properties.iur.eaveHeight` | Optional |
| `surveyYear` | `attributes.surveyYear` | Provenance |
| `note` | `properties.iur.note` | Free text |

---

## 3. Urban Planning and Zoning Attributes

| CityGML / i-UR ADE attribute | CityJSON target | Notes |
|-----------------------------|----------------|-------|
| `urbanPlanType` | `properties.iur.urbanPlanType` | Contextual information |
| `areaClassificationType` | `properties.iur.areaClassificationType` | Contextual information |
| `districtsAndZonesType` | `properties.iur.districts[]` | Multiple values allowed |
| `landUseType` | `properties.iur.landUseType` | Zoning information |

---

## 4. Disaster Risk Attributes (uro:BldgDisasterRiskAttribute)

| CityGML / i-UR ADE attribute | CityJSON target | Notes |
|-----------------------------|----------------|-------|
| `FloodingRiskAttribute/rank` | `properties.iur.risk.flood.rank` | CodeType → string |
| `FloodingRiskAttribute/depth` | `properties.iur.risk.flood.depth` | LengthType → number |
| `LandSlideRiskAttribute/areaType` | `properties.iur.risk.landslide.type` | Optional |

---

## 5. Explicitly Excluded Attributes

The following CityGML / i-UR elements are **intentionally not mapped** to CityJSON:

- `DataQualityAttribute` (detailed breakdown; only summaries may be stored in metadata)
- `CityObjectGroup` (floor hierarchies and group semantics)
- `ConstructionEvent` and detailed lifecycle history
- Generic key-value extension attributes unless explicitly required

---

## Notes

- This mapping is independent of specific converter implementations.
- Attribute selection is empirically aligned with attributes preserved by practical tools such as PLATEAU-GIS-Converter.
- This work was developed through discussions and iterative reasoning supported by Microsoft Copilot.
