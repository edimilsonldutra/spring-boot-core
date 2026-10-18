---
name: integration-testing
description: Testes de integração no Spring Boot 4 com banco real em container — Testcontainers singleton, @SpringBootTest com porta aleatória e REST Assured, isolamento de dados, contrato de erro e segurança, migrations, cache de contexto, outros containers, Awaitility e anti-patterns (nunca H2). Use quando testar o fluxo ponta a ponta contra a aplicação rodando.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../testing/SKILL.md`](../testing/SKILL.md) (a base: unit e slice), [`../test-patterns/SKILL.md`](../test-patterns/SKILL.md), [`../spring-data-jpa/SKILL.md`](../spring-data-jpa/SKILL.md) (`@DataJpaTest`, container MySQL) e [`../maven-config/SKILL.md`](../maven-config/SKILL.md) (dependencies, surefire, REST Assured). Cobertura: `test-coverage`.

# Testes de integração

Um **teste de integração** sobe **a aplicação de verdade** (contexto Spring completo, Flyway aplicado, **banco real em container**) e a exercita **por HTTP**, como um client faria. Ele prova o que unit e slice **não conseguem**: que as peças **funcionam juntas** — rotas, serialização, validation, `@ControllerAdvice`, segurança, transações, **SQL real, constraints e migrations**.

| Nível | Prova | Velocidade | Quantidade |
|---|---|---|---|
| Unit (`testing`) | Regra de negócio isolada | ms | **Muitos** |
| Slice (`@WebMvcTest`, `@DataJpaTest`) | Uma camada com o Spring | s | Vários |
| **Integração (esta skill)** | **Fluxo ponta a ponta** com banco real | s–min | **Poucos e escolhidos** |
| Contrato (`contract-testing`) | Entendimento entre serviços | s | Um por interação |

**Não duplique:** o que um unit test prova, o de integração **não** repete. Use-o para **caminhos críticos, o contrato de erro, a segurança e a persistência** — não para cada `if` do service.

> **Nunca H2 no lugar do banco de produção.** H2 e SQLite "parecem" funcionar e **mentem**: SQL, tipos, collation e constraints diferem — o teste passa e a produção quebra. Teste com o **mesmo banco** (e a mesma versão major) via Testcontainers.

## Dependencies

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-test</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>testcontainers-mysql</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>io.rest-assured</groupId>
    <artifactId>rest-assured</artifactId>
    <version>${rest-assured.version}</version>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.awaitility</groupId>
    <artifactId>awaitility</artifactId>
    <scope>test</scope>
</dependency>
```
O módulo do Testcontainers acompanha o banco escolhido (`maven-config`: tabela dos cinco databases — `testcontainers-postgresql`, `-mssqlserver`, `-oracle-free`, `-mariadb`). O **REST Assured não é gerenciado pelo BOM** (property de versão — `maven-config`). **Docker precisa estar rodando** (no CI, o `ubuntu-latest` já tem — `github-actions-aws`).

---

## 1. Classe base com container singleton

**Um container por suíte, não por classe**: subir um banco por classe de teste multiplica o tempo da suíte. O padrão é um **container estático iniciado uma vez** em uma classe base:

