---
name: transactional-outbox
description: Publicação confiável de eventos sem dual write — tabela outbox na mesma transaction, relay por polling com SELECT … FOR UPDATE SKIP LOCKED ou CDC com Debezium, consumer idempotente com tabela de processados, migrations, limpeza, ordenação, falhas e testes, para qualquer broker. Use quando um evento nasce de uma mudança no banco e não pode se perder nem duplicar efeito.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../messaging/SKILL.md`](../messaging/SKILL.md), [`../spring-data-jpa/SKILL.md`](../spring-data-jpa/SKILL.md) e [`../flyway-migrations/SKILL.md`](../flyway-migrations/SKILL.md).

# Transactional Outbox

## O problema: dual write

```java
@Transactional
public BookDTO create(BookDTO book) {
    var saved = repository.save(parseObject(book, Book.class));
    publisher.bookCreated(event(saved));
    return parseObject(saved, BookDTO.class);
}
```
Parece correto, mas há **dois sistemas sem transação em comum**: o database e o broker.
- Publica e depois o **commit falha** (ou a transaction faz rollback) → o broker tem um evento de algo que **não existe**.
- O commit funciona e a publicação **falha** (broker fora, timeout, crash entre as duas linhas) → o dado existe e **ninguém é avisado, para sempre**.
Em ambos os casos o sistema fica **silenciosamente inconsistente**. Ordem trocada ou `try/catch` não resolvem.

## A solução: Outbox

Grave o **evento na mesma transaction** da mudança de dados, em uma tabela `outbox_event` **do mesmo database**. Como é **uma** transaction, ou os dois existem ou nenhum. Um processo separado (**publisher/relay**) lê a outbox e publica no broker, marcando como publicado. A entrega vira **at-least-once** — o consumer precisa ser **idempotente** (seção 5).

```
HTTP ──► Service ──[ 1 transaction ]──► tabela books  +  tabela outbox_event
                                                              │
                      OutboxPublisher (polling) / Debezium ◄──┘
                                   │
                                   ▼
                          Broker (Kafka/RabbitMQ/SNS/JMS)  ──►  Consumers (idempotentes)
