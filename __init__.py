# Conteúdo do arquivo __init__.py
"""
/***************************************************************************
 IndeServicosBR
                                 A QGIS plugin
 Plugin para acesso aos geoserviços da INDE Brasil
                             -------------------
        begin                : 2025-03-18
        copyright            : (C) 2025
        authors              : Rogério Borba
        email                : rogerio.borba@ibge.gov.br
        organization         : IBGE
 ***************************************************************************/
"""

def classFactory(iface):
    """
    Carrega a classe principal do plugin IndeServicosBR.
    
    :param iface: Interface QGIS
    :type iface: QgsInterface
    :return: IndeServicosBR
    :rtype: IndeServicosBR
    """
    from .inde_servicos_br import IndeServicosBR
    return IndeServicosBR(iface)
