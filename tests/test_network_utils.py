import os
import unittest
from unittest import mock

from .. import network_utils


class NetworkUtilsTest(unittest.TestCase):
    def test_bundled_ca_bundle_exists(self):
        ca_bundle = network_utils._ca_bundle_path()
        self.assertIsNotNone(ca_bundle)
        self.assertTrue(os.path.exists(ca_bundle))

    def test_create_ssl_context_loads_ca_certificates(self):
        context = network_utils.create_ssl_context()
        self.assertGreater(context.cert_store_stats().get("x509_ca", 0), 0)

    def test_urlopen_rejects_non_http_scheme(self):
        with self.assertRaises(ValueError):
            network_utils.urlopen("file:///etc/passwd")

    def test_urlopen_rejects_url_without_network_location(self):
        with self.assertRaises(ValueError):
            network_utils.urlopen("https:///missing-host")

    def test_urlopen_passes_validated_url_to_python_fallback(self):
        expected_response = network_utils.MemoryResponse(b"ok")
        context = object()

        with mock.patch.object(network_utils, "_urlopen_with_qgis", side_effect=ImportError):
            with mock.patch.object(
                network_utils,
                "_python_urlopen_http",
                return_value=expected_response,
            ) as python_urlopen_http:
                response = network_utils.urlopen("https://example.com/data.xml", context=context)

        self.assertIs(response, expected_response)
        python_urlopen_http.assert_called_once_with(
            "https://example.com/data.xml",
            context=context,
            timeout=40,
            headers=None,
        )

    def test_urlopen_can_force_python_backend_and_pass_headers(self):
        expected_response = network_utils.MemoryResponse(b"ok")
        context = object()
        headers = {"Accept": "application/json"}

        with mock.patch.object(
            network_utils,
            "_urlopen_with_qgis",
        ) as qgis_urlopen:
            with mock.patch.object(
                network_utils,
                "_python_urlopen_http",
                return_value=expected_response,
            ) as python_urlopen_http:
                response = network_utils.urlopen(
                    "https://example.com/catalog.json",
                    context=context,
                    headers=headers,
                    use_qgis=False,
                )

        self.assertIs(response, expected_response)
        qgis_urlopen.assert_not_called()
        python_urlopen_http.assert_called_once_with(
            "https://example.com/catalog.json",
            context=context,
            timeout=40,
            headers=headers,
        )


if __name__ == "__main__":
    unittest.main()
