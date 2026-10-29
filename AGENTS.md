# Orientações para agentes — dbdg_inde

## Projeto e local de trabalho

Este é um plugin Python para QGIS que consulta o catálogo DBDG/INDE e carrega
serviços WMS, WFS e WCS. A interface e a documentação voltadas ao usuário são
escritas em português brasileiro.

- A pasta usada pelo mantenedor para desenvolver e gerar o pacote é
  `C:\desenv\qgis-des\plugins\dbdg_inde`.
- Confirme a pasta e execute `git status --short` antes de editar. Um worktree
  isolado não atualiza automaticamente essa pasta nem o plugin instalado no QGIS.
- Preserve alterações locais preexistentes. Integre mudanças por patches e
  verifique conflitos; não substitua arquivos inteiros sem comparar seu conteúdo.
- Não altere a cópia no perfil QGIS, nem encerre o QGIS do usuário, sem solicitação.
- Não faça commit, push ou PR sem pedido explícito. Informe onde as alterações
  foram aplicadas e o caminho do ZIP quando houver empacotamento.

## Mapa do código

- `__init__.py`: entrada `classFactory` exigida pelo QGIS.
- `dbdg_inde_plugin.py`: criação e remoção da barra de ferramentas e abertura da interface.
- `service_loader_dialog.py`: seleção de serviços/camadas, opções e coordenação do download.
- `service_handlers/`: implementações WMS, WFS e WCS; `base.py` contém leitura segura de XML.
- `wfs_filter_dialogs.py`: diálogos de BBOX, filtro espacial e condição por atributo.
- `wfs_attribute_filter.py`: validação dos valores e geração/composição do Filter Encoding.
- `catalog_client.py`, `network_utils.py`, `metadata_viewer.py`: catálogo, rede e metadados.
- `defusedxml/` e `certs/`: dependências e certificados distribuídos com o plugin.
- `tests/`: testes unitários e testes com runtime QGIS.
- `tools/package_plugin.py`: criação do pacote instalável.

## Convenções e contratos

- Siga o estilo Python existente, com indentação de quatro espaços e UTF-8.
- Use importações relativas dentro do plugin e os módulos `qgis.PyQt` para Qt.
  Verifique APIs/enums no runtime disponível; não deduza compatibilidade com
  outras versões apenas pelo intervalo declarado em `metadata.txt`.
- Reutilize as funções de rede e de leitura segura de XML existentes.
- Valores de filtros devem ser literais XML escapados, nunca expressões SQL
  concatenadas. O operador textual IN usa igualdades agrupadas por OU.
- Preserve o agrupamento lógico: condição por atributo E filtro espacial/BBOX.
  Contagem e download devem enviar o mesmo filtro, inclusive na paginação.
- Preserve os limites de quantidade, a seleção da camada e os fluxos WMS/WCS.
- Alterações de comportamento devem incluir testes relevantes. Não faça
  refatorações ou atualizações de versão sem relação com o pedido.

## Verificação

Execute os comandos abaixo na raiz do plugin, com Python e ambiente do QGIS
configurados (inclusive Qt, PYTHONPATH e dados PROJ). O runtime usado nas
verificações anteriores foi QGIS 3.44.11 em `C:\desenv\QGIS 3.44.11`.

```powershell
python -m unittest discover -s tests -t ..
git diff --check
```

Para mudanças em filtros ou empacotamento, a seleção focada é:

```powershell
Push-Location ..
python -m unittest dbdg_inde.tests.test_wfs_attribute_filter dbdg_inde.tests.test_wfs_handler dbdg_inde.tests.test_qgis_service_loader_runtime dbdg_inde.tests.test_plugin_package
Pop-Location
```

- Testes de interface exigem o runtime real do QGIS; para execução sem janela,
  use `QT_QPA_PLATFORM=offscreen`. Testes com stubs não comprovam o carregamento real.
- Evite dependência de serviços públicos nos testes automatizados. Diferencie
  testes com respostas simuladas de consultas reais ao servidor.
- Verifique o comportamento de interface alterado e, quando pertinente,
  `classFactory`, inicialização e descarregamento do plugin extraído do ZIP.
- Relate falhas, testes ignorados e limitações; não declare aprovação da suíte
  completa quando apenas os testes focados passaram.

## Segurança obrigatória antes da liberação

Após concluir os testes, execute o Bandit na raiz do projeto. Esta verificação
é obrigatória antes de liberar qualquer versão do plugin para a comunidade.

    python -m bandit -r . -x .git,tests,dist,build,__pycache__

- A análise deve abranger os módulos distribuídos no plugin, incluindo as
  dependências Python locais. Não exclua código de execução para obter aprovação.
- Registre o comando, a versão do Bandit, o resultado e os achados relevantes.
- Analise todos os achados e corrija os problemas confirmados antes da liberação;
  eventuais falsos positivos devem ter justificativa documentada e revisável.
- Não silencie achados com exclusões ou comentários de supressão sem justificativa.
- Se o Bandit não estiver disponível ou a análise falhar, informe o impedimento:
  a verificação de segurança continua pendente e a versão não está pronta para
  liberação à comunidade. Testes funcionais não substituem esta etapa.
- Mudanças posteriores no código distribuído exigem nova execução do Bandit
  antes da liberação.

## Empacotamento para QGIS

```powershell
python tools/package_plugin.py
```

O resultado é `dist/dbdg_inde.zip`, com uma única pasta superior `dbdg_inde/`,
contendo `metadata.txt`, `__init__.py`, os módulos do plugin e suas dependências.
Não compacte a pasta inteira manualmente: `.git` contém checkpoints com caminhos
longos que já causaram WinError 206 e instalação parcial no Windows. Exclua
também caches, bytecode, testes e ferramentas de desenvolvimento do pacote.

Ao adicionar módulos ou recursos necessários em execução, confira se o
empacotador os inclui e atualize o teste de pacote quando necessário. Preserve
os nomes e os pontos de entrada esperados pelo QGIS. Para entregar uma mudança
que o usuário testará por ZIP, regenere o pacote e informe seu caminho completo.
