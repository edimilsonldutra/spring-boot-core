---
name: contract-testing
description: Contract testing entre microsserviços — Pact (consumidor, verificação no provedor, provider states, broker, can-i-deploy), Spring Cloud Contract, contratos de eventos, breaking change do OpenAPI (oasdiff), tolerant reader e integração no CI. Use quando mudar uma API ou um evento consumido por outro serviço sem quebrá-lo.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../testing/SKILL.md`](../testing/SKILL.md), [`../microservices/SKILL.md`](../microservices/SKILL.md) e [`../service-communication/SKILL.md`](../service-communication/SKILL.md). Para eventos: `messaging`. Para o pipeline: `github-actions-aws`.

# Contract testing

## O problema

Em microsserviços, **o serviço A depende do formato que o serviço B devolve**. Como saber, **antes** do deploy, que uma mudança em B **não quebra** A?
- **Testes end-to-end** (subir tudo e testar o fluxo): **lentos, frágeis, caros**, difíceis de depurar, exigem todos os serviços no ar e **só acusam o erro tarde**. Não escalam com o número de serviços.
- **Mocks** do outro serviço nos testes do consumidor: rápidos, mas **mentem** — o mock é o que **você acha** que o provedor devolve; quando o provedor muda, o mock **continua verde** e a produção quebra. É o clássico "passou nos testes, quebrou em produção".
- **Mudança "compatível" por inspeção visual:** ninguém lembra de **todos** os consumidores.

**Contract testing** captura **o que o consumidor realmente usa** em um **contrato executável**, e **verifica o provedor contra esse contrato** — **cada lado testado isoladamente, sem subir o outro**, e o contrato é a prova de compatibilidade. É o que torna possível o **deploy independente** (`microservices`: o teste de independência).

```
Consumidor (lending)                    Provedor (catalog)
  teste contra um mock gerado  ──►  CONTRATO  ◄──  teste que reproduz as requests do contrato
  (gera o contrato)                  (Pact)         contra o provedor REAL e verifica as respostas
```

## Ferramentas — Pact × Spring Cloud Contract

| | **Pact** | **Spring Cloud Contract (SCC)** |
|---|---|---|
| Quem escreve o contrato | O **consumidor** (consumer-driven): "isto é o que **eu** uso" | O **provedor** (DSL/YAML em `src/test/resources/contracts`) |
| Linguagens | **Poliglota** (Java, JS, Go, .NET, Python…) | **JVM/Spring** (suporte a clientes não-JVM é limitado) |
| Distribuição | **Pact Broker / PactFlow** (publica contratos, versiona, **`can-i-deploy`**) | O provedor publica um **stubs JAR** (WireMock) em um repositório de artefatos |
| Verificação no provedor | O provedor **reproduz** as interações do pact | O provedor **gera testes** a partir do contrato |
| Para o consumidor | Mock server do próprio Pact | **Stub Runner** sobe os stubs do provedor |
| Escolha quando | **Vários times**, stack mista, quer o **consumidor** guiando a evolução, e o **`can-i-deploy`** como gate | **Tudo Spring**, o provedor controla o contrato e **quer entregar stubs** prontos |

**Padrão do pack: Pact** (consumer-driven, com broker e `can-i-deploy`) para APIs entre **times**; SCC quando é um ecossistema Spring fechado em que o provedor dita o contrato. **Escolha uma** por par provedor/consumidor.

> **Versões:** Pact JVM e Spring Cloud Contract mudam de API entre versões. Os trechos mostram a **estrutura**; **confirme os nomes e artifacts na versão resolvida** (Context7, `maven-config`).

---

## 1. Pact — o consumidor escreve o contrato

```xml
<dependency>
    <groupId>au.com.dius.pact.consumer</groupId>
    <artifactId>junit5</artifactId>
    <version>${pact.version}</version>
    <scope>test</scope>
</dependency>
```
(`pact.version` em `<properties>` — fora do BOM do Boot.) O teste do **consumidor** (`library-lending`, que chama o `library-catalog`) define a **interação esperada** e roda o **seu client real** contra um **mock server** do Pact; ao passar, **gera o arquivo do contrato**.

```java
@ExtendWith(PactConsumerTestExt.class)
@PactTestFor(providerName = "library-catalog", pactVersion = PactSpecVersion.V4)
class CatalogClientPactTest {

    @Pact(consumer = "library-lending")
    V4Pact bookIsAvailable(PactDslWithProvider builder) {
        return builder
                .given("book 42 exists and is available")
                .uponReceiving("a request for book 42")
                .path("/api/book/v1/42")
                .method("GET")
                .willRespondWith()
                .status(200)
                .headers(Map.of("Content-Type", "application/json"))
                .body(new PactDslJsonBody()
                        .integerType("id", 42)
                        .stringType("title", "Clean Code")
                        .booleanType("available", true))
                .toPact(V4Pact.class);
    }

