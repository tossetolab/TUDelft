#!/usr/bin/env python3
"""
PLATEAU CityGML → CityJSON 1.1 / 2.0 変換スクリプト
CityJSON 仕様: https://www.cityjson.org/specs/

使い方:
  # 第一段階: 単一ファイル変換
  python plateau_citygml2cityjson.py input.gml
  python plateau_citygml2cityjson.py input.gml -o output.city.json

  # 第二段階: フォルダ一括変換
  python plateau_citygml2cityjson.py udx/bldg/
  python plateau_citygml2cityjson.py udx/bldg/ -o output_dir/
  python plateau_citygml2cityjson.py udx/bldg/ --merge   # フォルダを1ファイルにまとめる

  # 座標系変換 (--epsg)
  python plateau_citygml2cityjson.py input.gml --epsg 6677         # 日本平面直角IX系
  python plateau_citygml2cityjson.py udx/bldg/ --epsg 4326         # WGS84 地理座標
  python plateau_citygml2cityjson.py udx/bldg/ --merge --epsg 6677 # マージ + 変換

  # CityJSON バージョン指定 (--cityjson-version)
  python plateau_citygml2cityjson.py input.gml --cityjson-version 2.0   # CityJSON 2.0 出力
  python plateau_citygml2cityjson.py input.gml --cityjson-version 1.1   # CityJSON 1.1 出力 (デフォルト)

動作:
  - 入力がファイル (.gml) → 単一変換
  - 入力がフォルダ       → フォルダ内の全 .gml を変換

属性マッピング (iUR-CityJSON-Building-Mapping v2026-05-04 準拠):
  attributes.*              : 建物基本属性
    .buildingID               : 建物ID (uro:BuildingIDAttribute)
    .branchID / .partID       : 枝番・部分番号 (任意)
    .class / .usage           : 建物クラス・用途
    .measuredHeight           : 建物高さ
    .storeysAboveGround/Below : 地上・地下階数
    .creationDate             : 作成日
    .footprintArea            : 建物投影面積 (uro:buildingRoofEdgeArea 等)
    .structureType            : 構造種別
    .fireproofType            : 防火構造種別
    .coverageRatio            : 指定建蔽率
    .floorAreaRatio           : 指定容積率
    .surveyYear               : 調査年
    .totalFloorArea / .siteArea / .vacancy / .eaveHeight : 任意
  metadata.address.*        : ファイルレベルの行政区画情報
    .prefecture               : 都道府県コード (uro:buildingIDAttribute)
    .city                     : 市区町村コード (uro:buildingIDAttribute, 複数可)
  properties.iur.*          : 都市計画・規制・災害リスク
    .urbanPlanType / .areaClassificationType / .landUseType
    .districts[]              : 地域地区 (複数値)
    .detailedUsage[]          : 詳細用途 (複数値)
    .developmentArea / .eaveHeight / .note
    .risk.flood[]             : 浸水リスク (description/rank/depth/adminType/scale)
    .risk.landslide[]         : 土砂災害リスク (description/areaType)
    .risk.inlandFlood[] / .risk.tsunami[] / .risk.highTide[]

座標系:
  - EPSG:6697 (JGD2011 geographic 3D) 維持
  - GML 軸順 (lat, lon, height) → CityJSON 軸順 (lon, lat, height) に変換
  - transform.scale を用いた整数量子化 (精度: 水平 0.1mm, 高さ 1mm)

ジオメトリ:
  - LOD0: lod0RoofEdge → MultiSurface
  - LOD1: lod1Solid    → Solid
  - LOD2: boundedBy (WallSurface/RoofSurface/GroundSurface等) → Solid + semantics

属性:
  - CityGML 標準属性 (class, usage, measuredHeight, storeys 等)
  - PLATEAU 拡張属性 gen:*Attribute を "gen_<名前>" として格納
"""

import json
import re
import sys
import time
import argparse
from pathlib import Path
from lxml import etree
import pyproj

# --------------------------------------------------------------------------- #
# XML 名前空間
# --------------------------------------------------------------------------- #
NS = {
    'core': 'http://www.opengis.net/citygml/2.0',
    'bldg': 'http://www.opengis.net/citygml/building/2.0',
    'gml':  'http://www.opengis.net/gml',
    'gen':  'http://www.opengis.net/citygml/generics/2.0',
    'uro':  'https://www.geospatial.jp/iur/uro/3.2',
    'app':  'http://www.opengis.net/citygml/appearance/2.0',
}

GML  = NS['gml']
BLDG = NS['bldg']
CORE = NS['core']
GEN  = NS['gen']