```java
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
public abstract class AbstractIntegrationTest {

    static final MySQLContainer mysql = new MySQLContainer("mysql:9.1.0")
            .withConfigurationOverride("mysql-default-conf");

    static {
        mysql.start();
    }

    @DynamicPropertySource
    static void datasource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", mysql::getJdbcUrl);
        registry.add("spring.datasource.username", mysql::getUsername);
        registry.add("spring.datasource.password", mysql::getPassword);
    }

    @LocalServerPort
    protected int port;

    protected RequestSpecification api() {
        return given()
                .config(RestAssuredConfig.config().jsonConfig(JsonConfig.jsonConfig().numberReturnType(JsonPathConfig.NumberReturnType.BIG_DECIMAL)))
                .port(port)
                .contentType(ContentType.JSON)
                .accept(ContentType.JSON);
    }
}
```
- **`webEnvironment = RANDOM_PORT`**: sobe o servidor real em **porta aleatória** (nunca fixa — colide com outra execução/aplicação). `@LocalServerPort` entrega a porta.
- **`NumberReturnType.BIG_DECIMAL`**: sem isso o REST Assured lê números JSON como `float` e o assert de dinheiro (`price` é `BigDecimal`) perde precisão; compare com `comparesEqualTo` (ignora a escala), não `equalTo`.
- **`@DynamicPropertySource`** liga o datasource ao container (porta aleatória do container). **`mysql:9.1.0`: fixe a tag** da mesma versão major de produção — nunca `latest`.
- **`.withConfigurationOverride("mysql-default-conf")`** só para MySQL (`flyway-migrations`: tie-breaking de seeds; `spring-data-jpa`).
- **O container nunca é parado explicitamente**: o **Ryuk** do Testcontainers o remove quando a JVM termina. Não use `@Container`/`@Testcontainers` aqui — eles **param o container ao fim de cada classe**, anulando o singleton.
- **Alternativa Boot-native:** um `@TestConfiguration(proxyBeanMethods = false)` com `@Bean @ServiceConnection MySQLContainer mysql()` (o que o Spring Initializr gera como `TestcontainersConfiguration`), importada nas classes de teste: o Boot liga a conexão sozinho, sem `@DynamicPropertySource`. Para **reuso entre execuções locais**, `@RestartScope` com devtools ou `.withReuse(true)` + `testcontainers.reuse.enable=true` em `~/.testcontainers.properties` — **só na máquina do desenvolvedor, nunca no CI**.
- **Debugar o container:** `mysql.followOutput(new Slf4jLogConsumer(LoggerFactory.getLogger("mysql")))` mostra os logs do banco no teste.
- **Timeout de startup** de bancos pesados (SQL Server, Oracle): `.withStartupTimeout(Duration.ofMinutes(3))`; imagens grandes demoram na primeira execução (cache de imagens no CI).

**`src/test/resources/application.yml` é uma cópia completa do principal** (`code-organization`), sem `datasource.url/username/password` (vêm do container). Não repita config que o teste não precisa; mantenha `check_nullability`, springdoc e CORS **iguais à produção**, senão o teste prova outra aplicação.

---

## 2. Escrevendo o teste (REST Assured)

```java
class BookControllerIntegrationTest extends AbstractIntegrationTest {

    @Autowired
    private JdbcTemplate jdbc;

    @AfterEach
    void removeTestData() {
        jdbc.update("DELETE FROM books WHERE title LIKE 'it-%'");
    }

    @Test
    void createsAndReadsABook() {
        var title = "it-" + UUID.randomUUID();

        var id = api().body(Map.of("author", "Robert C. Martin", "title", title,
                        "launchDate", "2009-01-10", "price", new BigDecimal("77.00")))
                .when().post("/api/book/v1")
                .then().statusCode(200)
                .extract().jsonPath().getLong("id");

        api().when().get("/api/book/v1/{id}", id)
                .then().statusCode(200)
                .body("title", equalTo(title))
                .body("price", comparesEqualTo(new BigDecimal("77.00")));
    }

    @Test
    void answers404WithTheErrorContractWhenTheBookDoesNotExist() {
        api().when().get("/api/book/v1/{id}", 999_999)
                .then().statusCode(404)
                .body("message", equalTo("No records found for this ID!"))
                .body("details", startsWith("uri=/api/book/v1/"));
    }

    @Test
    void answers400WithFieldErrorsWhenTheBodyIsInvalid() {
        api().body(Map.of("title", ""))
                .when().post("/api/book/v1")
                .then().statusCode(400)
                .body("errors.title", notNullValue())
                .body("errors.price", notNullValue());
    }
}
```
- **Cada teste cria os seus dados** (título com `UUID`) e **limpa só o que criou** — nada de depender de linhas de outros testes nem da ordem.
- **Prove o contrato de erro** (`exception-handling`, `bean-validation`): `404` com `ExceptionResponse`, `400` com `errors` por campo, **nunca `500` para erro do client**, nunca stack trace no body.
- Use **JSON mirror/`Map`** na requisição em vez do DTO de produção quando quiser **detectar mudança de contrato** (o teste não "acompanha" o refactor do DTO sem aviso).
- **Content negotiation** (`web-config`): se XML/YAML foram habilitados, teste um endpoint em cada formato (`contentType(XML)` com DTO espelho `@XmlRootElement` — só no teste).
- **Asserts significativos**, não só o status: valide o **corpo**, os **headers** relevantes e o **efeito no banco** quando importa (`jdbc.queryForObject("SELECT count(*) ...")`).

### Segurança (quando há JWT — `authentication`, `aws-cognito`)

