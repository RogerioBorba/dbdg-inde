class IndeServiceItem:
    """Classe para armazenar informações de um serviço INDE."""
    
    def __init__(self, data):
        self.descricao = data.get('descricao', 'Serviço sem nome')
        self.url = data.get('url', '')
        self.nivel_no = data.get('nivel_no', '')
        
        self.wms_available = data.get('wmsAvailable', False)
        self.wfs_available = data.get('wfsAvailable', False)
        self.wcs_available = data.get('wcsAvailable', False)
        
        self.wms_capabilities_url = data.get('wmsGetCapabilities', '')
        self.wfs_capabilities_url = data.get('wfsGetCapabilities', '')
        self.wcs_capabilities_url = data.get('wcsGetCapabilities', '')
        
        # Para armazenar camadas depois de obter capabilities
        self.wms_layers = []
        self.wfs_features = []
        self.wcs_coverages = [] 