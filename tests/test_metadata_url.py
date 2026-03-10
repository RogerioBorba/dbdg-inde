import unittest
from ..metadata_viewer import _prepare_metadata_url


class MetadataUrlNormalizationTest(unittest.TestCase):
    def test_add_output_schema_to_csw_getrecord(self):
        url = (
            "http://example.com/csw?service=CSW&request=GetRecordById&version=2.0.2&id=abcd"
        )
        normalized = _prepare_metadata_url(url)
        self.assertIn("outputSchema=http%3A%2F%2Fwww.isotc211.org%2F2005%2Fgmd", normalized)

    def test_do_not_duplicate_existing_output_schema(self):
        url = (
            "http://example.com/csw?service=csw&request=GetRecord&outputSchema="
            "http://www.isotc211.org/2005/gmd&id=123"
        )
        normalized = _prepare_metadata_url(url)
        # should be identical because schema already present
        self.assertEqual(url, normalized)

    def test_ignore_non_csw_urls(self):
        url = "http://example.com/metadata.xml"
        self.assertEqual(_prepare_metadata_url(url), url)

    def test_ignore_csw_but_not_getrecord(self):
        url = "http://example.com/csw?service=CSW&request=GetCapabilities"
        self.assertEqual(_prepare_metadata_url(url), url)

    def test_convert_geonetwork_catalog_search_to_csw_getrecordbyid(self):
        url = (
            "https://idem.dhn.mar.mil.br/geonetwork/srv/por/catalog.search"
            "#/metadata/26de5378-8016-428e-83cb-993d745b5cdf"
        )
        normalized = _prepare_metadata_url(url)
        self.assertIn("/geonetwork/srv/por/csw?", normalized)
        self.assertIn("request=GetRecordById", normalized)
        self.assertIn("id=26de5378-8016-428e-83cb-993d745b5cdf", normalized)
        self.assertIn("outputSchema=http%3A%2F%2Fwww.isotc211.org%2F2005%2Fgmd", normalized)

    def test_geonetwork_csw_getrecord_forces_gmd_schema(self):
        url = (
            "https://idem.dhn.mar.mil.br/geonetwork/srv/por/csw?"
            "service=CSW&request=GetRecordById&id=abcd"
        )
        normalized = _prepare_metadata_url(url)
        self.assertIn("outputSchema=http%3A%2F%2Fwww.isotc211.org%2F2005%2Fgmd", normalized)

    def test_replace_existing_non_gmd_output_schema(self):
        url = (
            "https://idem.dhn.mar.mil.br/geonetwork/srv/por/csw?"
            "service=CSW&request=GetRecordById&id=abcd&outputSchema=csw:IsoRecord"
        )
        normalized = _prepare_metadata_url(url)
        self.assertIn("outputSchema=http%3A%2F%2Fwww.isotc211.org%2F2005%2Fgmd", normalized)


if __name__ == "__main__":
    unittest.main()
