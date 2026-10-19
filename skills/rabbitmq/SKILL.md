---
name: rabbitmq
description: RabbitMQ com Spring Boot 4 / Spring AMQP — exchanges, queues, bindings e dead-letter exchange como beans, publisher confirms, @RabbitListener com ack e retry, quorum queues, retry com atraso (TTL e DLX), prefetch, JSON, Docker/Kubernetes/Amazon MQ, segurança, métricas e testes. Use quando criar filas de trabalho ou roteamento de mensagens com RabbitMQ.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md) e [`../messaging/SKILL.md`](../messaging/SKILL.md) (escolha de broker, desenho de eventos, garantias) — e **`../transactional-outbox/SKILL.md`** se a mensagem nasce de uma mudança no database.

# RabbitMQ

RabbitMQ é um **broker "esperto"** (AMQP 0-9-1): o produtor publica em uma **exchange**, que **roteia** para **queues** conforme **bindings** e **routing keys**; consumers leem das queues. A mensagem é entregue, confirmada (*ack*) e **removida** — não é um log com replay (para isso, `kafka`). Excelente para **filas de tarefas/comandos**, roteamento flexível, prioridade e atrasos.

> Nomes de classes do **Spring AMQP 4 / Boot 4** (conversor JSON com Jackson 3) mudaram em relação ao Boot 3. Confirme na versão resolvida (Context7, `maven-config`); os pontos incertos estão marcados.

## Dependencies

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-amqp</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.amqp</groupId>
    <artifactId>spring-rabbit-test</artifactId>
    <scope>test</scope>
</dependency>
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>testcontainers-rabbitmq</artifactId>
    <scope>test</scope>
</dependency>
```

---

## Conceitos que mudam o seu código

| Exchange | Roteia por | Use para |
|---|---|---|
| **direct** | routing key **igual** à do binding | Enviar a uma fila específica (comando/tarefa) |
| **topic** | **padrão** (`book.*`, `book.#`) | Eventos por assunto, vários consumers com interesses diferentes |
| **fanout** | **todas** as queues ligadas (ignora a key) | Broadcast |
| **headers** | atributos dos headers | Raro |

- **Produtor publica na exchange, nunca direto na queue.** Isso desacopla quem publica de quem consome.
- **Cada consumer lógico tem a sua queue** (fan-out de eventos = uma queue por serviço interessado, todas ligadas à mesma exchange). Vários **réplicas da mesma aplicação** consomem da **mesma queue** e **dividem** as mensagens (competing consumers).
- **Ack:** a mensagem só sai da queue quando o consumer confirma. Se o consumer morre sem ack, o broker **reentrega** (at-least-once → consumer idempotente — `messaging`).

---

## application.yml

```yaml
spring:
  rabbitmq:
    host: ${RABBITMQ_HOST:localhost}
    port: 5672
    username: ${RABBITMQ_USER:guest}
    password: ${RABBITMQ_PASSWORD:guest}
    virtual-host: /
    publisher-confirm-type: correlated
    publisher-returns: true
    template:
      mandatory: true
    listener:
      simple:
        acknowledge-mode: auto
        prefetch: 20
        concurrency: 2
        max-concurrency: 6
        default-requeue-rejected: false
        retry:
          enabled: true
          initial-interval: 1s
          multiplier: 2.0
          max-interval: 10s
          max-attempts: 4

app:
  rabbitmq:
    exchange: library.events
    queues:
      book-created: library.book-created.queue
```
- **`guest/guest` só funciona de `localhost`** e **nunca** em produção: crie um usuário por aplicação com permissões mínimas no virtual host; senha por Secret (`kubernetes`, `aws-rds-secrets-manager`).
- **`publisher-confirm-type: correlated` + `publisher-returns` + `mandatory`:** o broker confirma que **recebeu e enfileirou** a mensagem; se nenhuma queue casa com a routing key, a mensagem **volta** (return) em vez de sumir silenciosamente. Sem isso, `convertAndSend` "dá certo" mesmo quando a mensagem foi descartada.
- **`default-requeue-rejected: false`:** quando as tentativas se esgotam, a mensagem é **rejeitada sem voltar à queue** → vai para a **DLX/DLQ** (abaixo). Com `true` (o default histórico) ela volta ao início da queue e **gira em loop infinito** (poison message).
- **`retry`** é o retry **dentro do consumer** (bloqueante, mesma thread): 4 tentativas com backoff exponencial e depois rejeita. Mantenha curto.
- **`prefetch: 20`:** quantas mensagens não confirmadas o broker entrega de uma vez a cada consumer. Alto = throughput, mas uma mensagem lenta atrasa as seguintes e o `ack` fica atrás; para processamento pesado e desigual, use valores baixos (1–10). Combine com `concurrency` e com o pool de conexões do database (`jvm-performance`).

