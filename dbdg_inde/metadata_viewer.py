import html
import re
import urllib.parse

from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout

from .network_utils import create_ssl_context, urlopen
from .service_handlers.base import parse_xml_safe

ISO19139_OUTPUT_SCHEMA = "http://www.isotc211.org/2005/gmd"
ISO19115_3_OUTPUT_SCHEMA = "http://standards.iso.org/iso/19115/-3/mdb/2.0"


def _first_text(root, paths):
    for path in paths:
        node = root.find(path)
        if node is not None and node.text and node.text.strip():
            return node.text.strip()
    return None


def _all_texts(root, paths, limit=15):
    items = []
    seen = set()
    for path in paths:
        for node in root.findall(path):
            if not node.text:
                continue
            text = node.text.strip()
            if not text:
                continue
            marker = text.lower()
            if marker in seen:
                continue
            seen.add(marker)
            items.append(text)
            if len(items) >= limit:
                return items
    return items


def _bbox_value(root, axis):
    return _first_text(
        root,
        [
            f".//{{*}}EX_GeographicBoundingBox//{{*}}{axis}//{{*}}Decimal",
            f".//{{*}}EX_GeographicBoundingBox//{{*}}{axis}",
        ],
    )


def _extract_dates(root, limit=6):
    dates = []
    seen = set()
    for date_node in root.findall(".//{*}CI_Date"):
        date_value = None
        date_type = None

        date_value_node = date_node.find(".//{*}Date")
        if date_value_node is None:
            date_value_node = date_node.find(".//{*}DateTime")
        if date_value_node is not None and date_value_node.text:
            date_value = date_value_node.text.strip()

        date_type_node = date_node.find(".//{*}CI_DateTypeCode")
        if date_type_node is not None:
            date_type = (
                date_type_node.text.strip()
                if date_type_node.text and date_type_node.text.strip()
                else date_type_node.attrib.get("codeListValue", "").strip()
            )

        if not date_value:
            continue

        key = (date_value.lower(), (date_type or "").lower())
        if key in seen:
            continue
        seen.add(key)
        dates.append({"value": date_value, "type": date_type})
        if len(dates) >= limit:
            break
    return dates


def _extract_links(root, limit=8):
    links = []
    seen = set()

    for online_resource in root.findall(".//{*}CI_OnlineResource"):
        url = _first_text(online_resource, [".//{*}linkage//{*}URL", ".//{*}URL"])
        if not url:
            continue

        name = _first_text(
            online_resource,
            [
                ".//{*}name//{*}CharacterString",
                ".//{*}description//{*}CharacterString",
                ".//{*}protocol//{*}CharacterString",
            ],
        )
        marker = url.lower()
        if marker in seen:
            continue
        seen.add(marker)
        links.append({"url": url, "name": name or "Recurso"})
        if len(links) >= limit:
            break
    return links




