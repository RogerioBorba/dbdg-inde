# SOLID — Exemplos por Linguagem

## Conteúdo
- [TypeScript](#typescript)
- [Java](#java)
- [C#](#csharp)

---

## TypeScript {#typescript}

### SRP + DIP (com interfaces)

```typescript
// Interfaces (abstrações)
interface Repositorio<T> {
  salvar(entidade: T): Promise<void>;
  buscarPorId(id: string): Promise<T | null>;
}

interface Notificador {
  notificar(destinatario: string, mensagem: string): Promise<void>;
}

// Domínio — SRP: só lógica de negócio
class Usuario {
  constructor(
    public readonly id: string,
    public readonly email: string,
    public readonly nome: string
  ) {}
}

// Infraestrutura — SRP: só persistência
class UsuarioRepositorio implements Repositorio<Usuario> {
  async salvar(usuario: Usuario): Promise<void> {
    // lógica de banco
  }
  async buscarPorId(id: string): Promise<Usuario | null> {
    // lógica de banco
    return null;
  }
}

// Infraestrutura — SRP: só email
class EmailNotificador implements Notificador {
  async notificar(email: string, mensagem: string): Promise<void> {
    console.log(`Email para ${email}: ${mensagem}`);
  }
}

// Serviço — DIP: depende das interfaces, não implementações
class ServicoUsuario {
  constructor(
    private readonly repo: Repositorio<Usuario>,
    private readonly notificador: Notificador
  ) {}

  async cadastrar(usuario: Usuario): Promise<void> {
    await this.repo.salvar(usuario);
    await this.notificador.notificar(usuario.email, "Bem-vindo!");
  }
}

// OCP — Strategy para validação
interface RegraValidacao<T> {
  validar(valor: T): boolean;
  mensagem: string;
}

class EmailValido implements RegraValidacao<string> {
  mensagem = "Email inválido";
  validar(email: string): boolean {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  }
}

class Validador<T> {
  constructor(private readonly regras: RegraValidacao<T>[]) {}

  validar(valor: T): string[] {
    return this.regras
      .filter(r => !r.validar(valor))
      .map(r => r.mensagem);
  }
}
```

### ISP com tipos utilitários

```typescript
// ❌ Interface gorda
interface RepositorioCompleto<T> {
  buscarPorId(id: string): Promise<T>;
  salvar(entidade: T): Promise<void>;
  deletar(id: string): Promise<void>;
  buscarTodos(): Promise<T[]>;
  contar(): Promise<number>;
}

// ✅ Segregado
interface Legivel<T> {
  buscarPorId(id: string): Promise<T | null>;
  buscarTodos(): Promise<T[]>;
}

interface Gravavel<T> {
  salvar(entidade: T): Promise<void>;
}

interface Deletavel {
  deletar(id: string): Promise<void>;
}

// Composição de interfaces conforme necessidade
interface RepositorioCompleto<T>
  extends Legivel<T>, Gravavel<T>, Deletavel {}

// Serviço somente leitura
class ServicoRelatorio {
  constructor(private readonly repo: Legivel<any>) {}
}
```

---

## Java {#java}

### DIP com Spring (Injeção de Dependência)

```java
// Abstração
public interface PagamentoGateway {
    boolean processar(BigDecimal valor, String token);
}

// Implementações concretas
@Component("stripe")
public class StripeGateway implements PagamentoGateway {
    @Override
    public boolean processar(BigDecimal valor, String token) {
        // integração Stripe
        return true;
    }
}

@Component("paypal")
public class PaypalGateway implements PagamentoGateway {
    @Override
    public boolean processar(BigDecimal valor, String token) {
        // integração PayPal
        return true;
    }
}

// Serviço depende da abstração — DIP
@Service
public class ServicoPedido {
    private final PagamentoGateway gateway;

    @Autowired
    public ServicoPedido(@Qualifier("stripe") PagamentoGateway gateway) {
        this.gateway = gateway;
    }

    public void fecharPedido(Pedido pedido) {
        gateway.processar(pedido.getValor(), pedido.getTokenPagamento());
    }
}
```

### OCP com Enum + Strategy

```java
// OCP: adicionar novo tipo não altera a classe calculadora
public interface TaxaCalculo {
    BigDecimal calcular(BigDecimal valor);
}

public class TaxaSimples implements TaxaCalculo {
    @Override
    public BigDecimal calcular(BigDecimal valor) {
        return valor.multiply(new BigDecimal("0.05"));
    }
}

public class TaxaComposta implements TaxaCalculo {
    @Override
    public BigDecimal calcular(BigDecimal valor) {
        return valor.multiply(new BigDecimal("0.12"));
    }
}

// CalculadoraImposto fechada para modificação
public class CalculadoraImposto {
    public BigDecimal calcular(BigDecimal valor, TaxaCalculo taxa) {
        return taxa.calcular(valor);
    }
}
```

### LSP — Garantindo contratos

```java
public abstract class FormaGeometrica {
    /**
     * Contrato: sempre retorna valor positivo
     */
    public abstract double area();

    /**
     * Contrato: sempre retorna valor positivo  
     */
    public abstract double perimetro();
}

public class Circulo extends FormaGeometrica {
    private final double raio;

    public Circulo(double raio) {
        if (raio <= 0) throw new IllegalArgumentException("Raio deve ser positivo");
        this.raio = raio;
    }

    @Override
    public double area() { return Math.PI * raio * raio; } // ✓ cumpre contrato

    @Override
    public double perimetro() { return 2 * Math.PI * raio; } // ✓ cumpre contrato
}
```

---

## C# {#csharp}

### SOLID Completo — Sistema de Notificações

```csharp
// ISP: interfaces segregadas
public interface INotificador
{
    Task NotificarAsync(string destinatario, string mensagem);
}

public interface INotificadorComTemplate
{
    Task NotificarAsync(string destinatario, string templateId, object dados);
}

// SRP: cada classe tem uma responsabilidade
public class EmailNotificador : INotificador
{
    public async Task NotificarAsync(string email, string mensagem)
    {
        // lógica de email
        await Task.CompletedTask;
    }
}

public class SmsNotificador : INotificador
{
    public async Task NotificarAsync(string telefone, string mensagem)
    {
        // lógica de SMS
        await Task.CompletedTask;
    }
}

// OCP: novos canais sem modificar código existente
public class PushNotificador : INotificador  // ← novo canal
{
    public async Task NotificarAsync(string deviceId, string mensagem)
    {
        await Task.CompletedTask;
    }
}

// DIP: serviço depende da abstração
public class ServicoNotificacao
{
    private readonly IEnumerable<INotificador> _notificadores;

    public ServicoNotificacao(IEnumerable<INotificador> notificadores)
    {
        _notificadores = notificadores;
    }

    public async Task NotificarTodosAsync(string destinatario, string mensagem)
    {
        var tarefas = _notificadores
            .Select(n => n.NotificarAsync(destinatario, mensagem));
        await Task.WhenAll(tarefas);
    }
}

// Registro no container (ASP.NET Core)
// builder.Services.AddScoped<INotificador, EmailNotificador>();
// builder.Services.AddScoped<INotificador, SmsNotificador>();
// builder.Services.AddScoped<INotificador, PushNotificador>();
// builder.Services.AddScoped<ServicoNotificacao>();
```

### LSP com Generics e Constraints

```csharp
// Contrato via interface genérica
public interface IRepositorio<T> where T : class
{
    Task<T?> BuscarPorIdAsync(Guid id);
    Task SalvarAsync(T entidade);
}

// LSP: qualquer IRepositorio<T> pode substituir outro do mesmo tipo
public class RepositorioSqlServer<T> : IRepositorio<T> where T : class
{
    public async Task<T?> BuscarPorIdAsync(Guid id) { /* EF Core */ return null; }
    public async Task SalvarAsync(T entidade) { /* EF Core */ }
}

public class RepositorioInMemory<T> : IRepositorio<T> where T : class
{
    private readonly Dictionary<Guid, T> _dados = new();
    public async Task<T?> BuscarPorIdAsync(Guid id) =>
        _dados.TryGetValue(id, out var item) ? item : null;
    public async Task SalvarAsync(T entidade) { /* in-memory */ }
}

// Pode trocar SQL por InMemory em testes sem quebrar nada — LSP ✓
```