```

---

## 1. Migration (Flyway)

Em `V{n}__Create_Table_Outbox_Event.sql` (MySQL; `flyway-migrations` tem a tabela de equivalência para os outros databases — PostgreSQL usa `jsonb` e `uuid`, SQL Server `nvarchar(max)`, Oracle `CLOB`):
```sql
CREATE TABLE IF NOT EXISTS `outbox_event` (
  `id`             char(36)     NOT NULL,
  `aggregate_type` varchar(80)  NOT NULL,
  `aggregate_id`   varchar(80)  NOT NULL,
  `event_type`     varchar(120) NOT NULL,
  `payload`        json         NOT NULL,
  `created_at`     datetime(6)  NOT NULL,
  `published_at`   datetime(6)  DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_outbox_pending` (`published_at`, `created_at`)
);
```
- `id` é o **`eventId`** (UUID) que viaja na mensagem — chave de idempotência dos consumers.
- `aggregate_id` vira a **key** (Kafka) / `MessageGroupId` (SQS FIFO) / routing, preservando a ordem por entidade.
- O índice por `(published_at, created_at)` torna rápida a busca dos pendentes.

## 2. Entity e repository

```java
@Entity
@Table(name = "outbox_event")
public class OutboxEvent implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id
    @Column(length = 36)
    private String id;

    @Column(name = "aggregate_type", nullable = false, length = 80)
    private String aggregateType;

    @Column(name = "aggregate_id", nullable = false, length = 80)
    private String aggregateId;

    @Column(name = "event_type", nullable = false, length = 120)
    private String eventType;

    @Column(nullable = false, columnDefinition = "json")
    private String payload;

    @Column(name = "created_at", nullable = false)
    private Instant createdAt;

    @Column(name = "published_at")
    private Instant publishedAt;

    public OutboxEvent() {}

    public static OutboxEvent of(String eventId, String aggregateType, String aggregateId, String eventType, String payload) {
        var event = new OutboxEvent();
        event.id = eventId;
        event.aggregateType = aggregateType;
        event.aggregateId = aggregateId;
        event.eventType = eventType;
        event.payload = payload;
        event.createdAt = Instant.now();
        return event;
    }

    // getters, setters, equals, hashCode
}
```
```java
public interface OutboxEventRepository extends JpaRepository<OutboxEvent, String> {

    @Query(value = "SELECT * FROM outbox_event WHERE published_at IS NULL ORDER BY created_at, id LIMIT :limit FOR UPDATE SKIP LOCKED",
            nativeQuery = true)
    List<OutboxEvent> lockNextBatch(@Param("limit") int limit);

    @Modifying
    @Query("DELETE FROM OutboxEvent e WHERE e.publishedAt IS NOT NULL AND e.publishedAt < :before")
    int deletePublishedBefore(@Param("before") Instant before);
}
```
- **`FOR UPDATE SKIP LOCKED`** (MySQL 8+, PostgreSQL 9.5+): cada instância trava e processa um **lote diferente** dos pendentes, **pulando** as linhas travadas por outra. Várias réplicas da aplicação rodam o publisher **sem pisar uma na outra** e sem lock distribuído (ShedLock). Em SQL Server use `WITH (UPDLOCK, READPAST)`; em Oracle `FOR UPDATE SKIP LOCKED`. É SQL nativo (database-specific — `spring-data-jpa`: "só quando o JPQL não consegue").
- O `columnDefinition = "json"` é do MySQL; em PostgreSQL mapeie para `jsonb` (`@JdbcTypeCode(SqlTypes.JSON)`).

## 3. Gravando o evento na mesma transaction

```java
@Service
public class BookService {

    @Autowired
    private BookRepository repository;

    @Autowired
    private OutboxEventRepository outbox;

    @Autowired
    private JsonMapper jsonMapper;

    @Transactional
    public BookDTO create(BookDTO book) {
        if (book == null) throw new RequiredObjectIsNullException();
        var saved = repository.save(parseObject(book, Book.class));
        var eventId = UUID.randomUUID().toString();
        var event = new BookCreatedEvent(eventId, saved.getId(), saved.getTitle(), Instant.now());
        outbox.save(OutboxEvent.of(eventId, "Book", String.valueOf(saved.getId()), "BookCreated", jsonMapper.writeValueAsString(event)));
        return parseObject(saved, BookDTO.class);
    }
}
```
- **Mesmo método `@Transactional`**: a mudança de dados e o `outbox.save` fazem commit **ou** rollback **juntos**. Esse é o ponto de todo o padrão.
- `JsonMapper` é o `tools.jackson.databind.json.JsonMapper` do Jackson 3 (bean do Boot; **não** confunda com o `ObjectMapper` do Dozer do pack — `code-organization`). `JacksonException` é unchecked.
- O **evento é um record dedicado** (contrato público), não a entity (`messaging`). O `eventId` é gerado **uma vez** e usado tanto dentro do payload quanto como `id` da linha da outbox, para que a mesma identidade apareça no banco, no broker, nos logs e na tabela de idempotência dos consumers.
- **Nada de chamar o broker aqui.** O service só grava.

## 4. Publisher (relay) com polling

```java
@Component
public class OutboxPublisher {

    private static final Logger logger = LoggerFactory.getLogger(OutboxPublisher.class);

    @Autowired
    private OutboxEventRepository repository;

    @Autowired
    private EventPublisher eventPublisher;

    @Scheduled(fixedDelayString = "${app.outbox.poll-interval:1000}")
    @Transactional
    public void publishPending() {
        var batch = repository.lockNextBatch(100);
        for (var event : batch) {
            eventPublisher.publish(event.getAggregateId(), event.getEventType(), event.getId(), event.getPayload());
            event.setPublishedAt(Instant.now());
        }
        if (!batch.isEmpty()) logger.info("Published {} outbox events", batch.size());
    }

    @Scheduled(cron = "${app.outbox.cleanup-cron:0 0 3 * * *}")
    @Transactional
    public void cleanup() {
        var deleted = repository.deletePublishedBefore(Instant.now().minus(Duration.ofDays(7)));
        logger.info("Removed {} published outbox events", deleted);
    }
}
```
Habilite com `@EnableScheduling` em uma `@Configuration`. A interface isola o broker (**um adapter por broker**, na pasta `messaging/publisher`):
```java
public interface EventPublisher {

    void publish(String key, String eventType, String eventId, String payload);
}
```
Exemplo de adapter Kafka (`kafka`) — o **`.get(timeout)` espera a confirmação** do broker antes de seguir, e lança se falhar:
```java
@Component
public class KafkaEventPublisher implements EventPublisher {

    @Autowired
    private KafkaTemplate<String, String> kafkaTemplate;

    @Value("${app.kafka.topics.book-events}")
    private String topic;

    @Override
    public void publish(String key, String eventType, String eventId, String payload) {
        try {
            var record = new ProducerRecord<>(topic, key, payload);
            record.headers().add("eventType", eventType.getBytes(StandardCharsets.UTF_8));
            record.headers().add("eventId", eventId.getBytes(StandardCharsets.UTF_8));
            kafkaTemplate.send(record).get(10, TimeUnit.SECONDS);
        } catch (Exception e) {
            throw new IllegalStateException("Failed to publish event " + eventId, e);
        }
    }
}
```
Para RabbitMQ: `rabbitTemplate.convertAndSend(...)` + esperar o confirm (`rabbitmq`); SNS: `snsTemplate.sendNotification(...)` (síncrono, lança — `aws-sns-sqs`); JMS: `jmsTemplate.convertAndSend(...)` (`activemq-artemis`). Para brokers com payload `String`, o adapter envia o JSON **já serializado** (o consumer desserializa pelo `eventType`).

Por que funciona e o que ele **não** garante:
- Se a publicação **falha**, a exception faz **rollback**: `published_at` continua `NULL` e o evento será tentado no próximo ciclo. **Nada se perde.**
- Se o processo **cai depois de publicar e antes do commit**, o evento será **publicado de novo** — por isso é **at-least-once** e o consumer **tem que ser idempotente**.
- **Lotes pequenos e timeout curto** no `send`: o lock e a conexão do database ficam presos durante o `publish`. Um broker lento = pool de conexões ocupado (`jvm-performance`). Se o broker estiver fora, o loop falha rápido e tenta no próximo ciclo; **alarme** quando o backlog da outbox crescer.
- **Ordenação:** dentro de **uma** instância o `ORDER BY created_at, id` preserva a ordem. Com **várias** instâncias e `SKIP LOCKED`, eventos do **mesmo agregado** podem ser publicados por instâncias diferentes e **chegar fora de ordem**. Se a ordem por agregado é requisito: (a) rode **um** publisher (leader election/`replicas: 1` do relay), (b) particione a outbox por hash do `aggregate_id`, ou (c) faça os consumers tolerarem desordem (compare a versão/`occurredAt` do agregado e ignore o evento antigo). Para a maioria dos casos, (c) é o mais robusto.
- Latência = o `poll-interval` (1 s no exemplo). Para latência menor, **CDC** (abaixo).

### Alternativa: CDC com Debezium (sem polling)

O **Debezium** (Kafka Connect) lê o **log de transações** do database (binlog MySQL / WAL PostgreSQL) e publica cada linha inserida em `outbox_event` no Kafka, usando o **Outbox Event Router** (SMT). Vantagens: latência de milissegundos, sem carga de polling, sem lock, ordem preservada pelo log. Custo: **operar Kafka Connect + Debezium**, e ficar acoplado ao Kafka e ao formato do banco. Vale para quem **já tem Kafka em escala**; para uma API pequena, o polling acima é bem mais simples. Com CDC, a aplicação **só grava** na outbox (seções 1–3) e apaga as linhas antigas por job.

*Spring Modulith* também oferece um **event publication registry** com a mesma ideia (persiste publicações de eventos de aplicação e republica as incompletas) — uma opção se o projeto já usa Modulith.

---

## 5. Consumer idempotente

Como a entrega é *at-least-once*, o consumer **deve** aguentar o mesmo evento duas vezes. O jeito mais robusto: uma tabela de **mensagens processadas** com o `eventId` como **chave única**, gravada **na mesma transaction** do efeito.

```sql
CREATE TABLE IF NOT EXISTS `processed_message` (
  `message_id`   char(36)    NOT NULL,
  `consumer`     varchar(80) NOT NULL,
  `processed_at` datetime(6) NOT NULL,
  PRIMARY KEY (`message_id`, `consumer`)
);
```
```java
@Service
public class BookIndexService {

    @Autowired
    private ProcessedMessageRepository processed;

    @Autowired
    private BookIndexRepository index;

    @Transactional
    public void index(String eventId, BookCreatedEvent event) {
        try {
            processed.saveAndFlush(new ProcessedMessage(eventId, "book-index"));
        } catch (DataIntegrityViolationException duplicate) {
            logger.info("Event {} already processed, skipping", eventId);
            return;
        }
        index.save(new BookIndexEntry(event.id(), event.title()));
    }
}
```
- O `INSERT` em `processed_message` e o efeito (`index.save`) estão na **mesma transaction**: ou ambos ou nenhum. Duplicata → violação de chave → ignora com segurança. Tem que ser `saveAndFlush` para a violação aparecer **ali** (e não só no commit). **Cuidado:** a exception de integridade marca a transaction como *rollback-only* em alguns cenários — isole o insert em um método/`REQUIRES_NEW` ou use `INSERT ... ON DUPLICATE KEY`/`ON CONFLICT DO NOTHING` nativo e olhe o nº de linhas afetadas, que é mais limpo.
- **Alternativas:** operação naturalmente idempotente (`UPSERT`, `UPDATE ... SET status = 'PAID'`) dispensa a tabela; para efeito externo (pagamento) passe o `eventId` como **chave de idempotência** ao provedor.
- Apague `processed_message` antigas por job (janela maior que o maior atraso/redelivery possível, ex.: 14–30 dias).

---

## 6. Operação e observabilidade

- **Métricas do outbox** (Micrometer — `observability`): **backlog** (`SELECT count(*) WHERE published_at IS NULL`), **idade do evento pendente mais antigo**, eventos publicados/s, falhas de publicação. **Alarme** quando a idade do mais antigo passar de alguns minutos — é o sintoma de broker fora ou relay parado.
- **Limpeza** diária das publicadas (acima); a tabela não pode crescer sem limite (afeta o índice e o `SKIP LOCKED`).
- Em Kubernetes, o relay roda **dentro da própria aplicação** (várias réplicas seguras por `SKIP LOCKED`); o `@Scheduled` precisa de `@EnableScheduling` e **não** deve dividir o pool de conexões com o tráfego ao ponto de afogá-lo (`jvm-performance`).
- **Migrations:** a tabela nasce por Flyway; mudanças no formato do payload seguem a compatibilidade de contrato (`messaging`).
- **Reprocessar** um evento: `UPDATE outbox_event SET published_at = NULL WHERE id = ...` (consumers idempotentes absorvem).

## 7. Testes

- **Unit** do service com o `OutboxEventRepository` mockado: assert que `create` grava o evento **e** que, se `outbox.save` lança, o `repository.save` não é "confirmado" (o teste de rollback real é de integração).
- **Integration (Testcontainers com o database real — `testing`/`integration-testing`)**:
  1. `create` grava o livro **e** uma linha pendente na outbox;
  2. falha forçada **depois** do `repository.save` → **nenhuma** das duas linhas existe (rollback conjunto);
  3. `publishPending` com um `EventPublisher` fake marca `published_at` e **não** republica;
  4. `EventPublisher` que lança → `published_at` segue `NULL` (será retentado);
  5. consumer processa o mesmo `eventId` **duas vezes** → um único efeito.
- `SKIP LOCKED` precisa de um **database real** (não H2) — daí o Testcontainers. Para testar o relay, chame `publishPending()` direto (não dependa do scheduler/`sleep`; desligue o agendamento no teste com uma property).

---

## Regras principais

- **Nunca dual write.** Evento que nasce de mudança de dados vai para a **outbox na mesma transaction**; o broker só é falado pelo relay.
- A outbox tem `id` = `eventId` (UUID), `aggregate_id` (key/ordem), `event_type`, `payload` JSON, `created_at`, `published_at`.
- Relay: lote pequeno com `FOR UPDATE SKIP LOCKED`, publicação **confirmada** (`.get(timeout)`), `published_at` no mesmo commit; falha = rollback e retry.
- Entrega **at-least-once** → consumer **idempotente** (`processed_message` com chave única na mesma transaction, ou operação idempotente).
- Ordem por agregado **não** é garantida com vários relays: um relay, particionar por agregado, ou consumers que toleram desordem.
- Limpe a outbox e a `processed_message`; alarme no **backlog e na idade do evento mais antigo**.
- Debezium/CDC quando já há Kafka em escala; polling para o caso simples; Modulith se já usado.
- Teste com database real: atomicidade (rollback conjunto), relay, falha de publicação e duplicata.
- Evento = record dedicado, nunca a entity; `JsonMapper` (Jackson 3), não o `ObjectMapper` do Dozer.
- **Sem Lombok** — deliberado.
