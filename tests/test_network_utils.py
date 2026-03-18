import os
import unittest

from .. import network_utils


class NetworkUtilsTest(unittest.TestCase):
    def test_bundled_ca_bundle_exists(self):
        ca_bundle = network_utils._ca_bundle_path()
        self.assertIsNotNone(ca_bundle)
        self.assertTrue(os.path.exists(ca_bundle))

    def test_create_ssl_context_loads_ca_certificates(self):
        context = network_utils.create_ssl_context()
        self.assertGreater(context.cert_store_stats().get("x509_ca", 0), 0)


if __name__ == "__main__":
    unittest.main()
