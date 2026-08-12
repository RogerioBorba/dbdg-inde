"""Minimal defusedxml-compatible exceptions used by the plugin."""


class DefusedXmlException(ValueError):
    """Base exception for blocked unsafe XML constructs."""


class DTDForbidden(DefusedXmlException):
    """Raised when a document type declaration is present."""


class EntitiesForbidden(DefusedXmlException):
    """Raised when an entity declaration or reference is present."""

