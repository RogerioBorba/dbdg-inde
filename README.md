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
- Permite paginar features do WFS e requisitar nos formatos, GML, Shape-zip e Geojson, se disponíveis
- Permite visualizar metadados associados ao geosserviços
- Cache de capacidades para melhor performance


## Instalação

1. Baixe o arquivo ZIP do plugin
2. Abra o QGIS
3. Vá para Plugins > Gerenciar e Instalar Plugins
4. Clique em "Instalar do ZIP"
5. Selecione o arquivo ZIP baixado
6. Clique em "Instalar Plugin"

## Uso

1. Clique no ícone "Serviços DBDG/INDE" na barra de ferramentas
2. Selecione a aba do tipo de serviço desejado (WMS, WFS ou WCS)
3. Selecione ou filtre uma instituição na lista
4. Escolha ou filtre a camada 
5. Clique no botão Adicionar camada ao projeto


## Requisitos

- QGIS 3.0 ou superior
- Conexão com a internet para acessar os serviços

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
