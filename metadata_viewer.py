import html
import ssl
import urllib.request

from qgis.PyQt.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout

from .service_handlers.base import parse_xml_safe


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
        links.append({"url": url, "name": name or "Link"})
        if len(links) >= limit:
            break
    return links


def fetch_metadata_summary(metadata_url, timeout=30):
    context = ssl.create_default_context()
    with urllib.request.urlopen(metadata_url, context=context, timeout=timeout) as response:
        xml_data = response.read()

    root = parse_xml_safe(xml_data)

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
        return "<p><i>Not informed.</i></p>"
    return "<ul>" + "".join(f"<li>{html.escape(item)}</li>" for item in items) + "</ul>"


def _dates_html(items):
    if not items:
        return "<p><i>Not informed.</i></p>"
    lines = []
    for item in items:
        date_value = html.escape(item.get("value", ""))
        date_type = html.escape(item.get("type") or "date")
        lines.append(f"<li><b>{date_type}</b>: {date_value}</li>")
    return "<ul>" + "".join(lines) + "</ul>"


def _links_html(items):
    if not items:
        return "<p><i>Not informed.</i></p>"
    lines = []
    for item in items:
        url = html.escape(item.get("url", ""))
        label = html.escape(item.get("name", "Link"))
        lines.append(f'<li><a href="{url}">{label}</a><br/><small>{url}</small></li>')
    return "<ul>" + "".join(lines) + "</ul>"


def build_metadata_html(summary, metadata_url):
    title = html.escape(summary.get("title") or "Metadata")
    abstract = html.escape(summary.get("abstract") or "Not informed.")
    lineage = html.escape(summary.get("lineage") or "Not informed.")

    bbox = summary.get("bbox") or {}
    has_bbox = any(bbox.get(key) for key in ("west", "east", "south", "north"))
    if has_bbox:
        bbox_html = (
            "<p>"
            f"<b>West</b>: {html.escape(str(bbox.get('west') or '-'))}<br/>"
            f"<b>East</b>: {html.escape(str(bbox.get('east') or '-'))}<br/>"
            f"<b>South</b>: {html.escape(str(bbox.get('south') or '-'))}<br/>"
            f"<b>North</b>: {html.escape(str(bbox.get('north') or '-'))}"
            "</p>"
        )
    else:
        bbox_html = "<p><i>Not informed.</i></p>"

    source_url = html.escape(metadata_url)
    return f"""
    <html>
      <body style="font-family: Segoe UI, Arial, sans-serif; font-size: 10pt;">
        <h2>{title}</h2>
        <p><b>Source XML:</b> <a href="{source_url}">{source_url}</a></p>
        <h3>Abstract</h3>
        <p>{abstract}</p>
        <h3>Keywords</h3>
        {_list_html(summary.get("keywords") or [])}
        <h3>Contacts</h3>
        <p><b>Organizations</b></p>
        {_list_html(summary.get("organisations") or [])}
        <p><b>Emails</b></p>
        {_list_html(summary.get("emails") or [])}
        <h3>Reference dates</h3>
        {_dates_html(summary.get("dates") or [])}
        <h3>Geographic extent (BBOX)</h3>
        {bbox_html}
        <h3>Constraints</h3>
        {_list_html(summary.get("constraints") or [])}
        <h3>Lineage</h3>
        <p>{lineage}</p>
        <h3>Online resources</h3>
        {_links_html(summary.get("links") or [])}
      </body>
    </html>
    """


class MetadataSummaryDialog(QDialog):
    def __init__(self, metadata_url, summary, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Layer metadata")
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
