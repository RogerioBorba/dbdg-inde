# SOLID — Deep Dive e Casos Avançados

## Conteúdo

1. [Armadilhas comuns por princípio](#armadilhas)
2. [SOLID em conjunto — exemplo end-to-end](#end-to-end)
3. [Padrões de projeto relacionados](#padroes)
4. [SOLID vs pragmatismo: quando não aplicar](#quando-nao)
5. [Métricas de qualidade](#metricas)

---

## 1. Armadilhas Comuns {#armadilhas}

### SRP — Armadilhas
- **Over-engineering**: Dividir demais pode criar classes triviais demais. Uma entidade com 3 métodos coesos não precisa ser quebrada.
- **Granularidade errada**: SRP não significa "uma função por classe". É sobre *razão de mudança*, não tamanho.
- **God Objects disfarçados**: Às vezes a divisão é superficial mas uma classe orquestra tudo — ainda é violação.

### OCP — Armadilhas
- **Não prever pontos de extensão cedo**: Difícil aplicar OCP retroativamente. Identifique os eixos de variação no design inicial.
- **Over-abstraction prematura**: Não crie abstrações para variações que talvez nunca aconteçam (YAGNI).
- **Feature Flags ≠ OCP**: Condicional por feature flag ainda viola se modifica a classe toda vez.

### LSP — Armadilhas
- **Herança apenas para reuso**: Herdar de uma classe para aproveitar código, sem relação "é-um", viola LSP.
- **Pré/pós-condições mais restritivas**: Subclasse não pode exigir mais ou garantir menos que a classe pai.
- **Covariância errada**: Parâmetros de métodos em subclasses não podem ser mais específicos que no pai.

### ISP — Armadilhas
- **Interface única "por comodidade"**: Juntar métodos numa interface só porque são relacionados ao mesmo domínio.
- **Fat interfaces legadas**: Em sistemas legados, pode ser necessário criar interfaces adaptadoras (Adapter Pattern).

### DIP — Armadilhas
- **Injeção de dependência ≠ DIP**: DIP é sobre direção das dependências. DI é um padrão que *ajuda* a seguir DIP, mas não são sinônimos.
- **Abstração sem sentido**: Criar interface `IEmailService` com uma única implementação só por criar é over-engineering se não há plano de trocar.
- **DIP no bootstrap**: A composição root (onde tudo é instanciado) inevitavelmente conhece concretizações — isso é aceitável.

---

## 2. SOLID em Conjunto — Exemplo End-to-End {#end-to-end}

Cenário: Sistema de processamento de pagamentos.

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol

# --- Domínio ---

@dataclass
class Pagamento:
    valor: float
    moeda: str
    cliente_id: str

# --- DIP + ISP: Interfaces específicas ---

class ProcessadorPagamento(Protocol):
    """ISP: interface focada apenas em processar"""
    def processar(self, pagamento: Pagamento) -> bool: ...

class ValidadorPagamento(Protocol):
    """ISP: separado do processamento"""
    def validar(self, pagamento: Pagamento) -> bool: ...

class LogPagamento(Protocol):
    """ISP: separado da lógica de negócio"""
    def registrar(self, pagamento: Pagamento, sucesso: bool) -> None: ...

# --- OCP: Implementações extensíveis ---

class PagamentoCartao:
    """SRP: só sabe processar cartão"""
    def processar(self, pagamento: Pagamento) -> bool:
        print(f"Processando {pagamento.valor} via cartão")
        return True

class PagamentoPix:
    """OCP: nova forma sem alterar código existente"""
    def processar(self, pagamento: Pagamento) -> bool:
        print(f"Processando {pagamento.valor} via PIX")
        return True

class ValidadorBasico:
    """SRP: só valida"""
    def validar(self, pagamento: Pagamento) -> bool:
        return pagamento.valor > 0 and pagamento.moeda in ["BRL", "USD"]

class LogConsole:
    """SRP: só loga"""
    def registrar(self, pagamento: Pagamento, sucesso: bool):
        status = "✓" if sucesso else "✗"
        print(f"[LOG] {status} Pagamento {pagamento.cliente_id}: R${pagamento.valor}")

# --- SRP + DIP: Serviço de alto nível depende de abstrações ---

class ServicoPagamento:
    """
    SRP: orquestra o fluxo, não implementa detalhes
    DIP: recebe abstrações, não concretos
    """
    def __init__(
        self,
        processador: ProcessadorPagamento,
        validador: ValidadorPagamento,
        log: LogPagamento
    ):
        self._processador = processador
        self._validador = validador
        self._log = log

    def executar(self, pagamento: Pagamento) -> bool:
        if not self._validador.validar(pagamento):
            self._log.registrar(pagamento, False)
            return False
        sucesso = self._processador.processar(pagamento)
        self._log.registrar(pagamento, sucesso)
        return sucesso

# --- Composição (bootstrap) ---

servico_cartao = ServicoPagamento(
    processador=PagamentoCartao(),
    validador=ValidadorBasico(),
    log=LogConsole()
)

servico_pix = ServicoPagamento(  # OCP: troca o processador sem tocar no serviço!
    processador=PagamentoPix(),
    validador=ValidadorBasico(),
    log=LogConsole()
)
```

---

## 3. Padrões de Projeto Relacionados {#padroes}

| Princípio | Padrões que facilitam |
|-----------|----------------------|
| SRP | Facade, Command, Repository |
| OCP | Strategy, Template Method, Decorator, Plugin |
| LSP | Template Method (garante contrato) |
| ISP | Role Interface, Adapter |
| DIP | Factory, Abstract Factory, Dependency Injection, Service Locator |

---

## 4. Quando Não Aplicar SOLID {#quando-nao}

SOLID não é lei absoluta. Considere o contexto:

- **Scripts pequenos e descartáveis**: Overhead de abstrações não vale.
- **Prototipação rápida**: Aplique depois, quando a direção estiver clara.
- **Performance crítica**: Às vezes abstrações custam caro em hot paths.
- **Times iniciantes**: Muita abstração pode dificultar a leitura para quem ainda está aprendendo.
- **CRUD simples**: Camadas de abstração demais para operações triviais (YAGNI).

> **Regra prática**: Aplique SOLID quando a complexidade do domínio justifica. Se você vai mudar, testar, ou estender — SOLID ajuda. Se é código morto ou one-off — não.

---

## 5. Métricas de Qualidade {#metricas}

Para avaliar aderência a SOLID em uma codebase:

- **Acoplamento aferente/eferente**: ferramentas como `radon` (Python), `JDepend` (Java)
- **Cobertura de testes**: código SOLID tende a ter cobertura mais fácil de atingir
- **Número de dependências diretas por classe**: alto = possível violação de DIP
- **Tamanho de interfaces**: grande = possível violação de ISP
- **Frequência de modificação por motivo**: alta diversidade = violação de SRP
- **Code smell detectors**: SonarQube, ESLint com regras de design, Pylint
