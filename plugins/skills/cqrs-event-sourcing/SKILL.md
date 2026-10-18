---
name: cqrs-event-sourcing
description: CQRS e Event Sourcing no Spring Boot — três níveis de CQRS (do mais simples ao store separado), projeções idempotentes e reconstruíveis, read-your-writes, event store com optimistic concurrency, snapshots, upcasting, LGPD, Axon e quando NÃO usar. Use quando leitura e escrita tiverem necessidades muito diferentes ou o histórico precisar ser a fonte da verdade.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../microservices/SKILL.md`](../microservices/SKILL.md), [`../ddd-hexagonal/SKILL.md`](../ddd-hexagonal/SKILL.md), [`../messaging/SKILL.md`](../messaging/SKILL.md), [`../transactional-outbox/SKILL.md`](../transactional-outbox/SKILL.md) e [`../idempotency/SKILL.md`](../idempotency/SKILL.md). **Pré-requisitos reais:** projeções e consumers precisam ser idempotentes e os eventos publicados por outbox.

# CQRS e Event Sourcing

São **dois padrões independentes** que se combinam bem, e **ambos custam caro**. A regra de partida: **a maioria dos serviços não precisa de nenhum dos dois.** Um CRUD com `spring-data-jpa` resolve a maioria dos casos. Adote **CQRS** quando **leitura e escrita têm necessidades muito diferentes**; adote **Event Sourcing** só com **justificativa forte** (auditoria legal, histórico temporal central ao domínio).

---

## 1. CQRS — Command Query Responsibility Segregation

**Ideia:** separar **comandos** (mudam estado; retornam pouco/nada; validam invariantes) de **consultas** (leem; não mudam nada; retornam DTOs). Em vez de **um modelo** que serve a escrita (normalizado, com regras) **e** a leitura (listas, filtros, joins, relatórios) — e que fica ruim nas duas —, você tem **modelos distintos**, cada um otimizado para o seu papel.

### Por que
- O modelo de **escrita** quer **invariantes**, agregados pequenos, normalização.
- O modelo de **leitura** quer **velocidade**, **denormalização**, vários formatos (tela de busca, dashboard, relatório) — frequentemente **combinando dados de vários serviços** (que, com banco por serviço, **não** se resolve por JOIN — `microservices`).
- A **carga** de leitura costuma ser **ordens de grandeza maior** que a de escrita: escalar/armazenar cada lado de forma independente.

### Os três níveis (escolha o **menor** que resolve)

| Nível | O que é | Custo | Quando |
|---|---|---|---|
| **1. CQRS-lite (mesmo banco)** | Separação **no código**: *command services* (aggregates/regras) e *query services* (projeções `SELECT new ...DTO`, `JdbcClient`, views) sobre as **mesmas tabelas** | **Baixo**; consistência **imediata** | **Quase sempre o suficiente.** Resolve leitura ruim sem infraestrutura nova |
| **2. Tabelas de leitura por evento** | O lado de escrita publica eventos; um **projetor** mantém **tabelas de leitura denormalizadas** (no mesmo ou em outro banco) | Médio; consistência **eventual** | Consultas pesadas/agregadas que não cabem no modelo normalizado; leituras que **cruzam serviços** |
| **3. Store de leitura separado** | O read model vive em tecnologia **diferente** otimizada para consulta: **OpenSearch/Elasticsearch** (busca textual), **DynamoDB/Redis** (acesso por chave em escala — `aws-dynamodb`, `caching`), colunar para relatórios | **Alto**; mais um sistema a operar; consistência eventual | Padrões de leitura que o relacional **não atende** (busca full-text, escala de leitura massiva) |

**Comece no nível 1.** Suba de nível **só quando medir** que o anterior não basta (`jvm-performance`: queries/índices/N+1 primeiro).

### Nível 1 — CQRS-lite em Spring (o que quase todo mundo precisa)

```
application/
├── command/   BookCommandService (cria/atualiza: regras, @Transactional, aggregates)
└── query/     BookQueryService   (somente leitura: projeções DTO, @Transactional(readOnly = true))
```
```java
@Service
public class BookQueryService {

    private final JdbcClient jdbc;

