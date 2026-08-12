import unittest

from ..defusedxml.common import DefusedXmlException

from ..service_handlers.base import parse_xml_safe


class ParseXmlSafeTest(unittest.TestCase):
    def test_parses_well_formed_xml(self):
        root = parse_xml_safe(b"<root><a>1</a></root>")
        self.assertEqual(root.tag, "root")
        self.assertEqual(root.find("a").text, "1")

    def test_recovers_from_mismatched_tag(self):
        malformed = b"<root><a><b>value</a></b></root>"
        root = parse_xml_safe(malformed)
        self.assertEqual(root.find("a/b").text, "value")

    def test_decodes_html_named_entity(self):
        malformed = b"<root><a>x&nbsp;y</a></root>"
        root = parse_xml_safe(malformed)
        self.assertEqual(root.find("a").text, "x\xa0y")

    def test_rejects_entity_expansion(self):
        malicious = b"""<!DOCTYPE root [
        <!ENTITY xxe SYSTEM "file:///etc/passwd">
        ]>
        <root>&xxe;</root>
        """

        with self.assertRaises(DefusedXmlException):
            parse_xml_safe(malicious)


if __name__ == "__main__":
    unittest.main()
