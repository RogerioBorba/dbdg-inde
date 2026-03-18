import json

from .network_utils import urlopen


CATALOG_URL = "https://inde.gov.br/api/catalogo/get"


def fetch_catalog():
    """Download and parse JSON catalog from the INDE API."""
    with urlopen(CATALOG_URL, timeout=40) as response:
        return json.load(response)
