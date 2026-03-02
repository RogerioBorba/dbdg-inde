# Filtros OGC — Filter Encoding e CQL

## Índice
1. [OGC Filter Encoding por Versão](#ogc-filter)
2. [Comparação: Filter XML vs CQL](#comparação)
3. [Operadores de Comparação](#comparação-ops)
4. [Operadores Espaciais](#espaciais)
5. [Operadores Temporais](#temporais)
6. [Operadores Lógicos](#lógicos)
7. [CQL / ECQL (GeoServer)](#cql)
8. [Exemplos Completos](#exemplos)

---

## 1. OGC Filter Encoding por Versão

| Versão Filter | Padrão OGC | Usado em | Namespace |
|---|---|---|---|
| FE 1.0 | OGC 02-059 | WFS 1.0.0 | `http://www.opengis.net/ogc` |
| FE 1.1 | OGC 04-095 | WFS 1.1.0, WMS 1.1.1-1.3.0 | `http://www.opengis.net/ogc` |
| FES 2.0 | OGC 09-026r2 | WFS 2.0.0, OGC API | `http://www.opengis.net/fes/2.0` |

### Diferenças principais entre FE 1.x e FES 2.0

| Elemento | FE 1.x | FES 2.0 |
|---|---|---|
| Nome da propriedade | `<ogc:PropertyName>` | `<fes:ValueReference>` |
| Namespace | `xmlns:ogc="http://www.opengis.net/ogc"` | `xmlns:fes="http://www.opengis.net/fes/2.0"` |
| Identificador de feição | `<ogc:FeatureId fid="..."/>` | `<fes:ResourceId rid="..."/>` |
| Operador LIKE | `<ogc:PropertyIsLike wildCard="%" singleChar="_" escapeChar="\">` | `<fes:PropertyIsLike wildCard="%" singleChar="_" escapeChar="\">` |
| Spatial ops | `<ogc:Intersects>` | `<fes:Intersects>` |
| Temporal ops | parcial | ✅ completo |

---

## 2. Comparação: Filter XML vs CQL

```
# Mesmo filtro expresso das três formas

# 1. OGC Filter XML (WFS 1.x ou 2.0 — mais portável)
FILTER=<Filter><PropertyIsEqualTo><PropertyName>estado</PropertyName><Literal>SP</Literal></PropertyIsEqualTo></Filter>

# 2. CQL (Common Query Language — extensão, mais legível)
CQL_FILTER=estado='SP'

# 3. ECQL (Extended CQL — GeoServer, mais poderoso)
CQL_FILTER=estado='SP' AND populacao > 1000000
```

---

## 3. Operadores de Comparação

### FE 1.x (WFS 1.0/1.1)

```xml
<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">

  <!-- Igual -->
  <ogc:PropertyIsEqualTo>
    <ogc:PropertyName>estado</ogc:PropertyName>
    <ogc:Literal>SP</ogc:Literal>
  </ogc:PropertyIsEqualTo>

  <!-- Diferente -->
  <ogc:PropertyIsNotEqualTo>
    <ogc:PropertyName>estado</ogc:PropertyName>
    <ogc:Literal>RJ</ogc:Literal>
  </ogc:PropertyIsNotEqualTo>

  <!-- Menor que -->
  <ogc:PropertyIsLessThan>
    <ogc:PropertyName>populacao</ogc:PropertyName>
    <ogc:Literal>100000</ogc:Literal>
  </ogc:PropertyIsLessThan>

  <!-- Menor ou igual, Maior que, Maior ou igual: analogamente -->

  <!-- Entre (between) -->
  <ogc:PropertyIsBetween>
    <ogc:PropertyName>populacao</ogc:PropertyName>
    <ogc:LowerBoundary><ogc:Literal>100000</ogc:Literal></ogc:LowerBoundary>
    <ogc:UpperBoundary><ogc:Literal>1000000</ogc:Literal></ogc:UpperBoundary>
  </ogc:PropertyIsBetween>

  <!-- Like (% = qualquer seq, _ = um char) -->
  <ogc:PropertyIsLike wildCard="%" singleChar="_" escapeChar="\">
    <ogc:PropertyName>nome</ogc:PropertyName>
    <ogc:Literal>São%</ogc:Literal>
  </ogc:PropertyIsLike>

  <!-- Nulo -->
  <ogc:PropertyIsNull>
    <ogc:PropertyName>populacao</ogc:PropertyName>
  </ogc:PropertyIsNull>

</ogc:Filter>
```

### FES 2.0 (WFS 2.0)

```xml
<fes:Filter xmlns:fes="http://www.opengis.net/fes/2.0">

  <fes:PropertyIsEqualTo>
    <fes:ValueReference>estado</fes:ValueReference>
    <fes:Literal>SP</fes:Literal>
  </fes:PropertyIsEqualTo>

  <!-- Between -->
  <fes:PropertyIsBetween>
    <fes:ValueReference>populacao</fes:ValueReference>
    <fes:LowerBoundary><fes:Literal>100000</fes:Literal></fes:LowerBoundary>
    <fes:UpperBoundary><fes:Literal>1000000</fes:Literal></fes:UpperBoundary>
  </fes:PropertyIsBetween>

  <!-- Like com matchCase -->
  <fes:PropertyIsLike wildCard="%" singleChar="_" escapeChar="\" matchCase="false">
    <fes:ValueReference>nome</fes:ValueReference>
    <fes:Literal>são%</fes:Literal>
  </fes:PropertyIsLike>

</fes:Filter>
```

---

## 4. Operadores Espaciais

### Operadores disponíveis

| Operador | Descrição | FE 1.x | FES 2.0 |
|---|---|---|---|
| `Equals` | Geometrias iguais | ✅ | ✅ |
| `Disjoint` | Sem interseção | ✅ | ✅ |
| `Touches` | Toca na borda | ✅ | ✅ |
| `Within` | Dentro de | ✅ | ✅ |
| `Overlaps` | Sobrepõe | ✅ | ✅ |
| `Crosses` | Cruza | ✅ | ✅ |
| `Intersects` | Intersecta | ✅ | ✅ |
| `Contains` | Contém | ✅ | ✅ |
| `DWithin` | Dentro de distância | ✅ | ✅ |
| `Beyond` | Além de distância | ✅ | ✅ |
| `BBOX` | Bounding box rápido | ✅ | ✅ |

### Exemplos FE 1.x

```xml
<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc"
            xmlns:gml="http://www.opengis.net/gml">

  <!-- Intersecta ponto -->
  <ogc:Intersects>
    <ogc:PropertyName>geom</ogc:PropertyName>
    <gml:Point srsName="EPSG:4326">
      <gml:coordinates>-46.6333,-23.5505</gml:coordinates>
    </gml:Point>
  </ogc:Intersects>

  <!-- Intersecta polígono -->
  <ogc:Intersects>
    <ogc:PropertyName>geom</ogc:PropertyName>
    <gml:Polygon srsName="EPSG:4326">
      <gml:exterior>
        <gml:LinearRing>
          <gml:coordinates>
            -47.0,-24.0 -46.0,-24.0 -46.0,-23.0 -47.0,-23.0 -47.0,-24.0
          </gml:coordinates>
        </gml:LinearRing>
      </gml:exterior>
    </gml:Polygon>
  </ogc:Intersects>

  <!-- BBOX (mais eficiente para grandes volumes) -->
  <ogc:BBOX>
    <ogc:PropertyName>geom</ogc:PropertyName>
    <gml:Envelope srsName="EPSG:4326">
      <gml:lowerCorner>-47.0 -24.0</gml:lowerCorner>
      <gml:upperCorner>-46.0 -23.0</gml:upperCorner>
    </gml:Envelope>
  </ogc:BBOX>

  <!-- DWithin (dentro de N metros) -->
  <ogc:DWithin>
    <ogc:PropertyName>geom</ogc:PropertyName>
    <gml:Point srsName="EPSG:4326">
      <gml:coordinates>-46.6333,-23.5505</gml:coordinates>
    </gml:Point>
    <ogc:Distance units="m">5000</ogc:Distance>
  </ogc:DWithin>

</ogc:Filter>
```

### Exemplos FES 2.0

```xml
<fes:Filter xmlns:fes="http://www.opengis.net/fes/2.0"
            xmlns:gml="http://www.opengis.net/gml/3.2">

  <fes:Intersects>
    <fes:ValueReference>geom</fes:ValueReference>
    <gml:Point srsName="urn:ogc:def:crs:OGC:1.3:CRS84" gml:id="q1">
      <gml:pos>-46.6333 -23.5505</gml:pos>
    </gml:Point>
  </fes:Intersects>

  <fes:DWithin>
    <fes:ValueReference>geom</fes:ValueReference>
    <gml:Point srsName="urn:ogc:def:crs:OGC:1.3:CRS84" gml:id="q2">
      <gml:pos>-46.6333 -23.5505</gml:pos>
    </gml:Point>
    <fes:Distance uom="m">5000</fes:Distance>
  </fes:DWithin>

</fes:Filter>
```

---

## 5. Operadores Temporais (FES 2.0)

```xml
<fes:Filter xmlns:fes="http://www.opengis.net/fes/2.0">

  <!-- Depois de uma data -->
  <fes:After>
    <fes:ValueReference>data_ocorrencia</fes:ValueReference>
    <gml:TimeInstant xmlns:gml="http://www.opengis.net/gml/3.2" gml:id="t1">
      <gml:timePosition>2024-01-01T00:00:00Z</gml:timePosition>
    </gml:TimeInstant>
  </fes:After>

  <!-- Dentro de um período -->
  <fes:During>
    <fes:ValueReference>data_ocorrencia</fes:ValueReference>
    <gml:TimePeriod xmlns:gml="http://www.opengis.net/gml/3.2" gml:id="tp1">
      <gml:beginPosition>2024-01-01T00:00:00Z</gml:beginPosition>
      <gml:endPosition>2024-12-31T23:59:59Z</gml:endPosition>
    </gml:TimePeriod>
  </fes:During>

</fes:Filter>
```

---

## 6. Operadores Lógicos

```xml
<!-- AND -->
<ogc:And>
  <ogc:PropertyIsEqualTo>...</ogc:PropertyIsEqualTo>
  <ogc:Intersects>...</ogc:Intersects>
</ogc:And>

<!-- OR -->
<ogc:Or>
  <ogc:PropertyIsEqualTo>
    <ogc:PropertyName>estado</ogc:PropertyName>
    <ogc:Literal>SP</ogc:Literal>
  </ogc:PropertyIsEqualTo>
  <ogc:PropertyIsEqualTo>
    <ogc:PropertyName>estado</ogc:PropertyName>
    <ogc:Literal>RJ</ogc:Literal>
  </ogc:PropertyIsEqualTo>
</ogc:Or>

<!-- NOT -->
<ogc:Not>
  <ogc:PropertyIsNull>
    <ogc:PropertyName>populacao</ogc:PropertyName>
  </ogc:PropertyIsNull>
</ogc:Not>
```

---

## 7. CQL / ECQL (GeoServer)

CQL é uma extensão (não padrão OGC) implementada pelo GeoServer e outros servidores. ECQL (Extended CQL) adiciona operações extras.

### Parâmetros

```
CQL_FILTER=...    # Passado como query string no GET
FILTER=...        # Filter XML codificado (padrão OGC)
```

### Comparações

```
# Igual, diferente
estado='SP'
estado<>'RJ'

# Numérico
populacao > 1000000
populacao BETWEEN 100000 AND 1000000

# Like (case insensitive com ilike no ECQL)
nome LIKE 'São%'
nome ILIKE 'são%'   # ECQL

# Nulo
populacao IS NULL
populacao IS NOT NULL

# IN
estado IN ('SP','RJ','MG')
```

### Espaciais (ECQL — WKT)

```
# Intersecta ponto
INTERSECTS(geom, POINT(-46.63 -23.55))

# Intersecta polígono
INTERSECTS(geom, POLYGON((-47 -24, -46 -24, -46 -23, -47 -23, -47 -24)))

# Dentro de distância (em graus para EPSG:4326)
DWITHIN(geom, POINT(-46.63 -23.55), 0.05, degrees)
DWITHIN(geom, POINT(-46.63 -23.55), 5000, meters)

# BBOX rápido
BBOX(geom, -47.0, -24.0, -46.0, -23.0)
BBOX(geom, -47.0, -24.0, -46.0, -23.0, 'EPSG:4326')
```

### Combinações

```
estado='SP' AND populacao > 1000000
nome LIKE 'São%' OR nome LIKE 'Santo%'
NOT (estado='AM' OR estado='PA')
INTERSECTS(geom, POINT(-46.63 -23.55)) AND populacao > 500000
```

---

## 8. Exemplos Completos

### Exemplo: Buscar municípios de SP com população > 500k, filtrando por bbox

```python
import requests
from urllib.parse import quote

def get_municipios_sp_grandes(wfs_url, version="2.0.0"):
    if version >= "2.0.0":
        type_key = "TYPENAMES"
        # Usar CQL (mais simples)
        params = {
            "SERVICE": "WFS", "VERSION": version,
            "REQUEST": "GetFeature",
            type_key: "ns:municipios",
            "CQL_FILTER": "estado='SP' AND populacao>500000",
            "OUTPUTFORMAT": "application/json",
            "COUNT": 100,
            "SORTBY": "populacao DESC"
        }
    else:
        # WFS 1.x — usar Filter XML
        filter_xml = """<ogc:Filter xmlns:ogc="http://www.opengis.net/ogc">
          <ogc:And>
            <ogc:PropertyIsEqualTo>
              <ogc:PropertyName>estado</ogc:PropertyName>
              <ogc:Literal>SP</ogc:Literal>
            </ogc:PropertyIsEqualTo>
            <ogc:PropertyIsGreaterThan>
              <ogc:PropertyName>populacao</ogc:PropertyName>
              <ogc:Literal>500000</ogc:Literal>
            </ogc:PropertyIsGreaterThan>
          </ogc:And>
        </ogc:Filter>"""
        params = {
            "SERVICE": "WFS", "VERSION": version,
            "REQUEST": "GetFeature",
            "TYPENAME": "ns:municipios",
            "FILTER": filter_xml,
            "OUTPUTFORMAT": "application/json",
            "MAXFEATURES": 100
        }

    r = requests.get(wfs_url, params=params, timeout=30)
    return r.json()
```

### Exemplo: Filtro espacial — feições que intersectam geometria WKT

```python
def spatial_filter_wfs(wfs_url, typename, wkt_geometry, version="2.0.0",
                        geom_field="geom", crs="EPSG:4326"):
    params = {
        "SERVICE": "WFS", "VERSION": version,
        "REQUEST": "GetFeature",
        "TYPENAMES" if version >= "2.0.0" else "TYPENAME": typename,
        "OUTPUTFORMAT": "application/json",
        "CQL_FILTER": f"INTERSECTS({geom_field}, {wkt_geometry})"
    }
    r = requests.get(wfs_url, params=params, timeout=30)
    return r.json()

# Uso
geojson = spatial_filter_wfs(
    "https://geoserver.example.com/wfs",
    "ns:municipios",
    "POLYGON((-47 -24, -46 -24, -46 -23, -47 -23, -47 -24))"
)
```
