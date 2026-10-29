import unittest
from .test_wfs_handler import WfsServiceHandler
from dbdg_inde_testpkg.wfs_attribute_filter import attribute_filter, combine_filters
from xml.etree import ElementTree as ET
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs
from pathlib import Path


class AttributeFilterTest(unittest.TestCase):
    def test_in_generates_or_of_literal_equalities(self):
        root = ET.fromstring(attribute_filter('sigla', 'text', 'in', "'RJ', 'ES', 'MG'"))
        self.assertTrue(root[0].tag.endswith('Or'))
        self.assertEqual([node[1].text for node in root[0]], ['RJ', 'ES', 'MG'])
        self.assertTrue(all(node.tag.endswith('PropertyIsEqualTo') for node in root[0]))
        self.assertTrue(all(node[0].text == 'sigla' for node in root[0]))

    def test_in_handles_quotes_commas_and_xml_as_literal_values(self):
        root = ET.fromstring(attribute_filter('nome', 'text', 'in', "('D''Ávila', 'A,B', '<&>')"))
        self.assertEqual([node[1].text for node in root[0]], ["D'Ávila", 'A,B', '<&>'])
        root = ET.fromstring(attribute_filter('sigla', 'text', 'in', 'RJ'))
        self.assertTrue(root[0].tag.endswith('PropertyIsEqualTo'))
        self.assertEqual(root[0][1].text, 'RJ')

    def test_in_rejects_invalid_lists(self):
        for value in ("'RJ',", ",RJ", "RJ,,ES", "'RJ", "()", "''", "('RJ', 'ES'", "RJ 'ES'"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                attribute_filter('sigla', 'text', 'in', value)

    def test_in_stays_grouped_when_combined_with_bbox(self):
        root = ET.fromstring(combine_filters(
            attribute_filter('sigla', 'text', 'in', "'RJ', 'ES', 'MG'"),
            bbox='-48,-16,-46,-14,EPSG:4326', geometry_property='geom'))
        self.assertTrue(root[0].tag.endswith('And'))
        self.assertTrue(root[0][0].tag.endswith('Or'))
        self.assertEqual(len(root[0][0]), 3)
        self.assertTrue(root[0][1].tag.endswith('BBOX'))

    def test_text_escapes_xml_and_like_metacharacters(self):
        root = ET.fromstring(attribute_filter('nome', 'text', 'contains', 'Brasília & 10%_*'))
        self.assertEqual(root[0][1].text, r'*Brasília & 10%\_\**')

    def test_numeric_validation(self):
        self.assertIn('100000', attribute_filter('pop', 'integer', 'gt', '100000'))
        for value in ('100 mil', 'NaN', '1.5'):
            with self.assertRaises(ValueError):
                attribute_filter('pop', 'integer', 'gt', value)
        root = ET.fromstring(attribute_filter('area', 'number', 'le', '12,5'))
        self.assertEqual(root[0][1].text, '12.5')
        with self.assertRaises(ValueError):
            attribute_filter('area', 'number', 'contains', '12')

    def test_combines_advanced_spatial_filter_without_losing_geometry(self):
        spatial = '''<fes:Filter xmlns:fes="http://www.opengis.net/fes/2.0"
        xmlns:gml="http://www.opengis.net/gml/3.2"><fes:Intersects>
        <fes:ValueReference>geom</fes:ValueReference>
        <gml:Point srsName="EPSG:4326"><gml:pos>-16 -48</gml:pos></gml:Point>
        </fes:Intersects></fes:Filter>'''
        root = ET.fromstring(combine_filters(spatial, attribute_filter('nome', 'text', 'eq', '<Brasília>')))
        self.assertTrue(root[0][0].tag.endswith('Intersects'))
        self.assertEqual(root[0][0][1][0].text, '-16 -48')
        self.assertEqual(root[0][1][1].text, '<Brasília>')

    def test_combines_bbox_and_attribute_with_and(self):
        result = combine_filters(attribute_filter('pop', 'integer', 'gt', '100000'),
                                 bbox='-48,-16,-46,-14,EPSG:4326', geometry_property='geom')
        root = ET.fromstring(result)
        self.assertTrue(root[0].tag.endswith('And'))
        self.assertTrue(root[0][1].tag.endswith('BBOX'))
        envelope = root[0][1][1]
        self.assertEqual(envelope[0].text, '-16 -48')
        self.assertEqual(envelope[1].text, '-14 -46')

    def test_discovers_only_supported_scalar_fields(self):
        xml = b'''<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
        <xs:complexType name="cityType"><xs:sequence>
        <xs:element name="nome" type="xs:string"/>
        <xs:element name="pop" type="xs:long"/>
        <xs:element name="geom" type="gml:PointPropertyType"/>
        <xs:element name="date" type="xs:date"/>
        </xs:sequence></xs:complexType></xs:schema>'''
        self.assertEqual(WfsServiceHandler._parse_attribute_fields(xml),
                         [('nome', 'text'), ('pop', 'integer')])

    def test_download_and_hits_send_identical_filter_and_keep_limit(self):
        from dbdg_inde_testpkg.service_handlers import wfs_handler
        encoding = combine_filters(attribute_filter('sigla', 'text', 'in', "'RJ', 'ES', 'MG'"),
                                   bbox='-48,-16,-46,-14,EPSG:4326', geometry_property='geom')
        urls = []
        class Response:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def read(self):
                return b'<FeatureCollection numberMatched="25"/>'
        handler = WfsServiceHandler()
        with patch.object(wfs_handler, 'urlopen', side_effect=lambda url, **kwargs: (urls.append(url) or Response())):
            self.assertEqual(handler.get_feature_count({'url': 'https://example.invalid/wfs'}, 'cities',
                                                      count=10, filter_encoding=encoding), 10)
        def download(url, *args, **kwargs):
            urls.append(url)
            return b'{}'
        with patch.object(handler, '_attempt_download', side_effect=download):
            path, _ = handler._download_wfs_file('https://example.invalid/wfs', 'cities',
                                                'application/json', count=10, filter_encoding=encoding)
        Path(path).unlink()
        queries = [parse_qs(urlparse(url).query) for url in urls]
        self.assertEqual(queries[0]['FILTER'], queries[1]['FILTER'])
        self.assertNotIn('BBOX', queries[1])
        self.assertEqual(queries[1]['COUNT'], ['10'])
