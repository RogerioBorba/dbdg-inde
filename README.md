# INDE Serviços Brasil

Plugin para QGIS que permite acessar, de maneira centralizada, todos os serviços geoespaciais do DBDG (Diretório Brasileiro de Dados Geoespaciais) da INDE Brasil.

## Descrição

Este plugin foi desenvolvido para facilitar o acesso aos serviços WMS, WFS e WCS disponíveis no DBDG da INDE. Ele permite que usuários comuns acessem facilmente os serviços geoespaciais das instituições participantes da INDE, com uma interface amigável e intuitiva.

### Características

- Interface amigável com abas separadas para WMS, WFS e WCS
- Organização dos serviços por instituição
- Pesquisa rápida de instituições
- Integração direta com o projeto QGIS atual
- Suporte para consumo de serviços WMS, WFS e WCS
- Permite paginar features do WFS e requisitar nos formatos, GML, Shape-zip e Geojson, se disponíveis. Pode aplicar filtros espaciais e usar BBOX.
- Permite visualizar metadados associados ao geosserviços
- Cache de capacidades para melhor performance


## Instalação

### Repositório oficial do QGIS

1. No QGIS, acesse **Complementos > Gerenciar e Instalar Complementos**.
2. Na aba **Todos**, pesquise por **IndeServicosBR**.
3. Selecione o plugin e clique em **Instalar Complemento**.

Como o plugin é uma versão estável, não é necessário habilitar a opção de exibição de complementos experimentais.

### Instalação manual por ZIP

1. Baixe o arquivo ZIP de uma versão publicada no GitHub.
2. No QGIS, acesse **Complementos > Gerenciar e Instalar Complementos**.
3. Abra a aba **Instalar a partir do ZIP**.
4. Selecione o arquivo baixado e clique em **Instalar Complemento**.

## Uso

1. Clique no ícone "Serviços DBDG/INDE" na barra de ferramentas
2. Selecione a aba do tipo de serviço desejado (WMS, WFS ou WCS)
3. Selecione ou filtre uma instituição na lista
4. Escolha ou filtre a camada 
5. Clique no botão Adicionar camada ao projeto


## Requisitos

- QGIS 3.0 ou superior
- Conexão com a internet para acessar os serviços

### Dependência do catálogo da INDE

O catálogo de geosserviços é obtido em tempo de execução pela API pública da INDE:

https://inde.gov.br/api/catalogo/get

O plugin não exige a instalação de bibliotecas adicionais para acessar essa API. Entretanto, a listagem de instituições e serviços depende de conexão com a internet e da disponibilidade do endpoint. Caso a API esteja temporariamente indisponível, o catálogo poderá não ser carregado.

## Suporte

Para reportar problemas ou sugerir melhorias, por favor abra uma issue no repositório do projeto.

## Licença

Este projeto está licenciado sob a licença MIT - veja o arquivo [LICENSE](LICENSE) para detalhes.

## Autores

- Rogério Borba (dbdg@inde.gov.br)

## Agradecimentos

- INDE Brasil por disponibilizar os serviços
- Comunidade QGIS por fornecer a plataforma
- Todos os contribuidores do projeto

## Disclaimer

Este repositório, dbdg-inde, é disponibilizado sem garantias de qualquer natureza, expressas ou implícitas. O conteúdo, código-fonte, documentação e quaisquer outros materiais aqui presentes são fornecidos "como estão", sem responsabilidade por parte do autor ou colaboradores por eventuais danos, perdas ou problemas decorrentes do seu uso.
