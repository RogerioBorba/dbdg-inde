import json
import ssl
import urllib.request


CATALOG_URL = "https://inde.gov.br/api/catalogo/get"


def fetch_catalog():
    """Download and parse JSON catalog from the INDE API."""
    context = ssl.create_default_context()
    with urllib.request.urlopen(CATALOG_URL, context=context, timeout=30) as response:
        return json.load(response)