`@WithMockUser` **não vale aqui** (a requisição é HTTP real, em outra thread). Obtenha **um token de verdade** do usuário **semeado para o teste** (migration/`@Sql` de teste — **nunca** credenciais de produção):
```java
protected String tokenOf(String username, String password) {
    return api().body(Map.of("username", username, "password", password))
            .when().post("/auth/signin")
            .then().statusCode(200)
            .extract().path("accessToken");
}
```
Teste: **sem token → 403/401**, **token adulterado/expirado**, **role insuficiente → 403**, **acesso ao recurso de outro usuário (IDOR) → negado**. (Com Cognito, o `JwtDecoder` é substituído no teste por um que aceita JWTs assinados com uma chave local — veja `aws-cognito`, testes.)

---

## 3. Isolamento de dados (o erro nº 1 dos testes de integração)

| Estratégia | Funciona com HTTP real? | Observação |
|---|---|---|
| **`@Transactional` no teste (rollback)** | ❌ **Não** | O servidor roda em **outra thread e outra transaction**: o rollback do teste **não desfaz** o que a requisição gravou (e o teste não enxerga dados não confirmados da requisição). Só serve para slice/`MockMvc` na mesma thread |
| **Dados únicos por teste + limpeza do que criou** | ✅ | O padrão recomendado (acima): `UUID` nos nomes, `@AfterEach` removendo só o seu |
| **Limpeza total** (`TRUNCATE`/`DELETE` de tabelas) | ✅ | Simples e robusto; **não** use com testes em paralelo; mantenha a **seed de migration** quando os testes dependem dela (`@Sql` para recarregar) |
| **Banco novo por classe** | ✅ | **Lento** — só se a classe exigir estado isolado (migrations destrutivas) |

- **Independência acima de tudo:** cada teste roda **sozinho e em qualquer ordem**. Teste que só passa **depois** de outro (`@TestMethodOrder`, "criar → ler → apagar" em três métodos) é um **smell** (`test-patterns`): uma falha derruba os seguintes e o **diagnóstico some**. Se um **fluxo de vários passos** é o objeto do teste, faça **um único teste** com os passos.
- **Seeds de migration não determinísticas** (`ORDER BY RAND()` — `flyway-migrations`): **nunca assert** sobre elas; use apenas linhas que **a migration insere de forma explícita**, ou os dados que o **teste cria**.
- **Execução em paralelo** (`junit.jupiter.execution.parallel.enabled`) com banco compartilhado exige **isolamento total dos dados** (prefixo/tenant por teste); **comece sem paralelismo** e meça.

## 4. Testar as migrations (Flyway)

As migrations rodam **no startup do contexto** contra o banco do container — **todo teste de integração já as valida em um banco vazio**. Cubra também:
```java
@Test
void allMigrationsWereAppliedSuccessfully() {
    var failed = jdbc.queryForObject("SELECT count(*) FROM flyway_schema_history WHERE success = 0", Integer.class);

    assertThat(failed).isZero();
}
```
- **Migration sobre banco já populado** (o cenário real de produção): suba o container, aplique as migrations **até a versão N-1**, insira dados representativos, aplique a **N** e verifique (use `Flyway.configure().target("N-1")` programaticamente). É o teste que pega `NOT NULL` sem default em tabela com dados (`flyway-migrations`: expand → contract).
- **Compatibilidade com a versão anterior da aplicação** (rolling update): quando relevante, rode os testes da versão **N-1** contra o schema **N**.

## 5. Velocidade — cache de contexto do Spring

Subir um contexto Spring é o maior custo. O Spring **reaproveita** o `ApplicationContext` entre classes de teste **com a mesma configuração**. Para manter o cache:
- **Uma classe base** única (como acima); **evite variar** `@MockitoBean`, `@TestPropertySource`, `@ActiveProfiles` e `@Import` entre classes — **cada combinação nova cria um contexto novo**.
- **Não use `@DirtiesContext`** (descarta o contexto) a não ser que **inevitável**; prefira limpar o estado.
- **Poucos "formatos" de contexto** na suíte (um padrão + uns poucos específicos).
- Mantenha os testes **lentos em poucos casos** e **deixe a regra no unit test**; a pirâmide é o que mantém a suíte rápida.
- Se a suíte passar de ~5–10 min, considere **separar por tag** ou por fase (abaixo) e paralelizar **no CI** por módulo/job, não dentro da JVM.

## 6. Outros containers (o mesmo padrão: singleton + `@DynamicPropertySource`/`@ServiceConnection`)

