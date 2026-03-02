# WMS — Web Map Service (Referência Completa)

## Índice
1. [Versões e Diferenças](#versões)
2. [GetCapabilities](#getcapabilities)
3. [GetMap](#getmap)
4. [GetFeatureInfo](#getfeatureinfo)
5. [Estilos e SLD](#estilos)
6. [Exemplos](#exemplos)

---

## 1. Versões e Diferenças

### WMS 1.1.1 (OGC 01-068r3)
- Parâmetro de CRS: `SRS`
- BBOX para EPSG:4326: **minx,miny,maxx,maxy** (lon/lat, X/Y)
- Exception format: `application/vnd.ogc.se_xml`
- Amplamente suportado, boa compatibilidade

### WMS 1.3.0 (OGC 06-042 / ISO 19128)
- Parâmetro de CRS: `CRS` (renomeado de `SRS`)
- BBOX para EPSG:4326: **miny,minx,maxy,maxx** (lat/lon, Y/X) ⚠️
- Exception format: `XML`, `INIMAGE`, `BLANK`
- Introduz suporte a CRS com eixo latitude-first
- Para CRS com eixo lon-first (ex: EPSG:3857), BBOX não muda

### Matriz de diferenças

| Aspecto | WMS 1.1.1 | WMS 1.3.0 |
|---|---|---|
| Parâmetro CRS | `SRS=EPSG:4326` | `CRS=EPSG:4326` |
| BBOX EPSG:4326 | lon,lat,lon,lat | **lat,lon,lat,lon** ⚠️ |
| BBOX EPSG:3857 | x,y,x,y | x,y,x,y (igual) |
| Exception format | `application/vnd.ogc.se_xml` | `XML` |
| Suporte EPSG:3857 | via extensão | nativo |
| Namespace Capabilities | `WMT_MS_Capabilities` | `WMS_Capabilities` |

---

## 2. GetCapabilities

```
# Negociação de versão
GET /wms?SERVICE=WMS&REQUEST=GetCapabilities
       &VERSION=1.3.0

# Sem version → servidor retorna versão mais alta
GET /wms?SERVICE=WMS&REQUEST=GetCapabilities
```

### Namespaces no XML de Capabilities

```
WMS 1.1.1: <!DOCTYPE WMT_MS_Capabilities ...>
           <WMT_MS_Capabilities version="1.1.1">

WMS 1.3.0: <WMS_Capabilities version="1.3.0"
              xmlns="http://www.opengis.net/wms">
```

### Extraindo camadas disponíveis

```python
def list_wms_layers(caps_xml, version):
    root = ET.fromstring(caps_xml)
    if version == "1.3.0":
        ns = {"wms": "http://www.opengis.net/wms"}
        layers = root.findall(".//wms:Layer/wms:Name", ns)
    else:
        layers = root.findall(".//Layer/Name")
    return [l.text for l in layers if l.text]
```

---

## 3. GetMap

### Parâmetros

| Parâmetro | Obrigatório | Descrição |
|---|---|---|
| `SERVICE` | Sim | `WMS` |
| `VERSION` | Sim | `1.1.1` ou `1.3.0` |
| `REQUEST` | Sim | `GetMap` |
| `LAYERS` | Sim | Nome(s) da camada, separados por vírgula |
| `STYLES` | Sim | Estilo(s) correspondente(s), ou vazio |
| `SRS` / `CRS` | Sim | CRS (SRS em 1.1.1, CRS em 1.3.0) |
| `BBOX` | Sim | Bounding box (ordem depende da versão e CRS) |
| `WIDTH` | Sim | Largura em pixels |
| `HEIGHT` | Sim | Altura em pixels |
| `FORMAT` | Sim | ex: `image/png`, `image/jpeg` |
| `TRANSPARENT` | Não | `TRUE` ou `FALSE` |
| `BGCOLOR` | Não | Cor de fundo (padrão `0xFFFFFF`) |
| `EXCEPTIONS` | Não | Formato de exceção |
| `TIME` | Não | Dimensão temporal (se suportado) |
| `ELEVATION` | Não | Dimensão de elevação (se suportado) |
| `SLD` | Não | URL para SLD externo |
| `SLD_BODY` | Não | SLD inline |

### BBOX e inversão de eixo

```python
def build_bbox(minlon, minlat, maxlon, maxlat, version, crs="EPSG:4326"):
    """
    Constrói BBOX respeitando a ordem de eixos por versão e CRS.
    Para CRS com eixo latitude-first (ex: EPSG:4326 no WMS 1.3.0),
    a ordem é miny,minx,maxy,maxx.
    Para CRS com eixo longitude-first (ex: EPSG:3857), a ordem é sempre
    minx,miny,maxx,maxy independente da versão.
    """
    # CRS com eixo lat-first no WMS 1.3.0
    lat_first_crs = {
        "EPSG:4326", "CRS:84",
        "urn:ogc:def:crs:EPSG::4326",
        "urn:ogc:def:crs:OGC:1.3:CRS84"
    }
    if version == "1.3.0" and crs in lat_first_crs:
        # lat/lon order: miny, minx, maxy, maxx
        return f"{minlat},{minlon},{maxlat},{maxlon}"
    else:
        # lon/lat order: minx, miny, maxx, maxy
        return f"{minlon},{minlat},{maxlon},{maxlat}"

# Brasil
bbox_111 = build_bbox(-73.99, -33.75, -28.83, 5.27, "1.1.1")
# → "-73.99,-33.75,-28.83,5.27"

bbox_130 = build_bbox(-73.99, -33.75, -28.83, 5.27, "1.3.0")
# → "-33.75,-73.99,5.27,-28.83"   ← invertido!
```

### Exemplos GetMap

```
# WMS 1.1.1
GET /wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap
       &LAYERS=municipios&STYLES=
       &SRS=EPSG:4326
       &BBOX=-73.99,-33.75,-28.83,5.27
       &WIDTH=1024&HEIGHT=768
       &FORMAT=image/png
       &TRANSPARENT=TRUE

# WMS 1.3.0 — mesma área, BBOX invertido!
GET /wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap
       &LAYERS=municipios&STYLES=
       &CRS=EPSG:4326
       &BBOX=-33.75,-73.99,5.27,-28.83
       &WIDTH=1024&HEIGHT=768
       &FORMAT=image/png
       &TRANSPARENT=TRUE

# Com EPSG:3857 — BBOX igual nas duas versões
GET /wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap
       &LAYERS=municipios&STYLES=
       &CRS=EPSG:3857
       &BBOX=-8237642,-3985244,-3207892,589933
       &WIDTH=1024&HEIGHT=768
       &FORMAT=image/png
```

---

## 4. GetFeatureInfo

Retorna informações sobre feições num ponto do mapa.

### Parâmetros adicionais ao GetMap

| Parâmetro | Descrição |
|---|---|
| `QUERY_LAYERS` | Camadas a consultar (subconjunto de LAYERS) |
| `INFO_FORMAT` | Formato da resposta: `text/plain`, `text/html`, `application/json`, `application/vnd.ogc.gml` |
| `FEATURE_COUNT` | Número máximo de feições retornadas (padrão 1) |
| `I` / `J` (1.3.0) ou `X` / `Y` (1.1.1) | Pixel clicado (coluna e linha) |

```
# WMS 1.1.1 (X, Y)
GET /wms?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetFeatureInfo
       &LAYERS=municipios&STYLES=
       &SRS=EPSG:4326&BBOX=-73.99,-33.75,-28.83,5.27
       &WIDTH=1024&HEIGHT=768&FORMAT=image/png
       &QUERY_LAYERS=municipios
       &INFO_FORMAT=application/json
       &FEATURE_COUNT=10
       &X=512&Y=384

# WMS 1.3.0 (I, J)
GET /wms?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetFeatureInfo
       &LAYERS=municipios&STYLES=
       &CRS=EPSG:4326&BBOX=-33.75,-73.99,5.27,-28.83
       &WIDTH=1024&HEIGHT=768&FORMAT=image/png
       &QUERY_LAYERS=municipios
       &INFO_FORMAT=application/json
       &FEATURE_COUNT=10
       &I=512&J=384
```

---

## 5. Estilos e SLD

```
# Solicitar camada com estilo nomeado
LAYERS=municipios&STYLES=populacao_graduada

# Múltiplas camadas, estilos correspondentes
LAYERS=municipios,estados&STYLES=pop,contorno

# SLD inline (Styled Layer Descriptor)
SLD_BODY=<StyledLayerDescriptor version="1.0.0">...</StyledLayerDescriptor>
```

---

## 6. Formatos de Imagem Comuns

| FORMAT | Uso |
|---|---|
| `image/png` | Vetoriais, transparência, mapas gerais |
| `image/png8` | PNG 8-bit, menor tamanho (GeoServer) |
| `image/jpeg` | Ortoimagens, rasters contínuos |
| `image/gif` | Legado |
| `image/tiff` | GeoTIFF (se suportado) |
| `image/svg+xml` | Vetorial escalável (poucos servidores) |
