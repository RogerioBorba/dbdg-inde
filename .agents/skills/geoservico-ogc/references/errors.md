# Erros e Diagnóstico de Geoserviços OGC

## Índice
1. [Estrutura de ExceptionReport](#exceptionreport)
2. [Códigos de Exceção OGC](#códigos)
3. [Erros por Sintoma](#por-sintoma)
4. [Diagnóstico com Python](#diagnóstico)
5. [Checklist de Depuração](#checklist)

---

## 1. Estrutura de ExceptionReport

**Atenção crítica**: Geoserviços OGC frequentemente retornam **HTTP 200** mesmo em caso de erro, encapsulando o erro num XML de exceção no body. Sempre verificar o body, não só o status HTTP.

### WFS 1.x

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ServiceExceptionReport version="1.2.0"
  xmlns="http://www.opengis.net/ogc">
  <ServiceException code="InvalidParameterValue" locator="typeName">
    Feature type municipios not found
  </ServiceException>
</ServiceExceptionReport>
```

### WFS 2.0 (OWS Common)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ows:ExceptionReport version="2.0.0" language="en"
  xmlns:ows="http://www.opengis.net/ows/1.1">
  <ows:Exception exceptionCode="InvalidParameterValue" locator="typeName">
    <ows:ExceptionText>
      Feature type {http://example.com/ns}municipios unknown
    </ows:ExceptionText>
  </ows:Exception>
</ows:ExceptionReport>
```

### Detecção programática

```python
from xml.etree import ElementTree as ET

def check_ogc_exception(response_text: str) -> dict | None:
    """
    Verifica se o response é um ExceptionReport OGC.
    Retorna dict com code e message, ou None se não for exceção.
    """
    try:
        root = ET.fromstring(response_text)
        tag = root.tag.lower()

        # WFS 2.0 / OWS Common
        if "exceptionreport" in tag:
            ns = {"ows": "http://www.opengis.net/ows/1.1"}
            exc = root.find(".//ows:Exception", ns)
            if exc is None:
                exc = root.find(".//{http://www.opengis.net/ows/1.1}Exception")
            if exc is not None:
                text_el = exc.find("{http://www.opengis.net/ows/1.1}ExceptionText")
                return {
                    "code": exc.get("exceptionCode", "Unknown"),
                    "locator": exc.get("locator", ""),
                    "message": text_el.text.strip() if text_el is not None else ""
                }

        # WFS 1.x
        if "serviceexceptionreport" in tag:
            exc = root.find(".//{http://www.opengis.net/ogc}ServiceException")
            if exc is None:
                exc = root.find(".//ServiceException")
            if exc is not None:
                return {
                    "code": exc.get("code", "Unknown"),
                    "locator": exc.get("locator", ""),
                    "message": exc.text.strip() if exc.text else ""
                }
    except ET.ParseError:
        pass
    return None


def safe_wfs_request(url, params, timeout=30):
    """Faz requisição WFS e lança exceção clara se houver erro OGC."""
    r = requests.get(url, params=params, timeout=timeout)
    r.raise_for_status()  # Erros HTTP reais

    content_type = r.headers.get("Content-Type", "")
    # Se não for XML, provavelmente está OK (ex: GeoJSON, imagem)
    if "xml" in content_type or r.text.lstrip().startswith("<"):
        exc = check_ogc_exception(r.text)
        if exc:
            raise ValueError(
                f"OGC Exception [{exc['code']}] at '{exc['locator']}': {exc['message']}"
            )
    return r
```

---

## 2. Códigos de Exceção OGC

### OWS Common (WFS 2.0)

| exceptionCode | Causa | Solução |
|---|---|---|
| `OperationNotSupported` | Operação não implementada pelo servidor | Verificar Capabilities |
| `MissingParameterValue` | Parâmetro obrigatório ausente | Adicionar parâmetro indicado em `locator` |
| `InvalidParameterValue` | Valor de parâmetro inválido | Verificar valor em `locator` |
| `VersionNegotiationFailed` | Nenhuma versão em ACCEPTVERSIONS é suportada | Rever versões disponíveis |
| `InvalidUpdateSequence` | updateSequence inválido | Omitir ou corrigir updateSequence |
| `OptionNotSupported` | Opção não suportada | Verificar Capabilities |
| `NoApplicableCode` | Erro genérico do servidor | Verificar logs do servidor |

### WFS Específicos

| code | Causa | Solução |
|---|---|---|
| `InvalidValue` | Valor de propriedade inválido | Verificar tipo de dado |
| `DuplicateStoredQueryIdValue` | StoredQuery com ID já existente | Usar DropStoredQuery antes |
| `DuplicateStoredQueryParameterName` | Parâmetro duplicado na StoredQuery | Corrigir definição |
| `LockHasExpired` | Lock expirou | Obter novo lock |
| `OperationParsingFailed` | XML malformado na requisição | Validar XML |

---

## 3. Erros por Sintoma

### Geometrias aparentemente corretas mas deslocadas geograficamente

**Causa**: Inversão de eixo (lat/lon vs lon/lat)

```python
# Diagnóstico: verificar se coordenadas estão invertidas
# Se ponto está em (-23.5, -46.6) mas deveria estar em (-46.6, -23.5):
# Eixos estão trocados!

# Solução para WFS 1.1.0 + EPSG:4326:
# Ver references/crs.md → seção "Inversão de eixo"

# Ou forçar CRS:84 na requisição:
params["SRSNAME"] = "urn:ogc:def:crs:OGC:1.3:CRS84"
```

### `TYPENAME` ignorado / FeatureCollection vazia

**Causa**: WFS 2.0 requer `TYPENAMES` (plural)

```python
# Errado para WFS 2.0:
params["TYPENAME"] = "ns:municipios"

# Correto:
params["TYPENAMES"] = "ns:municipios"
```

### `numberMatched="unknown"`

**Causa**: Servidor não suporta contagem prévia

```python
# Não confiar em numberMatched — paginar até batch vazio
while len(batch) == page_size:
    start += page_size
    # buscar próxima página
```

### Timeout em coleções grandes

**Causa**: Sem paginação ou COUNT muito alto

```python
# Adicionar COUNT e STARTINDEX (WFS 2.0)
params["COUNT"] = 500
params["STARTINDEX"] = 0

# Ou reduzir bbox para queries menores
```

### HTTP 200 com HTML (proxy/auth redirect)

**Causa**: Requisição interceptada por proxy ou login

```python
# Verificar se response é HTML
if "text/html" in r.headers.get("Content-Type", ""):
    # Provável redirect para login ou proxy error
    print("Possível autenticação necessária ou proxy bloqueando")
    print(r.text[:500])
```

### Caracteres especiais em CQL_FILTER corrompidos

**Causa**: Falta de URL encoding

```python
from urllib.parse import urlencode
params["CQL_FILTER"] = "nome LIKE 'São%'"
# requests faz encoding automático — usar requests.get(url, params=params)
# Nunca concatenar manualmente na URL
```

### GetCapabilities retorna versão diferente da solicitada

**Causa**: `VERSION=` no GetCapabilities é sugestão, não obrigação; o servidor pode não suportar

```python
# Solução: ler a versão do atributo version= no XML retornado
root = ET.fromstring(caps.content)
actual_version = root.get("version")  # Usar ESTA versão nas requisições seguintes
```

### Filtro espacial retorna zero resultados

**Causas possíveis:**
1. Nome do campo geométrico errado
2. CRS do filtro diferente do CRS da camada
3. Coordenadas fora do extent da camada

```python
# 1. Descobrir campo geométrico via DescribeFeatureType
fields = describe_feature_type(url, typename, version)
geom_field = next((f["name"] for f in fields
                  if "gml" in f.get("type","").lower() or
                     "geometry" in f.get("type","").lower()), "geom")

# 2. Verificar extent da camada nas Capabilities
# Procurar por ows:WGS84BoundingBox ou LatLonBoundingBox
```

---

## 4. Diagnóstico com Python

```python
import requests
from xml.etree import ElementTree as ET

def diagnose_wfs(base_url):
    """
    Diagnóstico completo de um endpoint WFS.
    Retorna relatório com versões, camadas e capacidades.
    """
    report = {"url": base_url, "status": "unknown", "issues": []}

    # 1. GetCapabilities
    try:
        r = requests.get(base_url, params={
            "SERVICE": "WFS", "REQUEST": "GetCapabilities",
            "ACCEPTVERSIONS": "2.0.0,1.1.0,1.0.0"
        }, timeout=15)
    except requests.Timeout:
        report["status"] = "timeout"
        report["issues"].append("GetCapabilities timeout — servidor lento ou URL errada")
        return report
    except requests.ConnectionError as e:
        report["status"] = "connection_error"
        report["issues"].append(f"Erro de conexão: {e}")
        return report

    if r.status_code != 200:
        report["status"] = f"http_{r.status_code}"
        report["issues"].append(f"HTTP {r.status_code}: {r.text[:200]}")
        return report

    # 2. Verificar se é exceção OGC
    exc = check_ogc_exception(r.text)
    if exc:
        report["status"] = "ogc_exception"
        report["issues"].append(f"OGC Exception: {exc}")
        return report

    # 3. Parsear capabilities
    try:
        root = ET.fromstring(r.content)
        report["version"] = root.get("version")
        report["status"] = "ok"
    except ET.ParseError as e:
        report["status"] = "parse_error"
        report["issues"].append(f"XML inválido: {e}")
        return report

    # 4. Listar tipos de feição
    ns2 = {"wfs": "http://www.opengis.net/wfs/2.0",
           "wfs1": "http://www.opengis.net/wfs"}
    layers = []
    for tag in [".//wfs:FeatureType/wfs:Name", ".//wfs1:FeatureType/wfs1:Name",
                ".//FeatureType/Name"]:
        found = root.findall(tag, {**ns2})
        if found:
            layers = [el.text for el in found if el.text]
            break
    report["layers"] = layers[:20]  # primeiras 20

    if not layers:
        report["issues"].append("Nenhuma camada encontrada no Capabilities")

    return report
```

---

## 5. Checklist de Depuração

```
□ 1. URL base está correta e acessível?
     → requests.get(url + "?SERVICE=WFS&REQUEST=GetCapabilities")

□ 2. Versão do serviço está capturada corretamente do XML (não assumida)?
     → root.get("version")

□ 3. TYPENAME vs TYPENAMES conforme versão?
     → 1.x: TYPENAME | 2.0: TYPENAMES

□ 4. COUNT vs MAXFEATURES conforme versão?
     → 1.x: MAXFEATURES | 2.0: COUNT

□ 5. ExceptionReport verificado mesmo com HTTP 200?
     → check_ogc_exception(response.text)

□ 6. Inversão de eixo tratada para WFS 1.1.0 + EPSG:4326?
     → ver references/crs.md

□ 7. Paginação implementada para coleções grandes?
     → COUNT + STARTINDEX (WFS 2.0)

□ 8. CRS da geometria no filtro corresponde ao CRS da camada?

□ 9. Nome do campo geométrico correto?
     → verificar via DescribeFeatureType

□ 10. OutputFormat suportado?
      → verificar em Capabilities > GetFeature > outputFormat
```
