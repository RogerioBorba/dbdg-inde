"""Build the single attribute condition and combine WFS 2.0 predicates."""
from decimal import Decimal, InvalidOperation
import re
from xml.etree import ElementTree as XML
from .service_handlers.base import parse_xml_safe

FES = 'http://www.opengis.net/fes/2.0'
GML = 'http://www.opengis.net/gml/3.2'
XML.register_namespace('fes', FES)
XML.register_namespace('gml', GML)
OPERATORS = [('Igual a', 'eq'), ('Diferente de', 'ne')]
TEXT_OPERATORS = OPERATORS + [('Contém', 'contains'), ('Começa com', 'starts'), ('IN (na lista)', 'in')]
NUMBER_OPERATORS = OPERATORS + [('Maior que', 'gt'), ('Maior ou igual a', 'ge'),
                                ('Menor que', 'lt'), ('Menor ou igual a', 'le')]


def _in_values(value):
    value = value.strip()
    if value.startswith('(') and value.endswith(')'):
        value = value[1:-1].strip()
    token = re.compile(r'''\s*('(?:[^']|'')*'|"(?:[^"]|"")*"|[^,'"()]+)\s*(,|$)''')
    values = []
    position = 0
    while position < len(value):
        match = token.match(value, position)
        if not match:
            break
        item = match[1].strip()
        if item.startswith(("'", '"')):
            quote = item[0]
            item = item[1:-1].replace(quote * 2, quote)
        if not item:
            break
        values.append(item)
        position = match.end()
        if not match[2]:
            return values
    raise ValueError("Informe uma lista válida, por exemplo: 'RJ', 'ES', 'MG'.")


def attribute_filter(field, kind, operator, value):
    if not field or not value.strip():
        raise ValueError('Informe o campo e o valor da condição.')
    allowed = TEXT_OPERATORS if kind == 'text' else NUMBER_OPERATORS
    if operator not in dict((code, label) for label, code in allowed):
        raise ValueError('Operador incompatível com o tipo do campo.')
    if operator == 'in':
        values = _in_values(value)
        root = XML.Element('{%s}Filter' % FES)
        target = XML.SubElement(root, '{%s}Or' % FES) if len(values) > 1 else root
        for item in values:
            target.extend(list(XML.fromstring(attribute_filter(field, kind, 'eq', item))))
        return XML.tostring(root, encoding='unicode')
    if kind != 'text':
        try:
            number = Decimal(value.strip().replace(',', '.'))
        except InvalidOperation:
            raise ValueError('Informe um número válido, sem separador de milhares.')
        if not number.is_finite() or (kind == 'integer' and number != number.to_integral_value()):
            raise ValueError('Informe um número inteiro válido.' if kind == 'integer' else 'Informe um número finito.')
        value = format(number, 'f')
    root = XML.Element('{%s}Filter' % FES)
    tags = dict(eq='PropertyIsEqualTo', ne='PropertyIsNotEqualTo', gt='PropertyIsGreaterThan',
                ge='PropertyIsGreaterThanOrEqualTo', lt='PropertyIsLessThan', le='PropertyIsLessThanOrEqualTo')
    predicate = XML.SubElement(root, '{%s}%s' % (FES, tags.get(operator, 'PropertyIsLike')))
    if operator in ('contains', 'starts'):
        predicate.attrib.update(wildCard='*', singleChar='_', escapeChar='\\', matchCase='false')
        value = value.replace('\\', '\\\\').replace('*', '\\*').replace('_', '\\_')
        value = ('*' if operator == 'contains' else '') + value + '*'
    XML.SubElement(predicate, '{%s}ValueReference' % FES).text = field
    XML.SubElement(predicate, '{%s}Literal' % FES).text = value
    return XML.tostring(root, encoding='unicode')


def combine_filters(*filters, bbox=None, geometry_property=None):
    predicates = []
    for value in filters:
        if value:
            predicates.extend(list(parse_xml_safe(value)))
    if bbox:
        if not geometry_property:
            raise ValueError('Não foi possível identificar a geometria para combinar BBOX e atributo.')
        parts = bbox.split(',')
        predicate = XML.Element('{%s}BBOX' % FES)
        XML.SubElement(predicate, '{%s}ValueReference' % FES).text = geometry_property
        crs = parts[4] if len(parts) == 5 else 'EPSG:4326'
        # EPSG:4326 has latitude/longitude axis order in GML 3.2.
        swap = crs.upper() == 'EPSG:4326'
        envelope = XML.SubElement(predicate, '{%s}Envelope' % GML, srsName=crs)
        XML.SubElement(envelope, '{%s}lowerCorner' % GML).text = ' '.join([parts[1], parts[0]] if swap else parts[:2])
        XML.SubElement(envelope, '{%s}upperCorner' % GML).text = ' '.join([parts[3], parts[2]] if swap else parts[2:4])
        predicates.append(predicate)
    if not predicates:
        return ''
    root = XML.Element('{%s}Filter' % FES)
    target = XML.SubElement(root, '{%s}And' % FES) if len(predicates) > 1 else root
    target.extend(predicates)
    return XML.tostring(root, encoding='unicode')