---

## Topologia como código (queues, exchanges, bindings, DLQ)

O Spring AMQP **declara** no broker os beans `Queue`, `Exchange` e `Binding` no startup (idempotente, via `RabbitAdmin`). Mantenha tudo em uma classe de config:

```java
@Configuration
public class RabbitConfig {

    @Value("${app.rabbitmq.exchange}")
    private String exchangeName;

    @Value("${app.rabbitmq.queues.book-created}")
    private String queueName;

    @Bean
    TopicExchange eventsExchange() {
        return ExchangeBuilder.topicExchange(exchangeName).durable(true).build();
    }

    @Bean
    Queue bookCreatedQueue() {
        return QueueBuilder.durable(queueName)
                .quorum()
                .deadLetterExchange(exchangeName + ".dlx")
                .deadLetterRoutingKey(queueName + ".dlq")
                .build();
    }

    @Bean
    Binding bookCreatedBinding() {
        return BindingBuilder.bind(bookCreatedQueue()).to(eventsExchange()).with("book.created");
    }

    @Bean
    DirectExchange deadLetterExchange() {
        return ExchangeBuilder.directExchange(exchangeName + ".dlx").durable(true).build();
    }

    @Bean
    Queue bookCreatedDeadLetterQueue() {
        return QueueBuilder.durable(queueName + ".dlq").quorum().build();
    }

    @Bean
    Binding bookCreatedDeadLetterBinding() {
        return BindingBuilder.bind(bookCreatedDeadLetterQueue()).to(deadLetterExchange()).with(queueName + ".dlq");
    }
}
```
- **`durable` + `quorum`:** a queue sobrevive a restart do broker (durable) e é **replicada por consenso Raft** (quorum) — o tipo recomendado para dados que importam; substitui as *mirrored classic queues*, descontinuadas. Quorum queues exigem um cluster de 3 nós para ter o benefício de HA. Mensagens também precisam ser **persistentes** (o `RabbitTemplate` envia como persistentes por padrão).
- **DLX/DLQ declaradas junto**: cada queue de trabalho aponta para a sua dead-letter exchange; a queue `.dlq` guarda as rejeitadas para análise e **redrive** manual (mover de volta depois de corrigir). Monitore o tamanho da DLQ com alarme.
- **Mudar argumentos de uma queue existente falha** (`PRECONDITION_FAILED`): o broker não altera uma queue já criada. Para mudar (ex.: adicionar DLX), crie uma queue nova e migre, ou apague a de dev. Planeje a topologia antes do primeiro deploy.
- Em produção, algumas organizações gerenciam a topologia por IaC (Terraform/Messaging Topology Operator) e deixam a aplicação sem permissão de `configure`. Mantenha `RabbitConfig` para dev/teste ou por profile.
- Nomes de exchange/queue/routing key **vindos de configuração**, padronizados e versionáveis (`messaging`).

## Conversão JSON

```java
@Bean
MessageConverter jsonMessageConverter() {
    return new JacksonJsonMessageConverter();
}
```
O Boot aplica o bean `MessageConverter` ao `RabbitTemplate` e aos listeners. (**No Spring AMQP 4 / Jackson 3 a classe é a variante `Jackson…`; no Boot 3 era `Jackson2JsonMessageConverter` — confirme na sua versão.**) Sem conversor, o default é a **serialização Java** (insegura e acoplada a classes) — **sempre configure JSON** e **restrinja os tipos confiáveis** do conversor ao package dos eventos, por segurança (`messaging`, seção 7).

