---
name: design-patterns
description: Padrões de projeto (GoF e corporativos) aplicados a Spring Boot no padrão do pacote — Strategy, Factory, Template Method, Adapter, Decorator e Proxy (AOP, @Transactional, auto-invocação), Observer com eventos do Spring, Builder, Singleton e beans sem estado, Chain of Responsibility (filtros), State com enum/sealed, Facade, Specification para filtros dinâmicos, Repository e DTO — com onde o próprio Spring já os usa, quando usar, quando não usar e como testar. Use ao escolher como estruturar uma solução recorrente, ao revisar design ou quando alguém propuser um padrão.
---

Antes de aplicar este pattern, leia também [`../solid/SKILL.md`](../solid/SKILL.md) (os princípios por trás dos padrões), [`../code-organization/SKILL.md`](../code-organization/SKILL.md) e [`../code-style/SKILL.md`](../code-style/SKILL.md). Mudar código existente: [`../refactoring/SKILL.md`](../refactoring/SKILL.md). Padrões de arquitetura distribuída: [`../microservices/SKILL.md`](../microservices/SKILL.md) e as skills citadas na seção 4.

# Padrões de projeto

Um padrão é **uma solução conhecida para um problema recorrente** — e um **vocabulário**: dizer "é um Strategy" explica o desenho em duas palavras. O erro comum é o inverso: começar pelo padrão e procurar onde encaixá-lo. **Comece pelo problema.** Sem o problema, o padrão é só indireção (`refactoring`: design pattern sem problema real é over-engineering).

O Spring já implementa vários padrões para você — reconhecê-los evita reimplementá-los mal.

## Mapa rápido

| Problema | Padrão | No Spring / no pacote |
|---|---|---|
| Um algoritmo que varia por tipo (formato, meio de pagamento, regra de cálculo) | **Strategy** | `FileExporter` por formato (`file-import-export`) |
| Escolher/criar a implementação certa em tempo de execução | **Factory** | `FileExporterFactory`, o próprio container de beans |
| Mesmo esqueleto, passos que variam | **Template Method** | `JdbcTemplate`, `RestClient`, `AbstractIntegrationTest` |
| Encaixar uma interface externa no seu modelo | **Adapter** | Anti-corruption layer (`service-communication`), adapters do hexagonal |
| Acrescentar comportamento sem mudar a classe | **Decorator** / **Proxy** | `@Transactional`, `@Cacheable`, `@Async`, `@PreAuthorize` (AOP) |
| Avisar interessados sem conhecê-los | **Observer** | `ApplicationEventPublisher` + `@EventListener`/`@TransactionalEventListener` |
| Construir objetos com muitos parâmetros opcionais | **Builder** | `RestClient.builder()`, `OpenAPI`, `PageRequest`; records para dados |
| Uma instância compartilhada | **Singleton** | Todo bean do Spring (escopo padrão) — **sem estado mutável** |
| Uma requisição passando por etapas que podem interromper | **Chain of Responsibility** | `SecurityFilterChain`, `HandlerInterceptor`, filtros do Gateway |
| Comportamento que depende do estado do objeto | **State** | Enum/sealed com transições explícitas |
| Simplificar um subsistema para quem chama | **Facade** | O service que orquestra repositories e componentes |
| Filtros combináveis montados em tempo de execução | **Specification** | `Specification<T>` do Spring Data JPA |
| Isolar o acesso a dados / transportar dados entre camadas | **Repository** / **DTO** | Spring Data; `*DTO` do pacote |

---

## 1. Criacionais

### Factory
Quando a escolha da implementação depende de um dado de runtime (extensão do arquivo, header `Accept`, tipo de pagamento). No pacote: `FileImporterFactory`/`FileExporterFactory` (`file-import-export`).
- **O container do Spring já é uma factory.** Não escreva factory para criar objetos que podem ser beans — injete-os. A factory existe para **escolher entre beans** em runtime.
- Forma extensível: `List<Strategy>` injetada + `supports(...)` em cada estratégia (`solid`, seção O), ou um `Map<String, Strategy>` (o Spring injeta beans por nome).