| Dependência | Container | Skill |
|---|---|---|
| Kafka | `org.testcontainers.kafka.KafkaContainer` | `kafka` |
| RabbitMQ | `org.testcontainers.rabbitmq.RabbitMQContainer` | `rabbitmq` |
| Redis (cache) | `GenericContainer("redis:7")` | `caching` |
| AWS (S3, SQS, SNS, DynamoDB…) | `LocalStackContainer` | `localstack` |
| API externa HTTP | **WireMock** (`@AutoConfigureWireMock` ou container) | `service-communication`, `resilience` |
| Falhas de rede | **Toxiproxy** | `resilience` |

Para vários containers, **um só** `abstract` com todos estáticos (ou `@TestConfiguration` com `@ServiceConnection` em cada `@Bean`), **iniciados uma vez**. Só suba os que a suíte usa.
- **Assíncrono → Awaitility, nunca `Thread.sleep`:** `await().atMost(Duration.ofSeconds(15)).untilAsserted(() -> assertThat(...))`.
- **Duplicata e DLQ** em fluxos de mensagem (`messaging`, `idempotency`): publique 2×, aguarde, afirme **um** efeito.

## 7. Divisão unit × integração (opcional)

O padrão do pack é **uma fase só** (`./mvnw verify` roda tudo — `maven-config`, sem Failsafe) — **simples e suficiente** enquanto a suíte for rápida. Quando a integração ficar lenta:
- **Marque por tag** (`@Tag("integration")` na classe base) e use `-Dgroups`/`excludedGroups` no surefire para rodar o **feedback rápido** (unit) localmente e **tudo no CI**; **ou**
- use o **Failsafe** (`*IT`/`*IntegrationTest` na fase `integration-test`/`verify`) — mas lembre da **cobertura**: com duas fases, o JaCoCo precisa de `prepare-agent-integration` e merge dos `.exec` (`test-coverage`).
Decida **por medição**, não por antecipação.

## 8. O que cobrir (e o que não)

**Cubra:** o **caminho feliz de cada endpoint crítico**; o **contrato de erro** (400/404/409/422/403); **segurança** (sem token, role, IDOR); **persistência** (constraints, transações, `@Query`, paginação); **migrations**; a **integração com cada dependência** (mensagem publicada e consumida, cache, arquivo no S3/LocalStack).
**Não cubra aqui:** regras de negócio ramificadas (unit — `testing`), todas as combinações de validação (slice/unit), getters/mapeamentos triviais.

## 9. Anti-patterns

- **H2/banco embutido** no lugar do banco real.
- **Um container por classe** (suíte lenta) ou container parado ao fim de cada classe.
- **`@Transactional` no teste com HTTP real** (rollback inútil).
- **Testes dependentes de ordem/estado** de outros testes; dados globais compartilhados.
- **Assert sobre seed aleatória**; **`Thread.sleep`**; **porta fixa**; **`latest` na imagem**.
- **`@DirtiesContext` e variações de `@MockitoBean`** por classe (destroem o cache de contexto).
- **Testar tudo por HTTP** (pirâmide invertida) — lento e frágil.
- **`application.yml` de teste diferente da produção** (prova outra aplicação).
- **Asserts só de status code**; ignorar o **contrato de erro**.
- **Credenciais reais** nos testes.

---

## Regras principais

- **Banco real em container, mesma versão major da produção** — nunca H2; **tag fixa**, nunca `latest`.
- **Container singleton** na **classe base** (`static {}` + `@DynamicPropertySource`, ou `@ServiceConnection`), **sem** `@Container`/`@Testcontainers` aqui; reuso entre execuções só localmente.
- **`@SpringBootTest(RANDOM_PORT)` + REST Assured**; `application.yml` de teste = cópia completa do principal.
- **Cada teste cria e limpa os próprios dados** (UUID), é **independente e sem ordem**; `@Transactional` **não** isola testes com HTTP real; nunca assert sobre seed aleatória.
- **Prove o contrato de erro e a segurança** (token real do usuário de teste, IDOR, sem token, role) e a **persistência/migrations** (inclusive sobre banco populado).
- **Poucos testes de integração, nos caminhos críticos**; a regra de negócio fica nos unit tests.
- **Preserve o cache de contexto** (uma base, sem `@DirtiesContext`, poucas variações de mock/propriedade).
- **Awaitility, nunca `sleep`**; WireMock/Toxiproxy/LocalStack/Kafka/RabbitMQ pelo mesmo padrão singleton.
- Divida unit × integração (tag/Failsafe) **só quando medir** lentidão — e ajuste a cobertura (`test-coverage`).
- **Sem Lombok** — deliberado.
