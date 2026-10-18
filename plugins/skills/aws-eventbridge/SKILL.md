---
name: aws-eventbridge
description: Amazon EventBridge com Spring Boot — event bus, regras e event patterns, targets com retry e DLQ, PutEvents tratando FailedEntryCount, envelope de evento, archive/replay, schema registry e EventBridge Scheduler no lugar de @Scheduled em várias réplicas. Use quando rotear eventos por conteúdo, reagir a eventos da AWS ou agendar tarefas.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../messaging/SKILL.md`](../messaging/SKILL.md), [`../aws-sdk-java/SKILL.md`](../aws-sdk-java/SKILL.md) e [`../aws-sns-sqs/SKILL.md`](../aws-sns-sqs/SKILL.md) (a comparação com SNS+SQS e as filas-alvo). Se o evento nasce de uma mudança no banco, use `transactional-outbox`.

# Amazon EventBridge

**EventBridge** é um **barramento de eventos (event bus)** serverless: produtores publicam **eventos** (JSON) no bus; **regras** casam o conteúdo por **event pattern** e entregam a **targets** (SQS, Lambda, Step Functions, SNS, API HTTP externa, ECS tasks, outro bus…). Diferente do SNS (que faz *fan-out* por tópico), o EventBridge **roteia por conteúdo** do evento, integra **eventos de serviços AWS** (ex.: "task do ECS parou", "objeto criado no S3") e **SaaS parceiros**, e oferece **schema registry**, **archive/replay** e **Scheduler**.

## EventBridge, SNS+SQS ou Kafka?

| Preciso de… | Use |
|---|---|
| **Rotear por conteúdo** (regras sobre campos do JSON), reagir a **eventos de serviços AWS/SaaS**, integração entre contas/times com baixo acoplamento, agendamentos | **EventBridge** |
| Fan-out simples e **alta vazão** de mensagens entre serviços seus, com filtro por atributo | **SNS → SQS** (`aws-sns-sqs`) |
| **Replay do histórico**, ordem por partição, streaming em larga escala | **Kafka/MSK** (`kafka`) |
| Fila de trabalho (um consumer processa cada item) | **SQS** (`aws-s3-sqs`) — e o EventBridge pode ter uma **fila como target** |

EventBridge tem **latência e limites de vazão maiores** que SNS/Kafka (cotas por região, ~centenas de ms) — é **um barramento de integração/eventos de domínio**, não um canal de alto volume em tempo real. Padrão comum: **EventBridge (roteamento) → SQS por consumer (buffer + DLQ) → serviço** (o mesmo desenho do fan-out de `aws-sns-sqs`).

## Estrutura de um evento

```json
{
  "source": "br.com.padrao.library",
  "detail-type": "BookCreated",
  "detail": { "eventId": "6f1c...", "eventVersion": 1, "id": 42, "title": "Clean Code", "occurredAt": "2026-01-15T10:30:00Z" },
  "eventBusName": "library-bus"
}
```
- **`source`** (quem publica; use namespace reverso, **nunca** o prefixo reservado `aws.`), **`detail-type`** (o tipo do evento — nome no passado, `messaging`) e **`detail`** (seu payload JSON) são os campos que as **regras casam**.
- Dentro do `detail`, siga o envelope de `messaging`: **`eventId` único**, **`eventVersion`**, `occurredAt`, `correlationId`. O EventBridge também gera um `id` do evento, mas o **seu `eventId`** é a chave de **idempotência** dos consumers.
- **Tamanho máx. 256 KB** por evento; payload grande → S3 + referência (`aws-s3-sqs`).
- Evento é **record dedicado**, não entity (`messaging`, `java-modern-features`).

---

## Publicando com o SDK v2

Não há starter do Spring Cloud AWS para EventBridge: use o **SDK puro**, isolado atrás de uma interface do domínio (`aws-sdk-java`).

```xml
<dependency>
    <groupId>software.amazon.awssdk</groupId>
    <artifactId>eventbridge</artifactId>
</dependency>
```
```java
@Component
public class EventBridgeEventPublisher implements EventPublisher {

    private static final Logger logger = LoggerFactory.getLogger(EventBridgeEventPublisher.class);

    @Autowired
    private EventBridgeClient client;

    @Value("${app.aws.eventbus}")
    private String eventBus;

