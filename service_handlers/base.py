from abc import ABC, abstractmethod
import html.entities
import re
import xml.etree.ElementTree as ET


_NUMERIC_CHAR_REF_RE = re.compile(rb"&#(x[0-9A-Fa-f]+|\d+);")
_INVALID_CONTROL_BYTES_RE = re.compile(rb"[\x00-\x08\x0B\x0C\x0E-\x1F]")
_NAMED_ENTITY_RE = re.compile(r"&([A-Za-z][A-Za-z0-9]+);")
_XML_TOKEN_RE = re.compile(r"<!--.*?-->|<!\[CDATA\[.*?\]\]>|<\?.*?\?>|</?[^>]+?>", re.DOTALL)


def _is_valid_xml_codepoint(codepoint):
    return (
        codepoint == 0x9
        or codepoint == 0xA
        or codepoint == 0xD
        or 0x20 <= codepoint <= 0xD7FF
        or 0xE000 <= codepoint <= 0xFFFD
        or 0x10000 <= codepoint <= 0x10FFFF
    )


def _strip_invalid_numeric_references(xml_data):
    def replace(match):
        raw = match.group(1)
        base = 16 if raw.startswith(b"x") else 10
        number = raw[1:] if base == 16 else raw
        try:
            codepoint = int(number, base)
        except ValueError:
            return b""
        return match.group(0) if _is_valid_xml_codepoint(codepoint) else b""

    return _NUMERIC_CHAR_REF_RE.sub(replace, xml_data)


def _decode_named_entities(xml_data):
    """Convert HTML named entities (e.g. &nbsp;) into Unicode characters."""
    text = xml_data.decode("utf-8", errors="replace")
    xml_builtin = {"amp", "lt", "gt", "quot", "apos"}

    def replace(match):
        name = match.group(1)
        if name in xml_builtin:
            return match.group(0)
        codepoint = html.entities.name2codepoint.get(name)
        if codepoint is None:
            return " "
        return chr(codepoint) if _is_valid_xml_codepoint(codepoint) else ""

    return _NAMED_ENTITY_RE.sub(replace, text).encode("utf-8")


def _repair_mismatched_tags(xml_data):
    """Best-effort structural repair for malformed XML tag nesting."""
    text = xml_data.decode("utf-8", errors="replace")
    output = []
    stack = []
    last_index = 0

    for match in _XML_TOKEN_RE.finditer(text):
        token = match.group(0)
        output.append(text[last_index : match.start()])
        last_index = match.end()

        if token.startswith("<!--") or token.startswith("<![CDATA[") or token.startswith("<?"):
            output.append(token)
            continue

        if token.startswith("</"):
            tag_name = token[2:-1].strip().split()[0] if token.endswith(">") else ""
            if not tag_name:
                continue
            if tag_name in stack:
                while stack and stack[-1] != tag_name:
                    output.append(f"</{stack.pop()}>")
                if stack and stack[-1] == tag_name:
                    stack.pop()
                    output.append(f"</{tag_name}>")
            continue

        if token.startswith("<!"):
            output.append(token)
            continue

        tag_body = token[1:-1].strip()
        if not tag_body:
            continue
        tag_name = tag_body.split()[0].rstrip("/")
        if not tag_name:
            continue
        output.append(token)
        if not token.endswith("/>"):
            stack.append(tag_name)

    output.append(text[last_index:])
    while stack:
        output.append(f"</{stack.pop()}>")

    return "".join(output).encode("utf-8")


def parse_xml_safe(xml_data):
    """Parse XML bytes, trying a sanitized fallback for malformed capabilities."""
    try:
        return ET.fromstring(xml_data)
    except ET.ParseError:
        cleaned = _strip_invalid_numeric_references(xml_data)
        cleaned = _INVALID_CONTROL_BYTES_RE.sub(b"", cleaned)
        cleaned = _decode_named_entities(cleaned)
        try:
            return ET.fromstring(cleaned)
        except ET.ParseError:
            repaired = _repair_mismatched_tags(cleaned)
            return ET.fromstring(repaired)


class ServiceHandler(ABC):
    """Base contract for OGC service-specific behavior."""

    service_type = ""
    tab_name = ""
    availability_key = ""
    capabilities_key = ""

    @abstractmethod
    def list_layers(self, entry):
        """Return a list of (layer_name, layer_title) for a catalog entry."""

    @abstractmethod
    def create_layer(self, entry, layer_name, options=None, parent=None):
        """Build and return a QGIS layer for the given service entry."""


def _find_text_in_children(element, tag_names):
    """Return first non-empty child text for any local tag name in tag_names."""
    tag_names = set(tag_names)
    for child in list(element):
        local_name = child.tag.split("}", 1)[-1]
        if local_name in tag_names and child.text and child.text.strip():
            return child.text.strip()
    return None


def extract_wcs_coverages(root):
    """
    Extract coverage tuples from WCS GetCapabilities XML across common versions.

    Returns a list of (coverage_name, coverage_title).
    """
    coverage_nodes = root.findall(".//{*}CoverageSummary")
    if not coverage_nodes:
        coverage_nodes = root.findall(".//{*}CoverageOfferingBrief")

    coverages = []
    seen = set()

    for coverage in coverage_nodes:
        coverage_name = _find_text_in_children(
            coverage,
            {"CoverageId", "Identifier", "name", "Name"},
        )
        if not coverage_name:
            continue

        coverage_title = _find_text_in_children(coverage, {"Title", "label", "Label"})
        coverage_title = coverage_title or coverage_name

        if coverage_name not in seen:
            seen.add(coverage_name)
            coverages.append((coverage_name, coverage_title))

    return coverages