def _prepare_metadata_url(url, preferred_schema=ISO19139_OUTPUT_SCHEMA):
    """Return a possibly-modified metadata URL.

    Many CSW servers require the ``outputSchema`` parameter when performing a
    GetRecordById request so that the returned document is in the ISO/19139
    (``http://www.isotc211.org/2005/gmd``) schema.  The metadata URLs exposed
    under ``MetadataURL`` tags in WMS/WFS capabilities sometimes omit this
    parameter.  As a result the raw response may be delivered in an unexpected
    format (HTML, custom XML) and the plugin fails to recognise or display the
    metadata.

    We attempt to detect cases where the URL already contains a CSW
    ``GetRecord*`` request and no ``outputSchema`` parameter; when found we add
    the ISO schema value before the request is sent.  This matches the change
    requested by users: "para os casos que a tag MetadataURL esteja
    preenchida ... no GetCapabilities colocar o outputSchema da requisição
    GetRecordByID com o valor de http://www.isotc211.org/2005/gmd sempre que
    possível antes de fazer a requisição".
    """
    try:
        parsed = urllib.parse.urlparse(url)

        # GeoNetwork UI URL -> CSW GetRecordById endpoint.
        # Example:
        # .../catalog.search#/metadata/<uuid>
        fragment = parsed.fragment or ""
        match = re.search(
            r"(?:^|/)metadata/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})",
            fragment,
        )
        if match:
            metadata_id = match.group(1)
            csw_path = re.sub(r"/catalog\.search/?$", "/csw", parsed.path)
            if csw_path == parsed.path:
                csw_path = parsed.path.rstrip("/") + "/csw"
            query = {
                "service": ["CSW"],
                "version": ["2.0.2"],
                "request": ["GetRecordById"],
                "id": [metadata_id],
                "elementSetName": ["full"],
                "outputSchema": [preferred_schema],
            }
            return urllib.parse.urlunparse(
                parsed._replace(path=csw_path, query=urllib.parse.urlencode(query, doseq=True), fragment="")
            )

        query = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        service = query.get("service", [""])[0].lower()
        request = query.get("request", [""])[0].lower()

        # decide whether this looks like a CSW GetRecordById-type request
        needs_schema = False
        if "csw" in service or "csw" in parsed.netloc.lower():
            if "getrecord" in request or "getrecord" in url.lower():
                needs_schema = True
        if needs_schema:
            output_schema_key = next((k for k in query if k.lower() == "outputschema"), None)
            if output_schema_key is None:
                query["outputSchema"] = [preferred_schema]
            else:
                query[output_schema_key] = [preferred_schema]
            new_q = urllib.parse.urlencode(query, doseq=True)
            parsed = parsed._replace(query=new_q)
            return urllib.parse.urlunparse(parsed)
    except Exception:
        # on any parsing error just return original URL
        pass
    return url


def fetch_metadata_summary(metadata_url, timeout=30):
    context = create_ssl_context()
    candidate_urls = []
    for schema in (ISO19139_OUTPUT_SCHEMA, ISO19115_3_OUTPUT_SCHEMA):
        candidate = _prepare_metadata_url(metadata_url, preferred_schema=schema)
        if candidate not in candidate_urls:
            candidate_urls.append(candidate)

    root = None
    last_error = None
    for candidate_url in candidate_urls:
        try:
            with urlopen(candidate_url, context=context, timeout=timeout) as response:
                xml_data = response.read()
            root = parse_xml_safe(xml_data)
            metadata_url = candidate_url
            break
        except Exception as error:
            last_error = error

    if root is None:
        raise last_error if last_error else Exception("Failed to load metadata.")

    summary = {
        "title": _first_text(
            root,
            [
                ".//{*}identificationInfo//{*}citation//{*}title//{*}CharacterString",
                ".//{*}title//{*}CharacterString",
                ".//{*}Title",
            ],
        ),
        "abstract": _first_text(
            root,
            [
                ".//{*}identificationInfo//{*}abstract//{*}CharacterString",
                ".//{*}abstract//{*}CharacterString",
                ".//{*}Abstract",
            ],
        ),
        "keywords": _all_texts(
            root,
            [
                ".//{*}identificationInfo//{*}descriptiveKeywords//{*}keyword//{*}CharacterString",
                ".//{*}keyword//{*}CharacterString",
                ".//{*}Keyword",
            ],
            limit=20,
        ),
        "organisations": _all_texts(
            root,
            [
                ".//{*}contact//{*}organisationName//{*}CharacterString",
                ".//{*}organisationName//{*}CharacterString",
            ],
            limit=8,
        ),
        "emails": _all_texts(
            root,
            [
                ".//{*}contact//{*}electronicMailAddress//{*}CharacterString",
                ".//{*}electronicMailAddress//{*}CharacterString",
            ],
            limit=8,
        ),
        "dates": _extract_dates(root),
        "constraints": _all_texts(
            root,
            [
                ".//{*}resourceConstraints//{*}useLimitation//{*}CharacterString",
                ".//{*}useLimitation//{*}CharacterString",
            ],
            limit=6,
        ),
        "lineage": _first_text(
            root,
            [
                ".//{*}lineage//{*}statement//{*}CharacterString",
                ".//{*}statement//{*}CharacterString",
            ],
        ),
        "bbox": {
            "west": _bbox_value(root, "westBoundLongitude"),
            "east": _bbox_value(root, "eastBoundLongitude"),
            "south": _bbox_value(root, "southBoundLatitude"),
            "north": _bbox_value(root, "northBoundLatitude"),
        },
        "links": _extract_links(root),
    }
    return summary


