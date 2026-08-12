import json
from html.parser import HTMLParser
from urllib.parse import urlsplit, urlunsplit

from .network_utils import urlopen


CATALOG_URL = "https://inde.gov.br/api/catalogo/get"
CATALOG_PAGE_URL = "https://inde.gov.br/CatalogoGeoservicos"
_CATALOG_HEADERS = {
    "Accept": "application/json",
    "Referer": CATALOG_PAGE_URL,
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
}
_CATALOG_PAGE_HEADERS = {
    **_CATALOG_HEADERS,
    "Accept": "text/html,application/xhtml+xml",
}


class CatalogError(RuntimeError):
    """Raised when the INDE endpoint does not return a usable catalog."""


def service_is_available(entry, service_type):
    """Read availability from the documented or alternative spelling."""
    for suffix in ("Avalaible", "Available"):
        key = f"{service_type}{suffix}"
        if key in entry:
            return bool(entry[key])
    return False


def _service_base_url(capabilities_url):
    parts = urlsplit(capabilities_url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


class _CatalogPageParser(HTMLParser):
    """Extract the service table rendered by the official INDE catalog page."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.catalog = []
        self._in_li = False
        self._span_depth = 0
        self._description_parts = None
        self._description = ""
        self._button_url = None
        self._button_text = []
        self._services = {}

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "li":
            self._in_li = True
            self._span_depth = 0
            self._description_parts = None
            self._description = ""
            self._services = {}
        elif self._in_li and tag == "span":
            self._span_depth += 1
            if self._span_depth == 1 and not self._description:
                self._description_parts = []
        elif self._in_li and tag == "button":
            self._button_url = (attributes.get("url") or "").strip()
            self._button_text = []

    def handle_data(self, data):
        if self._description_parts is not None and self._span_depth == 1:
            self._description_parts.append(data)
        if self._button_url is not None:
            self._button_text.append(data)

    def handle_endtag(self, tag):
        if not self._in_li:
            return
        if tag == "span":
            if self._span_depth == 1 and self._description_parts is not None:
                self._description = " ".join(
                    "".join(self._description_parts).split()
                )
                self._description_parts = None
            self._span_depth = max(0, self._span_depth - 1)
        elif tag == "button" and self._button_url is not None:
            service_type = "".join(self._button_text).strip().lower()
            if service_type in {"wms", "wfs", "wcs"} and self._button_url:
                self._services[service_type] = self._button_url
            self._button_url = None
            self._button_text = []
        elif tag == "li":
            if self._description and self._services:
                entry = {"descricao": self._description}
                for service_type in ("wms", "wfs", "wcs"):
                    capabilities_url = self._services.get(service_type, "")
                    entry[f"{service_type}Avalaible"] = bool(capabilities_url)
                    entry[f"{service_type}GetCapabilities"] = capabilities_url
                entry["nivel_no"] = ""
                entry["cswAvalaible"] = False
                entry["cswGetCapabilities"] = ""
                first_url = next(iter(self._services.values()))
                entry["url"] = _service_base_url(first_url)
                self.catalog.append(entry)
            self._in_li = False


def _read_catalog_page(use_qgis=True):
    with urlopen(
        CATALOG_PAGE_URL,
        timeout=40,
        headers=_CATALOG_PAGE_HEADERS,
        use_qgis=use_qgis,
    ) as response:
        body = response.read()

    if not body or not body.strip():
        raise CatalogError("a página pública do catálogo retornou uma resposta vazia")

    parser = _CatalogPageParser()
    parser.feed(body.decode("utf-8", errors="replace"))
    if not parser.catalog:
        raise CatalogError("não foi possível extrair serviços da página pública do catálogo")
    return parser.catalog


def _read_catalog(use_qgis=True):
    with urlopen(
        CATALOG_URL,
        timeout=40,
        headers=_CATALOG_HEADERS,
        use_qgis=use_qgis,
    ) as response:
        body = response.read()
        status = getattr(response, "status", None)
        content_type = (getattr(response, "headers", {}) or {}).get(
            "Content-Type", ""
        )

    if not body or not body.strip():
        raise CatalogError(
            "a API da INDE retornou uma resposta vazia"
            + (f" (HTTP {status})" if status else "")
        )

    try:
        catalog = json.loads(body)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        preview = body[:160].decode("utf-8", errors="replace").replace("\n", " ")
        details = f"; Content-Type: {content_type}" if content_type else ""
        raise CatalogError(
            f"a API da INDE não retornou JSON válido{details}. Resposta: {preview!r}"
        ) from error

    if isinstance(catalog, str):
        try:
            catalog = json.loads(catalog)
        except json.JSONDecodeError as error:
            raise CatalogError(
                "a API da INDE retornou texto sem um catalogo JSON valido"
            ) from error

    if not isinstance(catalog, list):
        raise CatalogError(
            f"formato inesperado do catálogo: esperado uma lista, recebido {type(catalog).__name__}"
        )
    return catalog


def fetch_catalog():
    """Download and parse JSON catalog from the INDE API."""
    try:
        return _read_catalog(use_qgis=True)
    except CatalogError as qgis_error:
        # Some QGIS/Qt combinations (notably QGIS 3.44 on Windows) can finish
        # this request successfully but expose an empty response body. Retry
        # through Python's HTTPS implementation before reporting the failure.
        try:
            return _read_catalog(use_qgis=False)
        except Exception as python_error:
            page_errors = []
            for use_qgis in (True, False):
                try:
                    return _read_catalog_page(use_qgis=use_qgis)
                except Exception as page_error:
                    page_errors.append(page_error)
            raise CatalogError(
                f"API bloqueada pelo Qt/QGIS: {qgis_error}; "
                f"API bloqueada pelo Python: {python_error}; "
                "página pública indisponível: "
                + "; ".join(str(error) for error in page_errors)
            ) from page_errors[-1]
