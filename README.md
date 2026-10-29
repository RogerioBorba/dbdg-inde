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

### Filtro por atributo WFS

Na aba WFS, selecione uma camada e clique em **Filtrar por atributo**. O plugin
consulta `DescribeFeatureType` para listar campos de texto e numéricos. Escolha
um campo, um operador e um valor, por exemplo **nome contém Brasília** ou
**população maior que 100000**. Use números sem separador de milhares; valores
decimais aceitam ponto ou vírgula.

A condição é enviada ao servidor e combinada com BBOX ou filtro espacial
avançado usando **E**, tanto na contagem quanto no download. O limite de
quantidade continua funcionando. A condição aplicada fica vinculada à camada durante a
sessão. Ao reabrir o filtro por atributo, o formulário começa limpo para uma
nova condição; cancelar mantém o filtro aplicado anteriormente. Use
**Limpar atributo** para removê-lo. Quando não houver feições para os filtros e
limites informados, o plugin avisa e não adiciona uma camada vazia ao projeto.
Para selecionar vários textos, escolha **IN (na lista)** e informe, por exemplo,
'RJ', 'ES', 'MG'. A comparação é exata; basta um dos valores corresponder ao atributo.

Esta versão oferece uma condição e depende dos tipos simples informados pelo
serviço; esquemas com tipos personalizados ou importados podem não listar campos.


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


## Gerar ZIP para instalar no QGIS

Execute `python tools/package_plugin.py` na pasta do projeto. O arquivo gerado é
`dist/dbdg_inde.zip`, pronto para **Instalar a partir de ZIP** no QGIS.
O pacote inclui os módulos do plugin, bibliotecas locais e certificados,
sem `.git`, testes ou caches. Compactar a pasta inteira pode incluir caminhos
muito longos do histórico Git e interromper a extração no Windows.
