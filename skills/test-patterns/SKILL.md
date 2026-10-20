---
name: test-patterns
description: Padrões de teste em Java — Given/When/Then, FIRST, test doubles (dummy, stub, spy, mock, fake), não mocke o que não possui, Test Data Builder, @Nested, AssertJ, valores-limite, property-based (jqwik), approval e characterization tests, TDD/BDD, código assíncrono, test smells e testes flaky. Use quando escrever ou revisar testes frágeis, lentos ou sem asserts. Não use para configurar Testcontainers (integration-testing) nem JaCoCo (test-coverage).
---

Antes de aplicar este pattern, leia também [`../testing/SKILL.md`](../testing/SKILL.md) (unit e slice com JUnit 5/Mockito/`@WebMvcTest`), [`../integration-testing/SKILL.md`](../integration-testing/SKILL.md), [`../test-coverage/SKILL.md`](../test-coverage/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md) (sem comentários no código — o Given/When/Then é por linha em branco) e [`../ddd-hexagonal/SKILL.md`](../ddd-hexagonal/SKILL.md) (fakes para ports).

# Padrões de teste

Teste bom é **pequeno, rápido, determinístico, legível e falha por um motivo só** — e **documenta o comportamento** do sistema. Teste ruim **atrapalha**: quebra a cada refactor, passa quando o código está errado, ou ninguém entende. Esta skill reúne os **padrões** que separam os dois.

## 1. Estrutura: Given / When / Then (Arrange / Act / Assert)

Três blocos **separados por linha em branco** (sem comentários, que o pack não usa — `code-style`):
```java
@Test
void appliesTheLateFeeWhenTheLoanIsOverdue() {
    var loan = aLoan().dueOn(LocalDate.of(2026, 3, 1)).build();
    var clock = Clock.fixed(Instant.parse("2026-03-11T10:00:00Z"), ZoneOffset.UTC);

    var fee = policy.lateFee(loan, clock);

    assertThat(fee).isEqualTo(new Money(new BigDecimal("5.00"), "BRL"));
}
```
- **Given** (preparação) · **When** (**uma** ação sob teste) · **Then** (verificação). **Um único "When"**: se há duas ações, são dois testes.
- **Nome = comportamento**, não método (`appliesTheLateFeeWhenTheLoanIsOverdue`, não `testLateFee2`): o nome **é a especificação**; quando falha, o nome já diz o que quebrou.
- **Sem lógica no teste** (`if`, `for`, `try/catch` condicionando asserts): teste com lógica precisa de teste.

## 2. Princípios FIRST

| | Princípio | Significa |
|---|---|---|
| **F** | **Fast** | Milissegundos (unit). Teste lento deixa de ser rodado |
| **I** | **Isolated / Independent** | Roda **sozinho**, em **qualquer ordem**, sem depender de outro teste nem de estado global |
| **R** | **Repeatable** | Mesmo resultado **sempre**, em qualquer máquina e horário (sem `now()`, `Random`, rede, ordem de `HashMap`) |
| **S** | **Self-validating** | Passa ou falha **sozinho** (asserts), sem ler log a olho |
| **T** | **Timely** | Escrito **junto** do código (ou antes — TDD), não "depois, se der tempo" |

## 3. Test doubles — o vocabulário certo (Meszaros)

"Mock" virou sinônimo de qualquer dublê, mas **são cinco coisas diferentes**:
| Dublê | O que é | Quando usar | Exemplo |
|---|---|---|---|
| **Dummy** | Objeto passado só para preencher um parâmetro; **nunca usado** | Assinatura exige, o teste não usa | `new Object()`, `null` seguro |
| **Stub** | Devolve **respostas prontas** (controla as **entradas indiretas**) | O código lê algo de uma dependência | `when(repository.findById(1L)).thenReturn(Optional.of(book))` |
| **Spy** | Registra **como foi chamado** (e/ou delega ao real) | Verificar uma interação sem trocar o comportamento | `spy(realService)`; uso **raro** |
| **Mock** | Stub **+ verificação de interações** (**saídas indiretas**) | Provar um **efeito colateral** (enviou e-mail, publicou evento) | `verify(publisher).publish(event)` |
| **Fake** | Implementação **funcional simplificada** (em memória) | Substituir uma dependência pesada **mantendo comportamento real** | `InMemoryLoanRepository` |