    @Override
    public void publish(String key, String eventType, String eventId, String payload) {
        var entry = PutEventsRequestEntry.builder()
                .eventBusName(eventBus)
                .source("br.com.padrao.library")
                .detailType(eventType)
                .detail(payload)
                .build();

        var response = client.putEvents(PutEventsRequest.builder().entries(entry).build());

        if (response.failedEntryCount() > 0) {
            var failed = response.entries().get(0);
            throw new IllegalStateException("EventBridge rejected event " + eventId
                    + ": " + failed.errorCode() + " - " + failed.errorMessage());
        }
        logger.debug("Published {} to {}", eventId, eventBus);
    }
}
```
**A armadilha principal:** `PutEvents` retorna **HTTP 200 mesmo quando entradas falham** (throttling, evento inválido). A falha vem em `failedEntryCount()` / nos `entries()` com `errorCode`. Se você **não verifica**, **perde eventos em silêncio**. Sempre cheque, e **lance** (para o outbox/retry reagir).
- **Lote:** até **10 entradas por chamada** e **256 KB no total**; em lote, **re-envie só as entradas que falharam** (as `entries()` vêm na mesma ordem do request).
- Implemente a interface `EventPublisher` do `transactional-outbox` (a mesma de Kafka/RabbitMQ/SNS): o **relay do outbox** publica no EventBridge **depois do commit** e só marca como publicado se `failedEntryCount == 0`. **Não** chame `putEvents` de dentro da transaction do negócio (dual write — `messaging`).
- Nome do bus por configuração (`app.aws.eventbus`); o bus `default` recebe eventos dos serviços AWS — para os **seus** eventos use um **bus customizado** (isola permissões e regras).

## Regras (event patterns) e targets

Uma regra **casa** eventos e os envia a até 5 targets. Exemplo — enviar `BookCreated` para a fila do serviço de busca:
```json
{
  "source": ["br.com.padrao.library"],
  "detail-type": ["BookCreated", "BookUpdated"],
  "detail": { "price": [{ "numeric": [">", 0] }] }
}
```
O padrão suporta **prefixo**, **numérico**, **exists**, **anything-but**, listas (OR) e aninhamento no `detail`. O filtro roda **no EventBridge** — o consumer só recebe o que importa.

Criar por **IaC** (`aws-terraform`); a ideia em CLI:
```bash
aws events create-event-bus --name library-bus
aws events put-rule --event-bus-name library-bus --name book-created-to-search \
  --event-pattern file://pattern.json
aws events put-targets --event-bus-name library-bus --rule book-created-to-search \
  --targets 'Id=search-queue,Arn=arn:aws:sqs:us-east-1:123456789012:library-search-index,DeadLetterConfig={Arn=arn:aws:sqs:us-east-1:123456789012:library-eb-dlq},RetryPolicy={MaximumRetryAttempts=10,MaximumEventAgeInSeconds=3600}'
