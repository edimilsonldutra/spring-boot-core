---
name: saga-pattern
description: Saga para transações de negócio entre microsserviços — por que não 2PC, coreografia × orquestração, compensações, ordem dos passos, semantic lock, implementação com outbox e consumers idempotentes, orquestrador persistido, timeouts, Temporal/Step Functions e testes de cada falha. Use quando uma operação atravessa vários serviços e precisa de compensação.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../microservices/SKILL.md`](../microservices/SKILL.md), [`../messaging/SKILL.md`](../messaging/SKILL.md), [`../transactional-outbox/SKILL.md`](../transactional-outbox/SKILL.md) e [`../idempotency/SKILL.md`](../idempotency/SKILL.md). **A saga só é correta se cada passo usa outbox e cada consumer é idempotente** — essas skills são pré-requisito, não opcionais.

# Saga

## O problema

Em um monolito, "criar pedido + reservar estoque + cobrar pagamento" é **uma transaction ACID** do banco: tudo ou nada. Com **um banco por serviço** (`microservices`) **não há transaction única**. O **two-phase commit (2PC/XA)** existe, mas é **lento, frágil, bloqueia recursos, exige participantes compatíveis** e não escala — **evite**.

A **saga** é a alternativa: uma **sequência de transações locais**, uma por serviço, cada uma publicando um evento/comando que dispara a próxima. Se um passo **falha**, executam-se **transações compensatórias** que **desfazem semanticamente** os passos anteriores. Você troca **atomicidade** por **consistência eventual**.

```
Pedido criado ─► Reservar estoque ─► Cobrar pagamento ─► Confirmar pedido
     │                 │ ✗ falha                │ ✗ falha
     ▼                 ▼                        ▼
 (rejeitar)      (rejeitar pedido)   Liberar estoque ─► Rejeitar pedido   ← compensações