# CityGML 意味サーフェスタグ → CityJSON セマンティクス型名
SURFACE_TYPE_MAP: dict[str, str] = {
    f'{{{BLDG}}}GroundSurface':       'GroundSurface',
    f'{{{BLDG}}}WallSurface':         'WallSurface',
    f'{{{BLDG}}}RoofSurface':         'RoofSurface',
    f'{{{BLDG}}}OuterFloorSurface':   'OuterFloorSurface',
    f'{{{BLDG}}}OuterCeilingSurface': 'OuterCeilingSurface',
    f'{{{BLDG}}}ClosureSurface':      'ClosureSurface',
    f'{{{BLDG}}}InteriorWallSurface': 'InteriorWallSurface',
    f'{{{BLDG}}}FloorSurface':        'FloorSurface',
    f'{{{BLDG}}}CeilingSurface':      'CeilingSurface',
}

# --------------------------------------------------------------------------- #
# CRS 読み取りと座標変換
# --------------------------------------------------------------------------- #

def _read_source_epsg(root) -> int:
    """
    gml:Envelope の srsName 属性から EPSG コードを読み取る。
    例: "http://www.opengis.net/def/crs/EPSG/0/6697" → 6697
        "urn:ogc:def:crs:EPSG::6697"                 → 6697
    見つからない場合は PLATEAU のデフォルト 6697 を返す。
    """
    envelope = root.find(f'.//{{{GML}}}Envelope')
    if envelope is not None:
        srs = envelope.get('srsName', '')
        m = re.search(r'EPSG[:/]+(?:\d+[:/]+)?(\d+)\s*$', srs)
        if m:
            return int(m.group(1))
    return 6697


def _build_crs(src_epsg: int, dst_epsg: int | None) -> tuple:
    """
    座標変換に必要な情報をまとめて返す。

    Returns:
        transformer : pyproj.Transformer (変換不要な場合 None)
        scale       : VertexRegistry 用スケール
        crs_uri     : metadata.referenceSystem URI
        src_latlon  : ソース GML が lat 先行軸順かどうか
    """
    src_crs = pyproj.CRS.from_epsg(src_epsg)

    # GML 軸順の判定: EPSG:6697 などは latitude が第1軸 (direction='north')
    src_latlon = (
        src_crs.is_geographic
        and src_crs.axis_info[0].direction.lower() == 'north'
    )

    eff_dst = dst_epsg if dst_epsg else src_epsg
    dst_crs = pyproj.CRS.from_epsg(eff_dst)

    if dst_epsg and dst_epsg != src_epsg:
        # always_xy=True: 入出力を (経度/東距, 緯度/北距, 高さ) に統一
        transformer = pyproj.Transformer.from_crs(
            src_crs, dst_crs, always_xy=True
        )
    else:
        transformer = None

    # スケール: 投影座標 (m 単位) は 1mm 精度、地理座標は 1e-7° ≈ 11mm
    scale: list[float] = (
        [1e-3, 1e-3, 1e-3] if dst_crs.is_projected
        else [1e-7, 1e-7, 1e-3]
    )
    crs_uri = f"https://www.opengis.net/def/crs/EPSG/0/{eff_dst}"

    return transformer, scale, crs_uri, src_latlon


# --------------------------------------------------------------------------- #
# 座標処理
# --------------------------------------------------------------------------- #

def parse_pos_list(
    text: str,
    src_latlon: bool = True,
) -> list[tuple[float, float, float]]:
    """
    gml:posList テキスト → [(lon_or_x, lat_or_y, z), ...] のリスト。

    src_latlon=True (デフォルト): EPSG:6697 等の lat 先行軸順を lon/lat に入れ替える。
    変換 (pyproj) はこの後 VertexRegistry.add() で行う。
    """
    nums = list(map(float, text.split()))
    coords: list[tuple[float, float, float]] = []
    for i in range(0, len(nums) - 2, 3):
        if src_latlon:
            lat, lon, z = nums[i], nums[i + 1], nums[i + 2]
        else:
            lon, lat, z = nums[i], nums[i + 1], nums[i + 2]
        coords.append((lon, lat, z))
    return coords


def extract_ring_coords(
    ring_elem,
    src_latlon: bool = True,
) -> list[tuple[float, float, float]]:
    """gml:LinearRing 要素から座標を抽出"""
    pl = ring_elem.find(f'{{{GML}}}posList')
    if pl is not None and pl.text:
        return parse_pos_list(pl.text, src_latlon)
    # gml:pos のフォールバック (稀なケース)
    pos_list = ring_elem.findall(f'{{{GML}}}pos')
    if pos_list:
        nums: list[float] = []
        for p in pos_list:
            if p.text:
                nums.extend(map(float, p.text.split()))
        return parse_pos_list(' '.join(map(str, nums)), src_latlon)
    return []