---

## Producer

```java
@Component
public class BookEventPublisher {

    @Autowired
    private RabbitTemplate rabbitTemplate;

    @Value("${app.rabbitmq.exchange}")
    private String exchange;

    public void bookCreated(BookCreatedEvent event) {
        var correlation = new CorrelationData(event.eventId());
        rabbitTemplate.convertAndSend(exchange, "book.created", event, message -> {
            message.getMessageProperties().setMessageId(event.eventId());
            return message;
        }, correlation);
    }
}
```
- **`messageId` = `eventId`**: base da idempotência do consumer.
- Trate o **confirm** (callback `ConfirmCallback`/`correlation.getFuture()`): `ack=false` significa que o broker **não** aceitou. Para garantia real, use o **outbox** (`transactional-outbox`), que só marca como publicado depois do confirm.
- Não chame `convertAndSend` dentro de `@Transactional` esperando atomicidade com o commit do database — é o **dual write**.

## Consumer

```java
@Component
public class BookEventListener {

    private static final Logger logger = LoggerFactory.getLogger(BookEventListener.class);

    @Autowired
    private BookIndexService service;

    @RabbitListener(queues = "${app.rabbitmq.queues.book-created}")
    public void onBookCreated(BookCreatedEvent event) {
        logger.info("Processing {} for book {}", event.eventId(), event.id());
        service.index(event);
    }
}
```
- Fino: delega ao service (`@Transactional`, **idempotente**). Se o método **retorna**, o container confirma (*ack*); se **lança exception**, o retry/rejeição entra em ação.
- Para **erro permanente** (payload inválido, regra violada) **não retente**: lance `AmqpRejectAndDontRequeueException` (vai direto para a DLQ), em vez de gastar as 4 tentativas.
- Nunca engula a exception: o container entenderia como sucesso e a mensagem seria **perdida**.
- Para controle fino use `acknowledge-mode: manual` com `Channel` + `basicAck/basicNack` — mais poder, mais chance de erro; o `auto` serve para a maioria.

---

## Retry com atraso (sem bloquear a queue)

O retry do container **bloqueia** o consumer. Para tentar de novo **depois de um tempo** sem travar, use uma **retry queue com TTL** que devolve para a principal por dead-lettering:

```
work.queue  --(falha/nack)-->  retry.queue (x-message-ttl=30000, DLX → exchange principal, routing key original)
retry.queue --(TTL expira)-->  work.queue
Após N tentativas (contador no header x-death/próprio) --> parking-lot/dlq
```
O RabbitMQ registra o histórico no header `x-death` (contagem de vezes). O **atraso exato por mensagem** não é nativo (TTL por queue é o jeito simples; o plugin *delayed-message-exchange* existe mas é um ponto extra de operação). Em muitos casos, o **retry bloqueante curto + DLQ + redrive manual** basta.

## Outros padrões úteis

- **Competing consumers / work queue:** uma queue, N consumers, `prefetch` baixo → distribui trabalho de forma justa.
- **Prioridade:** `x-max-priority` na queue (uso moderado; não combine com quorum queues sem checar a doc da versão).
- **TTL** de mensagem/queue para dados que perdem a validade.
- **RPC (request/reply)** existe (`sendAndReceive`), mas prefira **assíncrono**; é fácil criar acoplamento e timeouts em cascata.
- **Streams** do RabbitMQ (log com replay) existem para casos tipo Kafka dentro do RabbitMQ — avalie `kafka` se replay/volume são o requisito principal.

---

## RabbitMQ em Docker e produção

**docker-compose (dev):**
```yaml
services:
  rabbitmq:
    image: rabbitmq:4-management
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER:-app}
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD:-app123}
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "-q", "ping"]
      interval: 10s
      timeout: 5s
      retries: 10
```
A UI de management em `http://localhost:15672` mostra filas, taxas e permite inspecionar mensagens (nunca exponha a 15672 publicamente). Fixe a **tag** da imagem.

