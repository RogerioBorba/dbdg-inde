# WMTS — Web Map Tile Service

## Índice
1. [Visão Geral](#visão-geral)
2. [GetCapabilities](#getcapabilities)
3. [GetTile](#gettile)
4. [TileMatrixSet](#tilematrixset)
5. [GetFeatureInfo](#getfeatureinfo)
6. [Exemplos](#exemplos)

---

## 1. Visão Geral

WMTS (OGC 07-057r7) serve mapas como tiles pré-renderizados em grade regular, otimizado para performance via cache. Diferença fundamental do WMS: tiles têm dimensões fixas (geralmente 256×256px) em escalas pré-definidas.

**Quando usar WMTS vs WMS:**
- **WMTS**: visualização em clientes web/mobile, alta performance, cache eficiente
- **WMS**: consultas dinâmicas, filtros, estilos customizados, GetFeatureInfo complexo

---

## 2. GetCapabilities

```
GET /wmts?SERVICE=WMTS&VERSION=1.0.0&REQUEST=GetCapabilities
```

O documento de Capabilities contém:
- `Layer`: camadas disponíveis com estilos e TileMatrixSets suportados
- `TileMatrixSet`: definições das grades (escalas, origens, tamanhos de tile)
- `ResourceURL` (REST): templates de URL para acesso RESTful

---

## 3. GetTile

### Via KVP (Key-Value Pair)

```
GET /wmts?SERVICE=WMTS
        &VERSION=1.0.0
        &REQUEST=GetTile
        &LAYER=ortoimagem
        &STYLE=default
        &FORMAT=image/png
        &TILEMATRIXSET=WebMercatorQuad
        &TILEMATRIX=10
        &TILEROW=387
        &TILECOL=302
```

### Via REST (ResourceURL)

Template típico:
```
https://server/wmts/{Layer}/{Style}/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.{format}
https://server/wmts/ortoimagem/default/WebMercatorQuad/10/387/302.png
```

### Parâmetros obrigatórios

| Parâmetro | Descrição |
|---|---|
| `LAYER` | Nome da camada |
| `STYLE` | Estilo (`default` geralmente) |
| `FORMAT` | `image/png`, `image/jpeg` |
| `TILEMATRIXSET` | Grade de tiles (ex: `WebMercatorQuad`, `NZTM2000Quad`) |
| `TILEMATRIX` | Nível de zoom (identificador, não necessariamente inteiro) |
| `TILEROW` | Linha do tile (Y) |
| `TILECOL` | Coluna do tile (X) |

---

## 4. TileMatrixSet

Define o conjunto de grades para diferentes escalas. O mais comum é `WebMercatorQuad` (Google/OSM).

### WebMercatorQuad (EPSG:3857)

| TileMatrix | Escala (aprox) | Tiles totais | Uso típico |
|---|---|---|---|
| 0 | 1:559 milhões | 1×1 | Mundo inteiro |
| 5 | 1:17 milhões | 32×32 | Continente |
| 10 | 1:545 mil | 1024×1024 | Cidade grande |
| 15 | 1:17 mil | 32k×32k | Bairro |
| 18 | 1:2 mil | 262k×262k | Rua |

### Calculando TileRow/TileCol a partir de lon/lat

```python
import math

def lonlat_to_tile(lon, lat, zoom):
    """Converte longitude/latitude para TileCol/TileRow no WebMercatorQuad"""
    n = 2 ** zoom
    col = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    row = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return col, row

# São Paulo (-23.5505, -46.6333) no zoom 12
col, row = lonlat_to_tile(-46.6333, -23.5505, 12)
print(f"TileCol={col}, TileRow={row}")
# → TileCol=2327, TileRow=2998

def tile_bbox(col, row, zoom):
    """Retorna bbox geográfica (lon/lat) de um tile"""
    n = 2 ** zoom
    min_lon = col / n * 360.0 - 180.0
    max_lon = (col + 1) / n * 360.0 - 180.0
    min_lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * (row + 1) / n)))
    max_lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * row / n)))
    return min_lon, math.degrees(min_lat_rad), max_lon, math.degrees(max_lat_rad)
```

---

## 5. GetFeatureInfo (WMTS)

```
GET /wmts?SERVICE=WMTS
        &VERSION=1.0.0
        &REQUEST=GetFeatureInfo
        &LAYER=municipios
        &STYLE=default
        &FORMAT=image/png
        &TILEMATRIXSET=WebMercatorQuad
        &TILEMATRIX=10
        &TILEROW=387
        &TILECOL=302
        &J=128
        &I=200
        &INFOFORMAT=application/json
```

---

## 6. Exemplos

### Cliente WMTS com Leaflet (JavaScript)

```javascript
// Via plugin Leaflet WMTS ou TileLayer genérico
const wmtsLayer = L.tileLayer(
    'https://server/wmts/ortoimagem/default/WebMercatorQuad/{z}/{y}/{x}.png',
    {
        attribution: 'Fonte: Servidor',
        minZoom: 5,
        maxZoom: 18,
        tileSize: 256
    }
);
```

### Cliente WMTS com requests (Python)

```python
def download_tile(base_url, layer, style, tile_matrix_set,
                  tile_matrix, tile_row, tile_col, fmt="image/png"):
    params = {
        "SERVICE": "WMTS", "VERSION": "1.0.0", "REQUEST": "GetTile",
        "LAYER": layer, "STYLE": style, "FORMAT": fmt,
        "TILEMATRIXSET": tile_matrix_set, "TILEMATRIX": tile_matrix,
        "TILEROW": tile_row, "TILECOL": tile_col
    }
    r = requests.get(base_url, params=params, timeout=15)
    r.raise_for_status()
    return r.content  # bytes da imagem PNG/JPEG

# Download de tile para São Paulo zoom 12
tile = download_tile(
    "https://geoserver.example.com/wmts",
    "ortoimagem", "default", "WebMercatorQuad",
    "12", 2998, 2327
)
with open("tile_sao_paulo.png", "wb") as f:
    f.write(tile)
```