# --------------------------------------------------------------------------- #
# 頂点レジストリ (重複排除 + 整数量子化 + CRS変換)
# --------------------------------------------------------------------------- #

class VertexRegistry:
    """
    頂点を整数インデックスで管理する。
    CityJSON の transform: real = integer * scale + translate

    transformer が設定されている場合、add() 内で pyproj 変換を適用する。
    入力座標は常に (lon/x, lat/y, z) 順 (always_xy=True 準拠)。
    """

    def __init__(
        self,
        translate: list[float],
        scale: list[float],
        transformer: pyproj.Transformer | None = None,
    ):
        self.translate = translate
        self.scale = scale
        self.transformer = transformer
        self._map: dict[tuple[int, int, int], int] = {}
        self._list: list[list[int]] = []

    def add(self, lon: float, lat: float, z: float) -> int:
        # CRS 変換 (指定時のみ)
        if self.transformer:
            lon, lat, z = self.transformer.transform(lon, lat, z)
        tx, ty, tz = self.translate
        sx, sy, sz = self.scale
        ix = round((lon - tx) / sx)
        iy = round((lat - ty) / sy)
        iz = round((z   - tz) / sz)
        key = (ix, iy, iz)
        if key not in self._map:
            idx = len(self._list)
            self._map[key] = idx
            self._list.append([ix, iy, iz])
        return self._map[key]

    def ring_indices(self, coords: list[tuple[float, float, float]]) -> list[int]:
        """座標リスト → 頂点インデックスリスト (閉じ点は除外)"""
        if len(coords) > 1 and coords[0] == coords[-1]:
            coords = coords[:-1]
        return [self.add(lon, lat, z) for lon, lat, z in coords]

    @property
    def vertices(self) -> list[list[int]]:
        return self._list


# --------------------------------------------------------------------------- #
# ジオメトリ抽出
# --------------------------------------------------------------------------- #

def polygon_to_rings(
    poly_elem,
    reg: VertexRegistry,
    src_latlon: bool = True,
) -> list[list[int]] | None:
    """gml:Polygon → [[exterior_indices], [interior_indices?], ...] または None"""
    ext_ring = poly_elem.find(f'{{{GML}}}exterior/{{{GML}}}LinearRing')
    if ext_ring is None:
        return None
    coords = extract_ring_coords(ext_ring, src_latlon)
    if not coords:
        return None
    rings = [reg.ring_indices(coords)]
    for intr_ring in poly_elem.findall(f'{{{GML}}}interior/{{{GML}}}LinearRing'):
        ic = extract_ring_coords(intr_ring, src_latlon)
        if ic:
            rings.append(reg.ring_indices(ic))
    return rings


def _polygons_from_subtree(
    elem,
    reg: VertexRegistry,
    src_latlon: bool = True,
) -> list[list[list[int]]]:
    """要素の子孫にある全 gml:Polygon をサーフェスリストとして収集"""
    surfaces = []
    for poly in elem.iter(f'{{{GML}}}Polygon'):
        rings = polygon_to_rings(poly, reg, src_latlon)
        if rings:
            surfaces.append(rings)
    return surfaces


def extract_lod0(bldg_elem, reg: VertexRegistry, src_latlon: bool = True) -> dict | None:
    """bldg:lod0RoofEdge → CityJSON MultiSurface (LOD 0)"""
    lod0 = bldg_elem.find(f'{{{BLDG}}}lod0RoofEdge')
    if lod0 is None:
        return None
    surfaces = _polygons_from_subtree(lod0, reg, src_latlon)
    if not surfaces:
        return None
    return {"type": "MultiSurface", "lod": "0", "boundaries": surfaces}


def extract_lod1(bldg_elem, reg: VertexRegistry, src_latlon: bool = True) -> dict | None:
    """bldg:lod1Solid → CityJSON Solid (LOD 1)"""
    lod1 = bldg_elem.find(f'{{{BLDG}}}lod1Solid')
    if lod1 is None:
        return None
    shell = _polygons_from_subtree(lod1, reg, src_latlon)
    if not shell:
        return None
    return {"type": "Solid", "lod": "1", "boundaries": [shell]}