```
- **Target SQS**: a **queue policy** precisa permitir `events.amazonaws.com` com `sqs:SendMessage` e `aws:SourceArn` = ARN da **regra** (sem isso, nada chega — mesmo problema do SNS em `aws-sns-sqs`). **Uma fila (com DLQ própria) por consumer** — buffer, retry e isolamento (`messaging`).
- **Retry e DLQ do target**: o EventBridge re-tenta a entrega ao target com **backoff** por até 24 h (configurável por `RetryPolicy`) e, esgotado, envia o evento à **DLQ do target** (`DeadLetterConfig`, uma fila SQS). **Configure sempre a DLQ do target** e alarme nela — sem ela, entregas falhas são **descartadas**. (Isso é separado da DLQ da fila/consumer.)
- **Input transformer** reformata o evento antes de entregar ao target (extrai campos, monta outro JSON) — útil para acionar targets que esperam um formato (ex.: API de terceiro).
- **API destinations**: chama um **endpoint HTTP externo** com autenticação (API key/OAuth/basic em **connection** com segredo no Secrets Manager gerenciado pelo EventBridge) e **rate limit** — integração com SaaS sem escrever código.

## Eventos de serviços AWS (poderoso e subutilizado)

Reaja ao que acontece na própria AWS **sem código de polling**: "task ECS parou/deploy falhou" (`aws.ecs`), "imagem ECR com vulnerabilidade crítica" (`aws.ecr`), "objeto criado no S3" (`aws.s3`, com EventBridge habilitado no bucket), "alarme do CloudWatch mudou de estado" (`aws.cloudwatch`), "RDS failover". Regra no **bus `default`** → target SNS/Lambda/SQS para notificar o time ou automatizar (`aws-observability`, `aws-ecs-fargate`).

---

## EventBridge Scheduler — agendamento sem `@Scheduled` multiplicado

`@Scheduled` em **N réplicas** executa **N vezes** (precisa de lock distribuído — ShedLock). O **EventBridge Scheduler** agenda **fora** da aplicação e dispara **uma vez**:
- **Cron/rate** (`cron(0 3 * * ? *)`, com fuso) ou **one-time** (`at(2026-03-01T09:00:00)` — ex.: "lembrete 24 h antes do vencimento", criado dinamicamente pela aplicação via `SchedulerClient.createSchedule`).
- **Targets**: SQS (a aplicação consome como qualquer mensagem), Lambda, **`ecs:RunTask`** (job batch no Fargate — `aws-ecs-fargate`), Step Functions, API.
- **Retry** e **DLQ** próprios; *flexible time window* para espalhar a carga; IAM role do scheduler com **só** `sqs:SendMessage` etc. na fila-alvo.
O consumer deve ser **idempotente** (o agendamento pode entregar mais de uma vez em falhas — `messaging`). Bom padrão para: relatórios noturnos, expiração/limpeza, lembretes, *jobs* por usuário.

## Archive, replay e schema registry

- **Archive**: guarda eventos do bus (filtrável) por N dias; **replay** reenvia um intervalo para o bus — útil para **reprocessar** depois de um bug ou **popular um serviço novo** (limitado em comparação ao replay do Kafka: é reenvio de eventos arquivados, não leitura de offset). Os consumers precisam ser **idempotentes** (vão ver duplicatas).
- **Schema registry/discovery**: o EventBridge **descobre** os schemas dos eventos do bus e gera **bindings de código** (inclusive Java) — ajuda a manter **contrato de evento** e a detectar quebra (`messaging`: evolução só compatível).
- **Cross-account/cross-region**: uma regra pode ter como target **outro bus** em outra conta/região (com *resource policy*) — base de arquiteturas multi-conta (cada time publica no seu bus e compartilha eventos).

## IAM de menor privilégio

Produtor (role da aplicação — IRSA/task role, **nunca access keys**):
```json
{ "Effect": "Allow", "Action": "events:PutEvents", "Resource": "arn:aws:events:us-east-1:123456789012:event-bus/library-bus" }
```
Restrinja também por `events:source`/`events:detail-type` com `Condition` quando quiser que o serviço só publique **os seus** tipos. Consumers **não** precisam de permissão no EventBridge: leem das **filas** (targets). A role que cria regras/targets é de **IaC/deploy**, não da aplicação.

## Observabilidade

Métricas do CloudWatch por regra: **`FailedInvocations`** (entrega ao target falhou), **`ThrottledRules`**, `Invocations`, `MatchedEvents`, `DeadLetterInvocations`. **Alarmes:** `FailedInvocations > 0`, mensagens na **DLQ do target** e na DLQ do consumer, idade da fila-alvo (`ApproximateAgeOfOldestMessage`). Propague `correlationId`/trace no `detail`/headers e logue `eventId` (`observability`, `aws-observability`).

## Testes

- **Unit:** o adapter com o `EventBridgeClient` mockado: com `failedEntryCount = 0` não lança; com `failedEntryCount > 0` **lança** (teste esse caso — é o que previne perda silenciosa). O service com o `EventPublisher` mockado (`testing`).
- **Integration:** LocalStack com `.withServices("events", "sqs")` (`aws-s3-sqs`): crie bus, fila-alvo, regra e target (SDK/`awslocal`), publique e **aguarde a mensagem na fila** com Awaitility; evento que **não casa** com o pattern **não** chega. A cobertura de recursos avançados (Scheduler, archive/replay) no LocalStack pode ser parcial — valide-os na conta de dev.
- **Contrato:** um JSON de exemplo do evento desserializa no record do consumer (pega quebra de schema).

---

## Regras principais

- **EventBridge** para roteamento por conteúdo, eventos de serviços AWS/SaaS e agendamento; SNS+SQS para fan-out de alta vazão; Kafka para replay/streaming.
- **Bus customizado** para os seus eventos; `source` com namespace reverso (nunca `aws.`), `detail-type` no passado, `detail` com **`eventId`**, versão, `occurredAt`, `correlationId`.
- **Sempre verifique `failedEntryCount`** do `PutEvents` (200 não significa sucesso) e re-envie só as falhas; lote ≤ 10 entradas / 256 KB.
- Publique pelo **relay do outbox** (`transactional-outbox`), nunca dentro da transaction do negócio.
- Targets: **uma fila SQS por consumer** com DLQ, queue policy permitindo `events.amazonaws.com` + `aws:SourceArn` da regra; **DLQ e retry policy do target sempre configurados**, com alarme.
- Consumers **idempotentes** (at-least-once; replay duplica).
- **Scheduler** no lugar de `@Scheduled` multiplicado por réplica; consumer idempotente.
- Regras/targets/buses por **IaC**; IAM `events:PutEvents` no ARN do bus, via IRSA/task role.
- Alarmes: `FailedInvocations`, DLQs, idade da fila; testes que cobrem a falha parcial do `PutEvents` e o não-casamento do pattern.
- **Sem Lombok** — deliberado.
