# WFS — Web Feature Service (Referência Completa)

## Índice
1. [Visão Geral das Versões](#versões)
2. [GetCapabilities e Negociação de Versão](#getcapabilities)
3. [DescribeFeatureType](#describefeaturetype)
4. [GetFeature — Parâmetros por Versão](#getfeature)
5. [Paginação (WFS 2.0)](#paginação)
6. [Stored Queries (WFS 2.0)](#stored-queries)
7. [GetPropertyValue (WFS 2.0)](#getpropertyvalue)
8. [Transações (WFS-T)](#transações)
9. [OutputFormats](#outputformats)
10. [Exemplos Completos por Versão](#exemplos)

---

## 1. Visão Geral das Versões

### WFS 1.0.0 (OGC 00-049r6)
- GML 2 como formato padrão
- Filtros OGC Filter Encoding 1.0
- Coordenadas lon/lat para EPSG:4326
- Sem paginação nativa
- Operações: GetCapabilities, DescribeFeatureType, GetFeature, Transaction (WFS-T)

### WFS 1.1.0 (OGC 04-094)
- GML 3.1.1 como formato padrão
- Filtros OGC Filter Encoding 1.1
- **ATENÇÃO**: coordenadas lat/lon para EPSG:4326 (inversão de eixo!)
- Sem paginação nativa
- `GetGmlObject` adicionado
- Operações: GetCapabilities, DescribeFeatureType, GetFeature, GetGmlObject, LockFeature, Transaction

### WFS 2.0.0 (OGC 09-025r2 / ISO 19142:2010)
- GML 3.2.1 como formato padrão
- Filtros OGC FES 2.0 (Filter Encoding Standard)
- Coordenadas lon/lat para EPSG:4326 (voltou ao comportamento do 1.0)
- **Paginação nativa**: `COUNT` + `STARTINDEX`
- **Stored Queries**: queries parametrizadas e reutilizáveis
- `GetPropertyValue`: extrai valores de propriedades específicas
- `CreateStoredQuery`, `DropStoredQuery`, `ListStoredQueries`, `DescribeStoredQueries`
- Joins entre tipos de feições via `TYPENAMES`
- `ACCEPTVERSIONS` para negociação
- Operações: GetCapabilities, DescribeFeatureType, GetFeature, GetPropertyValue,
  LockFeature, GetFeatureWithLock, ListStoredQueries, DescribeStoredQueries,
  CreateStoredQuery, DropStoredQuery, Transaction

### WFS 2.0.2 (OGC 09-025r2, corrigendum)
- Correções e clarificações da 2.0.0
- Nenhuma mudança de API relevante para clientes

---

## 2. GetCapabilities e Negociação de Versão

### Parâmetros

| Parâmetro | Obrigatório | Descrição |
|---|---|---|
| `SERVICE` | Sim | Sempre `WFS` |
| `REQUEST` | Sim | Sempre `GetCapabilities` |
| `ACCEPTVERSIONS` | Não | Lista de versões aceitas, separadas por vírgula, ordem decrescente de preferência. **Apenas WFS 2.0** formalmente, mas servidores modernos o aceitam. |
| `VERSION` | Não | Versão exata (alternativa ao ACCEPTVERSIONS) |
| `ACCEPTFORMATS` | Não | Formato de resposta (`text/xml` padrão) |
| `SECTIONS` | Não | Seções do documento a retornar (`ServiceIdentification`, `ServiceProvider`, `OperationsMetadata`, `FeatureTypeList`, `Filter_Capabilities`) |
| `UPDATESEQUENCE` | Não | Para cache condicional |

### Algoritmo de Negociação (OWS Common 1.1, seção 7.3.2)

```
Cliente envia ACCEPTVERSIONS=v1,v2,v3 (decrescente)
Servidor avalia:
  - Para cada versão v na lista (da maior para menor):
    - Se servidor suporta v → retorna Capabilities com version=v
  - Se nenhuma versão for suportada → ExceptionReport: VersionNegotiationFailed
  - Se ACCEPTVERSIONS ausente → retorna versão mais alta suportada pelo servidor
```

### Exemplos

```
# Negociação flexível — preferir 2.0, aceitar 1.1 e 1.0 como fallback
GET /wfs?SERVICE=WFS&REQUEST=GetCapabilities&ACCEPTVERSIONS=2.0.0,1.1.0,1.0.0

# Forçar versão específica
GET /wfs?SERVICE=WFS&REQUEST=GetCapabilities&VERSION=2.0.0

# Apenas metadados do serviço (sem lista completa de camadas)
GET /wfs?SERVICE=WFS&REQUEST=GetCapabilities&SECTIONS=ServiceIdentification,OperationsMetadata
```

### Extraindo versão negociada do XML

```python
import requests
from xml.etree import ElementTree as ET

def get_negotiated_version(base_url, preferred=("2.0.0", "1.1.0", "1.0.0")):
    params = {
        "SERVICE": "WFS",
        "REQUEST": "GetCapabilities",
        "ACCEPTVERSIONS": ",".join(preferred)
    }
    r = requests.get(base_url, params=params, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    version = root.attrib.get("version")
    if not version:
        # Alguns servidores colocam em namespace
        version = root.get("{http://www.opengis.net/wfs/2.0}version") or \
                  root.get("{http://www.opengis.net/wfs}version")
    return version

# Uso
version = get_negotiated_version("https://geoserver.example.com/wfs")
print(f"Versão negociada: {version}")
# → "2.0.0"
```

### Namespaces XML por versão

```
WFS 1.0.0: xmlns:wfs="http://www.opengis.net/wfs"
WFS 1.1.0: xmlns:wfs="http://www.opengis.net/wfs"
WFS 2.0.0: xmlns:wfs="http://www.opengis.net/wfs/2.0"
           xmlns:ows="http://www.opengis.net/ows/1.1"
           xmlns:fes="http://www.opengis.net/fes/2.0"
```

---

## 3. DescribeFeatureType

Retorna o XML Schema (XSD) dos tipos de feição, descrevendo seus atributos e tipos.

```
# WFS 1.x
GET /wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=DescribeFeatureType
       &TYPENAME=ns:municipios

# WFS 2.0
GET /wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=DescribeFeatureType
       &TYPENAMES=ns:municipios
       &OUTPUTFORMAT=application/gml+xml; version=3.2

# Múltiplos tipos
GET /wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=DescribeFeatureType
       &TYPENAMES=ns:municipios,ns:estados

# Todos os tipos (omitir TYPENAMES)
GET /wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=DescribeFeatureType
```

### Extraindo campos do XSD

```python
def describe_feature_type(base_url, typename, version):
    param_key = "TYPENAMES" if version >= "2.0.0" else "TYPENAME"
    r = requests.get(base_url, params={
        "SERVICE": "WFS", "VERSION": version,
        "REQUEST": "DescribeFeatureType",
        param_key: typename
    })
    root = ET.fromstring(r.content)
    ns = {"xs": "http://www.w3.org/2001/XMLSchema"}
    fields = []
    for el in root.findall(".//xs:element[@name]", ns):
        fields.append({
            "name": el.get("name"),
            "type": el.get("type", ""),
            "nillable": el.get("nillable", "false"),
            "minOccurs": el.get("minOccurs", "1"),
        })
    return fields
```

---

## 4. GetFeature — Parâmetros por Versão

### Tabela de Parâmetros

| Parâmetro | WFS 1.0.0 | WFS 1.1.0 | WFS 2.0.0 | Notas |
|---|---|---|---|---|
| Tipo de feição | `TYPENAME` | `TYPENAME` | `TYPENAMES` | 2.0 aceita múltiplos separados por vírgula |
| Limite | `MAXFEATURES` | `MAXFEATURES` | `COUNT` | |
| Início (paginação) | ❌ | ❌ | `STARTINDEX` | Inicia em 0 |
| CRS de saída | `SRSNAME` | `SRSNAME` | `SRSNAME` | |
| Bbox | `BBOX` | `BBOX` | `BBOX` | Formato: minx,miny,maxx,maxy[,crs] |
| Filtro XML | `FILTER` | `FILTER` | `FILTER` | URL-encoded XML |
| Filtro CQL | `CQL_FILTER` | `CQL_FILTER` | `CQL_FILTER` | Extensão (GeoServer/MapServer) |
| Propriedades | `PROPERTYNAME` | `PROPERTYNAME` | `PROPERTYNAME` | Projeção de campos |
| Ordenação | ❌ | `SORTBY` | `SORTBY` | ex: `campo ASC` |
| IDs de feição | `FEATUREID` | `FEATUREID` | `RESOURCEID` | |
| Formato de saída | `OUTPUTFORMAT` | `OUTPUTFORMAT` | `OUTPUTFORMAT` | |
| Resultado tipo | — | — | `RESULTTYPE` | `results` (default) ou `hits` |

### RESULTTYPE=hits (WFS 2.0)

Retorna apenas a contagem, sem feições — útil para saber total antes de paginar:

```
GET /wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature
       &TYPENAMES=ns:municipios
       &RESULTTYPE=hits
       &CQL_FILTER=estado='SP'
```

Resposta:
```xml
<wfs:FeatureCollection ... numberMatched="645" numberReturned="0" timeStamp="..."/>
```

### BBOX

```
# Sem CRS declarado → CRS default da camada
BBOX=-73.99,-33.75,-28.83,5.27

# Com CRS explícito (WFS 1.x)
BBOX=-73.99,-33.75,-28.83,5.27,EPSG:4326

# Com CRS explícito (WFS 2.0 — URN)
BBOX=-73.99,-33.75,-28.83,5.27,urn:ogc:def:crs:EPSG::4326
```

### SORTBY

```
# Ordenação simples
SORTBY=populacao DESC

# Múltiplos campos
SORTBY=estado ASC,municipio ASC

# WFS 1.1.0+ e 2.0.0
```

### PROPERTYNAME — Projeção de campos

```
# Retornar apenas campos específicos
PROPERTYNAME=nome,populacao,geom

# WFS 2.0: com namespace
PROPERTYNAME=ns:nome,ns:populacao,ns:geom
```

---

## 5. Paginação (WFS 2.0)

### Modelo de paginação

```
totalFeatures = numberMatched
página_N = GetFeature + COUNT=page_size + STARTINDEX=(N-1)*page_size
```

### Campos no response

```xml
<wfs:FeatureCollection
  numberMatched="12543"
  numberReturned="500"
  timeStamp="2024-01-01T00:00:00Z"
  next="https://server/wfs?...&STARTINDEX=500"
  previous="https://server/wfs?...&STARTINDEX=0">
  ...
</wfs:FeatureCollection>
```

### Observações importantes

- `numberMatched="unknown"` — servidor não suporta contagem total (paginar até batch vazio)
- `next` nem sempre está presente mesmo quando há mais dados — usar `numberMatched` como controle
- GeoJSON response usa `totalFeatures` (GeoServer) em vez de `numberMatched`

### Implementação robusta

```python
import requests

def paginate_wfs(url, typename, version="2.0.0", page_size=500,
                 cql_filter=None, output_format="application/json"):
    type_key = "TYPENAMES" if version >= "2.0.0" else "TYPENAME"
    count_key = "COUNT" if version >= "2.0.0" else "MAXFEATURES"

    base_params = {
        "SERVICE": "WFS", "VERSION": version, "REQUEST": "GetFeature",
        type_key: typename,
        count_key: page_size,
        "OUTPUTFORMAT": output_format,
    }
    if cql_filter:
        base_params["CQL_FILTER"] = cql_filter

    features = []
    start = 0
    total = None

    while True:
        params = {**base_params}
        if version >= "2.0.0":
            params["STARTINDEX"] = start

        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        data = r.json()

        batch = data.get("features", [])
        features.extend(batch)

        if total is None:
            total = data.get("totalFeatures") or data.get("numberMatched")

        print(f"  Baixados {len(features)}/{total or '?'} feições...")

        if len(batch) < page_size:
            break
        if total and len(features) >= int(total):
            break
        start += page_size

    return features
```

---

## 6. Stored Queries (WFS 2.0.0)

### Operações

```
# Listar todas as stored queries
GET /wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=ListStoredQueries

# Descrever parâmetros de uma stored query
GET /wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=DescribeStoredQueries
       &STOREDQUERY_ID=urn:ogc:def:query:OGC-WFS::GetFeatureById

# Executar stored query obrigatória (todo servidor WFS 2.0 deve ter)
GET /wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature
       &STOREDQUERY_ID=urn:ogc:def:query:OGC-WFS::GetFeatureById
       &ID=municipios.42

# Criar stored query (POST com XML)
# Dropar stored query
GET /wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=DropStoredQuery
       &STOREDQUERY_ID=minha:query
```

### Stored query obrigatória: GetFeatureById

```
# Formato do ID: {typename}.{id}
STOREDQUERY_ID=urn:ogc:def:query:OGC-WFS::GetFeatureById
ID=municipios.3550308   # São Paulo, SP
```

### Criando stored query customizada (POST)

```xml
<wfs:CreateStoredQuery
  xmlns:wfs="http://www.opengis.net/wfs/2.0"
  service="WFS" version="2.0.0">
  <wfs:StoredQueryDefinition id="local:MunicipiosPorEstado">
    <wfs:Title>Municípios por Estado</wfs:Title>
    <wfs:Abstract>Retorna municípios filtrando por UF</wfs:Abstract>
    <wfs:Parameter name="uf" type="xs:string"/>
    <wfs:QueryExpressionText
      returnFeatureTypes="ns:municipios"
      language="urn:ogc:def:queryLanguage:OGC-WFS::WFS_QueryExpression"
      isPrivate="false">
      <wfs:Query typeNames="ns:municipios">
        <fes:Filter xmlns:fes="http://www.opengis.net/fes/2.0">
          <fes:PropertyIsEqualTo>
            <fes:ValueReference>estado</fes:ValueReference>
            <fes:Literal>${uf}</fes:Literal>
          </fes:PropertyIsEqualTo>
        </fes:Filter>
      </wfs:Query>
    </wfs:QueryExpressionText>
  </wfs:StoredQueryDefinition>
</wfs:CreateStoredQuery>
```

---

## 7. GetPropertyValue (WFS 2.0.0)

Extrai apenas valores de propriedades específicas sem retornar geometrias — muito mais eficiente quando não precisa da geometria.

```
# Listar todos os valores distintos de um campo
GET /wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetPropertyValue
       &TYPENAMES=ns:municipios
       &VALUEREFERENCE=estado

# Com filtro
GET /wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetPropertyValue
       &TYPENAMES=ns:municipios
       &VALUEREFERENCE=municipio
       &CQL_FILTER=estado='SP'
       &COUNT=100
```

---

## 8. Transações (WFS-T)

Disponível em WFS 1.0+. Requer POST com XML.

```xml
<wfs:Transaction service="WFS" version="2.0.0"
  xmlns:wfs="http://www.opengis.net/wfs/2.0"
  xmlns:fes="http://www.opengis.net/fes/2.0">

  <!-- INSERT -->
  <wfs:Insert>
    <ns:municipio xmlns:ns="http://example.com/ns">
      <ns:nome>Novo Município</ns:nome>
      <ns:populacao>50000</ns:populacao>
      <ns:geom>
        <gml:Point srsName="EPSG:4326" xmlns:gml="http://www.opengis.net/gml/3.2">
          <gml:pos>-46.63 -23.55</gml:pos>
        </gml:Point>
      </ns:geom>
    </ns:municipio>
  </wfs:Insert>

  <!-- UPDATE -->
  <wfs:Update typeName="ns:municipio">
    <wfs:Property>
      <wfs:ValueReference>ns:populacao</wfs:ValueReference>
      <wfs:Value>55000</wfs:Value>
    </wfs:Property>
    <fes:Filter>
      <fes:ResourceId rid="municipio.42"/>
    </fes:Filter>
  </wfs:Update>

  <!-- DELETE -->
  <wfs:Delete typeName="ns:municipio">
    <fes:Filter>
      <fes:ResourceId rid="municipio.99"/>
    </fes:Filter>
  </wfs:Delete>

</wfs:Transaction>
```

---

## 9. OutputFormats

### Por versão e servidor

| Formato | WFS 1.0 | WFS 1.1 | WFS 2.0 | Notas |
|---|---|---|---|---|
| `GML2` | ✅ padrão | ✅ | ✅ | Compatibilidade máxima |
| `GML3` / `text/xml; subtype=gml/3.1.1` | ✅ | ✅ padrão | ✅ | |
| `application/gml+xml; version=3.2` | ❌ | ❌ | ✅ padrão | ISO 19136 |
| `application/json` | extensão | extensão | extensão | GeoJSON — verificar suporte |
| `application/zip` | extensão | extensão | extensão | Shapefile comprimido (GeoServer) |
| `csv` | extensão | extensão | extensão | Sem geometria geralmente |

### Verificando formatos suportados via Capabilities

```python
def list_output_formats(caps_xml, version="2.0.0"):
    root = ET.fromstring(caps_xml)
    if version >= "2.0.0":
        ns = {"ows": "http://www.opengis.net/ows/1.1"}
        path = ".//ows:Operation[@name='GetFeature']//ows:Parameter[@name='outputFormat']//ows:Value"
    else:
        ns = {"wfs": "http://www.opengis.net/wfs",
              "ows": "http://www.opengis.net/ows"}
        path = ".//ows:Parameter[@name='outputFormat']//ows:Value"
    return [el.text for el in root.findall(path, ns)]
```

---

## 10. Exemplos Completos por Versão

### WFS 1.0.0

```
# GetCapabilities
GET /wfs?SERVICE=WFS&VERSION=1.0.0&REQUEST=GetCapabilities

# GetFeature simples
GET /wfs?SERVICE=WFS&VERSION=1.0.0&REQUEST=GetFeature
       &TYPENAME=ns:municipios
       &MAXFEATURES=50
       &SRSNAME=EPSG:4326
       &BBOX=-73.99,-33.75,-28.83,5.27

# GetFeature com filtro por atributo
GET /wfs?SERVICE=WFS&VERSION=1.0.0&REQUEST=GetFeature
       &TYPENAME=ns:municipios
       &FILTER=<Filter><PropertyIsEqualTo><PropertyName>estado</PropertyName><Literal>SP</Literal></PropertyIsEqualTo></Filter>
```

### WFS 1.1.0

```
# GetCapabilities
GET /wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetCapabilities

# GetFeature com SORTBY
GET /wfs?SERVICE=WFS&VERSION=1.1.0&REQUEST=GetFeature
       &TYPENAME=ns:municipios
       &MAXFEATURES=100
       &SRSNAME=EPSG:4326
       &SORTBY=populacao DESC
       &OUTPUTFORMAT=GML3

# ATENÇÃO: Se SRSNAME=EPSG:4326, coordenadas retornam em lat/lon!
# Para obter lon/lat use URN alternativo (comportamento varia por servidor):
       &SRSNAME=urn:x-ogc:def:crs:EPSG:4326
```

### WFS 2.0.0

```
# GetCapabilities com negociação
GET /wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetCapabilities
       &ACCEPTVERSIONS=2.0.0,1.1.0,1.0.0

# GetFeature com paginação e GeoJSON
GET /wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature
       &TYPENAMES=ns:municipios
       &COUNT=500
       &STARTINDEX=0
       &OUTPUTFORMAT=application/json
       &CQL_FILTER=estado='SP'
       &SORTBY=populacao DESC

# Apenas contagem (hits)
GET /wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature
       &TYPENAMES=ns:municipios
       &RESULTTYPE=hits

# Join entre tipos de feição
GET /wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature
       &TYPENAMES=ns:municipios ns:estados
       &FILTER=<fes:Filter>...</fes:Filter>

# GetPropertyValue
GET /wfs?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetPropertyValue
       &TYPENAMES=ns:municipios
       &VALUEREFERENCE=estado
```
