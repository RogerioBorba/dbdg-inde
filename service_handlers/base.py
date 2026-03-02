from abc import ABC, abstractmethod
import re
import xml.etree.ElementTree as ET


_NUMERIC_CHAR_REF_RE = re.compile(rb"&#(x[0-9A-Fa-f]+|\d+);")
_INVALID_CONTROL_BYTES_RE = re.compile(rb"[\x00-\x08\x0B\x0C\x0E-\x1F]")


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


def parse_xml_safe(xml_data):
    """Parse XML bytes, trying a sanitized fallback for malformed capabilities."""
    try:
        return ET.fromstring(xml_data)
    except ET.ParseError:
        cleaned = _strip_invalid_numeric_references(xml_data)
        cleaned = _INVALID_CONTROL_BYTES_RE.sub(b"", cleaned)
        return ET.fromstring(cleaned)


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
