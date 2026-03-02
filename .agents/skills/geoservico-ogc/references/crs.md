# CRS — Sistemas de Referência de Coordenadas

## Índice
1. [CRS Mais Utilizados](#crs-comuns)
2. [Inversão de Eixo — O Problema Central](#inversão-de-eixo)
3. [URNs OGC para CRS](#urns)
4. [Transformações com Python/Pyproj](#transformações)
5. [CRS em GML por Versão](#crs-em-gml)

---

## 1. CRS Mais Utilizados

| EPSG | Nome | Unidade | Uso Principal |
|---|---|---|---|
| EPSG:4326 | WGS 84 | graus | GPS, padrão global |
| EPSG:3857 | WebMercator (Pseudo-Mercator) | metros | Web tiles, Google, OSM |
| EPSG:4674 | SIRGAS 2000 | graus | Brasil (moderno) |
| EPSG:29190-29195 | UTM SIRGAS 2000 | metros | Brasil por fuso |
| EPSG:31981-31985 | UTM SAD69 | metros | Brasil (legado) |
| EPSG:4291 | SAD69 | graus | Brasil (legado) |
| EPSG:32601-32660 | WGS84 UTM Norte | metros | Norte do equador |
| EPSG:32701-32760 | WGS84 UTM Sul | metros | Sul do equador |

---

## 2. Inversão de Eixo — O Problema Central

Este é o bug mais comum ao trabalhar com geoserviços OGC. A confusão surge porque:

- **Convenção matemática/GIS**: eixo X = Longitude (leste-oeste), eixo Y = Latitude (norte-sul)
- **Convenção geográfica ISO**: eixo 1 = Latitude, eixo 2 = Longitude

### Comportamento por serviço e versão

| Serviço / Versão | EPSG:4326 retornado | EPSG:3857 retornado |
|---|---|---|
| WFS 1.0.0 | lon/lat (X/Y) ✅ | lon/lat |
| WFS 1.1.0 | **lat/lon (Y/X)** ⚠️ | lon/lat |
| WFS 2.0.0 | lon/lat (X/Y) ✅ | lon/lat |
| WMS 1.1.1 BBOX | minlon,minlat,maxlon,maxlat ✅ | |
| WMS 1.3.0 BBOX EPSG:4326 | **minlat,minlon,maxlat,maxlon** ⚠️ | |
| WMS 1.3.0 BBOX EPSG:3857 | minx,miny,maxx,maxy ✅ | |
| OGC API Features | lon/lat (GeoJSON padrão) ✅ | |

### Regra geral

A ISO 19111 define a ordem de eixos por CRS. Para **EPSG:4326**, a ordem oficial é **lat/lon**. Implementações mais antigas ignoravam isso e usavam lon/lat. A partir do WFS 1.1.0 e WMS 1.3.0, a implementação passou a seguir a ISO.

### CRS "CRS:84" — Solução para lon/lat consistente

A OGC definiu `CRS:84` como alias para EPSG:4326 **mas com ordem garantida lon/lat**:

```
SRSNAME=CRS:84                           # WFS — sempre lon/lat
CRS=CRS:84                               # WMS 1.3.0 — BBOX sempre lon/lat

# URN equivalente:
SRSNAME=urn:ogc:def:crs:OGC:1.3:CRS84
```

Usar `CRS:84` ou `urn:ogc:def:crs:OGC:1.3:CRS84` é a forma recomendada para obter coordenadas em lon/lat de forma consistente em qualquer versão de serviço.

### Detecção e correção programática

```python
from pyproj import CRS

def needs_axis_swap(crs_string: str, service_version: str) -> bool:
    """
    Determina se as coordenadas retornadas pelo servidor precisam ser invertidas
    para resultar em lon/lat (convenção GeoJSON/GIS).
    """
    # WFS 1.1.0 retorna lat/lon para CRS com eixo lat-first
    if service_version == "1.1.0":
        try:
            crs = CRS.from_user_input(crs_string)
            # Verifica se o primeiro eixo é latitude
            axes = crs.axis_info
            if axes and axes[0].direction.lower() in ("north", "south"):
                return True
        except Exception:
            # Fallback conservador para CRS conhecidos
            return crs_string in ("EPSG:4326", "urn:ogc:def:crs:EPSG::4326",
                                   "urn:ogc:def:crs:OGC:2:84")
    return False

def swap_coordinates(geojson_geometry):
    """Inverte lon/lat ↔ lat/lon em qualquer geometria GeoJSON"""
    import copy
    geom = copy.deepcopy(geojson_geometry)

    def swap_coords(coords):
        if isinstance(coords[0], (int, float)):
            return [coords[1], coords[0]] + list(coords[2:])
        return [swap_coords(c) for c in coords]

    geom["coordinates"] = swap_coords(geom["coordinates"])
    return geom
```

---

## 3. URNs OGC para CRS

OGC define URNs como identificadores formais de CRS. São mais verbosos, mas sem ambiguidade de eixo.

| Forma curta | URN OGC equivalente | Eixo |
|---|---|---|
| `EPSG:4326` | `urn:ogc:def:crs:EPSG::4326` | lat/lon (ISO) |
| `CRS:84` | `urn:ogc:def:crs:OGC:1.3:CRS84` | lon/lat (garantido) |
| `EPSG:3857` | `urn:ogc:def:crs:EPSG::3857` | lon/lat |
| `EPSG:4674` | `urn:ogc:def:crs:EPSG::4674` | lat/lon |

**Dica**: Em WFS 2.0.0, prefira usar URNs em `SRSNAME` para eliminar ambiguidade:

```
SRSNAME=urn:ogc:def:crs:OGC:1.3:CRS84     → sempre lon/lat
SRSNAME=urn:ogc:def:crs:EPSG::4326        → lat/lon (conforme ISO)
```

---

## 4. Transformações com Python/Pyproj

```python
from pyproj import Transformer

def transform_coordinates(x, y, from_crs, to_crs, always_xy=True):
    """
    Transforma coordenadas entre CRS.
    always_xy=True força ordem lon/lat independente da definição do CRS.
    """
    transformer = Transformer.from_crs(from_crs, to_crs, always_xy=always_xy)
    return transformer.transform(x, y)

# Exemplos
# SIRGAS 2000 (EPSG:4674) → WebMercator (EPSG:3857)
x, y = transform_coordinates(-46.6333, -23.5505, "EPSG:4674", "EPSG:3857")
# → (-5185588.0, -2700000.0) aproximado

# UTM para WGS84 lon/lat
lon, lat = transform_coordinates(333000, 7399000, "EPSG:31983", "EPSG:4326")
```

### Reprojetando coleção GeoJSON

```python
import json
from pyproj import Transformer
from shapely.geometry import shape, mapping
from shapely.ops import transform as shapely_transform

def reproject_geojson(geojson_dict, from_crs, to_crs):
    transformer = Transformer.from_crs(from_crs, to_crs, always_xy=True)
    features = []
    for feat in geojson_dict.get("features", []):
        geom = shape(feat["geometry"])
        projected = shapely_transform(transformer.transform, geom)
        features.append({**feat, "geometry": mapping(projected)})
    return {**geojson_dict, "features": features}
```

---

## 5. CRS em GML por Versão

### GML 2 (WFS 1.0.0)
```xml
<gml:Point srsName="EPSG:4326">
  <gml:coordinates>-46.6333,-23.5505</gml:coordinates>
</gml:Point>
```

### GML 3.1 (WFS 1.1.0) — ATENÇÃO: lat/lon!
```xml
<!-- EPSG:4326 no GML 3.1 = lat/lon conforme ISO -->
<gml:Point srsName="urn:ogc:def:crs:EPSG::4326"
           xmlns:gml="http://www.opengis.net/gml">
  <gml:pos>-23.5505 -46.6333</gml:pos>
  <!-- lat lon → Y X → -23.55, -46.63 -->
</gml:Point>

<!-- Para forçar lon/lat em GML 3.1, usar CRS:84 -->
<gml:Point srsName="urn:ogc:def:crs:OGC:1.3:CRS84">
  <gml:pos>-46.6333 -23.5505</gml:pos>
</gml:Point>
```

### GML 3.2 (WFS 2.0.0)
```xml
<gml:Point srsName="urn:ogc:def:crs:EPSG::4326"
           gml:id="p1"
           xmlns:gml="http://www.opengis.net/gml/3.2">
  <gml:pos>-23.5505 -46.6333</gml:pos>
</gml:Point>
```

### Extraindo coordenadas de GML com cuidado de eixo

```python
def parse_gml_point(gml_element, srs_name, wfs_version):
    """Extrai lon/lat de um elemento gml:Point respeitando inversão de eixo."""
    ns = {"gml": "http://www.opengis.net/gml",
          "gml32": "http://www.opengis.net/gml/3.2"}
    pos = (gml_element.find("gml:pos", ns) or
           gml_element.find("gml32:pos", ns))
    if pos is None:
        coords = gml_element.find("gml:coordinates", ns)
        x, y = map(float, coords.text.strip().split(","))
        return x, y  # GML 2 sempre lon/lat

    vals = list(map(float, pos.text.strip().split()))
    v0, v1 = vals[0], vals[1]

    # WFS 1.1.0 + EPSG:4326 → lat/lon → inverter para lon/lat
    lat_first_srs = {"urn:ogc:def:crs:EPSG::4326", "EPSG:4326"}
    if wfs_version == "1.1.0" and srs_name in lat_first_srs:
        return v1, v0  # inverter para lon/lat
    return v0, v1
```