```

**Quando NÃO usar:** se a operação cabe em **um serviço/uma transaction local**, não há saga. **Se você precisa de muitas sagas entre os mesmos dois serviços, é um sinal de design:** talvez eles sejam um **único bounded context** e devam ser **um serviço** (`microservices`: "em dúvida, junte"). Saga é o **último recurso** para consistência entre fronteiras legítimas, não a forma padrão de fazer um fluxo.

---

## 1. Coreografia × Orquestração

| | **Coreografia** | **Orquestração** |
|---|---|---|
| Como | Cada serviço **reage a eventos** e publica o seu; **sem coordenador** | Um **orquestrador** envia **comandos** a cada participante e processa as respostas |
| Fluxo | Implícito, espalhado pelos serviços | **Explícito e em um só lugar** (máquina de estados) |
| Acoplamento | Baixo entre os serviços (só eventos); **alto** conceitualmente (ciclos de eventos) | Os participantes só conhecem o orquestrador; o orquestrador conhece todos |
| Bom para | **2–4 passos**, simples, equipes autônomas | **Muitos passos**, ramificações, timeouts, compensações complexas |
| Risco | Difícil **ver/depurar o fluxo**; dependências cíclicas; "quem faz o quê?" | O orquestrador vira ponto central (mantenha **sem regra de negócio dos participantes**) |
| Observar o estado | Reconstruir a partir de eventos | Consulta direta ao estado da saga |

**Regra prática:** **coreografia para fluxos curtos e lineares; orquestração assim que houver > 3–4 passos, ramificação ou prazos.** A maioria dos sistemas reais com compensação acaba **orquestrando**.

---

## 2. Princípios de projeto (valem para os dois estilos)

1. **Cada passo é uma transaction local** que **grava a mudança + o evento/comando na outbox na mesma transaction** (`transactional-outbox`). Sem outbox, um crash entre "gravou" e "publicou" **trava a saga para sempre**.
2. **Cada handler é idempotente** (`idempotency`): mensagens chegam **at-least-once** e fora de ordem. Reprocessar `ReserveStock` para o mesmo `sagaId` **não** reserva duas vezes.
3. **Toda mensagem carrega o `sagaId`** (e `eventId`/`correlationId`) — a chave de correlação e idempotência (`messaging`, `observability`).
4. **Cada passo tem uma compensação** (exceto os que não precisam), e **a compensação também é idempotente, retentável e não pode falhar "para sempre"** — retente até conseguir (com alarme se demorar).
5. **Compensar ≠ rollback.** A compensação é uma **nova transação de negócio** que desfaz o efeito (`ReleaseStock`, `RefundPayment`), e o histórico **mostra** os dois (o estoque foi reservado **e depois liberado**). Alguns efeitos **não são compensáveis** (um e-mail enviado, uma notificação) — por isso a **ordem** importa:

### Ordem dos passos

| Tipo | Significado | Posição |
|---|---|---|
| **Compensáveis** | Podem ser desfeitos (reservar estoque, criar pré-autorização) | **No início** |
| **Pivot** | O ponto de **não retorno**: se ele passa, a saga **vai até o fim**; se falha, compensa tudo antes | No meio (ex.: **capturar o pagamento**) |
| **Retentáveis** | **Depois do pivot**: garantidos de completar (retry até dar certo) — confirmar o pedido, enviar e-mail, emitir nota | **No final** |

Coloque as ações **irreversíveis e de efeito externo** (e-mail, envio, cobrança definitiva) **depois** do pivot, para não precisar "des-enviar" um e-mail.

### Falta de isolamento (o "I" do ACID não existe)

Entre os passos, **outros** podem ver o estado **intermediário** (um pedido `PENDING` com estoque já reservado). Contramedidas:
- **Estados explícitos no domínio:** `PENDING` → `CONFIRMED`/`REJECTED`, nunca "meio criado" sem rótulo. O **semantic lock**: o registro fica **marcado como "em processamento"** e outras operações o respeitam (um pedido `PENDING` não pode ser cancelado/alterado até a saga terminar).
- **Atualizações comutativas** (somar/subtrair em vez de sobrescrever) quando possível.
- **A UX conta com a espera:** devolva `202 Accepted` + `GET /orders/{id}` com o status (`PENDING` → ...); o front **faz polling/recebe push**. **Não** prometa confirmação síncrona de algo eventual.

---

## 3. Exemplo: criar pedido (Order → Stock → Payment)

Participantes: `order`, `inventory`, `payment`. Eventos/comandos como **records** (`java-modern-features`), todos com `sagaId`:
```java
public record ReserveStock(String sagaId, long orderId, long bookId, int quantity) {}
public record StockReserved(String sagaId, long orderId) {}
public record StockRejected(String sagaId, long orderId, String reason) {}
public record ChargePayment(String sagaId, long orderId, BigDecimal amount) {}
public record PaymentCompleted(String sagaId, long orderId) {}
public record PaymentFailed(String sagaId, long orderId, String reason) {}
public record ReleaseStock(String sagaId, long orderId) {}
```

### 3.1 Coreografia (sem coordenador)

```
order:     cria Order(PENDING)            ──► publica OrderCreated
inventory: ouve OrderCreated; reserva     ──► publica StockReserved | StockRejected
payment:   ouve StockReserved; cobra      ──► publica PaymentCompleted | PaymentFailed
order:     ouve PaymentCompleted          ──► Order = CONFIRMED
order:     ouve StockRejected/PaymentFailed ──► Order = REJECTED
inventory: ouve PaymentFailed             ──► libera o estoque (compensação)
```
Cada serviço tem **um listener idempotente** por evento e publica o seguinte **via outbox**:
```java
@Component
public class InventoryOrderListener {

    private final InventoryService inventory;

    public InventoryOrderListener(InventoryService inventory) {
        this.inventory = inventory;
    }