### Builder
Para objetos com muitos parâmetros, vários opcionais, ou que precisam ser válidos ao final da construção.
- Use os builders das libraries (`RestClient.builder()`, `ResponseEntity.ok()...`, `GroupedOpenApi.builder()`).
- **DTOs do pacote não usam builder** (são POJOs com getters/setters explícitos, sem Lombok — `code-organization`). Para dados imutáveis (eventos, respostas internas), um **record** resolve sem builder (`java-modern-features`).
- **Test Data Builder** nos testes (`test-patterns`) é o lugar onde o Builder mais compensa no dia a dia.

### Singleton
**Todo bean do Spring é singleton por padrão** — uma instância servindo todas as requisições, em várias threads ao mesmo tempo. Consequência: **beans não guardam estado de requisição em campos** (um campo `currentUser` num service é um bug de concorrência que vaza dados entre usuários). Estado por requisição vai em variável local, parâmetro ou no `SecurityContext`. Nunca escreva um Singleton "clássico" (`getInstance()` estático) para algo que pode ser bean: ele não é injetável nem substituível em teste.

---

## 2. Estruturais

### Adapter
Converte a interface de um sistema externo para o modelo do seu domínio, para que a mudança no parceiro fique em **um lugar**:
```java
@Component
public class CatalogClientAdapter implements BookCatalog {

    @Autowired
    private CatalogHttpClient client;

    @Override
    public Optional<BookInfo> findByIsbn(String isbn) {
        try {
            var response = client.getBook(isbn);
            return Optional.of(new BookInfo(response.isbn13(), response.fullTitle(), response.authorNames()));
        } catch (HttpClientErrorException.NotFound e) {
            return Optional.empty();
        }
    }
}
```
O resto da aplicação usa `BookCatalog` e `BookInfo` (seus nomes), nunca os DTOs nem os erros HTTP do parceiro. É a **anti-corruption layer** de `service-communication` e o **adapter** de `ddd-hexagonal`.

### Decorator e Proxy (AOP)
O Spring envolve seus beans em **proxies** para acrescentar comportamento: `@Transactional` abre/fecha a transação, `@Cacheable` consulta o cache (`caching`), `@Async` muda de thread (`email`), `@PreAuthorize` checa a permissão (`authentication`), `@Retryable`/Resilience4j repete (`resilience`).

**A armadilha nº 1 — auto-invocação:** o proxy só age em chamadas que **vêm de fora** do bean. `this.metodo()` dentro da mesma classe chama o objeto real e **pula** o proxy:
```java
@Service
public class LoanService {

    public void renewAll(List<Long> ids) {
        ids.forEach(this::renew);
    }

    @Transactional
    public void renew(Long id) { ... }
}
```
Aqui `renew` roda **sem transação** quando chamado por `renewAll`. Correções: anote o método de entrada (`renewAll`), mova `renew` para outro bean, ou desenhe a transação no nível certo. O mesmo vale para `@Cacheable`, `@Async` e `@PreAuthorize`. Proxies também não interceptam métodos `private` nem `final`.

Para um decorator **seu** (ex.: medir o tempo de um client), prefira compor explicitamente — uma classe que implementa a mesma interface e delega — a escrever um aspecto, a não ser que o comportamento atravesse muitos beans.

### Facade
O service do pacote é uma facade: o controller chama `bookService.create(dto)` sem saber de repository, mapper, eventos e validações. Mantenha a facade **fina** — orquestração, não a regra inteira escondida num método de 200 linhas (`solid`, seção S).

---

## 3. Comportamentais