**Produção:**
- **Amazon MQ for RabbitMQ**: gerenciado, em subnets privadas, TLS (`amqps`, porta 5671 — `spring.rabbitmq.ssl.enabled: true`), cluster de 3 nós Multi-AZ, usuário por aplicação (`aws-rds-secrets-manager` para a senha no Secrets Manager).
- **Kubernetes:** o **RabbitMQ Cluster Operator** (e o *Messaging Topology Operator*) declaram cluster, usuários, queues e permissões como YAML (`kubernetes`); volumes persistentes para as quorum queues.
- Mínimo de 3 nós para quorum; alarme de **memória/disco** do broker (o RabbitMQ **bloqueia produtores** quando atinge o limite — *flow control* — e a API passa a pendurar).
- TLS, usuário/virtual host por serviço, permissões `configure/write/read` por regex mínimo.

## Observabilidade

- Métricas Micrometer do `RabbitTemplate`/listeners (`spring.rabbitmq.listener.simple.observation-enabled`/`template.observation-enabled` para tracing) via Actuator (`observability`); métricas do **broker** no plugin Prometheus do RabbitMQ.
- Alarmes: **`messages_ready` crescendo** (consumer não acompanha), **mensagens na DLQ > 0**, `messages_unacknowledged` alto, consumers = 0, alarmes de memória/disco, conexões/canais vazando.
- Propague o trace id e o `correlationId` nos headers da mensagem; logue `eventId`/routing key.

## Testes

```java
@SpringBootTest
@Testcontainers
class BookEventIntegrationTest {

    @Container
    @ServiceConnection
    static RabbitMQContainer rabbit = new RabbitMQContainer("rabbitmq:4-management");

    @Autowired
    private BookEventPublisher publisher;

    @Autowired
    private BookIndexRepository index;

    @Test
    void consumerProcessesTheEventOnlyOnceEvenWhenDeliveredTwice() {
        var event = new BookCreatedEvent(UUID.randomUUID().toString(), 42L, "Clean Code", Instant.now());

        publisher.bookCreated(event);
        publisher.bookCreated(event);

        await().atMost(Duration.ofSeconds(15))
                .untilAsserted(() -> assertThat(index.countByBookId(42L)).isEqualTo(1));
    }
}
```
- `org.testcontainers.rabbitmq.RabbitMQContainer` (Testcontainers 2; artifact `testcontainers-rabbitmq`) + `@ServiceConnection`. Fixe a imagem.
- **Awaitility**, nunca `Thread.sleep`. Teste também: **mensagem inválida vai para a DLQ** (consuma a `.dlq` e verifique), e **duplicata não duplica o efeito**.
- Unit tests do listener chamam o método direto (sem broker) — `testing`.

---

## Regras principais

- Produtor publica na **exchange**; **uma queue por consumer lógico**; réplicas da mesma app dividem a queue.
- Queues **durable + quorum**; mensagens persistentes; **DLX/DLQ** declaradas para toda queue de trabalho, com alarme e processo de redrive.
- `default-requeue-rejected: false` (evita loop infinito); retry curto e limitado; erro permanente → `AmqpRejectAndDontRequeueException`.
- **Publisher confirms + returns + mandatory**; `messageId = eventId`; consumer **idempotente**; at-least-once.
- **JSON** com tipos confiáveis restritos — nunca serialização Java.
- `prefetch` ajustado ao tempo de processamento; `concurrency` somado ao pool do database.
- Topologia como beans (ou IaC), nomes por configuração; mudar argumentos de queue existente = queue nova.
- Usuário por aplicação com permissões mínimas, TLS, `guest` nunca em produção; senha por Secret; UI de management nunca pública.
- Monitore `messages_ready`, DLQ, unacked, consumers e alarmes de memória/disco do broker.
- Teste com RabbitMQ real (Testcontainers) e Awaitility, incluindo duplicata e DLQ; confirme classes do Spring AMQP 4.
- **Sem Lombok** — deliberado.
