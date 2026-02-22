import xml.etree.ElementTree as ET
from qgis.core import QgsMessageLog, Qgis, QgsRasterLayer, QgsProject
from qgis.PyQt.QtWidgets import QMessageBox

class WMSService:
    """Classe para manipular serviços WMS."""
    
    @staticmethod
    def parse_capabilities(root):
        """Analisa o documento WMS GetCapabilities."""
        try:
            QgsMessageLog.logMessage("Iniciando parse do WMS Capabilities", "IndeServicosBR", Qgis.Info)
            
            # O namespace padrão é definido no elemento raiz
            default_ns = root.tag.split('}')[0].strip('{') if '}' in root.tag else None
            QgsMessageLog.logMessage(f"Namespace padrão: {default_ns}", "IndeServicosBR", Qgis.Info)
            
            namespaces = {}
            if default_ns:
                namespaces['wms'] = default_ns
            
            def extract_layers(layer_elem, layers_list):
                """Função recursiva para extrair camadas e subcamadas."""
                # Tentar obter nome e título
                name = None
                title = None
                
                # Primeiro, tentar com namespace
                if 'wms' in namespaces:
                    name_elem = layer_elem.find('wms:Name', namespaces)
                    title_elem = layer_elem.find('wms:Title', namespaces)
                
                # Se não encontrar, tentar sem namespace
                if name_elem is None:
                    name_elem = layer_elem.find('Name')
                if title_elem is None:
                    title_elem = layer_elem.find('Title')
                
                if name_elem is not None and name_elem.text:
                    name = name_elem.text
                    title = title_elem.text if title_elem is not None else name
                    
                    # Adicionar camada à lista
                    layer_info = {
                        'name': name,
                        'title': title
                    }
                    layers_list.append(layer_info)
                    QgsMessageLog.logMessage(f"Camada encontrada: {name} ({title})", "IndeServicosBR", Qgis.Info)
                
                # Procurar por subcamadas
                # Primeiro com namespace
                if 'wms' in namespaces:
                    sublayers = layer_elem.findall('wms:Layer', namespaces)
                
                # Se não encontrar, tentar sem namespace
                if not sublayers:
                    sublayers = layer_elem.findall('Layer')
                
                for sublayer in sublayers:
                    extract_layers(sublayer, layers_list)
            
            # Encontrar o elemento Capability
            capability = None
            if 'wms' in namespaces:
                capability = root.find('.//wms:Capability', namespaces)
            if capability is None:
                capability = root.find('.//Capability')
            
            if capability is None:
                QgsMessageLog.logMessage("Elemento Capability não encontrado", "IndeServicosBR", Qgis.Warning)
                return []
            
            # Processar todas as camadas
            layers = []
            
            # Primeiro com namespace
            if 'wms' in namespaces:
                root_layers = capability.findall('.//wms:Layer', namespaces)
            
            # Se não encontrar, tentar sem namespace
            if not root_layers:
                root_layers = capability.findall('.//Layer')
            
            QgsMessageLog.logMessage(f"Número de camadas encontradas: {len(root_layers)}", "IndeServicosBR", Qgis.Info)
            
            for layer in root_layers:
                extract_layers(layer, layers)
            
            QgsMessageLog.logMessage(f"Total de camadas processadas: {len(layers)}", "IndeServicosBR", Qgis.Info)
            return layers
            
        except Exception as e:
            QgsMessageLog.logMessage(f"Erro ao processar WMS Capabilities: {str(e)}", "IndeServicosBR", Qgis.Critical)
            return []
            
    @staticmethod
    def load_layer(url, layer_name, display_name):
        """Carrega uma camada WMS no projeto."""
        try:
            layer = QgsRasterLayer(
                f"type=wms&url={url}&layers={layer_name}&styles=&format=image/png&crs=EPSG:4326",
                display_name,
                "wms"
            )
            
            if layer.isValid():
                QgsProject.instance().addMapLayer(layer)
                return True
            else:
                QMessageBox.warning(None, "Erro", "Camada WMS inválida")
                return False
                
        except Exception as e:
            QMessageBox.warning(None, "Erro", f"Erro ao carregar camada WMS: {str(e)}")
            return False 