def build_service_handlers():
    """Factory to assemble available OGC service handlers."""
    from .wcs_handler import WcsServiceHandler
    from .wfs_handler import WfsServiceHandler
    from .wms_handler import WmsServiceHandler

    return {
        "wms": WmsServiceHandler(),
        "wfs": WfsServiceHandler(),
        "wcs": WcsServiceHandler(),
    }
