from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QTreeWidget,
    QTreeWidgetItem, QPushButton, QLabel, QLineEdit, QProgressBar,
    QMessageBox, QWidget, QHeaderView, QSplitter, QApplication,
    QGroupBox
)
from qgis.PyQt.QtCore import Qt, QSize, pyqtSignal
from qgis.PyQt.QtGui import QIcon, QFont, QCursor
from qgis.core import QgsMessageLog, Qgis


class IndeServicosBRDialog(QDialog):
    """Dialog principal do plugin."""
    
    serviceSelected = pyqtSignal(object)
    addLayerRequested = pyqtSignal(object)
    
    def __init__(self, parent=None):
        """Construtor."""
        super(IndeServicosBRDialog, self).__init__(parent)
        self.setWindowTitle("Serviços INDE Brasil")
        self.setMinimumSize(1000, 700)
        
        # Layout principal
        layout = QVBoxLayout()
        layout.setSpacing(5)  # Reduz o espaçamento entre elementos
        layout.setContentsMargins(5, 5, 5, 5)  # Reduz as margens
        
        # Container para barra de progresso e status
        progress_container = QWidget()
        progress_layout = QVBoxLayout(progress_container)
        progress_layout.setContentsMargins(0, 0, 0, 0)  # Remove margens
        progress_layout.setSpacing(2)  # Espaçamento mínimo entre barra e label
        progress_container.setMaximumHeight(40)  # Limita altura máxima
        
        # Barra de progresso
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMaximumHeight(10)  # Altura reduzida
        progress_layout.addWidget(self.progress_bar)
        
        # Label de status
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-style: italic; font-size: 11px;")
        self.status_label.setVisible(False)
        progress_layout.addWidget(self.status_label)
        
        layout.addWidget(progress_container, 0)  # Stretch factor 0 para não expandir
        
        # Barra de pesquisa
        search_layout = QHBoxLayout()
        search_layout.setContentsMargins(0, 0, 0, 0)  # Remove margens
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Pesquisar instituição...")
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)
        
        # Splitter principal
        main_splitter = QSplitter(Qt.Horizontal)
        
        # Widget de abas
        self.tab_widget = QTabWidget()
        self.tab_widget.setDocumentMode(True)  # Visual mais compacto
        
        # Criar abas para cada tipo de serviço
        self.wms_tab = self.create_service_tab("WMS")
        self.wfs_tab = self.create_service_tab("WFS")
        self.wcs_tab = self.create_service_tab("WCS")
        
        # Adicionar abas ao widget
        self.tab_widget.addTab(self.wms_tab, "Serviços WMS")
        self.tab_widget.addTab(self.wfs_tab, "Serviços WFS")
        self.tab_widget.addTab(self.wcs_tab, "Serviços WCS")
        
        main_splitter.addWidget(self.tab_widget)
        
        # Painel direito para exibir camadas
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)  # Remove margens
        right_layout.setSpacing(5)  # Reduz espaçamento
        
        # Label para o painel de camadas
        layers_label = QLabel("Camadas Disponíveis")
        layers_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 0px;")
        right_layout.addWidget(layers_label)
        
        # Árvore de camadas
        self.layers_tree = QTreeWidget()
        self.layers_tree.setHeaderLabels(["Título", "Nome"])
        self.layers_tree.setColumnCount(2)
        self.layers_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.layers_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.layers_tree.setSortingEnabled(True)  # Habilita ordenação por clique no cabeçalho
        self.layers_tree.setVisible(False)
        right_layout.addWidget(self.layers_tree)
        
        right_panel.setLayout(right_layout)
        main_splitter.addWidget(right_panel)
        
        # Configurar proporção do splitter
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)
        
        # Adiciona o splitter com stretch factor 1 para ocupar o espaço disponível
        layout.addWidget(main_splitter, 1)  # Stretch factor 1
        
        # Botões
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)  # Remove margens
        self.add_button = QPushButton("Adicionar Camada")
        self.add_button.setEnabled(False)
        self.refresh_button = QPushButton("Atualizar Lista")
        self.about_button = QPushButton("Sobre")
        
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.refresh_button)
        button_layout.addWidget(self.about_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Aplicar estilo
        self.apply_style()
        
        # Conectar sinais
        self.layers_tree.itemSelectionChanged.connect(self.on_layer_selected)
        self.layers_tree.itemDoubleClicked.connect(self.on_layer_double_clicked)
        
        # Conectar sinais dos QTreeWidgets dentro das abas
        self.wms_tree = self.wms_tab.findChild(QTreeWidget)
        self.wfs_tree = self.wfs_tab.findChild(QTreeWidget)
        self.wcs_tree = self.wcs_tab.findChild(QTreeWidget)
        
        self.wms_tree.itemDoubleClicked.connect(self.on_service_double_clicked)
        self.wfs_tree.itemDoubleClicked.connect(self.on_service_double_clicked)
        self.wcs_tree.itemDoubleClicked.connect(self.on_service_double_clicked)
        
        self.wms_tree.itemSelectionChanged.connect(self.on_service_selection_changed)
        self.wfs_tree.itemSelectionChanged.connect(self.on_service_selection_changed)
        self.wcs_tree.itemSelectionChanged.connect(self.on_service_selection_changed)
        
        # Conectar sinal de mudança de aba
        self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
    def create_service_tab(self, service_type):
        """Cria uma aba para um tipo específico de serviço."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margens
        layout.setSpacing(0)  # Remove espaçamento
        
        # Árvore de serviços
        tree = QTreeWidget()
        tree.setHeaderLabels(["Instituição", "Nível", "URL"])
        tree.setColumnCount(3)
        tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        tree.header().setSectionResizeMode(2, QHeaderView.Stretch)
        tree.setSortingEnabled(True)  # Habilita ordenação por clique no cabeçalho
        
        layout.addWidget(tree)
        tab.setLayout(layout)
        
        # Armazenar a árvore como propriedade do widget da aba
        tab.tree = tree
        
        return tab
        
    def get_current_tree(self):
        """Retorna a árvore da aba atual."""
        current_index = self.tab_widget.currentIndex()
        if current_index == 0:
            return self.wms_tree
        elif current_index == 1:
            return self.wfs_tree
        elif current_index == 2:
            return self.wcs_tree
        return None
        
    def on_service_selected(self, tree):
        """Manipula a seleção de um serviço na árvore."""
        selected_items = tree.selectedItems()
        
        # Limpar árvore de camadas
        self.layers_tree.clear()
        self.layers_tree.setVisible(False)
        self.add_button.setEnabled(False)
        
        if selected_items:
            service = selected_items[0].data(0, Qt.UserRole)
            if service:
                QgsMessageLog.logMessage(f"Serviço selecionado: {service.descricao}", "IndeServicosBR", Qgis.Info)
                self.serviceSelected.emit(service)
            
    def update_layers_tree(self, items):
        """Atualiza a árvore de camadas com os itens fornecidos."""
        self.layers_tree.clear()
        
        for item in items:
            tree_item = QTreeWidgetItem([item['title'], item['name']])
            tree_item.setData(0, Qt.UserRole, item)
            self.layers_tree.addTopLevelItem(tree_item)
            
        self.layers_tree.setVisible(True)
        
    def on_layer_selected(self):
        """Manipula a seleção de uma camada."""
        selected_items = self.layers_tree.selectedItems()
        self.add_button.setEnabled(bool(selected_items))

    def on_layer_double_clicked(self, item, column):
        """Manipula o duplo clique em uma camada - adiciona ao projeto."""
        if item:
            self.addLayerRequested.emit(item)
        
    def on_service_double_clicked(self, item, column):
        """Trata o duplo clique em um serviço."""
        service = item.data(0, Qt.UserRole)
        if service:
            self.serviceSelected.emit(service)
            
    def on_service_selection_changed(self):
        """Trata a mudança de seleção em um serviço."""
        sender = self.sender()
        self.on_service_selected(sender)
        
    def on_tab_changed(self, index):
        """Trata a mudança de aba."""
        try:
            # Limpar árvore de camadas
            self.layers_tree.clear()
            self.layers_tree.setVisible(False)
            self.add_button.setEnabled(False)
            
            # Limpar seleção na árvore da aba atual
            current_tree = self.get_current_tree()
            if current_tree:
                current_tree.clearSelection()
            
            QgsMessageLog.logMessage(f"Mudou para a aba {self.tab_widget.tabText(index)}", "IndeServicosBR", Qgis.Info)
        except Exception as e:
            QgsMessageLog.logMessage(f"Erro ao trocar de aba: {str(e)}", "IndeServicosBR", Qgis.Critical)
        
    def apply_style(self):
        """Aplica estilo ao dialog."""
        self.setStyleSheet("""
            QDialog {
                background-color: #f5f5f5;
            }
            QTreeWidget {
                border: 1px solid #ddd;
                background-color: white;
                alternate-background-color: #f9f9f9;
            }
            QTreeWidget::item {
                padding: 3px;
                border-bottom: 1px solid #eee;
            }
            QTreeWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QTreeWidget::item:hover {
                background-color: #e6f3ff;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 6px;
                border: 1px solid #ddd;
                font-weight: bold;
            }
            QHeaderView::section:hover {
                background-color: #e0e0e0;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:disabled {
                background-color: #ccc;
                color: #666;
            }
            QLineEdit {
                border: 1px solid #ddd;
                padding: 6px;
                border-radius: 4px;
            }
            QTabWidget::pane {
                border: 1px solid #ddd;
                background-color: white;
            }
            QTabBar::tab {
                background-color: #f0f0f0;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid #0078d4;
            }
        """) 

    def show_loading(self, message="Carregando..."):
        """Mostra indicadores de carregamento."""
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Modo indeterminado
        self.status_label.setText(message)
        self.status_label.setVisible(True)
        QApplication.processEvents()  # Força atualização da UI
        
    def hide_loading(self):
        """Esconde indicadores de carregamento."""
        QApplication.restoreOverrideCursor()
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        QApplication.processEvents()  # Força atualização da UI 