    @KafkaListener(topics = "library.order.created.v1")
    public void on(OrderCreated event) {
        inventory.reserve(event.sagaId(), event.orderId(), event.bookId(), event.quantity());
    }
}
```
```java
@Service
public class InventoryService {

    private final StockRepository stocks;
    private final ProcessedMessageRepository processed;
    private final OutboxEventRepository outbox;
    private final JsonMapper jsonMapper;

    // construtor omitido

    @Transactional
    public void reserve(String sagaId, long orderId, long bookId, int quantity) {
        if (!processed.markProcessed(sagaId, "inventory-reserve")) return;
        var stock = stocks.findByBookId(bookId).orElseThrow();
        if (stock.available() < quantity) {
            outbox.save(event(sagaId, "StockRejected", new StockRejected(sagaId, orderId, "out of stock")));
            return;
        }
        stock.reserve(quantity);
        outbox.save(event(sagaId, "StockReserved", new StockReserved(sagaId, orderId)));
    }
}
```
(`processed.markProcessed` é o `INSERT` da tabela de mensagens processadas — `idempotency`/`transactional-outbox`, mesma transaction do efeito.) **Limites da coreografia:** o fluxo "Pedido" só existe **somando** quatro listeners em três serviços — documente com um diagrama (e use `traceId`/`sagaId` para ver uma execução). Quando passar de 4 passos ou ganhar ramificações, **migre para orquestração**.

### 3.2 Orquestração (orquestrador com estado persistido)

O **orquestrador** (um serviço — frequentemente o próprio `order`) guarda o **estado da saga** em uma tabela e **decide o próximo passo** a cada resposta. Ele **só coordena**; a regra de negócio de reservar/cobrar fica nos participantes.

```java
@Entity
@Table(name = "order_saga")
public class OrderSaga {

    @Id
    private String id;

    @Column(name = "order_id", nullable = false)
    private Long orderId;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private SagaStep step;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private SagaStatus status;

    @Column(name = "failure_reason")
    private String failureReason;

    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    @Version
    private Long version;

    // getters, setters, equals, hashCode
}

public enum SagaStep { RESERVING_STOCK, CHARGING_PAYMENT, COMPENSATING_STOCK, DONE }

public enum SagaStatus { RUNNING, COMPLETED, COMPENSATED, FAILED }
```
```java
@Service
public class OrderSagaOrchestrator {

    private final OrderSagaRepository sagas;
    private final OrderRepository orders;
    private final Outbox outbox;

    // construtor omitido

    @Transactional
    public void start(Order order) {
        var saga = OrderSaga.start(order.getId());
        sagas.save(saga);
        outbox.command("library.inventory.commands.v1", saga.getId(),
                new ReserveStock(saga.getId(), order.getId(), order.getBookId(), order.getQuantity()));
    }

    @Transactional
    public void on(StockReserved reply) {
        var saga = sagas.findById(reply.sagaId()).orElseThrow();
        if (saga.getStep() != SagaStep.RESERVING_STOCK) return;
        saga.moveTo(SagaStep.CHARGING_PAYMENT);
        outbox.command("library.payment.commands.v1", saga.getId(),
                new ChargePayment(saga.getId(), saga.getOrderId(), orders.amountOf(saga.getOrderId())));
    }

    @Transactional
    public void on(PaymentCompleted reply) {
        var saga = sagas.findById(reply.sagaId()).orElseThrow();
        if (saga.getStep() != SagaStep.CHARGING_PAYMENT) return;
        saga.complete();
        orders.confirm(saga.getOrderId());
    }

    @Transactional
    public void on(PaymentFailed reply) {
        var saga = sagas.findById(reply.sagaId()).orElseThrow();
        if (saga.getStep() != SagaStep.CHARGING_PAYMENT) return;
        saga.moveTo(SagaStep.COMPENSATING_STOCK, reply.reason());
        outbox.command("library.inventory.commands.v1", saga.getId(),
                new ReleaseStock(saga.getId(), saga.getOrderId()));
    }