def extract_lod2(bldg_elem, reg: VertexRegistry, src_latlon: bool = True) -> dict | None:
    """
    bldg:boundedBy → CityJSON Solid + semantics (LOD 2)。

    lod2Solid は xlink:href でポリゴンを参照するため、実際のジオメトリは
    boundedBy 内の lod2MultiSurface から取得する。
    boundedBy が存在しない場合は lod2Solid の inline ジオメトリを使用。
    """
    bounded_by_list = bldg_elem.findall(f'{{{BLDG}}}boundedBy')

    if not bounded_by_list:
        # フォールバック: lod2Solid の直接パース
        lod2 = bldg_elem.find(f'{{{BLDG}}}lod2Solid')
        if lod2 is None:
            return None
        shell = _polygons_from_subtree(lod2, reg, src_latlon)
        if not shell:
            return None
        return {"type": "Solid", "lod": "2", "boundaries": [shell]}

    sem_surfaces: list[dict] = []
    sem_values: list[int]   = []
    shell: list[list[list[int]]] = []

    for bb in bounded_by_list:
        # boundedBy 直下の意味サーフェス要素を特定
        surface_elem = None
        surface_type = None
        for child in bb:
            st = SURFACE_TYPE_MAP.get(child.tag)
            if st is not None:
                surface_elem = child
                surface_type = st
                break
        if surface_elem is None:
            continue

        # lod2MultiSurface / lod2Geometry 配下の MultiSurface を取得
        ms = surface_elem.find(f'.//{{{GML}}}MultiSurface')
        if ms is None:
            ms = surface_elem.find(f'.//{{{GML}}}CompositeSurface')
        if ms is None:
            continue

        sem_idx = len(sem_surfaces)
        sem_surfaces.append({"type": surface_type})

        for poly in ms.iter(f'{{{GML}}}Polygon'):
            rings = polygon_to_rings(poly, reg, src_latlon)
            if rings:
                shell.append(rings)
                sem_values.append(sem_idx)

    if not shell:
        return None

    return {
        "type": "Solid",
        "lod": "2",
        "boundaries": [shell],
        "semantics": {
            "surfaces": sem_surfaces,
            "values": [sem_values],
        },
    }


# --------------------------------------------------------------------------- #
# 属性抽出
# --------------------------------------------------------------------------- #

def _cast(val: str) -> int | float | str:
    """文字列を int / float / str に型変換"""
    try:
        f = float(val)
        return int(f) if f == int(f) else f
    except (ValueError, OverflowError):
        return val


def _get_text(elem, tag_with_ns: str) -> str | None:
    """直接の子要素テキストを取得 (Clark記法タグ)"""
    e = elem.find(tag_with_ns)
    return e.text.strip() if e is not None and e.text else None


def _extract_building_id(bldg_elem, attrs: dict) -> None:
    """
    uro:buildingIDAttribute → attributes.*
      buildingID / branchID / partID / prefecture / city
    """
    bid_root = bldg_elem.find(
        f'{{{NS["uro"]}}}buildingIDAttribute'
        f'/{{{NS["uro"]}}}BuildingIDAttribute'
    )
    if bid_root is None:
        return
    URO = NS['uro']
    for tag, key in [
        (f'{{{URO}}}buildingID', 'buildingID'),
        (f'{{{URO}}}branchID',   'branchID'),
        (f'{{{URO}}}partID',     'partID'),
        (f'{{{URO}}}prefecture', 'prefecture'),
        (f'{{{URO}}}city',       'city'),
    ]:
        v = _get_text(bid_root, tag)
        if v is not None:
            attrs[key] = _cast(v)