    public BookQueryService(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @Transactional(readOnly = true)
    public List<BookSummary> searchByAuthor(String author, int limit) {
        return jdbc.sql("SELECT id, title, author, price FROM books WHERE author = :author ORDER BY title LIMIT :limit")
                .param("author", author)
                .param("limit", limit)
                .query(BookSummary.class)
                .list();
    }
}
```
```java
public record BookSummary(Long id, String title, String author, BigDecimal price) {}
```
A leitura **não passa pelo aggregate/entity** (nem carrega o grafo): vai direto a uma **projeção/record**, com SQL feito para a tela. A escrita continua pelo aggregate com as invariantes. Mesmo banco, **zero consistência eventual**, e a leitura **sem N+1** (`spring-data-jpa`). Isso já é CQRS.

### Níveis 2 e 3 — read model alimentado por eventos

```
[ serviço de escrita ] ──(outbox)──► broker ──► [ projetor ] ──► read model (tabela / OpenSearch / DynamoDB)
        ▲                                                              │
        └──── comandos                                    consultas ───┘
```
**O projetor** é um consumer que **traduz eventos em atualizações do read model**. Regras **inegociáveis**:

1. **Idempotente** (mensagens duplicam — `idempotency`): reaplicar o mesmo evento não corrompe a projeção.
2. **Tolerante a desordem** com **versão**: aplique o evento **só se for mais novo** que o já projetado.
3. **Reconstruível**: o read model é **descartável** — se corromper ou mudar de formato, **apague e reconstrua** reprocessando os eventos (do log do broker com retenção, do event store, ou de um *snapshot* do banco de escrita). **Projete-o para poder ser refeito.**
```java
@Component
public class BookSearchProjector {

    private final JdbcClient jdbc;

    public BookSearchProjector(JdbcClient jdbc) {
        this.jdbc = jdbc;
    }