**Como escolher:**
- **Prefira estado a interação.** Verifique o **resultado** (`assertThat(result)...`) antes de verificar **chamadas** (`verify(...)`). Testes presos a interações **quebram em todo refactor** (*fragile test*) e provam **como**, não **o quê**.
- **`verify` só para efeitos colaterais que importam** (comandos que saem do sistema: publicar, enviar, gravar), **nunca para consultas** (`findById`).
- **Fakes para suas próprias portas** (`LoanRepository`, `BookCatalog` — `ddd-hexagonal`): testes legíveis e **resistentes a refactor**. **Mockito para o `JpaRepository`** do Spring Data (um fake seria enorme).
- **Não mocke o que você não possui** (*don't mock types you don't own*): `RestClient`, `S3Client`, `JdbcTemplate`. Mocar a API de terceiro **acopla o teste à sua suposição** sobre ela. Em vez disso, **encapsule** em um adapter **seu** (`CatalogGateway`, `FileStorage`) e **mocke/faça fake** do adapter; teste o adapter **contra o real** (WireMock/Testcontainers/LocalStack — `integration-testing`, `localstack`).
- **Não mocke o que é simples e seu**: value objects, records, o próprio domínio. Instancie de verdade.
- **Strict stubs** (o `MockitoExtension` já falha em stub não usado): apague o stub sobrando em vez de `lenient()`.
- **Muitos mocks num teste** (5+) é **sinal de design**: a classe tem dependências demais.

```java
public class InMemoryLoanRepository implements LoanRepository {

    private final Map<LoanId, Loan> store = new HashMap<>();

    @Override
    public Optional<Loan> findById(LoanId id) {
        return Optional.ofNullable(store.get(id));
    }

    @Override
    public void save(Loan loan) {
        store.put(loan.id(), loan);
    }
}
```

## 4. Dados de teste: Test Data Builder e Object Mother

Montar objetos com 8 campos **em cada teste** polui e acopla. Dois padrões:
- **Object Mother**: métodos estáticos que devolvem objetos **prontos** (`Books.cleanCode()`, `Loans.overdue()`). Simples, bom para **cenários nomeados**.
- **Test Data Builder** (o mais flexível): **valores default válidos** + **só o que importa ao teste é sobrescrito** — o teste **mostra apenas o que é relevante**.
```java
public final class BookBuilder {

    private Long id = 1L;
    private String author = "Robert C. Martin";
    private String title = "Clean Code";
    private LocalDate launchDate = LocalDate.of(2009, 1, 10);
    private BigDecimal price = new BigDecimal("77.00");

    public static BookBuilder aBook() {
        return new BookBuilder();
    }

    public BookBuilder withTitle(String title) {
        this.title = title;
        return this;
    }

    public BookBuilder withPrice(BigDecimal price) {
        this.price = price;
        return this;
    }

    public Book build() {
        var book = new Book();
        book.setId(id);
        book.setAuthor(author);
        book.setTitle(title);
        book.setLaunchDate(launchDate);
        book.setPrice(price);
        return book;
    }
}
```
Uso: `aBook().withPrice(new BigDecimal("-1.00")).build()` — o leitor entende que **o preço negativo é o ponto** do teste. Regras: defaults **sempre válidos**; builders ficam em `src/test/.../support`; **nunca compartilhe uma instância mutável** entre testes (cada teste constrói a sua); **valores determinísticos** (não `random()` sem semente).
- **Dados "esquisitos" por valor-limite** vão no **builder + parametrização** (seção 6).
- **Tempo e aleatoriedade são dependências**: injete **`Clock`** (`Clock.fixed(...)`) e `Supplier<UUID>`/`Random` com semente — **nunca** `LocalDate.now()`/`UUID.randomUUID()` dentro de lógica testada (`ddd-hexagonal` já recebe `Clock`).