def _list_html(items):
    if not items:
        return "<p><i>Não informado.</i></p>"
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"


def _dates_html(items):
    if not items:
        return "<p><i>Não informado.</i></p>"
    lines = []
    for item in items:
        date_value = html.escape(item.get("value", ""))
        date_type = html.escape(item.get("type") or "data")
        lines.append(f"<li><b>{date_type}</b>: {date_value}</li>")
    return "<ul>" + "".join(lines) + "</ul>"


def _links_html(items):
    if not items:
        return "<p><i>Não informado.</i></p>"
    lines = []
    for item in items:
        url = html.escape(item.get("url", ""))
        label = html.escape(item.get("name", "Recurso"))
        lines.append(f'<li><a href="{url}">{label}</a><br/><small>{url}</small></li>')
    return "<ul>" + "".join(lines) + "</ul>"


def build_metadata_html(summary, metadata_url):
    title = html.escape(summary.get("title") or "Metadados")
    abstract = html.escape(summary.get("abstract") or "Não informado.")
    lineage = html.escape(summary.get("lineage") or "Não informado.")

    bbox = summary.get("bbox") or {}
    has_bbox = any(bbox.get(key) for key in ("west", "east", "south", "north"))
    if has_bbox:
        bbox_html = (
            "<p>"
            f"<b>Oeste</b>: {html.escape(str(bbox.get('west') or '-'))}<br/>"
            f"<b>Leste</b>: {html.escape(str(bbox.get('east') or '-'))}<br/>"
            f"<b>Sul</b>: {html.escape(str(bbox.get('south') or '-'))}<br/>"
            f"<b>Norte</b>: {html.escape(str(bbox.get('north') or '-'))}"
            "</p>"
        )
    else:
        bbox_html = "<p><i>Não informado.</i></p>"

    source_url = html.escape(metadata_url)
    return f"""
    <html>
      <body style="font-family: Segoe UI, Arial, sans-serif; font-size: 10pt;">
        <h2>{title}</h2>
        <p><b>Fonte XML:</b> <a href="{source_url}">{source_url}</a></p>
        <h3>Resumo</h3>
        <p>{abstract}</p>
        <h3>Palavras-chave</h3>
        {_list_html(summary.get("keywords") or [])}
        <h3>Contatos</h3>
        <p><b>Organizações</b></p>
        {_list_html(summary.get("organisations") or [])}
        <p><b>E-mails</b></p>
        {_list_html(summary.get("emails") or [])}
        <h3>Datas de referência</h3>
        {_dates_html(summary.get("dates") or [])}
        <h3>Extensão geográfica (BBOX)</h3>
        {bbox_html}
        <h3>Restrições</h3>
        {_list_html(summary.get("constraints") or [])}
        <h3>Linhagem</h3>
        <p>{lineage}</p>
        <h3>Recursos online</h3>
        {_links_html(summary.get("links") or [])}
      </body>
    </html>
    """


class MetadataSummaryDialog(QDialog):
    def __init__(self, metadata_url, summary, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Metadados da camada")
        self.resize(860, 620)

        browser = QTextBrowser(self)
        browser.setOpenExternalLinks(True)
        browser.setHtml(build_metadata_html(summary, metadata_url))

        buttons = QDialogButtonBox(QDialogButtonBox.Close, parent=self)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout()
        layout.addWidget(browser)
        layout.addWidget(buttons)
        self.setLayout(layout)
