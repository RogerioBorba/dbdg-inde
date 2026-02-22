# -*- coding: utf-8 -*-
"""
/***************************************************************************
 IndeServicosBR
                                 A QGIS plugin
 Plugin para acesso aos geoserviços da INDE Brasil
                              -------------------
        begin                : 2025-03-21
        copyright            : (C) 2025
        email                : dev@example.com
 ***************************************************************************/
"""

import os
import json
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, parse_qs

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt, QUrl, pyqtSignal
from qgis.PyQt.QtGui import QIcon, QDesktopServices
from qgis.PyQt.QtWidgets import (
    QAction, QMessageBox, QTreeWidget, QTreeWidgetItem, QDialog, 
    QVBoxLayout, QPushButton, QLabel, QProgressBar, QProgressDialog,
    QHBoxLayout, QTabWidget, QSplitter, QWidget, QComboBox, QLineEdit,
    QCheckBox, QApplication, QHeaderView
)
from qgis.core import QgsRasterLayer, QgsVectorLayer, QgsProject, QgsMessageLog, Qgis

from .inde_servicos_br_dialog import IndeServicosBRDialog
from .inde_service_item import IndeServiceItem
from .services import WMSService, WFSService, WCSService

class IndeServicosBR:
    """Plugin QGIS para acessar os serviços do DBDG da INDE Brasil."""

    def __init__(self, iface):
        """Inicializa o plugin.
        
        :param iface: Interface QGIS
        :type iface: QgsInterface
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = 'INDE Brasil'
        self.toolbar = self.iface.addToolBar('INDE Brasil')
        self.toolbar.setObjectName('IndeBrasilToolbar')
        self.api_url = "https://inde.gov.br/api/catalogo/get"
        self.services = []  # Lista de objetos IndeServiceItem
        
        # Dicionário para armazenar respostas de capabilities em cache
        self.capabilities_cache = {}
        
        # Inicializar o tradutor
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'IndeServicosBR_{}.qm'.format(locale))
            
        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

    def tr(self, message):
        """Tradução para o plugin."""
        return QCoreApplication.translate('IndeServicosBR', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True,
                   add_to_menu=True, add_to_toolbar=True, status_tip=None,
                   whats_this=None, parent=None):
        """Adiciona uma ação ao plugin."""
        icon = QIcon(icon_path) if icon_path else QIcon()
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToWebMenu(self.menu, action)

        self.actions.append(action)
        return action

    def initGui(self):
        """Cria as ações do menu e a barra de ferramentas."""
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.add_action(
            icon_path,
            text=self.tr('Serviços INDE Brasil'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Remove o plugin do QGIS."""
        for action in self.actions:
            self.iface.removePluginWebMenu(self.menu, action)
            self.toolbar.removeAction(action)
        del self.toolbar

    def fetch_services(self):
        """Busca os serviços disponíveis na API da INDE."""
        try:
            response = requests.get(self.api_url, verify=False)
            if response.status_code == 200:
                data = response.json()
                self.services = [IndeServiceItem(item) for item in data]
                return True
            else:
                QMessageBox.critical(None, "Erro", f"Falha ao obter dados: HTTP {response.status_code}")
                return False
        except Exception as e:
            QMessageBox.critical(None, "Erro", f"Erro ao conectar com a API da INDE: {str(e)}")
            return False

    def get_capabilities(self, url, service_type):
        """Obtém as capabilities do serviço."""
        try:
            # Mostrar mensagem de debug
            QgsMessageLog.logMessage(f"Obtendo capabilities de: {url}", "IndeServicosBR", Qgis.Info)
            
            # Atualizar status
            self.dialog.status_label.setText(f"Conectando ao serviço {service_type.upper()}...")
            QApplication.processEvents()
            
            response = requests.get(url)
            response.raise_for_status()
            
            # Mostrar mensagem de debug
            QgsMessageLog.logMessage("Resposta recebida com sucesso", "IndeServicosBR", Qgis.Info)
            
            # Atualizar status
            self.dialog.status_label.setText("Processando resposta do serviço...")
            QApplication.processEvents()
            
            root = ET.fromstring(response.content)
            
            if service_type.lower() == 'wms':
                return self.parse_wms_capabilities(root)
            elif service_type.lower() == 'wfs':
                return self.parse_wfs_capabilities(root)
            else:  # WCS
                return self.parse_wcs_capabilities(root)
                
        except requests.exceptions.RequestException as e:
            QgsMessageLog.logMessage(f"Erro na requisição: {str(e)}", "IndeServicosBR", Qgis.Critical)
            QMessageBox.warning(None, "Erro", f"Erro ao acessar o serviço: {str(e)}")
            return []
        except ET.ParseError as e:
            QgsMessageLog.logMessage(f"Erro ao parsear XML: {str(e)}", "IndeServicosBR", Qgis.Critical)
            QMessageBox.warning(None, "Erro", f"Erro ao processar resposta do serviço: {str(e)}")
            return []
        except Exception as e:
            QgsMessageLog.logMessage(f"Erro inesperado: {str(e)}", "IndeServicosBR", Qgis.Critical)
            QMessageBox.warning(None, "Erro", f"Erro inesperado: {str(e)}")
            return []

    def parse_wms_capabilities(self, root):
        """Parse WMS capabilities."""
        return WMSService.parse_capabilities(root)

    def parse_wfs_capabilities(self, root):
        """Parse WFS capabilities."""
        return WFSService.parse_capabilities(root)

    def parse_wcs_capabilities(self, root):
        """Parse WCS capabilities."""
        return WCSService.parse_capabilities(root)

    def load_wms_layer(self, url, layer_name, display_name):
        """Load WMS layer."""
        return WMSService.load_layer(url, layer_name, display_name)

    def load_wfs_layer(self, url, layer_name, display_name):
        """Load WFS layer."""
        return WFSService.load_layer(url, layer_name, display_name)

    def load_wcs_layer(self, url, coverage_name, display_name):
        """Load WCS layer."""
        return WCSService.load_layer(url, coverage_name, display_name)

    def populate_service_tree(self, tree, service_type):
        """Popula a árvore de serviços com os dados da API."""
        tree.clear()
        
        services_list = []
        for service in self.services:
            if service_type == 'wms' and service.wms_available:
                item = QTreeWidgetItem([service.descricao, service.nivel_no, service.wms_capabilities_url])
                item.setData(0, Qt.UserRole, service)
                services_list.append(item)
            elif service_type == 'wfs' and service.wfs_available:
                item = QTreeWidgetItem([service.descricao, service.nivel_no, service.wfs_capabilities_url])
                item.setData(0, Qt.UserRole, service)
                services_list.append(item)
            elif service_type == 'wcs' and service.wcs_available:
                item = QTreeWidgetItem([service.descricao, service.nivel_no, service.wcs_capabilities_url])
                item.setData(0, Qt.UserRole, service)
                services_list.append(item)
        
        # Ordenar por instituição por padrão
        services_list.sort(key=lambda item: item.text(0).lower())
        
        # Adicionar itens ordenados à árvore
        for item in services_list:
            tree.addTopLevelItem(item)

    def run(self):
        """Executa o plugin."""
        # Criar e mostrar a janela principal
        self.dialog = IndeServicosBRDialog(self.iface.mainWindow())
        
        # Conectar sinais
        self.dialog.refresh_button.clicked.connect(self.refresh_services)
        self.dialog.add_button.clicked.connect(self.add_selected_layer)
        self.dialog.addLayerRequested.connect(self.add_layer_from_item)
        self.dialog.about_button.clicked.connect(self.show_about)
        self.dialog.search_input.textChanged.connect(self.filter_services)
        self.dialog.layers_tree.itemSelectionChanged.connect(self.dialog.on_layer_selected)
        self.dialog.serviceSelected.connect(self.on_service_selected)
        
        # Carregar serviços iniciais
        self.refresh_services()
        
        # Mostrar a janela
        self.dialog.show()

    def refresh_services(self):
        """Atualiza a lista de serviços."""
        self.dialog.progress_bar.setVisible(True)
        self.dialog.progress_bar.setRange(0, 0)  # Modo indeterminado
        
        if self.fetch_services():
            # Atualizar as árvores de cada aba
            self.populate_service_tree(self.dialog.wms_tab.findChild(QTreeWidget), 'wms')
            self.populate_service_tree(self.dialog.wfs_tab.findChild(QTreeWidget), 'wfs')
            self.populate_service_tree(self.dialog.wcs_tab.findChild(QTreeWidget), 'wcs')
            
        self.dialog.progress_bar.setVisible(False)

    def filter_services(self, text):
        """Filtra os serviços na árvore baseado no texto de pesquisa."""
        for tab in [self.dialog.wms_tab, self.dialog.wfs_tab, self.dialog.wcs_tab]:
            tree = tab.findChild(QTreeWidget)
            for i in range(tree.topLevelItemCount()):
                item = tree.topLevelItem(i)
                item.setHidden(text.lower() not in item.text(0).lower())

    def on_service_selected(self, service_item):
        """Processa a seleção de um serviço."""
        try:
            # Mostrar indicador de carregamento
            self.dialog.show_loading("Obtendo informações do serviço...")
            
            QgsMessageLog.logMessage(f"Processando serviço: {service_item.descricao}", "IndeServicosBR", Qgis.Info)
            
            service_type = self.dialog.tab_widget.currentIndex()
            QgsMessageLog.logMessage(f"Tipo de serviço (índice): {service_type}", "IndeServicosBR", Qgis.Info)
            
            # Obter capabilities baseado no tipo de serviço
            if service_type == 0:  # WMS
                capabilities_url = service_item.wms_capabilities_url
                QgsMessageLog.logMessage(f"URL WMS Capabilities: {capabilities_url}", "IndeServicosBR", Qgis.Info)
                self.dialog.status_label.setText("Obtendo camadas WMS...")
                layers = self.get_capabilities(capabilities_url, 'wms')
                if layers:
                    QgsMessageLog.logMessage(f"Camadas encontradas: {len(layers)}", "IndeServicosBR", Qgis.Info)
                    self.dialog.status_label.setText(f"Atualizando lista de camadas ({len(layers)} encontradas)...")
                    self.dialog.update_layers_tree(layers)
                else:
                    QgsMessageLog.logMessage("Nenhuma camada encontrada", "IndeServicosBR", Qgis.Warning)
                    QMessageBox.warning(None, "Aviso", "Nenhuma camada encontrada neste serviço.")
            elif service_type == 1:  # WFS
                capabilities_url = service_item.wfs_capabilities_url
                QgsMessageLog.logMessage(f"URL WFS Capabilities: {capabilities_url}", "IndeServicosBR", Qgis.Info)
                self.dialog.status_label.setText("Obtendo features WFS...")
                features = self.get_capabilities(capabilities_url, 'wfs')
                if features:
                    QgsMessageLog.logMessage(f"Features encontradas: {len(features)}", "IndeServicosBR", Qgis.Info)
                    self.dialog.status_label.setText(f"Atualizando lista de features ({len(features)} encontradas)...")
                    self.dialog.update_layers_tree(features)
                else:
                    QgsMessageLog.logMessage("Nenhuma feature encontrada", "IndeServicosBR", Qgis.Warning)
                    QMessageBox.warning(None, "Aviso", "Nenhuma feature encontrada neste serviço.")
            else:  # WCS
                capabilities_url = service_item.wcs_capabilities_url
                QgsMessageLog.logMessage(f"URL WCS Capabilities: {capabilities_url}", "IndeServicosBR", Qgis.Info)
                self.dialog.status_label.setText("Obtendo coverages WCS...")
                coverages = self.get_capabilities(capabilities_url, 'wcs')
                if coverages:
                    QgsMessageLog.logMessage(f"Coverages encontradas: {len(coverages)}", "IndeServicosBR", Qgis.Info)
                    self.dialog.status_label.setText(f"Atualizando lista de coverages ({len(coverages)} encontradas)...")
                    self.dialog.update_layers_tree(coverages)
                else:
                    QgsMessageLog.logMessage("Nenhuma coverage encontrada", "IndeServicosBR", Qgis.Warning)
                    QMessageBox.warning(None, "Aviso", "Nenhuma coverage encontrada neste serviço.")
                    
        except Exception as e:
            QgsMessageLog.logMessage(f"Erro ao processar serviço: {str(e)}", "IndeServicosBR", Qgis.Critical)
            QMessageBox.warning(None, "Erro", f"Erro ao carregar camadas: {str(e)}")
        finally:
            # Esconder indicador de carregamento
            self.dialog.hide_loading()

    def add_selected_layer(self):
        """Adiciona a camada selecionada ao projeto."""
        selected_items = self.dialog.layers_tree.selectedItems()
        if not selected_items:
            QMessageBox.warning(None, "Aviso", "Selecione uma camada primeiro")
            return
        self._add_layer_from_item(selected_items[0])

    def add_layer_from_item(self, tree_item):
        """Adiciona a camada ao projeto a partir do item da árvore (usado no duplo clique)."""
        if not tree_item:
            return
        self._add_layer_from_item(tree_item)

    def _add_layer_from_item(self, tree_item):
        """Lógica interna para adicionar camada a partir de um item da árvore."""
        layer_item = tree_item.data(0, Qt.UserRole)
        if not layer_item:
            return

        current_tab = self.dialog.tab_widget.currentWidget()
        service_tree = current_tab.findChild(QTreeWidget)
        service_items = service_tree.selectedItems()

        if not service_items:
            QMessageBox.warning(None, "Aviso", "Selecione um serviço primeiro")
            return

        service = service_items[0].data(0, Qt.UserRole)
        service_type = self.dialog.tab_widget.currentIndex()

        # Exibir janela de aguarde enquanto a camada é carregada
        progress = QProgressDialog(
            "Carregando camada. Aguarde...",
            None,
            0,
            0,
            self.dialog
        )
        progress.setWindowTitle("INDE Serviços Brasil")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setRange(0, 0)  # Modo indeterminado (barra animada)
        progress.setValue(0)
        progress.show()
        QApplication.processEvents()

        try:
            if service_type == 0:  # WMS
                self.load_wms_layer(service.url, layer_item['name'], layer_item['title'])
            elif service_type == 1:  # WFS
                self.load_wfs_layer(service.url, layer_item['name'], layer_item['title'])
            else:  # WCS
                self.load_wcs_layer(service.url, layer_item['name'], layer_item['title'])
        finally:
            progress.close()

    def show_about(self):
        """Mostra diálogo Sobre."""
        QMessageBox.about(
            self.dialog,
            "Sobre INDE Serviços Brasil",
            """<h3>INDE Serviços Brasil</h3>
            <p>Plugin para acesso aos geoserviços da INDE Brasil.</p>
            <p>Desenvolvido para facilitar o acesso aos serviços WMS, WFS e WCS disponíveis no DBDG da INDE.</p>
            <p>Versão 0.0.1</p>"""
        )
