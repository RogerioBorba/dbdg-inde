# WCS — Web Coverage Service

## Índice
1. [Versões](#versões)
2. [GetCapabilities](#getcapabilities)
3. [DescribeCoverage](#describecoverage)
4. [GetCoverage](#getcoverage)
5. [Exemplos](#exemplos)

---

## 1. Versões

| Versão | Padrão | Principais mudanças |
|---|---|---|
| WCS 1.0.0 | OGC 03-065r6 | Básico, amplamente suportado |
| WCS 1.1.x | OGC 07-067r5 | Alinhamento OWS Common, múltiplos campos |
| WCS 2.0 | OGC 09-110r4 | Subsetting, scaling, interpolation, GeoTIFF output |
| WCS 2.1 | OGC 17-089r1 | Cobertura de dados temporais e multi-dimensionais |

**WCS 2.0** é o padrão atual recomendado. Usa extensões para funcionalidades avançadas:
- Core + Scaling Extension + Interpolation Extension + Range Subsetting Extension + CRS Extension

---

## 2. GetCapabilities

```
GET /wcs?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCapabilities
GET /wcs?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCapabilities
```

---

## 3. DescribeCoverage

Retorna metadados de uma cobertura: CRS, extent, campos, resolução.

```
# WCS 2.0
GET /wcs?SERVICE=WCS&VERSION=2.0.1&REQUEST=DescribeCoverage
       &COVERAGEID=dem_brasil

# WCS 1.0
GET /wcs?SERVICE=WCS&VERSION=1.0.0&REQUEST=DescribeCoverage
       &COVERAGE=dem_brasil
```

---

## 4. GetCoverage

### WCS 1.0.0

```
GET /wcs?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage
       &COVERAGE=dem_brasil
       &CRS=EPSG:4326
       &BBOX=-50,-25,-45,-20
       &WIDTH=500&HEIGHT=500
       &FORMAT=GeoTIFF
```

### WCS 2.0 — Subsetting por coordenada

```
# Subset espacial
GET /wcs?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage
       &COVERAGEID=dem_brasil
       &SUBSET=Long(-50,-45)
       &SUBSET=Lat(-25,-20)
       &FORMAT=image/tiff

# Subset + scaling (output 500x500px)
GET /wcs?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage
       &COVERAGEID=dem_brasil
       &SUBSET=Long(-50,-45)&SUBSET=Lat(-25,-20)
       &SCALEFACTOR=0.1
       &FORMAT=image/tiff

# Subset temporal (se dimensão time disponível)
GET /wcs?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage
       &COVERAGEID=landsat_brasil
       &SUBSET=Long(-50,-45)&SUBSET=Lat(-25,-20)
       &SUBSET=time("2024-01-01","2024-03-31")
       &FORMAT=image/tiff

# Range subsetting — selecionar bandas específicas
GET /wcs?SERVICE=WCS&VERSION=2.0.1&REQUEST=GetCoverage
       &COVERAGEID=landsat_brasil
       &RANGESUBSET=B4,B3,B2
       &SUBSET=Long(-50,-45)&SUBSET=Lat(-25,-20)
       &FORMAT=image/tiff
```

### Formatos de output

| FORMAT | Descrição |
|---|---|
| `image/tiff` | GeoTIFF (recomendado para rasters) |
| `image/tiff;subtype=geotiff/1.0` | GeoTIFF explícito |
| `image/netcdf` | NetCDF (dados multi-dimensionais) |
| `image/png` | PNG (sem metadados geoespaciais) |
| `image/jpeg` | JPEG |
| `application/gml+xml` | GML Coverage |

---

## 5. Exemplos

### Download de DEM (Digital Elevation Model)

```python
def download_wcs_coverage(base_url, coverage_id, bbox,
                           version="2.0.1", output_format="image/tiff"):
    """
    bbox: (minlon, minlat, maxlon, maxlat)
    """
    minlon, minlat, maxlon, maxlat = bbox

    if version >= "2.0.0":
        params = {
            "SERVICE": "WCS", "VERSION": version,
            "REQUEST": "GetCoverage",
            "COVERAGEID": coverage_id,
            "SUBSET": [f"Long({minlon},{maxlon})", f"Lat({minlat},{maxlat})"],
            "FORMAT": output_format
        }
        r = requests.get(base_url, params=params, timeout=120)
    else:
        params = {
            "SERVICE": "WCS", "VERSION": "1.0.0",
            "REQUEST": "GetCoverage",
            "COVERAGE": coverage_id,
            "CRS": "EPSG:4326",
            "BBOX": f"{minlon},{minlat},{maxlon},{maxlat}",
            "WIDTH": 1000, "HEIGHT": 1000,
            "FORMAT": "GeoTIFF"
        }
        r = requests.get(base_url, params=params, timeout=120)

    r.raise_for_status()
    return r.content  # bytes do GeoTIFF

# Exemplo: DEM da região Sul do Brasil
data = download_wcs_coverage(
    "https://geoserver.example.com/wcs",
    "srtm_dem",
    bbox=(-54, -33, -48, -28)
)
with open("dem_sul.tif", "wb") as f:
    f.write(data)
```