def _extract_building_detail(bldg_elem, attrs: dict, _iur: dict) -> None:
    """
    uro:buildingDetailAttribute/uro:BuildingDetailAttribute → attributes.*
    §2 建物詳細・§3 都市計画ゾーニング属性をすべて attrs に書き込む。
    (_iur は attrs と同じオブジェクトを渡す — QGIS互換のためフラット化)
    """
    det = bldg_elem.find(
        f'{{{NS["uro"]}}}buildingDetailAttribute'
        f'/{{{NS["uro"]}}}BuildingDetailAttribute'
    )
    if det is None:
        return
    URO = NS['uro']

    # --- §2 attributes フィールド ---
    # 同一キーは先に設定された値を優先 (buildingFootprintArea > buildingRoofEdgeArea 等)
    ATTR_FIELDS = [
        (f'{{{URO}}}totalFloorArea',               'totalFloorArea'),
        (f'{{{URO}}}siteArea',                     'siteArea'),
        (f'{{{URO}}}buildingFootprintArea',         'footprintArea'),
        (f'{{{URO}}}buildingRoofEdgeArea',          'footprintArea'),      # 屋根投影面積 (上記がない場合に使用)
        (f'{{{URO}}}buildingStructureType',         'structureType'),
        (f'{{{URO}}}fireproofStructureType',        'fireproofType'),
        (f'{{{URO}}}majorUsage',                    'usage'),              # bldg:usage がなければ補完
        (f'{{{URO}}}vacancy',                       'vacancy'),
        (f'{{{URO}}}buildingCoverageRate',          'coverageRatio'),
        (f'{{{URO}}}specifiedBuildingCoverageRate', 'coverageRatio'),      # 指定建蔽率 (上記がない場合)
        (f'{{{URO}}}floorAreaRate',                 'floorAreaRatio'),
        (f'{{{URO}}}specifiedFloorAreaRate',        'floorAreaRatio'),     # 指定容積率 (上記がない場合)
        (f'{{{URO}}}buildingHeight',                'measuredHeight'),     # bldg:measuredHeight がなければ補完
        (f'{{{URO}}}surveyYear',                    'surveyYear'),
    ]
    for tag, key in ATTR_FIELDS:
        if key in attrs:
            continue                                # より上位の属性を優先
        v = _get_text(det, tag)
        if v is not None:
            attrs[key] = _cast(v)

    # --- §2 / §3: attributes に直接格納するスカラーフィールド ---
    # (QGISはattributesのみ属性として認識するため、iurフィールドもここに入れる)
    IUR_TO_ATTR = [
        (f'{{{URO}}}developmentArea',          'developmentArea'),
        (f'{{{URO}}}eaveHeight',               'eaveHeight'),
        (f'{{{URO}}}note',                     'note'),
        (f'{{{URO}}}urbanPlanType',            'urbanPlanType'),
        (f'{{{URO}}}areaClassificationType',   'areaClassificationType'),
        (f'{{{URO}}}landUseType',              'landUseType'),
    ]
    for tag, key in IUR_TO_ATTR:
        v = _get_text(det, tag)
        if v is not None:
            _iur[key] = _cast(v)

    # districtsAndZonesType → attributes.districts (複数値は"|"区切り文字列)
    districts = [
        str(_cast(e.text.strip()))
        for e in det.findall(f'{{{URO}}}districtsAndZonesType')
        if e.text
    ]
    if districts:
        _iur['districts'] = '|'.join(districts)

    # detailedUsage / orgUsage → detailedUsage ("|"区切り文字列)
    det_usages = [
        str(_cast(e.text.strip()))
        for e in det.findall(f'{{{URO}}}detailedUsage')
        if e.text
    ]
    org_usages = [
        str(_cast(e.text.strip()))
        for e in det.findall(f'{{{URO}}}orgUsage')
        if e.text
    ]
    all_usages = list(dict.fromkeys(det_usages + org_usages))   # 重複排除・順序保持
    if all_usages:
        _iur['detailedUsage'] = '|'.join(all_usages)


def _extract_disaster_risk(bldg_elem, attrs: dict) -> None:
    """
    uro:bldgDisasterRiskAttribute (複数) → attributes.*Risk

    1件なら各フィールドをフラットに展開、複数件ならコンパクトなJSON文字列に格納。
    QGISで直接参照できるよう attributes に書き込む。

    属性名の対応:
      RiverFloodingRiskAttribute  → floodRisk_*  / floodRisk  (複数件)
      LandSlideRiskAttribute      → landslideRisk_* / landslideRisk
      InlandFloodingRiskAttribute → inlandFloodRisk_* / inlandFloodRisk
      TsunamiRiskAttribute        → tsunamiRisk_* / tsunamiRisk
      HighTideRiskAttribute       → highTideRisk_* / highTideRisk
    """
    URO = NS['uro']

    RISK_MAP = {
        f'{{{URO}}}RiverFloodingRiskAttribute':  'floodRisk',
        f'{{{URO}}}LandSlideRiskAttribute':      'landslideRisk',
        f'{{{URO}}}InlandFloodingRiskAttribute': 'inlandFloodRisk',
        f'{{{URO}}}TsunamiRiskAttribute':        'tsunamiRisk',
        f'{{{URO}}}HighTideRiskAttribute':       'highTideRisk',
    }

    risk_buckets: dict[str, list[dict]] = {}

    for bda in bldg_elem.findall(f'{{{URO}}}bldgDisasterRiskAttribute'):
        for child in bda:
            attr_key = RISK_MAP.get(child.tag)
            if attr_key is None:
                continue
            entry: dict = {}
            for sub in child:
                local = sub.tag.split('}', 1)[-1]
                if sub.text and sub.text.strip():
                    entry[local] = _cast(sub.text.strip())
            if entry:
                risk_buckets.setdefault(attr_key, []).append(entry)

    for attr_key, entries in risk_buckets.items():
        if len(entries) == 1:
            # 1件: 各フィールドをフラット展開  例) floodRisk_rank, floodRisk_depth
            for field, val in entries[0].items():
                attrs[f'{attr_key}_{field}'] = val
        else:
            # 複数件: JSON文字列として格納
            attrs[attr_key] = json.dumps(entries, ensure_ascii=False)