    @Transactional
    public void on(StockRejected reply) {
        var saga = sagas.findById(reply.sagaId()).orElseThrow();
        if (saga.getStep() != SagaStep.RESERVING_STOCK) return;
        saga.fail(reply.reason());
        orders.reject(saga.getOrderId());
    }
}
```
Pontos que importam:
- **Cada `on(...)` verifica o `step` atual e ignora** a mensagem se não é o esperado — é a **idempotência** da máquina de estados (uma resposta duplicada ou atrasada **não** avança duas vezes). `@Version` (optimistic locking) protege contra **duas respostas simultâneas**.
- **Cada transição** = **uma transaction** que **atualiza o estado da saga + grava o próximo comando na outbox** (`transactional-outbox`).
- **O orquestrador não calcula regra do participante**: pergunta-lhes (comandos) e reage às respostas.
- **Os participantes** (`inventory`, `payment`) tratam o **comando**, executam a transaction local, e **respondem** com evento (`StockReserved`/`StockRejected`) — sempre idempotentes e via outbox.
- Guarde o **histórico** das transições (tabela `saga_event` ou logs) para auditoria e depuração.

### Timeouts e sagas travadas

Um participante pode **nunca responder**. Sem tratamento, a saga fica em `RUNNING` para sempre (estoque preso, pedido `PENDING`). Mecanismos:
- **Deadline por passo** (`step_deadline`) e um **job** que busca sagas `RUNNING` passadas do prazo e **compensa/alerta** (`@Scheduled` com lock — `SELECT ... FOR UPDATE SKIP LOCKED` como no relay do outbox — ou **EventBridge Scheduler** disparando uma mensagem de timeout — `aws-eventbridge`).
- **Retry** do comando antes de desistir (comandos são idempotentes).
- **Alarme** em "saga em `RUNNING` há > X minutos" e em **sagas `FAILED`** (a compensação não completou — **intervenção humana**). Mantenha um **runbook** para elas.
- **DLQ** para mensagens que o orquestrador não consegue processar (`messaging`).

---

## 4. Ferramentas de mercado (quando não escrever o orquestrador à mão)

| Ferramenta | O que é | Quando |
|---|---|---|
| **Temporal** (Java SDK, `temporal-spring-boot-starter`) | **Durable execution**: você escreve o fluxo como **código** (`workflow`), com `try/catch` de compensação; o Temporal persiste o estado, faz **retry, timers, timeouts** e retoma após crash | Fluxos longos/complexos; quer **o fluxo como código Java legível** em vez de máquina de estados; aceita operar o cluster Temporal (ou Temporal Cloud) |
| **AWS Step Functions** | Orquestrador **gerenciado** (JSON/ASL), com `Catch`/`Retry`, integração com Lambda/SQS/ECS/DynamoDB, *standard workflows* de longa duração | Já na AWS, passos são Lambdas/serviços AWS, quer **zero operação** (`aws-lambda`) |
| **Camunda 8 (Zeebe)** / Flowable | **BPMN**: o fluxo é um diagrama executável, com tarefas humanas e visibilidade para o negócio | O fluxo é um **processo de negócio** modelado/revisado com analistas; tarefas manuais |
| **Axon Framework** | *Sagas* integradas a CQRS/Event Sourcing (`cqrs-event-sourcing`) | Já usa o ecossistema Axon |
| **Eventuate Tram**, **MicroProfile LRA** | Frameworks de saga/outbox | Casos específicos |
| **Orquestrador próprio** (seção 3.2) | Máquina de estados + outbox | **Poucas sagas**, fluxos simples, sem querer nova plataforma |

**Critério:** **1–2 sagas simples** → orquestrador próprio ou coreografia. **Várias sagas complexas, longas, com timers/humanos** → **Temporal/Step Functions/Camunda** (reinventar durable execution à mão é caro e propenso a bugs). Em todos, **os participantes continuam idempotentes**.

---

## 5. Observabilidade

- **`sagaId` como correlation id** em **todo** log, evento e span (`observability`): dá para ver **uma execução ponta a ponta** (Logs Insights/trace — `aws-observability`).
- **Métricas:** sagas iniciadas/concluídas/**compensadas**/**falhas**, **duração** (p50/p99), **sagas em `RUNNING` por idade**, mensagens na DLQ. **Alarmes:** idade da saga mais antiga em andamento, taxa de compensação (sobe = problema num participante), `FAILED > 0`.
- **Dashboard de estado** (consulta à tabela de sagas): quantas em cada `step`.
- **Endpoint/tela de status** para o usuário (`GET /orders/{id}` → `PENDING/CONFIRMED/REJECTED`, com o motivo).

## 6. Testes — cada falha, em cada passo

O valor de uma saga está no **caminho de falha**; teste-o:
- **Caminho feliz** completo (todos os passos → `CONFIRMED`).
- **Falha em cada passo** → as compensações corretas, na ordem, e o estado final `REJECTED`/`COMPENSATED`.
- **Mensagem duplicada** (cada resposta entregue 2×) → **sem efeito duplo** (estoque reservado uma vez).
- **Mensagem fora de ordem/atrasada** (`PaymentCompleted` depois do timeout/compensação) → ignorada com segurança.
- **Participante não responde** → o timeout compensa/alerta.
- **Compensação que falha** → é retentada; fica `FAILED` com alarme se persistir.
- **Crash entre "gravou e publicou"** → o outbox publica depois (`transactional-outbox`).
- **Unit** do orquestrador (máquina de estados: dado `step` X e resposta Y → próximo `step` e comando) **sem broker**; **integration** com broker e banco reais em container (`messaging`, `integration-testing`) + Awaitility; **contract tests** das mensagens entre orquestrador e participantes (`contract-testing`).

## 7. Anti-patterns

- **2PC/transação distribuída** no lugar da saga.
- **Saga sem outbox** (crash = saga travada) e **sem idempotência** (duplicata = efeito duplo).
- **Sem compensação** ou compensação **não idempotente/que pode falhar**.
- **Passos irreversíveis no início** (enviar e-mail antes de saber se o pagamento passou).
- **Coreografia com muitos passos/ciclos** ("evento espaguete") onde um orquestrador seria claro.
- **Orquestrador com regra de negócio dos participantes** (vira monolito distribuído).
- **Sem timeout** nem monitoramento de sagas travadas.
- **Estado intermediário não modelado** (sem `PENDING`) e UX que promete confirmação síncrona.
- **Saga entre dois serviços que mudam sempre juntos** (talvez seja um serviço só).

---

## Regras principais

- **Saga em vez de 2PC**, e **só quando a operação atravessa fronteiras legítimas**; muitas sagas entre os mesmos serviços = reconsidere as fronteiras (`microservices`).
- **Coreografia para 2–4 passos lineares; orquestração para mais passos, ramificações e prazos** (estado persistido + `@Version`).
- **Cada passo = transaction local + outbox**; **todo handler idempotente** (verifica o `step`/marca processado); **`sagaId` em toda mensagem**.
- **Compensações** idempotentes e retentáveis; **ordem: compensáveis → pivot → retentáveis**; ações irreversíveis e externas **depois** do pivot.
- **Modele os estados intermediários** (`PENDING`/`CONFIRMED`/`REJECTED`, semantic lock) e a **UX eventual** (`202` + consulta de status).
- **Timeouts e monitoramento** de sagas travadas; alarmes em `RUNNING` antiga, taxa de compensação e `FAILED`; runbook para intervenção humana.
- Temporal/Step Functions/Camunda quando as sagas forem várias, longas ou com humanos; orquestrador próprio para o simples.
- **Teste cada falha em cada passo**, duplicata, desordem, timeout e compensação que falha.
- **Sem Lombok** — deliberado.
