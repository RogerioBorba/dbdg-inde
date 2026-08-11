"""Safe subset of defusedxml.ElementTree used by this plugin.

This module intentionally mirrors the small API surface needed here while
remaining dependency-free for QGIS Python environments that do not include the
third-party defusedxml package.
"""

import re
import xml.parsers.expat as expat
import xml.etree.ElementTree as _ET

from .common import DTDForbidden, EntitiesForbidden


ParseError = _ET.ParseError

_DOCTYPE_RE = re.compile(br"<!DOCTYPE\b", re.IGNORECASE)
_ENTITY_DECL_RE = re.compile(br"<!ENTITY\b", re.IGNORECASE)


def fromstring(text, parser=None):
    """Parse XML after blocking DTDs and custom entity expansion."""
    if parser is not None:
        raise ValueError("Custom XML parsers are not supported")
    if isinstance(text, str):
        raw = text.encode("utf-8")
    else:
        raw = bytes(text)

    if _DOCTYPE_RE.search(raw):
        raise DTDForbidden("DTD declarations are forbidden")
    if _ENTITY_DECL_RE.search(raw):
        raise EntitiesForbidden("Entity declarations are forbidden")

    root = None
    stack = []

    def convert_name(name):
        return "{" + name if "}" in name else name

    def start_element(name, attrs):
        nonlocal root
        element = _ET.Element(
            convert_name(name),
            {convert_name(attr_name): attr_value for attr_name, attr_value in attrs.items()},
        )
        if stack:
            stack[-1].append(element)
        else:
            root = element
        stack.append(element)

    def end_element(name):
        if not stack or stack[-1].tag != convert_name(name):
            raise ParseError("mismatched tag")
        stack.pop()

    def character_data(data):
        if not stack:
            return
        parent = stack[-1]
        if len(parent):
            child = parent[-1]
            child.tail = (child.tail or "") + data
        else:
            parent.text = (parent.text or "") + data

    active_parser = expat.ParserCreate(namespace_separator="}")
    active_parser.StartElementHandler = start_element
    active_parser.EndElementHandler = end_element
    active_parser.CharacterDataHandler = character_data

    try:
        active_parser.Parse(raw, True)
    except expat.ExpatError as error:
        raise ParseError(str(error)) from error

    if root is None or stack:
        raise ParseError("no element found")
    return root


def parse(source, parser=None):
    """Parse a file-like source after applying the same protections."""
    if hasattr(source, "read"):
        data = source.read()
        return _ET.ElementTree(fromstring(data, parser=parser))

    with open(source, "rb") as handle:
        data = handle.read()
    return _ET.ElementTree(fromstring(data, parser=parser))


Element = _ET.Element
ElementTree = _ET.ElementTree
SubElement = _ET.SubElement
TreeBuilder = _ET.TreeBuilder
tostring = _ET.tostring