### Strategy
Um algoritmo intercambiável atrás de uma interface — o padrão mais útil do dia a dia:
```java
public interface LateFeePolicy {

    boolean appliesTo(Member member);

    BigDecimal calculate(Loan loan, LocalDate returnDate);
}
```
Uma implementação por regra (`StandardLateFeePolicy`, `StudentLateFeePolicy`), todas `@Component`, escolhidas por `appliesTo`. Nova regra = nova classe (`solid`, seção O). **Não use** para duas variações que nunca vão crescer: um `if` é mais claro.

### Template Method
Um esqueleto fixo com passos que variam. No Spring, aparece "invertido" como **callback**: `JdbcTemplate`, `TransactionTemplate` e `RestClient` controlam abrir/fechar/tratar erro e você passa só o passo variável (um lambda). Nos testes, `AbstractIntegrationTest` (`integration-testing`) é um template: a base sobe o container e configura o client; cada teste escreve só o cenário. Prefira **callbacks/composição** a hierarquias de herança profundas.

### Observer (eventos)
Avisar outras partes do sistema sem acoplá-las ao produtor:
```java
publisher.publishEvent(new BookCreatedEvent(saved.getId()));
```
```java
@TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
public void on(BookCreatedEvent event) { ... }
```
- `@EventListener` roda **na mesma thread e na mesma transação**: uma exceção no listener desfaz o produtor. `@TransactionalEventListener(AFTER_COMMIT)` roda só se o commit aconteceu — o certo para efeitos externos (e-mail, mensagens — `email`).
- Eventos em memória **se perdem** se a aplicação cair. Para outros serviços ou entrega garantida, use **outbox** (`transactional-outbox`) e um broker (`messaging`). Entre módulos de um monolito modular, o Spring Modulith persiste os eventos (`modular-monolith`).
- Eventos são records imutáveis, com ids — não a entity inteira.

### Chain of Responsibility
Cada elo decide tratar, passar adiante ou interromper: a `SecurityFilterChain` (o `JwtTokenFilter` de `authentication` é um elo), os `HandlerInterceptor` do MVC e os filtros do Spring Cloud Gateway (`api-gateway`). Para validações de negócio em sequência ("o sócio está ativo? o livro está disponível? o limite foi atingido?"), uma lista de regras (`List<RenewalRule>`) avaliada em ordem é uma chain simples e testável.

### State
Quando o que se pode fazer depende do estado (`ACTIVE`, `RENEWED`, `OVERDUE`, `RETURNED`), centralize as **transições permitidas** em vez de espalhar `if (status == ...)`:
```java
public enum LoanStatus {
    ACTIVE, RENEWED, OVERDUE, RETURNED;

    public boolean canRenew() {
        return this == ACTIVE || this == RENEWED;
    }
}
```
Com comportamento por estado mais rico, um **sealed interface** com um record por estado e `switch` exaustivo deixa o compilador apontar o caso esquecido (`java-modern-features`). Persistido como `@Enumerated(EnumType.STRING)` (`spring-data-jpa`). Transições também são boas candidatas a links condicionais (`hateoas`).

---

## 4. Padrões corporativos que o pacote usa

| Padrão | Para quê | Skill |
|---|---|---|
| **Repository** | Acesso a dados atrás de uma interface de coleção | `spring-data-jpa` |
| **DTO** | Contrato da API separado do modelo persistido | `code-organization` |
| **Specification** | Filtros dinâmicos combináveis (`Specification<Book>` + `JpaSpecificationExecutor`), em vez de dezenas de métodos `findByXAndYAndZ` | `spring-data-jpa` |
| **Unit of Work** | A transação JPA (persistence context) agrupa as mudanças até o commit | `spring-data-jpa` |
| **Anti-corruption layer / Adapter** | Proteger o domínio de modelos externos | `service-communication`, `ddd-hexagonal` |
| **Transactional Outbox** | Publicar evento junto com a mudança no banco | `transactional-outbox` |
| **Saga** | Transação de negócio entre serviços | `saga-pattern` |
| **CQRS** | Modelos de leitura e escrita separados | `cqrs-event-sourcing` |
| **Circuit Breaker, Retry, Bulkhead** | Falhas parciais | `resilience` |
| **Idempotency Key** | Repetição sem efeito duplicado | `idempotency` |
| **API Gateway / BFF** | Borda única para os clients | `api-gateway` |
| **Strangler Fig** | Migração incremental | `refactoring`, `microservices` |