## 5. Organização e asserts

**`@Nested`** agrupa por **contexto** e dá legibilidade (e setup compartilhado do grupo):
```java
class BookServiceTest {

    @Nested
    class WhenTheBookExists {

        @Test
        void returnsIt() { ... }

        @Test
        void updatesTheTitle() { ... }
    }

    @Nested
    class WhenTheBookDoesNotExist {

        @Test
        void throwsResourceNotFound() { ... }
    }
}
```
**AssertJ** (`testing`) — escreva asserts **expressivos** em vez de vários `assertEquals`:
```java
assertThat(books).extracting(Book::getTitle).containsExactly("Clean Code", "Refactoring");
assertThat(result).usingRecursiveComparison().ignoringFields("id", "createdAt").isEqualTo(expected);
assertThatThrownBy(() -> service.findById(99L))
        .isInstanceOf(ResourceNotFoundException.class)
        .hasMessage("No records found for this ID!");
```
- **"Um conceito por teste", não "um assert por teste":** vários asserts sobre **o mesmo resultado** são ok; asserts sobre **comportamentos diferentes** são testes diferentes. Quando precisar de vários independentes, **`SoftAssertions`** (reporta **todas** as falhas de uma vez em vez de parar na primeira).
- **Assert no que importa**; ignore campos incidentais (`usingRecursiveComparison().ignoringFields(...)`) para não prender o teste ao irrelevante.
- **Mensagens de falha úteis** (`.as("lateFee for overdue loan")`) quando o assert não for autoexplicativo.

## 6. Parametrização e valores-limite

Uma regra, vários valores — `@ParameterizedTest` (`testing`). A fonte clássica de bugs são os **limites**:
```java
@ParameterizedTest
@CsvSource({
    "249, true",
    "250, true",
    "251, false"
})
void titleLengthMustBeAtMost250(int length, boolean valid) {
    assertThat(validator.isValidTitle("x".repeat(length))).isEqualTo(valid);
}
```
**Técnicas:** **classes de equivalência** (um representante por classe), **valores-limite** (`min−1, min, max, max+1`), **vazio/`null`/em branco**, **zero/negativo/máximo**, **unicode/acentos**, **datas** (passado, presente, futuro, bissexto), **ordenação/empate**. Use `@MethodSource` para dados complexos e `@EnumSource` para enums (com `mode = EXCLUDE` onde couber).

## 7. Property-based testing (jqwik)

Em vez de **exemplos** escolhidos à mão, você declara **propriedades que valem para qualquer entrada** e o framework **gera centenas de casos** (e **reduz** a falha ao menor contra-exemplo — *shrinking*). Ótimo para **parsers, cálculos, conversões, invariantes de domínio**:
```xml
<dependency>
    <groupId>net.jqwik</groupId>
    <artifactId>jqwik</artifactId>
    <version>${jqwik.version}</version>
    <scope>test</scope>
</dependency>
```
```java
class MoneyProperties {

    @Property
    void addingIsCommutative(@ForAll("amounts") BigDecimal a, @ForAll("amounts") BigDecimal b) {
        var left = new Money(a, "BRL").add(new Money(b, "BRL"));
        var right = new Money(b, "BRL").add(new Money(a, "BRL"));

        assertThat(left).isEqualTo(right);
    }

    @Provide
    Arbitrary<BigDecimal> amounts() {
        return Arbitraries.bigDecimals().between(BigDecimal.ZERO, new BigDecimal("1000000")).ofScale(2);
    }
}
```
**Propriedades úteis:** **comutatividade/associatividade**, **idempotência** (`f(f(x)) == f(x)` — casa com `idempotency`), **ida e volta** (`parse(format(x)) == x`, serializar/desserializar), **invariantes** (saldo nunca negativo), **comparar com um oráculo simples** (implementação lenta e óbvia × a otimizada). **Quando usar:** lógica com **muitas combinações** de entrada. **Quando não:** código de cola, fluxos com I/O. Mantenha a **semente do caso que falhou** (o jqwik a imprime) e transforme-a em **teste de exemplo** de regressão. `jqwik.version` fora do BOM (`maven-config`; confirme a versão compatível com o JUnit da plataforma).