def extract_attributes(bldg_elem) -> dict:
    """
    建物要素から attributes 辞書を生成。
    §0〜§4 の全フィールドを attributes に直接格納することで QGIS 互換にする。
    """
    attrs: dict = {}

    # --- §0: CityGML 標準建物属性 ---
    SIMPLE_FIELDS = [
        ('core:creationDate',        'creationDate'),
        ('bldg:class',               'class'),
        ('bldg:usage',               'usage'),
        ('bldg:measuredHeight',      'measuredHeight'),
        ('bldg:storeysAboveGround',  'storeysAboveGround'),
        ('bldg:storeysBelowGround',  'storeysBelowGround'),
    ]
    for xpath, key in SIMPLE_FIELDS:
        e = bldg_elem.find(xpath, NS)
        if e is not None and e.text:
            attrs[key] = _cast(e.text.strip())

    # --- §1: i-UR BuildingIDAttribute ---
    _extract_building_id(bldg_elem, attrs)

    # --- §2 & §3: BuildingDetailAttribute (建物詳細・都市計画・ゾーニング) ---
    _extract_building_detail(bldg_elem, attrs, attrs)  # iur → attrs に直接書き込む

    # --- §4: 災害リスク ---
    _extract_disaster_risk(bldg_elem, attrs)

    # --- PLATEAU gen:*Attribute (汎用キー・バリュー) ---
    # 下記は町丁目コード類・地区計画名など他の属性で代替できるため除外
    _GEN_EXCLUDE = {
        '延べ面積換算係数',
        '大字・町コード',
        '町・丁目コード',
        '13+区市町村コード+大字・町コード+町・丁目コード',
        '地区計画',
        '説明注記',
        '再開発等促進区を定める地区計画',
    }
    for tag_suffix in ('stringAttribute', 'intAttribute', 'doubleAttribute'):
        for ga in bldg_elem.findall(f'gen:{tag_suffix}', NS):
            name = ga.get('name', '').strip()
            if name in _GEN_EXCLUDE:
                continue
            ve = ga.find('gen:value', NS)
            if name and ve is not None and ve.text:
                attrs[f'gen_{name}'] = _cast(ve.text.strip())

    return attrs


# --------------------------------------------------------------------------- #
# ファイル変換コア
# --------------------------------------------------------------------------- #

def convert_file(
    gml_path: Path,
    target_epsg: int | None = None,
    cityjson_version: str = "1.1",
    verbose: bool = True,
) -> dict:
    """
    単一 GML ファイルを CityJSON 辞書に変換して返す。

    Args:
        gml_path         : 入力 GML ファイルパス
        target_epsg      : 出力座標系 EPSG コード (None = GML と同じ CRS を維持)
        cityjson_version : 出力 CityJSON バージョン ("1.1" または "2.0")
        verbose          : 進捗メッセージを表示するか

    Returns:
        指定バージョンの CityJSON 準拠辞書
    """
    if verbose:
        size_mb = gml_path.stat().st_size / 1024 / 1024
        print(f"  パース中: {gml_path.name}  ({size_mb:.1f} MB)", flush=True)

    t0 = time.perf_counter()
    tree = etree.parse(str(gml_path))
    root = tree.getroot()

    # --- CRS 読み取りと変換準備 ---
    src_epsg = _read_source_epsg(root)
    transformer, scale, crs_uri, src_latlon = _build_crs(src_epsg, target_epsg)
    if verbose:
        dst_label = f"EPSG:{target_epsg}" if target_epsg else f"EPSG:{src_epsg} (変換なし)"
        print(f"  CRS: EPSG:{src_epsg} → {dst_label}", flush=True)

    # --- Step 1: translate (原点) の決定 ---
    if verbose:
        print("  座標スキャン中...", end=' ', flush=True)

    xs, ys, zs = [], [], []
    for pl in root.iter(f'{{{GML}}}posList'):
        if pl.text:
            for lon, lat, z in parse_pos_list(pl.text, src_latlon):
                if transformer:
                    tx, ty, tz = transformer.transform(lon, lat, z)
                else:
                    tx, ty, tz = lon, lat, z
                xs.append(tx); ys.append(ty); zs.append(tz)

    if not xs:
        raise ValueError(f"座標データが見つかりません: {gml_path}")

    translate = [min(xs), min(ys), min(zs)]
    if verbose:
        print(f"translate=[{translate[0]:.4f}, {translate[1]:.4f}, {translate[2]:.3f}]",
              flush=True)

    reg = VertexRegistry(translate, scale, transformer)

    # --- Step 2: 建物変換 ---
    buildings = root.findall(f'.//{{{BLDG}}}Building')
    if verbose:
        print(f"  建物変換中: {len(buildings)} 棟...", flush=True)

    city_objects: dict[str, dict] = {}

    for bldg in buildings:
        gml_id = bldg.get(f'{{{GML}}}id') or f'bldg_{len(city_objects)}'

        geoms: list[dict] = []
        for fn in (extract_lod0, extract_lod1, extract_lod2):
            g = fn(bldg, reg, src_latlon)
            if g is not None:
                geoms.append(g)

        city_objects[gml_id] = {
            "type": "Building",
            "attributes": extract_attributes(bldg),
            "geometry": geoms,
        }

    elapsed = time.perf_counter() - t0
    if verbose:
        print(f"  完了: {len(city_objects)} 棟, {len(reg.vertices):,} 頂点"
              f"  ({elapsed:.1f}s)", flush=True)

    # --- CityJSON 出力オブジェクトを組み立て ---
    cj: dict = {
        "type": "CityJSON",
        "version": cityjson_version,
        "transform": {
            "scale": scale,
            "translate": translate,
        },
        "metadata": {
            "referenceSystem": crs_uri,
        },
        "CityObjects": city_objects,
        "vertices": reg.vertices,
    }

    # CityJSON 2.0 固有の追加対応
    # ・referenceSystem の URI は 1.1 / 2.0 いずれも同じ OGC URL 形式を使用
    # ・2.0 では GenericCityObject が拡張なしのネイティブ型になるが、
    #   本スクリプトは Building のみ出力するため差分なし
    # ・将来的に 2.0 で追加される仕様変更に対応する場合はここに記述する

    return cj


