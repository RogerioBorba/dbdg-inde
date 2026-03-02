# OGC API Features (REST Moderno)

## Índice
1. [Visão Geral e Partes](#visão-geral)
2. [Endpoints Principais](#endpoints)
3. [Filtragem e Paginação](#filtragem)
4. [Conformance Classes](#conformance)
5. [Exemplos Completos](#exemplos)

---

## 1. Visão Geral e Partes

OGC API Features é o sucessor moderno do WFS, baseado em REST, JSON e OpenAPI 3.0.

| Parte | Padrão | Descrição |
|---|---|---|
| Part 1: Core | OGC 17-069r4 | CRUD básico, GeoJSON, paginação |
| Part 2: CRS by Reference | OGC 18-058r1 | Múltiplos CRS além de WGS 84 |
| Part 3: Filtering | OGC 19-079r2 | CQL2, filtros avançados |
| Part 4: Create/Replace/Update/Delete | OGC 20-002 | Transações |

---

## 2. Endpoints Principais

```
# Landing page — descoberta
GET /ogcapi/
→ {links: [...], title: "...", description: "..."}

# Conformance — capacidades do servidor
GET /ogcapi/conformance
→ {conformsTo: ["http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core", ...]}

# Listar coleções
GET /ogcapi/collections
→ {collections: [{id, title, description, extent, links}, ...]}

# Metadados de uma coleção
GET /ogcapi/collections/{collectionId}
→ {id, title, description, extent, crs, storageCrs, links}

# Schema da coleção (Part 5)
GET /ogcapi/collections/{collectionId}/schema

# Feições da coleção
GET /ogcapi/collections/{collectionId}/items
→ GeoJSON FeatureCollection

# Feição por ID
GET /ogcapi/collections/{collectionId}/items/{featureId}
→ GeoJSON Feature
```

---

## 3. Filtragem e Paginação

### Parâmetros principais (Part 1 Core)

| Parâmetro | Tipo | Descrição |
|---|---|---|
| `limit` | inteiro | Máximo de feições por página (padrão: 10, max: definido pelo servidor) |
| `offset` | inteiro | Índice inicial (paginação) |
| `bbox` | string | `minlon,minlat,maxlon,maxlat` (sempre lon/lat, WGS84) |
| `bbox-crs` | URI | CRS do bbox (Part 2) |
| `datetime` | string | Filtro temporal: `2024-01-01`, `2024-01-01/2024-12-31`, `../2024-12-31` |
| `crs` | URI | CRS de saída das coordenadas (Part 2) |

### Parâmetros de filtro (Part 3 — CQL2)

| Parâmetro | Descrição |
|---|---|
| `filter` | Expressão de filtro |
| `filter-lang` | `cql2-text` (padrão) ou `cql2-json` |
| `filter-crs` | CRS das geometrias no filtro |

```
# Paginação
GET /ogcapi/collections/municipios/items?limit=100&offset=0
GET /ogcapi/collections/municipios/items?limit=100&offset=100

# BBOX
GET /ogcapi/collections/municipios/items?bbox=-73.99,-33.75,-28.83,5.27

# Temporal
GET /ogcapi/collections/ocorrencias/items?datetime=2024-01-01T00:00:00Z/2024-12-31T23:59:59Z

# CQL2 simples
GET /ogcapi/collections/municipios/items?filter=estado='SP'&filter-lang=cql2-text

# CQL2 espacial
GET /ogcapi/collections/municipios/items?filter=S_INTERSECTS(geom,POINT(-46.63 -23.55))

# CQL2 combinado
GET /ogcapi/collections/municipios/items?filter=estado='SP' AND populacao>1000000

# CRS de saída (Part 2)
GET /ogcapi/collections/municipios/items?crs=http://www.opengis.net/def/crs/EPSG/0/31983
```

### Navegação por links HATEOAS

O response inclui links para navegação:

```json
{
  "type": "FeatureCollection",
  "numberMatched": 5570,
  "numberReturned": 100,
  "links": [
    {"rel": "self",  "href": "...?offset=0&limit=100"},
    {"rel": "next",  "href": "...?offset=100&limit=100"},
    {"rel": "prev",  "href": null}
  ],
  "features": [...]
}
```

```python
def get_all_features_ogcapi(base_url, collection_id, cql_filter=None, limit=500):
    url = f"{base_url}/collections/{collection_id}/items"
    params = {"limit": limit}
    if cql_filter:
        params["filter"] = cql_filter
        params["filter-lang"] = "cql2-text"

    features = []
    while url:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        features.extend(data.get("features", []))
        # Seguir link "next"
        next_link = next((l["href"] for l in data.get("links", [])
                         if l.get("rel") == "next"), None)
        url = next_link
        params = {}  # params já estão na URL do next link
    return features
```

---

## 4. Conformance Classes

```python
def check_conformance(base_url):
    """Verifica quais partes do OGC API Features o servidor suporta"""
    r = requests.get(f"{base_url}/conformance")
    conforms_to = r.json().get("conformsTo", [])

    capabilities = {
        "core": "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core",
        "oas30": "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/oas30",
        "geojson": "http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/geojson",
        "crs": "http://www.opengis.net/spec/ogcapi-features-2/1.0/conf/crs",
        "filtering": "http://www.opengis.net/spec/ogcapi-features-3/1.0/conf/filter",
        "cql2_text": "http://www.opengis.net/spec/cql2/1.0/conf/cql2-text",
        "cql2_spatial": "http://www.opengis.net/spec/cql2/1.0/conf/spatial-operators",
        "crud": "http://www.opengis.net/spec/ogcapi-features-4/1.0/conf/create-replace-delete",
    }
    return {name: uri in conforms_to for name, uri in capabilities.items()}
```

---

## 5. Exemplos Completos

### Cliente genérico OGC API Features

```python
import requests

class OGCAPIClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self._conformance = None

    def conformance(self):
        if not self._conformance:
            r = requests.get(f"{self.base_url}/conformance")
            self._conformance = r.json().get("conformsTo", [])
        return self._conformance

    def supports_cql2(self):
        return any("cql2" in c for c in self.conformance())

    def collections(self):
        r = requests.get(f"{self.base_url}/collections")
        return r.json().get("collections", [])

    def items(self, collection_id, limit=100, offset=0,
              bbox=None, datetime=None, cql_filter=None):
        params = {"limit": limit, "offset": offset}
        if bbox:
            params["bbox"] = ",".join(map(str, bbox))  # [minlon,minlat,maxlon,maxlat]
        if datetime:
            params["datetime"] = datetime
        if cql_filter:
            params["filter"] = cql_filter
            params["filter-lang"] = "cql2-text"

        r = requests.get(
            f"{self.base_url}/collections/{collection_id}/items",
            params=params, timeout=30
        )
        r.raise_for_status()
        return r.json()

    def item(self, collection_id, feature_id):
        r = requests.get(
            f"{self.base_url}/collections/{collection_id}/items/{feature_id}"
        )
        r.raise_for_status()
        return r.json()

    def all_items(self, collection_id, **kwargs):
        """Pagina automaticamente e retorna todas as feições"""
        features = []
        offset = 0
        limit = kwargs.pop("limit", 500)
        while True:
            page = self.items(collection_id, limit=limit, offset=offset, **kwargs)
            batch = page.get("features", [])
            features.extend(batch)
            if len(batch) < limit:
                break
            offset += limit
        return features

# Uso
client = OGCAPIClient("https://api.geodados.example.com/ogcapi")
# Listar coleções
cols = client.collections()
# Buscar municípios de SP
items = client.all_items("municipios", cql_filter="estado='SP'")
```
