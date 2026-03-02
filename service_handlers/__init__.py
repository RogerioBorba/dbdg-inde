from .wms_handler import WmsServiceHandler
from .wfs_handler import WfsServiceHandler
from .wcs_handler import WcsServiceHandler


def build_service_handlers():
    """Factory to assemble available OGC service handlers."""
    return {
        "wms": WmsServiceHandler(),
        "wfs": WfsServiceHandler(),
        "wcs": WcsServiceHandler(),
    }