## 8. Approval / snapshot e characterization tests

- **Approval (golden master) test**: compara a saída com um **arquivo aprovado** versionado (um JSON de resposta, um relatório). Útil para **payloads grandes** e **contratos de resposta** (`JSONassert` strict já vem no `spring-boot-starter-test`: `JSONAssert.assertEquals(expected, actual, JSONCompareMode.STRICT)`). Cuidados: o arquivo é **revisado como código** quando muda; **não aprove às cegas** ("atualizar todos os snapshots" sem ler apaga a proteção); evite campos voláteis (ids, timestamps — normalize).
- **Characterization test** (para **código legado** sem testes): em vez de dizer o que o código *deveria* fazer, **registre o que ele faz hoje** (entradas → saídas reais) para **refatorar com rede de segurança**. Depois de refatorar, **substitua** pelos testes de comportamento corretos e **corrija** os bugs que a caracterização expôs.

## 9. TDD e BDD — quando valem

- **TDD (red → green → refactor):** escreva um teste que **falha**, faça-o **passar** do jeito mais simples, **refatore** com a rede de segurança. **Vale muito para:** regras de negócio, algoritmos, parsers, **reproduzir um bug** (teste que falha → correção → passa — `developer`, `qa`). **Menos útil para:** exploração/spikes, UI, código de cola, configuração. Não é dogma: o ganho é o **design guiado pelo uso** e a **cobertura de comportamento** naturalmente alta.
- **BDD:** descrever o comportamento em **Given/When/Then** como **linguagem comum** entre produto, QA e engenharia (`user-stories`, `prd-writing`: critérios de aceite). **Na maioria dos times, JUnit com nomes e Given/When/Then já basta.** **Cucumber/Gherkin** só compensa quando **pessoas não-técnicas leem e mantêm** os cenários; caso contrário é uma camada extra de cola a manter. Os **critérios de aceite do PM** viram **casos de teste** diretamente.
- **ATDD:** o teste de aceite (de integração) escrito **a partir do critério de aceite** antes da implementação.

## 10. Código assíncrono, concorrente e dependente de tempo

- **Assíncrono:** **Awaitility** (`await().atMost(...).untilAsserted(...)`) — **nunca `Thread.sleep`** (lento **e** flaky).
- **Concorrência:** `ExecutorService` + `CountDownLatch`/`CyclicBarrier` para **largada simultânea** e `assert` no resultado (`idempotency`: N requests concorrentes → um efeito); **repita** o teste várias vezes localmente (`@RepeatedTest(50)`) para provocar a corrida — se **falha às vezes**, **é bug do código** (ou do teste), não "flaky inevitável".
- **Tempo:** `Clock` injetado; **nunca** `sleep` para "esperar passar o tempo".
- **Executores determinísticos** em unit tests (executar a tarefa na thread chamadora) para testar a lógica sem threads.

## 11. Test smells — o que cheira mal