Specification, em resumo:
```java
public final class BookSpecifications {

    private BookSpecifications() {}

    public static Specification<Book> titleContains(String title) {
        return (root, query, cb) -> title == null ? null
            : cb.like(cb.lower(root.get("title")), "%" + title.toLowerCase(Locale.ROOT) + "%");
    }

    public static Specification<Book> publishedAfter(LocalDate date) {
        return (root, query, cb) -> date == null ? null : cb.greaterThan(root.get("launchDate"), date);
    }
}
```
`repository.findAll(titleContains(title).and(publishedAfter(date)), pageable)` — o critério é montado com a Criteria API (parâmetros, sem concatenação de SQL) e continua paginado (`pagination`). Filtros `null` são ignorados.

---

## 5. Anti-padrões

- **Padrão sem problema:** factory para uma implementação, strategy para dois casos fixos, interface + `Impl` para tudo (`solid`, D).
- **God Service / God Object:** uma classe que sabe tudo (`refactoring`).
- **Service Locator:** buscar beans no `ApplicationContext` espalhado pelo código esconde as dependências — restrinja ao **ponto de escolha** de uma factory.
- **Singleton com estado:** campo mutável em bean (vaza dados entre requisições).
- **Herança para reaproveitar código:** `BaseService<T>`, `BaseEntity` genéricos que acoplam tudo (o pacote não usa `BaseEntity` — `spring-data-jpa`).
- **Modelo anêmico** num domínio rico (todas as regras no service, entidade só com getters/setters) — aceitável em CRUD, um problema em domínio complexo (`ddd-hexagonal`).
- **Proxy ignorado:** `@Transactional`/`@Cacheable` em método chamado por `this`, `private` ou `final`.

---

## 6. Testando os padrões

- **Strategy:** um teste por implementação, mais um teste da escolha (factory/registry) com todas as estratégias; teste de contrato comum quando houver muitas (`solid`, L).
- **Adapter:** WireMock simulando o parceiro, incluindo erros e respostas estranhas (`service-communication`).
- **Observer:** o produtor publica o evento (verifique com `@RecordApplicationEvents`/`ApplicationEvents` no teste do Spring); o listener testado isoladamente; o caso de rollback (nenhum efeito).
- **Proxy:** um teste de integração que prova que a transação/cache **de fato** acontece — um teste unitário com o objeto real não passa pelo proxy.
- **State:** uma tabela de transições (`@ParameterizedTest`) com as permitidas e as proibidas.

---

## Regras principais

- Comece pelo problema, nunca pelo padrão; sem problema recorrente real, prefira o código direto.
- Reconheça o que o Spring já faz: container (factory/singleton), proxies (decorator), eventos (observer), filtros (chain), templates/callbacks.
- Beans são singletons compartilhados entre threads: **sem estado mutável de requisição em campos**.
- Proxies não agem em auto-invocação (`this.metodo()`), em métodos `private` ou `final` — desenhe a fronteira transacional sabendo disso.
- Strategy (interface + implementações como beans, escolhidas por `supports`) para variações que crescem; `if`/`switch` exaustivo para poucas variações fixas.
- Adapter/anti-corruption layer para todo sistema externo; o domínio usa os próprios nomes.
- Eventos: `AFTER_COMMIT` para efeitos externos; outbox quando não podem se perder; records com ids.
- State com enum/sealed e transições explícitas; Specification para filtros dinâmicos paginados.
- Evite Service Locator, herança para reaproveitar código, `BaseService`/`BaseEntity` genéricos e interface + `Impl` sem necessidade.
- Teste cada estratégia, a escolha entre elas, os adapters contra um servidor simulado e os proxies em teste de integração.
- **Sem Lombok** — deliberado.
