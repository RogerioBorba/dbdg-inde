import unittest

from ..service_handlers.base import extract_wcs_coverages, parse_xml_safe


class ExtractWcsCoveragesTest(unittest.TestCase):
    def test_extracts_wcs_2_coverage_summary_with_coverage_id(self):
        xml = b"""
        <wcs:Capabilities xmlns:wcs="http://www.opengis.net/wcs/2.0"
                          xmlns:ows="http://www.opengis.net/ows/2.0">
          <wcs:Contents>
            <wcs:CoverageSummary>
              <wcs:CoverageId>funai:layer_1</wcs:CoverageId>
              <ows:Title>Camada 1</ows:Title>
            </wcs:CoverageSummary>
            <wcs:CoverageSummary>
              <wcs:CoverageId>funai:layer_2</wcs:CoverageId>
            </wcs:CoverageSummary>
          </wcs:Contents>
        </wcs:Capabilities>
        """
        root = parse_xml_safe(xml)
        self.assertEqual(
            extract_wcs_coverages(root),
            [("funai:layer_1", "Camada 1"), ("funai:layer_2", "funai:layer_2")],
        )

    def test_extracts_wcs_summary_with_identifier(self):
        xml = b"""
        <wcs:Capabilities xmlns:wcs="http://www.opengis.net/wcs/1.1.1"
                          xmlns:ows="http://www.opengis.net/ows/1.1">
          <wcs:Contents>
            <wcs:CoverageSummary>
              <ows:Identifier>cmr:cobertura_a</ows:Identifier>
              <ows:Title>Cobertura A</ows:Title>
            </wcs:CoverageSummary>
          </wcs:Contents>
        </wcs:Capabilities>
        """
        root = parse_xml_safe(xml)
        self.assertEqual(extract_wcs_coverages(root), [("cmr:cobertura_a", "Cobertura A")])

    def test_extracts_wcs_1_coverage_offering_brief(self):
        xml = b"""
        <wcs:WCS_Capabilities xmlns:wcs="http://www.opengis.net/wcs">
          <wcs:ContentMetadata>
            <wcs:CoverageOfferingBrief>
              <wcs:name>cmr:raster_1</wcs:name>
              <wcs:label>Raster 1</wcs:label>
            </wcs:CoverageOfferingBrief>
          </wcs:ContentMetadata>
        </wcs:WCS_Capabilities>
        """
        root = parse_xml_safe(xml)
        self.assertEqual(extract_wcs_coverages(root), [("cmr:raster_1", "Raster 1")])

    def test_ignores_entries_without_identifier_and_deduplicates(self):
        xml = b"""
        <wcs:Capabilities xmlns:wcs="http://www.opengis.net/wcs/2.0">
          <wcs:Contents>
            <wcs:CoverageSummary>
              <wcs:Title>Sem identificador</wcs:Title>
            </wcs:CoverageSummary>
            <wcs:CoverageSummary>
              <wcs:CoverageId>dup:item</wcs:CoverageId>
            </wcs:CoverageSummary>
            <wcs:CoverageSummary>
              <wcs:CoverageId>dup:item</wcs:CoverageId>
            </wcs:CoverageSummary>
          </wcs:Contents>
        </wcs:Capabilities>
        """
        root = parse_xml_safe(xml)
        self.assertEqual(extract_wcs_coverages(root), [("dup:item", "dup:item")])


if __name__ == "__main__":
    unittest.main()