def write_cityjson(cj: dict, output_path: Path) -> None:
    """CityJSON 辞書をファイルに書き込む (compact JSON)"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(cj, f, ensure_ascii=False, separators=(',', ':'))


# --------------------------------------------------------------------------- #
# 第一段階: 単一ファイル変換
# --------------------------------------------------------------------------- #

def cmd_single(args) -> None:
    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"エラー: ファイルが存在しません: {input_path}")

    output_path = Path(args.output) if args.output else input_path.with_suffix('.city.json')

    print(f"\n[単一ファイル変換]")
    print(f"  入力: {input_path}")
    print(f"  出力: {output_path}")

    cj = convert_file(input_path, target_epsg=args.epsg,
                      cityjson_version=args.cityjson_version, verbose=True)
    write_cityjson(cj, output_path)
    print(f"  書き込み完了: {output_path}  ({output_path.stat().st_size / 1024:.0f} KB)\n")


# --------------------------------------------------------------------------- #
# 第二段階: フォルダ一括変換
# --------------------------------------------------------------------------- #

def _merge_cityjson(base: dict, addition: dict) -> None:
    """
    addition を base にマージする (in-place)。
    頂点オフセットを計算して addition の頂点インデックスを調整する。
    注意: 両ファイルの translate が異なる場合、頂点を実座標に変換して統合する。
    """
    # translate / scale を実座標に変換してから base の座標系に再量子化
    a_scale = addition['transform']['scale']
    a_trans = addition['transform']['translate']
    b_scale = base['transform']['scale']
    b_trans = base['transform']['translate']

    def remap_index(old_idx: int) -> int:
        ix, iy, iz = addition['vertices'][old_idx]
        # 実座標に戻す
        rx = ix * a_scale[0] + a_trans[0]
        ry = iy * a_scale[1] + a_trans[1]
        rz = iz * a_scale[2] + a_trans[2]
        # base の座標系で量子化
        nx = round((rx - b_trans[0]) / b_scale[0])
        ny = round((ry - b_trans[1]) / b_scale[1])
        nz = round((rz - b_trans[2]) / b_scale[2])
        key = (nx, ny, nz)
        if key not in _merge_cityjson._vmap:
            idx = len(base['vertices'])
            _merge_cityjson._vmap[key] = idx
            base['vertices'].append([nx, ny, nz])
        return _merge_cityjson._vmap[key]

    def remap_ring(ring: list[int]) -> list[int]:
        return [remap_index(i) for i in ring]

    def remap_boundaries(geom_type: str, boundaries):
        if geom_type == 'MultiPoint':
            return [remap_index(i) for i in boundaries]
        if geom_type in ('MultiLineString', 'LineString'):
            return [[remap_index(i) for i in ring] for ring in boundaries]
        if geom_type == 'MultiSurface':
            return [[remap_ring(ring) for ring in surf] for surf in boundaries]
        if geom_type in ('Solid', 'CompositeSolid'):
            return [[[remap_ring(ring) for ring in surf] for surf in shell]
                    for shell in boundaries]
        return boundaries

    for co_id, co in addition['CityObjects'].items():
        for geom in co.get('geometry', []):
            geom['boundaries'] = remap_boundaries(
                geom['type'], geom['boundaries']
            )
        base['CityObjects'][co_id] = co


def cmd_batch(args) -> None:
    input_dir = Path(args.input)
    if not input_dir.is_dir():
        sys.exit(f"エラー: フォルダが存在しません: {input_dir}")

    pattern = args.pattern or '*.gml'
    gml_files = sorted(input_dir.glob(pattern))
    if not gml_files:
        sys.exit(f"エラー: {input_dir} に {pattern} ファイルが見つかりません")

    print(f"\n[フォルダ一括変換]")
    print(f"  入力フォルダ: {input_dir}")
    print(f"  対象ファイル数: {len(gml_files)}")

    if args.merge:
        # 全ファイルを1つの CityJSON にまとめる
        output_path = (
            Path(args.output) if args.output
            else input_dir.parent / f"{input_dir.name}_merged.city.json"
        )
        print(f"  出力 (マージ): {output_path}\n")

        merged: dict | None = None
        _merge_cityjson._vmap = {}  # type: ignore[attr-defined]

        for i, gml_path in enumerate(gml_files, 1):
            print(f"[{i}/{len(gml_files)}] {gml_path.name}")
            cj = convert_file(gml_path, target_epsg=args.epsg,
                              cityjson_version=args.cityjson_version, verbose=True)
            if merged is None:
                merged = cj
                # 既存頂点をマップに登録
                for idx, v in enumerate(merged['vertices']):
                    _merge_cityjson._vmap[tuple(v)] = idx
            else:
                _merge_cityjson(merged, cj)

        if merged:
            write_cityjson(merged, output_path)
            size_mb = output_path.stat().st_size / 1024 / 1024
            print(f"\n  マージ完了: {len(merged['CityObjects'])} 棟"
                  f", {len(merged['vertices']):,} 頂点"
                  f"  → {output_path} ({size_mb:.1f} MB)\n")

    else:
        # ファイルごとに個別変換
        output_dir = Path(args.output) if args.output else input_dir.parent / f"{input_dir.name}_cityjson"
        print(f"  出力フォルダ: {output_dir}\n")

        ok = 0
        for i, gml_path in enumerate(gml_files, 1):
            print(f"[{i}/{len(gml_files)}] {gml_path.name}")
            try:
                cj = convert_file(gml_path, target_epsg=args.epsg,
                                  cityjson_version=args.cityjson_version, verbose=True)
                out = output_dir / gml_path.with_suffix('.city.json').name
                write_cityjson(cj, out)
                size_kb = out.stat().st_size / 1024
                print(f"  → {out.name}  ({size_kb:.0f} KB)\n")
                ok += 1
            except Exception as e:
                print(f"  [スキップ] エラー: {e}\n", file=sys.stderr)

        print(f"  一括変換完了: {ok}/{len(gml_files)} ファイル成功\n")


# --------------------------------------------------------------------------- #
# CLI エントリポイント
# --------------------------------------------------------------------------- #

def main() -> None:
    parser = argparse.ArgumentParser(
        description='PLATEAU CityGML → CityJSON 1.1 変換スクリプト',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        'input',
        help='入力 GML ファイルまたはフォルダ',
    )
    parser.add_argument(
        '-o', '--output',
        help='出力先 (ファイルまたはフォルダ)。省略時は自動命名',
    )
    parser.add_argument(
        '-p', '--pattern',
        default='*.gml',
        help='フォルダ変換時のファイルパターン (デフォルト: *.gml)',
    )
    parser.add_argument(
        '--merge',
        action='store_true',
        help='フォルダ変換時に全ファイルを1つの CityJSON にまとめる',
    )
    parser.add_argument(
        '--epsg',
        type=int,
        default=None,
        metavar='CODE',
        help=(
            '出力座標系の EPSG コード。'
            '例: 6677=日本平面直角IX系, 6676=VIII系, 4326=WGS84地理座標。'
            '省略時は元 CRS (通常 EPSG:6697) を維持。'
        ),
    )
    parser.add_argument(
        '--cityjson-version',
        dest='cityjson_version',
        choices=['1.1', '2.0'],
        default='1.1',
        metavar='VER',
        help=(
            '出力 CityJSON バージョン: "1.1" または "2.0" (デフォルト: 1.1)。'
            'CityJSON 2.0 は https://www.cityjson.org/specs/2.0.0/ 準拠。'
        ),
    )

    args = parser.parse_args()
    input_path = Path(args.input)

    if input_path.is_file():
        cmd_single(args)
    elif input_path.is_dir():
        cmd_batch(args)
    else:
        sys.exit(f"エラー: 入力が存在しません: {input_path}")


if __name__ == '__main__':
    main()