    @KafkaListener(topics = "library.book.updated.v1")
    @Transactional
    public void on(BookUpdated event) {
        jdbc.sql("""
                INSERT INTO book_search_view (book_id, title, author, price, version)
                VALUES (:id, :title, :author, :price, :version)
                ON DUPLICATE KEY UPDATE
                    title = IF(VALUES(version) > version, VALUES(title), title),
                    author = IF(VALUES(version) > version, VALUES(author), author),
                    price = IF(VALUES(version) > version, VALUES(price), price),
                    version = GREATEST(version, VALUES(version))
                """)
                .param("id", event.id()).param("title", event.title())
                .param("author", event.author()).param("price", event.price())
                .param("version", event.version())
                .update();
    }
}
```
(MySQL; outros bancos usam `ON CONFLICT ... DO UPDATE ... WHERE excluded.version > book_search_view.version` — `flyway-migrations`.) O **upsert condicionado à versão** torna a projeção **idempotente e à prova de desordem** numa só instrução. O evento **carrega a versão do agregado** (`aggregate.version`), que o lado de escrita incrementa (`@Version`).

### Consistência eventual e "read-your-writes"

Depois de um comando, o read model **ainda não reflete** a mudança por milissegundos/segundos. O usuário cria um livro, recarrega a lista… e ele **não aparece**. Estratégias:
- **Devolver o resultado no próprio comando** (o `BookDTO` criado) e deixar a UI **atualizar otimisticamente** — a lista só confirma depois.
- **Devolver a `version`** no comando; a query aceita `?minVersion=` e **espera/retenta** até o projetor alcançar (ou responde `202`/`409` "ainda processando").
- **Ler do lado de escrita** as consultas "do próprio usuário logo após escrever" (uma exceção pontual).
- **Comunique o atraso** ao usuário/UX (a "janela" é quase sempre curta — **meça-a**: lag do consumer, `kafka`/`messaging`).
- **Nunca** use o read model eventual para uma **decisão que exige o valor exato agora** (saldo antes de debitar) — a decisão consulta o lado de **escrita** (fonte de verdade).

### Quando NÃO usar CQRS (níveis 2–3)
CRUD simples; carga de leitura baixa; equipe pequena sem experiência com mensageria; quando a **consistência imediata** é requisito; quando o nível 1 já resolve. **Custos:** consistência eventual (UX e testes mais difíceis), **duplicação** de modelo e de lógica, projetores a operar e **reconstruir**, mais monitoramento (lag), mais pontos de falha.

---

## 2. Event Sourcing

**Ideia:** em vez de guardar o **estado atual** (a linha da conta com `balance = 70`), guarde a **sequência de eventos** que levou até ele (`AccountOpened`, `Deposited 100`, `Withdrawn 30`). O **estado é derivado**: *reproduzir* os eventos (fold) reconstrói o aggregate. Os eventos são a **fonte de verdade**, **imutáveis** e **append-only**.

| ✅ Ganhos | ❌ Custos |
|---|---|
| **Auditoria total e nativa** (cada mudança, quem/quando/por quê) | **Curva de aprendizado** alta; mudança de mentalidade para o time inteiro |
| **Consultas temporais** ("qual era o saldo em 15/03?") e **reprocessamento** | **Consultas exigem projeções** (CQRS é praticamente obrigatório) |
| **Debug** por reprodução; **novas projeções** a partir do histórico | **Evolução do schema dos eventos** (eles vivem para sempre — upcasting) |
| Integração natural com **eventos** para outros serviços | **LGPD/direito ao esquecimento** conflita com imutabilidade (crypto-shredding) |
| Resolve o *dual write* (o evento **é** o estado) | Complexidade operacional (snapshots, replays, event store) e **ferramentas menos comuns** |

**Use Event Sourcing apenas quando** o histórico **é o domínio** (financeiro/contábil, auditoria regulatória, rastreabilidade, colaboração/versões, domínios complexos de estados) — **não** "porque eventos são legais". **Para auditoria simples**, uma tabela de **histórico/auditoria** ao lado do estado atual (ou *change data capture*) é **muito mais barata**. **Não** é "armazenar tudo num Kafka" nem "publicar eventos de integração" (isso é `messaging`/outbox sem ES).

### Event store (relacional)

```sql
CREATE TABLE IF NOT EXISTS `event_store` (
  `aggregate_id` char(36)     NOT NULL,
  `version`      bigint       NOT NULL,
  `event_type`   varchar(120) NOT NULL,
  `payload`      json         NOT NULL,
  `occurred_at`  datetime(6)  NOT NULL,
  PRIMARY KEY (`aggregate_id`, `version`)
);
```
A **chave `(aggregate_id, version)`** é o coração: ela garante a **ordem por aggregate** e dá **optimistic concurrency** — dois comandos concorrentes no mesmo aggregate tentam gravar a **mesma versão**, e o banco **rejeita** o segundo (`DuplicateKey`), que **relê e tenta de novo**. Eventos **nunca** são atualizados nem apagados.

### Aggregate com eventos (rehidratação)

```java
public sealed interface AccountEvent permits AccountOpened, MoneyDeposited, MoneyWithdrawn {}

public record AccountOpened(String accountId, String owner) implements AccountEvent {}
public record MoneyDeposited(String accountId, BigDecimal amount) implements AccountEvent {}
public record MoneyWithdrawn(String accountId, BigDecimal amount) implements AccountEvent {}
```
```java
public class Account {

    private String id;
    private BigDecimal balance = BigDecimal.ZERO;
    private long version;
    private final List<AccountEvent> uncommitted = new ArrayList<>();

    public static Account open(String id, String owner) {
        var account = new Account();
        account.apply(new AccountOpened(id, owner));
        return account;
    }

    public static Account rehydrate(List<AccountEvent> history) {
        var account = new Account();
        history.forEach(account::mutate);
        account.version = history.size();
        return account;
    }

    public void withdraw(BigDecimal amount) {
        if (amount.signum() <= 0) throw new IllegalArgumentException("amount must be positive");
        if (balance.compareTo(amount) < 0) throw new InsufficientFundsException(id);
        apply(new MoneyWithdrawn(id, amount));
    }

    private void apply(AccountEvent event) {
        mutate(event);
        uncommitted.add(event);
    }

    private void mutate(AccountEvent event) {
        switch (event) {
            case AccountOpened e -> this.id = e.accountId();
            case MoneyDeposited e -> this.balance = balance.add(e.amount());
            case MoneyWithdrawn e -> this.balance = balance.subtract(e.amount());
        }
    }

    public List<AccountEvent> pullUncommitted() {
        var pulled = List.copyOf(uncommitted);
        uncommitted.clear();
        return pulled;
    }