| Smell | Sintoma | Cura |
|---|---|---|
| **Fragile test** | Quebra a cada refactor sem mudar comportamento (over-mocking, `verify` de tudo) | Verifique **estado/resultado**; fakes; menos mocks |
| **Obscure test / Mystery Guest** | Não dá para entender sem abrir outros arquivos (dados escondidos em fixture/arquivo/banco) | Dados **visíveis no teste** (builders); nome claro |
| **Assertion Roulette** | Muitos asserts sem mensagem; não se sabe qual falhou | `SoftAssertions`, `.as(...)`, ou dividir |
| **Eager test** | Um teste verifica **vários comportamentos** | Um comportamento por teste |
| **Lógica condicional** | `if/for/try` no teste | Tire; parametrize; teste a lógica separadamente |
| **Test-per-method** | Um teste por método de produção, atrelado à estrutura | Um teste por **comportamento** |
| **Ordem/estado compartilhado** | Passa sozinho, falha na suíte (ou o contrário) | Independência; builders novos por teste; limpeza |
| **Slow test** | Unit test que sobe Spring/banco | Rebaixe para unit; mova o que é de integração |
| **Conditional / ignored test** | `@Disabled`, `assumeTrue` "permanente" | Conserte ou **apague** (teste desabilitado é dívida invisível) |
| **Duplicação de setup** | Mesmo setup em 30 testes | Builders/`@BeforeEach` enxuto/helpers |
| **Testar a implementação** | O teste espelha o código linha a linha | Teste **comportamento público** |
| **Teste que nunca falha** | Sem assert; `assertTrue(true)`; `catch` engolindo | **Mutation check** (quebre o código de propósito e veja o teste falhar — `test-coverage`, PIT) |
| **Sleepy test** | `Thread.sleep` para esperar | Awaitility/latch |
| **Excessive setup** | 40 linhas de Given | A classe faz demais; builders; revisar o design |

**Teste é código de produção para efeito de revisão** (`code-reviewer`): nomes, duplicação, clareza. **Refatore testes** e **apague os obsoletos**.

## 12. Testes flaky (intermitentes)

Um teste **flaky** passa e falha **sem mudança de código**. Corrói a confiança: o time passa a **ignorar vermelho** e **bugs reais passam**. **Trate como bug, não como "azar".**
| Causa | Cura |
|---|---|
| **Tempo** (`now()`, fusos, virada de dia/mês) | `Clock` fixo; não dependa do relógio real |
| **Aleatoriedade** | Semente fixa; dados determinísticos |
| **Assíncrono sem espera correta** | Awaitility; nunca `sleep` fixo |
| **Concorrência/corrida** | Corrija a corrida no código; latches no teste |
| **Estado compartilhado / ordem** | Independência; dados únicos por teste; limpeza |
| **Dependência externa** (rede, serviço real) | WireMock/Testcontainers/LocalStack; **nunca** a internet |
| **Recursos** (porta fixa, arquivo, diretório temporário) | Portas aleatórias; `@TempDir` |
| **Ordem de coleções/`HashMap`/resultados sem `ORDER BY`** | Ordene explicitamente; asserts independentes de ordem (`containsExactlyInAnyOrder`) |
| **Seed aleatória do banco** (`flyway-migrations`) | Nunca assert sobre ela |
| **Locale/timezone/encoding da máquina** | Fixe o locale/timezone nos testes; UTF-8 explícito |
| **CI lento/recursos limitados** | Timeouts realistas; Awaitility em vez de tempo fixo |

**Política:** **quarentena** imediata do flaky (marca/isola, com **issue e dono e prazo**, e **corrige**, não apaga em silêncio); **meça a taxa de flakiness** da suíte; **não "resolva" com retry** (`rerunFailingTestsCount` mascara o bug — use só como **diagnóstico** temporário). Reproduza com **repetição** (`@RepeatedTest`, execução em loop) e **semente impressa**.

## 13. Pirâmide × honeycomb — onde está o valor

