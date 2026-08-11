import json
import unittest
from unittest import mock

from .. import catalog_client
from ..network_utils import MemoryResponse


class CatalogClientTest(unittest.TestCase):
    def test_fetch_catalog_parses_json_list(self):
        response = MemoryResponse(
            b'[{"descricao": "IBGE"}]',
            status=200,
            headers={"Content-Type": "application/json"},
        )
        with mock.patch.object(catalog_client, "urlopen", return_value=response) as opener:
            catalog = catalog_client.fetch_catalog()

        self.assertEqual(catalog, [{"descricao": "IBGE"}])
        self.assertEqual(opener.call_args.kwargs["headers"], catalog_client._CATALOG_HEADERS)

    def test_fetch_catalog_preserves_igeoservico_descricao_contract(self):
        expected = {
            "descricao": "IBGE",
            "url": "https://example.gov/ows",
            "nivel_no": "1",
            "wcsAvalaible": False,
            "wcsGetCapabilities": "",
            "wfsAvalaible": True,
            "wfsGetCapabilities": "https://example.gov/ows?service=WFS",
            "wmsAvalaible": True,
            "wmsGetCapabilities": "https://example.gov/ows?service=WMS",
            "cswAvalaible": False,
            "cswGetCapabilities": "",
        }
        response = MemoryResponse(
            json.dumps([expected]).encode("utf-8"),
            status=200,
            headers={"Content-Type": "application/json"},
        )
        with mock.patch.object(catalog_client, "urlopen", return_value=response):
            entry = catalog_client.fetch_catalog()[0]

        for key, value in expected.items():
            self.assertEqual(entry[key], value)

    def test_fetch_catalog_accepts_double_encoded_json(self):
        inner_catalog = json.dumps(
            [{"descricao": "BNDES", "wmsAvailable": True}]
        )
        response = MemoryResponse(
            json.dumps(inner_catalog).encode("utf-8"),
            status=200,
            headers={"Content-Type": "application/json"},
        )
        with mock.patch.object(catalog_client, "urlopen", return_value=response):
            catalog = catalog_client.fetch_catalog()

        self.assertEqual(
            catalog,
            [{"descricao": "BNDES", "wmsAvailable": True}],
        )

    def test_service_availability_accepts_both_spellings(self):
        self.assertTrue(
            catalog_client.service_is_available({"wmsAvalaible": True}, "wms")
        )
        self.assertTrue(
            catalog_client.service_is_available({"wmsAvailable": True}, "wms")
        )
        self.assertFalse(catalog_client.service_is_available({}, "wms"))

    def test_service_availability_prefers_documented_spelling(self):
        entry = {"wmsAvalaible": False, "wmsAvailable": True}
        self.assertFalse(catalog_client.service_is_available(entry, "wms"))

    def test_fetch_catalog_retries_with_python_after_empty_qgis_response(self):
        responses = [
            MemoryResponse(b"", status=200),
            MemoryResponse(b"[]", status=200),
        ]
        with mock.patch.object(catalog_client, "urlopen", side_effect=responses) as opener:
            catalog = catalog_client.fetch_catalog()

        self.assertEqual(catalog, [])
        self.assertTrue(opener.call_args_list[0].kwargs["use_qgis"])
        self.assertFalse(opener.call_args_list[1].kwargs["use_qgis"])

    def test_fetch_catalog_reports_both_failures(self):
        responses = [
            MemoryResponse(b"", status=200),
            MemoryResponse(b"<html>indisponivel</html>", status=200),
            MemoryResponse(b"<html>indisponivel</html>", status=200),
            MemoryResponse(b"<html>indisponivel</html>", status=200),
        ]
        with mock.patch.object(catalog_client, "urlopen", side_effect=responses):
            with self.assertRaisesRegex(
                catalog_client.CatalogError,
                "API bloqueada pelo Qt/QGIS.*página pública indisponível",
            ):
                catalog_client.fetch_catalog()

    def test_catalog_must_be_a_list(self):
        responses = [
            MemoryResponse(b'{"erro": "indisponivel"}', status=200),
            MemoryResponse(b'{"erro": "indisponivel"}', status=200),
            MemoryResponse(b"<html>indisponivel</html>", status=200),
            MemoryResponse(b"<html>indisponivel</html>", status=200),
        ]
        with mock.patch.object(catalog_client, "urlopen", side_effect=responses):
            with self.assertRaisesRegex(catalog_client.CatalogError, "formato inesperado"):
                catalog_client.fetch_catalog()

    def test_catalog_page_parser_extracts_service_entries(self):
        html = b"""
        <ul class="list">
          <li><span>Instituicao</span><span>Servicos</span></li>
          <li>
            <span>ANA - Agencia Nacional de Aguas</span>
            <span>
              <button url="https://example.gov/ows?service=wms&amp;request=GetCapabilities">WMS</button>
              <button url="" disabled>WFS</button>
              <button url="https://example.gov/ows?service=WCS&amp;request=GetCapabilities">WCS</button>
            </span>
          </li>
        </ul>
        """
        parser = catalog_client._CatalogPageParser()
        parser.feed(html.decode("utf-8"))

        self.assertEqual(len(parser.catalog), 1)
        entry = parser.catalog[0]
        self.assertEqual(entry["descricao"], "ANA - Agencia Nacional de Aguas")
        self.assertEqual(entry["url"], "https://example.gov/ows")
        self.assertTrue(entry["wmsAvalaible"])
        self.assertFalse(entry["wfsAvalaible"])
        self.assertTrue(entry["wcsAvalaible"])

    def test_fetch_catalog_uses_public_page_when_api_is_blocked(self):
        html = b"""
        <li><span>IBGE</span><span>
          <button url="https://example.gov/ows?service=wms">WMS</button>
        </span></li>
        """
        responses = [
            MemoryResponse(b"Request Rejected", status=200),
            MemoryResponse(b"Request Rejected", status=200),
            MemoryResponse(html, status=200),
        ]
        with mock.patch.object(catalog_client, "urlopen", side_effect=responses) as opener:
            catalog = catalog_client.fetch_catalog()

        self.assertEqual(catalog[0]["descricao"], "IBGE")
        self.assertEqual(opener.call_args_list[2].args[0], catalog_client.CATALOG_PAGE_URL)


if __name__ == "__main__":
    unittest.main()