    public long version() {
        return version;
    }
}
```
- **A regra valida o estado atual e produz um evento** (`withdraw` checa o saldo derivado e emite `MoneyWithdrawn`); **`mutate` só aplica**, **sem regra e sem efeito colateral** (senão a rehidratação refaria efeitos).
- `switch` exaustivo sobre `sealed` (`java-modern-features`): adicionar um evento sem tratá-lo **quebra a compilação**.
- Eventos de domínio no **passado**, imutáveis (records), **versionados** (campo/tipo) e **compatíveis**.

### Salvar e carregar

```java
@Service
public class AccountEventStore {

    private final JdbcClient jdbc;
    private final JsonMapper jsonMapper;

    // construtor omitido

    public Account load(String accountId) {
        var history = jdbc.sql("SELECT event_type, payload FROM event_store WHERE aggregate_id = :id ORDER BY version")
                .param("id", accountId)
                .query((rs, n) -> deserialize(rs.getString("event_type"), rs.getString("payload")))
                .list();
        if (history.isEmpty()) throw new AccountNotFoundException(accountId);
        return Account.rehydrate(history);
    }

    @Transactional
    public void append(String accountId, long expectedVersion, List<AccountEvent> events) {
        var version = expectedVersion;
        try {
            for (var event : events) {
                version++;
                jdbc.sql("INSERT INTO event_store (aggregate_id, version, event_type, payload, occurred_at) VALUES (:id, :version, :type, :payload, :at)")
                        .param("id", accountId).param("version", version)
                        .param("type", event.getClass().getSimpleName())
                        .param("payload", jsonMapper.writeValueAsString(event))
                        .param("at", Timestamp.from(Instant.now()))
                        .update();
            }
        } catch (DuplicateKeyException concurrent) {
            throw new ConcurrentModificationException("Account " + accountId + " was modified concurrently");
        }
    }
}
```
O **comando** carrega o aggregate, executa o método de negócio e faz `append(id, aggregate.version(), aggregate.pullUncommitted())` — tudo em **uma transaction**. O conflito de versão vira **retry** (ou `409`). **Publique os eventos** para os outros serviços/projeções pela **outbox na mesma transaction** (`transactional-outbox`) — ou, com CDC (Debezium), lendo o próprio `event_store`.

**Ordenação global para projeções:** a ordem **por aggregate** vem da `version`. Se projeções precisam de uma **ordem global**, uma coluna `AUTO_INCREMENT`/sequência **pode se tornar visível fora de ordem** (transactions concorrentes confirmam em ordem diferente da dos ids) — projetores que "leem até o maior id" podem **pular** eventos. Prefira projetar **a partir dos eventos publicados** (broker/CDC) com consumers por aggregate (chave de partição = `aggregateId`), em vez de varrer a tabela por id.

### Snapshots, upcasting e LGPD

- **Snapshots:** carregar 50 mil eventos para cada comando é caro. Grave um **snapshot** do estado a cada N eventos (ex.: 100) e rehidrate de **snapshot + eventos posteriores**. É uma **otimização**, não fonte de verdade (descartável).
- **Evolução dos eventos (upcasting):** eventos antigos **nunca** mudam. Quando o schema evolui (campo novo/renomeado), um **upcaster** converte `v1 → v2` **na leitura**, antes de chegar ao aggregate. Prefira **mudanças aditivas** (campo opcional novo — `messaging`). Um evento com tipo errado/inválido no histórico é um problema **permanente** — projete-os com cuidado.
- **LGPD / direito ao esquecimento:** como os eventos são imutáveis, **não dá para "apagar" o dado pessoal**. Estratégias: **não coloque PII nos eventos** (guarde-a em outra tabela por referência, que **pode** ser apagada), ou **crypto-shredding** (PII cifrada no evento com uma **chave por titular**; "esquecer" = **destruir a chave**). **Decida isto antes de gravar o primeiro evento.**
- **Correções:** nunca edite/delete um evento errado — publique um **evento compensatório** (`MoneyDepositCorrected`).

### Ferramentas

**Axon Framework** (+ **Axon Server** como event store/message router) dá **aggregates, event store, sagas, projeções, upcasting, snapshots e testes** prontos em Spring Boot — **reduz muito** o esforço de ES/CQRS, ao custo de **adotar o framework (e seu servidor)** e acoplar-se a ele. **EventStoreDB (Kurrent)** é um banco feito para ES. Um **event store relacional próprio** (acima) é viável para **poucos aggregates** e equipes que querem controle; para **muitos aggregates/times**, considere o Axon. **Kafka como event store primário** não é recomendado (carregar o histórico de **um** aggregate é ineficiente; serve melhor como **barramento** de integração).

---

## 3. Testes

- **Aggregate (com ES):** o teste **dado/quando/então** em termos de eventos, **sem banco**: *dado* `[AccountOpened, MoneyDeposited(100)]`, *quando* `withdraw(130)`, *então* lança `InsufficientFundsException`; *quando* `withdraw(30)`, *então* emite `MoneyWithdrawn(30)`. Testes de domínio **rápidos e legíveis** (a grande vantagem — `ddd-hexagonal`).
- **Concorrência do event store:** duas gravações na mesma versão → **a segunda falha** com conflito (banco real em container — `integration-testing`).
- **Projetor:** o **mesmo evento 2×** → projeção igual (idempotência); eventos **fora de ordem** (v3 antes de v2) → estado final correto; **reconstruir** a projeção do zero a partir do histórico e comparar com a projeção incremental.
- **Consistência eventual:** teste que, após o comando, a query **eventualmente** reflete (Awaitility — **nunca `Thread.sleep`**) e que o fluxo de **read-your-writes** funciona.
- **Contratos dos eventos** (`contract-testing`) e **upcasting** (um evento v1 gravado antigo continua sendo lido).

## 4. Anti-patterns

- **CQRS/ES em CRUD** ("arquitetura de revista"): custo sem benefício.
- **Event Sourcing sem CQRS** (consultas escaneando eventos) ou **sem plano de schema/LGPD**.
- **Read model como fonte de verdade** ou usado para decisões que exigem valor exato.
- **Projetor não idempotente / sem versão** (duplicata ou desordem corrompem a projeção) e **não reconstruível**.
- **`mutate`/`apply` com regra de negócio ou efeito colateral** (a rehidratação reexecuta).
- **Editar/apagar eventos**; PII nos eventos sem estratégia de esquecimento.
- **Confundir evento de ES (estado interno) com evento de integração (contrato público)**: traduza-os.
- **Event store como fila de mensagens** ou Kafka como fonte primária.
- **Ignorar o lag** do read model e a UX da consistência eventual.

---

## Regras principais

- **A maioria dos serviços não precisa de CQRS/ES.** Comece no **CQRS nível 1** (separar *command* e *query* no código, leitura por projeção/DTO, mesmo banco); suba de nível só ao **medir** a necessidade.
- **Escrita** = aggregate com invariantes e `@Transactional`; **leitura** = projeção/record direto no SQL, `@Transactional(readOnly = true)`, **sem passar pelo aggregate**.
- **Read model por eventos:** projetor **idempotente**, **tolerante a desordem (versão)**, **reconstruível**; eventos publicados por **outbox**; monitore o **lag**.
- **Consistência eventual é de verdade:** trate *read-your-writes* (resultado no comando, `version`, UX otimista); decisões que exigem o valor exato consultam o **lado de escrita**.
- **Event Sourcing só quando o histórico é o domínio** (auditoria regulatória, temporal); para auditoria simples, tabela de histórico/CDC. Sempre **com CQRS**.
- **Event store**: `(aggregate_id, version)` como PK (ordem + optimistic concurrency); eventos **imutáveis, no passado, versionados, compatíveis**; `mutate` **puro** (sem regra/efeito); snapshots como otimização; **upcasting** para evoluir; correções por **evento compensatório**.
- **LGPD decidida antes do 1º evento**: sem PII nos eventos ou crypto-shredding.
- **Axon (+Server)** para muitos aggregates/times; event store próprio para poucos; **Kafka não é o event store primário**.
- Teste o aggregate **dado/quando/então por eventos**, a concorrência do store, a **idempotência/desordem/reconstrução** do projetor e a consistência eventual com Awaitility.
- **Sem Lombok** — deliberado.