- **Pirâmide clássica** (muitos unit, alguns integration, poucos e2e): ótima para **serviços com regra de negócio rica**.
- **"Honeycomb"/troféu** (poucos unit, **muitos testes de integração do serviço**, poucos e2e): serve melhor a **microsserviços "finos"** (muita cola e integração, pouca regra), onde o **risco está nas fronteiras** (banco, mensageria, HTTP). Aqui o foco é **integração do serviço com dependências reais** (`integration-testing`) + **contratos** entre serviços (`contract-testing`) — e **pouquíssimos** e2e.
**Escolha pelo onde mora o risco**, não por religião. Em qualquer formato: **regra de negócio em unit tests rápidos**, **integração com o real nas fronteiras**, **contratos entre serviços**, **e2e só de fumaça**.
| O que provar | Nível |
|---|---|
| Regra de negócio, cálculo, validação | **Unit** (puro, sem Spring) |
| Rota, serialização, validation, erro | **Slice** (`@WebMvcTest`) |
| SQL, constraints, `@Query` | **`@DataJpaTest`** com banco real |
| Fluxo ponta a ponta do serviço, segurança, migrations | **Integração** |
| Serviço A entende o serviço B | **Contrato** |
| A plataforma está de pé | **Smoke e2e** (poucos) |

## 14. Testes no estilo hexagonal/DDD

(`ddd-hexagonal`) O **domínio** se testa com **unit tests puros** (sem Spring, sem mocks — `Clock` fixo); os **use cases** com **fakes em memória** das portas; os **adapters** (web, persistência, ACL) com **testes de slice/integração/contrato**; e a **arquitetura** com **ArchUnit**. É onde os padrões desta skill rendem mais.

## 15. Revisão de testes (checklist do `code-reviewer`/`qa`)

- O teste **falharia** se o código estivesse errado? (mutation check)
- O **nome** descreve o comportamento? Given/When/Then visíveis?
- **Um** comportamento; **sem lógica**; **dados visíveis** (builders)?
- Mocks **só onde necessário**; **fakes** para portas; **não** mocka o que não possui?
- **Determinístico** (Clock, sem sleep, sem aleatório, sem ordem)?
- **Rápido** no nível certo? **Independente**?
- **Cobre o limite e o erro**, não só o caminho feliz?
- Sem `@Disabled`/asserts afrouxados para "passar"?

---

## Regras principais

- **Given/When/Then** em blocos separados (sem comentários), **um When**, **nome = comportamento**, **sem lógica** no teste; **FIRST**.
- **Test doubles com o nome certo**: stub controla entradas, **mock** verifica **efeitos colaterais que importam**, **fake** para suas portas; **prefira estado a interação**; **`verify` não vale para consultas**.
- **Não mocke o que você não possui** (encapsule em adapter seu e teste o adapter contra o real); **não mocke o simples e seu**; muitos mocks = design ruim; sem `lenient()` para esconder stub sobrando.
- **Test Data Builder** (defaults válidos, o teste mostra só o relevante) e **Object Mother**; **`Clock` e aleatoriedade injetados**; **nada de instâncias mutáveis compartilhadas**.
- **`@Nested`** por contexto; **AssertJ** expressivo (`extracting`, `usingRecursiveComparison`, `SoftAssertions`); **um conceito por teste**.
- **Parametrização e valores-limite** (`min−1, min, max, max+1`, vazio/null/unicode); **property-based (jqwik)** para lógica com muitas combinações; **approval/snapshot** revisados como código; **characterization** para legado.
- **TDD** para regras de negócio e reprodução de bug; **BDD** como linguagem comum (JUnit basta; Cucumber só com não-técnicos mantendo cenários).
- **Assíncrono com Awaitility**, concorrência com latches e `@RepeatedTest`, tempo com `Clock` — **nunca `sleep`**.
- **Combata os test smells** e **trate flaky como bug** (causa, quarentena com dono/prazo, medir a taxa; nunca "resolver" com retry).
- **Pirâmide ou honeycomb conforme onde mora o risco**; regra no unit, fronteiras em integração, serviços por contrato, e2e só de fumaça.
- **Sem Lombok** — deliberado.