    @Test
    @PactTestFor(pactMethod = "bookIsAvailable")
    void readsAnAvailableBook(MockServer mockServer) {
        var catalog = new CatalogGateway(CatalogClients.create(mockServer.getUrl()));

        assertThat(catalog.isAvailable(new BookId(42L))).isTrue();
    }

    @Pact(consumer = "library-lending")
    V4Pact bookDoesNotExist(PactDslWithProvider builder) {
        return builder
                .given("book 99 does not exist")
                .uponReceiving("a request for a missing book")
                .path("/api/book/v1/99")
                .method("GET")
                .willRespondWith()
                .status(404)
                .toPact(V4Pact.class);
    }

    @Test
    @PactTestFor(pactMethod = "bookDoesNotExist")
    void translatesNotFoundToADomainException(MockServer mockServer) {
        var catalog = new CatalogGateway(CatalogClients.create(mockServer.getUrl()));

        assertThrows(BookNotFoundException.class, () -> catalog.isAvailable(new BookId(99L)));
    }
}
```
- **Use o client de produção** (`CatalogGateway` + o `RestClient` do `service-communication`) — o teste prova que **o seu código real** entende a resposta, não um mock paralelo.
- **`given(...)` é o *provider state*:** "livro 42 existe e está disponível" — a pré-condição que o provedor deve montar para reproduzir a interação.
- **Matchers por tipo** (`integerType`, `stringType`, `booleanType`) em vez de valores exatos: o contrato exige **forma e tipo**, não que o título seja exatamente "Clean Code" — **contratos frágeis a valores** quebram sem motivo.
- **Escreva só o que o consumidor USA.** Se o `lending` só lê `id` e `available`, o contrato **só** os lista — o `catalog` fica **livre** para adicionar/alterar o resto (**tolerant reader** — `service-communication`). Um contrato que lista **todos** os campos "por completude" trava a evolução do provedor à toa.
- Cubra **os casos de erro** que o consumidor trata (404, 409, 5xx) — o contrato de erro também é contrato.
- **O contrato não é teste de regra de negócio** do provedor: só **formato e semântica de uso** (status, headers, forma do JSON).

## 2. Pact — o provedor verifica

```xml
<dependency>
    <groupId>au.com.dius.pact.provider</groupId>
    <artifactId>junit5spring</artifactId>
    <version>${pact.version}</version>
    <scope>test</scope>
</dependency>
```
O provedor **sobe a própria aplicação** (com banco em container — `integration-testing`) e o Pact **reexecuta cada interação** dos contratos dos consumidores contra ela:
```java
@Provider("library-catalog")
@PactBroker
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class CatalogProviderPactTest {

    @LocalServerPort
    private int port;

    @Autowired
    private BookRepository repository;

    @BeforeEach
    void target(PactVerificationContext context) {
        context.setTarget(new HttpTestTarget("localhost", port));
    }

    @TestTemplate
    @ExtendWith(PactVerificationInvocationContextProvider.class)
    void verifyPact(PactVerificationContext context) {
        context.verifyInteraction();
    }

    @State("book 42 exists and is available")
    void bookExists() {
        repository.save(Books.available(42L, "Clean Code"));
    }

    @State("book 99 does not exist")
    void bookMissing() {
        repository.deleteById(99L);
    }
}
```
(Configure o broker por properties/variáveis de ambiente — `pactbroker.url`, token — **o token vem do Secret do CI**, nunca do código.)
- Cada **`@State`** **monta a pré-condição** no banco (dados de teste). Mantenha-os **pequenos e determinísticos**.
- A verificação roda **no pipeline do provedor, a cada build** — se alguém renomeia `available` para `isAvailable`, **o build do `catalog` quebra** com a mensagem "o consumidor `library-lending` espera `available`", **antes** de chegar a produção.
- **Segurança nos contratos:** como o provedor exige token, use um **filtro de teste** ou perfil que **aceite um token de teste** (`@MockitoBean JwtDecoder` ou configuração de teste) — não desligue a segurança em produção; não coloque tokens reais no contrato.

## 3. Pact Broker e `can-i-deploy` — o gate do deploy

O **Pact Broker** (open source) ou o **PactFlow** (SaaS) **guarda os contratos e os resultados de verificação**, versionados:
1. **CI do consumidor:** roda os testes de contrato e **publica o pact** no broker, marcado com a **versão (o `git sha`)** e a **branch**.
2. **CI do provedor:** busca os pacts dos consumidores relevantes (os da `main` e os **implantados** em cada ambiente — `consumerVersionSelectors`) e **publica o resultado da verificação**.
3. **Webhook:** quando um **contrato novo/alterado** é publicado, o broker **dispara o build do provedor** para verificá-lo imediatamente.
4. **Gate do deploy (`can-i-deploy`):** antes de implantar **qualquer** serviço, o pipeline pergunta ao broker:
```bash
pact-broker can-i-deploy --pacticipant library-lending --version $GITHUB_SHA --to-environment production
pact-broker record-deployment --pacticipant library-lending --version $GITHUB_SHA --environment production
```
**"Esta versão do `lending` é compatível com **as versões que estão hoje em produção** dos serviços de que ela depende?"** Se **não**, o deploy **é bloqueado**. Após implantar, **`record-deployment`** registra o que está em cada ambiente — é o que alimenta o `can-i-deploy` seguinte. Integre no `github-actions-aws`/`argocd` (um passo **antes** do `promote`/deploy de produção).

**Evolução sem quebra (consumidor e provedor desacoplados):** *adicionar* um campo no provedor **não** quebra nenhum contrato (tolerant reader). *Remover/renomear* um campo que **algum consumidor usa** **quebra a verificação** — o time do provedor **vê quem depende** e coordena (versão nova `/v2`, deprecação — `service-communication`). Para **remover**: primeiro faça o consumidor **parar de usar** o campo (publica contrato novo), **depois** o provedor remove — o `can-i-deploy` garante a ordem.

---

## 4. Spring Cloud Contract — o provedor escreve o contrato

O provedor mantém **contratos** (YAML/Groovy) em `src/test/resources/contracts/`:
```yaml
description: should return an available book
request:
  method: GET
  url: /api/book/v1/42
response:
  status: 200
  headers:
    Content-Type: application/json
  body:
    id: 42
    title: Clean Code
    available: true
  matchers:
    body:
      - path: $.title
        type: by_type
```
O **plugin do SCC** (Maven/Gradle) **gera testes** do provedor a partir dos contratos (você implementa uma **base class** que monta o estado, equivalente ao `@State`) e **publica um stubs JAR** com os WireMock stubs. O **consumidor** usa o **Stub Runner** para subir os stubs reais:
```java
@SpringBootTest
@AutoConfigureStubRunner(ids = "br.com.padrao:library-catalog:+:stubs:8090", stubsMode = StubRunnerProperties.StubsMode.LOCAL)
class CatalogGatewayContractTest {
    // o client aponta para http://localhost:8090 e fala com os stubs gerados do contrato REAL do provedor
}
```
Vantagem: o **provedor controla o contrato** e entrega **stubs prontos**. Limitação: o contrato nasce do **provedor** (não do que o consumidor realmente usa — risco de contratos "completos demais") e é **centrado em JVM**. Use `stubsMode = CLASSPATH`/`REMOTE` (repositório de artefatos) conforme o fluxo; **fixe a versão dos stubs** (evite `+` em CI — reprodutibilidade).

---

## 5. Contratos de mensagens (eventos)

Eventos têm contrato também — o **schema do evento** que o produtor publica e o consumer lê (`messaging`: "evolução só compatível"). Quebrar um evento é **pior** que quebrar uma API (consumidores **assíncronos**, às vezes desconhecidos, e mensagens antigas ainda na fila).
- **Pact (mensagens):** o **consumidor** declara a mensagem que **espera receber** (`@Pact` de mensagem V4 / `MessagePactBuilder`, com `withContent(new PactDslJsonBody()...)`) e o teste prova que **seu listener** a processa; o **produtor** verifica que **realmente gera** uma mensagem que casa (`@PactVerifyProvider("a BookCreated event")` retornando o JSON produzido pelo código real de publicação).
- **SCC (mensagens):** contratos com `input`/`outputMessage` e *stubs de mensagem* (suporta Kafka/RabbitMQ).
- **Schema Registry** (Kafka — `kafka`) com **regras de compatibilidade** (`BACKWARD`/`FULL`) **impede** o produtor de registrar um schema incompatível — outra forma (complementar) de contrato para eventos.
- Teste mínimo, **sem Pact**: **um JSON de exemplo versionado** (`BookCreated.v1.json`) que **desserializa** no record do consumidor **e** é o que o produtor gera (assert com o mesmo arquivo nos dois lados).
- **Eventos antigos convivem:** teste que o consumer atual lê **mensagens da versão anterior** (campo novo ausente → `null`/default).

## 6. Compatibilidade do OpenAPI (a rede de segurança complementar)

Além dos contratos dos consumidores **conhecidos**, detecte **breaking changes na sua própria API** pelo **diff do OpenAPI**: o `springdoc` gera `/v3/api-docs` (`swagger`); no CI, **gere o JSON** e compare com o da `main` usando o **`oasdiff`** (ou `openapi-diff`):
```bash
oasdiff breaking origin-main/openapi.json openapi.json --fail-on ERR
```
Pega: campo/endpoint **removido**, tipo mudado, parâmetro obrigatório novo, enum encolhido — **mesmo sem consumidor cadastrado no broker**. Falhe o PR em **breaking change** a menos que seja uma **nova versão** de propósito. Pact/SCC cobrem **quem usa o quê**; o diff cobre **tudo que a API promete**.

## 7. Regras de um bom contrato

1. **Mínimo necessário** (só o que o consumidor usa) + **matchers de tipo/formato**, não valores fixos.
2. **Cubra o erro tratado** (404/409/422/503), além do caminho feliz.
3. **Provider states pequenos e determinísticos**; nenhum dado real/PII.
4. **Sem lógica de negócio** no contrato — só **forma e semântica de uso**.
5. **Tolerant reader** no consumidor (Jackson ignora campos desconhecidos — `web-config`), **Postel**: "seja liberal no que aceita, conservador no que envia".
6. **Versão = `git sha`; ambiente registrado** (`record-deployment`); contratos **da branch** testados antes do merge.
7. O contrato **vive junto do código do consumidor** (gerado pelo teste), e o resultado no broker.
8. **Mudou o contrato → conversa entre os times** (o contrato é o ponto de colaboração, não de burocracia).

## 8. Onde encaixa na pirâmide de testes de microsserviços

| Camada | Quantidade | Prova |
|---|---|---|
| Unit (regra do serviço) | **Muitos** | Lógica de negócio (`testing`) |
| Slice/integração do serviço (banco real, WireMock) | Vários | O serviço funciona sozinho (`integration-testing`) |
| **Contract tests** | **Um por interação relevante** | **Serviços entendem uns aos outros** (esta skill) |
| End-to-end (ambiente integrado) | **Pouquíssimos** (só *smoke* dos fluxos críticos) | A plataforma está de pé |

Contract tests **substituem** a maior parte dos e2e entre serviços: rápidos, determinísticos, **por serviço**, e apontam **exatamente** quem quebrou o quê.

## 9. Anti-patterns

- **Contrato com todos os campos e valores exatos** (frágil, trava o provedor).
- **Consumidor que não usa o client de produção** no teste de contrato (prova um mock, não o código real).
- **Provider states com dados reais**, gigantes ou dependentes de ordem.
- **Contrato como teste funcional do provedor** (regra de negócio no contrato).
- **Não rodar a verificação do provedor no CI**, ou rodá-la só ocasionalmente; **deploy sem `can-i-deploy`**.
- **Contratos só no happy path.**
- **Eventos sem teste de contrato/compatibilidade** (a quebra silenciosa mais cara).
- Usar **SCC e Pact** para o mesmo par (duas fontes de verdade).
- **Tokens/segredos reais** em contratos ou nos states.
- Achar que contract test **dispensa** testes de integração do provedor (cada um prova uma coisa).

---

## Regras principais

- **Contract testing no lugar de e2e entre serviços:** cada lado testado isolado, o **contrato** prova a compatibilidade — requisito do **deploy independente**.
- **Pact** (consumer-driven, broker, `can-i-deploy`) para APIs entre times; **SCC** para ecossistema Spring fechado em que o provedor dita o contrato; **uma ferramenta por par**. Confirme APIs/artifacts na versão.
- Consumidor: teste **com o client real de produção**; contrato **mínimo** (só o que usa), **matchers de tipo**, inclui os **erros tratados**.
- Provedor: **verificação a cada build** (app real + banco em container), **provider states** pequenos e determinísticos; segurança de teste **sem** afrouxar produção.
- **Pact Broker/PactFlow**: publicar com `git sha` + branch; webhook dispara a verificação; **`can-i-deploy` antes de todo deploy** e **`record-deployment` depois**.
- Remover/renomear campo: primeiro o consumidor **para de usar**, depois o provedor remove; **mudanças só aditivas** na versão corrente; **tolerant reader**.
- **Eventos têm contrato**: Pact/SCC de mensagens, Schema Registry com compatibilidade, e JSON de exemplo versionado; teste de **mensagens antigas**.
- **`oasdiff` no CI** para breaking changes do OpenAPI, complementar aos contratos.
- Pirâmide: **poucos e2e (smoke)**, muitos unit, contract tests por interação.
- Sem tokens/dados reais em contratos; token do broker no Secret do CI.
- **Sem Lombok** — deliberado.
