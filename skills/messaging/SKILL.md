---
name: messaging
description: Ponto de partida de mensageria — quando usar (e quando não), comparação de Kafka, RabbitMQ, Artemis, SQS/SNS, EventBridge e outros, desenho de eventos, garantias de entrega, idempotência, ordenação, retry, DLQ, schema, observabilidade, segurança e anti-patterns como dual write. Use para escolher um broker ou antes de kafka, rabbitmq, activemq-artemis, aws-sns-sqs ou transactional-outbox.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) e [`../code-style/SKILL.md`](../code-style/SKILL.md) para as preferências do projeto, o package layout base e as convenções de code style.

# Mensageria — visão geral e escolha de ferramenta

Esta skill **não gera código de broker**: ela ajuda a decidir **se** e **qual** mensageria usar e define as regras comuns a todas. Depois vá para a skill da ferramenta escolhida: `kafka`, `rabbitmq`, `activemq-artemis`, `aws-sns-sqs` (e `aws-s3-sqs` para SQS/S3 básico) — e **sempre** `transactional-outbox` quando o evento nasce de uma mudança no database.

---

## 1. Você realmente precisa de mensageria?

Mensageria troca **simplicidade** por **desacoplamento e resiliência**: processamento assíncrono, consistência eventual, mais peças para operar, debugging mais difícil. Use quando houver motivo concreto:

| Motivo válido | Exemplo |
|---|---|
| **Desacoplar** produtor e consumidor (tempo e disponibilidade) | Pedido criado → faturamento, estoque e e-mail reagem sem a API esperar |
| **Absorver picos** (buffer) | Importação de 100 mil linhas; campanha que gera rajada de requests |
| **Trabalho demorado** fora da request | Gerar PDF, enviar e-mail, processar upload |
| **Fan-out**: um fato, vários interessados | `BookCreated` → search index, cache, analytics |
| **Integração entre serviços** com tolerância a falha | Serviço B fora do ar não derruba o A |
| **Streaming/replay de eventos** | Reprocessar o histórico, event sourcing, CDC, analytics em tempo real |

**Não use** quando uma chamada síncrona resolve (você precisa da resposta *agora* para responder ao client), quando é só um módulo dentro do mesmo monólito (use um `ApplicationEvent`/chamada de método), ou como "banco de dados" (fila não é storage consultável). Request/reply sobre broker só com motivo forte. **Monólito modular + eventos internos** costuma bastar no começo (veja `architect`).

---

## 2. Comparação das ferramentas do mercado

| Ferramenta | Modelo | Ponto forte | Atenção | Use quando |
|---|---|---|---|---|
| **Apache Kafka** | Log distribuído particionado, retenção, consumer groups | Throughput enorme, **replay**, ordem por partição/chave, ecossistema (Connect, Streams, Schema Registry) | Operação complexa, curva de aprendizado, partições/rebalances, sem roteamento sofisticado | Streaming de eventos, event-driven em escala, CDC (Debezium), analytics, múltiplos consumidores independentes lendo o mesmo histórico |
| **RabbitMQ** | Broker "esperto": exchanges + filas + routing keys (AMQP) | Roteamento flexível (direct/topic/fanout/headers), baixa latência, prioridade, TTL, DLX, simples de operar | Não é log (mensagem consumida some; replay limitado — *streams* existem), throughput menor que Kafka | Filas de **tarefas/comandos**, roteamento complexo, workflows, integrações empresariais |
| **ActiveMQ Artemis** (e Classic) | Broker **JMS** (queues/topics), protocolos AMQP/MQTT/STOMP | Padrão **JMS**, transações XA, legado e ecossistema Java EE/Jakarta | Menor adoção em greenfield | Sistema que **exige JMS**, migração de legado, integração corporativa |
| **Amazon SQS** | Fila gerenciada (Standard/FIFO) | **Zero operação**, escala automática, simples, barato, DLQ nativa | Sem replay, sem roteamento, *at-least-once*, latência de polling | Filas de trabalho na AWS, desacoplar serviços, picos |
| **Amazon SNS** | Pub/sub gerenciado (topics) | **Fan-out** para SQS/Lambda/HTTP/e-mail, filter policies | Sem retenção; combine com SQS | Um evento → várias filas (padrão **SNS → SQS**) |
| **Amazon EventBridge** | Event bus com regras e roteamento | Integra serviços AWS/SaaS, schema registry, agendamento | Latência e limites maiores que streaming; menos throughput | Eventos de infraestrutura/SaaS, orquestração leve |
| **Amazon Kinesis** | Stream gerenciado (shards) | Streaming gerenciado na AWS | Modelo e limites próprios; menos ecossistema que Kafka | Streaming dentro da AWS sem operar Kafka |
| **Amazon MSK / Amazon MQ** | Kafka / RabbitMQ-ActiveMQ **gerenciados** | Mesmo modelo, sem operar o cluster | Custo; ainda exige conhecer o broker | Quer Kafka/RabbitMQ sem administrar as máquinas |
| **Apache Pulsar** | Log + filas, multi-tenant, tiered storage | Multi-tenancy, georreplicação, armazenamento em camadas | Ecossistema/mão de obra menor | Multi-tenant em larga escala |
| **NATS / JetStream** | Mensageria leve, cloud-native | Latência mínima, simples, persistência com JetStream | Ecossistema menor no mundo Java/Spring | Edge/IoT, microsserviços leves |
| **Google Pub/Sub / Azure Service Bus** | Serviços gerenciados de cada cloud | Equivalentes de SNS+SQS (Service Bus: sessões, transações, DLQ) | Acoplamento à cloud | Quando a empresa roda nessas clouds |
| **Redis Streams** | Stream leve no Redis | Já tem Redis; simples | Durabilidade e escala limitadas | Casos pequenos/menos críticos |

Spring Boot tem suporte de primeira classe para **Kafka**, **RabbitMQ (AMQP)** e **JMS/Artemis**; Spring Cloud AWS cobre **SQS/SNS**; as demais costumam ter starter próprio do fornecedor ou Spring Cloud Stream.

### Como escolher (árvore rápida)

1. **Precisa de replay, retenção longa, ordem em alta escala, vários consumidores lendo o mesmo histórico, CDC ou stream processing?** → **Kafka** (ou MSK/Kinesis na AWS).
2. **É fila de tarefas/comandos com roteamento flexível, prioridade, atraso, TTL?** → **RabbitMQ** (ou Amazon MQ).
3. **Está na AWS e quer zero operação?** → **SQS** (fila) e **SNS + SQS** (fan-out). O padrão para a maioria das APIs pequenas/médias na AWS.
4. **Requisito de JMS/XA ou legado?** → **ActiveMQ Artemis**.
5. **Equipe pequena, sem experiência com brokers?** → comece pelo **gerenciado mais simples** (SQS, ou RabbitMQ/Amazon MQ) e evolua; Kafka só se o caso de uso o justificar.

**Não misture sem necessidade:** um broker por necessidade. Cada broker novo é custo de operação, monitoramento, segurança e conhecimento da equipe. Registre a decisão em um ADR (`architect`).

---

## 3. Desenho de mensagens e eventos

**Comando × evento.** *Comando* = pedido para algo acontecer (`ProcessPayment`) — um destinatário, pode ser rejeitado, nome no imperativo. *Evento* = fato que **já aconteceu** (`BookCreated`) — zero ou N interessados, imutável, nome no **passado**. Prefira **eventos** para integração entre bounded contexts: o produtor não conhece os consumidores.

**Envelope e payload.** Todo evento carrega metadados e dados:
```json
{
  "eventId": "6f1c2a52-9d0e-4f7e-8d0f-1a2b3c4d5e6f",
  "eventType": "BookCreated",
  "eventVersion": 1,
  "occurredAt": "2026-01-15T10:30:00Z",
  "correlationId": "c3f1...",
  "payload": { "id": 42, "title": "Clean Code" }
}
```
- **`eventId` único** é a base da idempotência do consumer.
- **`occurredAt`** em UTC (ISO-8601); **`correlationId`/trace id** para rastrear de ponta a ponta (`observability`).
- Em Java, o evento é um **record** imutável (`java-modern-features`): `public record BookCreatedEvent(String eventId, long id, String title, Instant occurredAt) {}`.
- **Payload enxuto vs. estado completo:** evento *notification* (só o `id`, o consumer busca o resto — acopla ao produtor e sofre race) × *event-carried state transfer* (carrega os campos necessários — desacopla, mas aumenta a mensagem e exige versionamento). Para a maioria dos casos, **carregue o estado que o consumer precisa**, sem entity inteira e **sem dado sensível** desnecessário.
- **Nunca publique a entity JPA**: publique um DTO/record dedicado ao evento (contrato público, evolui separado do banco).
- Mensagens **pequenas** (limite do broker: SQS 256 KB; Kafka 1 MB por padrão). Payload grande → arquivo no S3 e a **referência** na mensagem (`aws-s3-sqs`).
- **Nome de tópico/fila/exchange** padronizado e versionado: `<contexto>.<entidade>.<evento>.v1` (`library.book.created.v1`), vindo de configuração, nunca hardcoded.

**Evolução de schema** (a mensagem vive mais que o deploy): só mudanças **compatíveis**: adicionar campo **opcional**, nunca renomear/remover/mudar tipo. Consumers **ignoram campos desconhecidos** (o Jackson 3 já faz isso por padrão — `web-config`). Quebra de contrato = **novo tópico/versão** (`.v2`) com período de convivência. Em Kafka em escala, use **Schema Registry** (Avro/Protobuf/JSON Schema) com regras de compatibilidade.

---

## 4. Garantias de entrega — o que você pode e não pode prometer

| Semântica | Significado | Realidade |
|---|---|---|
| At-most-once | Pode perder, nunca duplica | Raro; só para dado descartável |
| **At-least-once** | Nunca perde, **pode duplicar** | **O padrão** de SQS, RabbitMQ, Kafka (com ack/commit após processar) |
| Exactly-once | Processa exatamente uma vez | Só em escopos restritos (Kafka transactions entre tópicos). **Fim a fim com efeito externo, na prática é *effectively-once*: at-least-once + consumer idempotente.** |

**Regra de ouro: projete todo consumer para receber a mesma mensagem duas vezes.** Estratégias de idempotência:
1. **Operação naturalmente idempotente** (`UPSERT`, `SET status = 'PAID'`).
2. **Tabela de mensagens processadas** com `eventId` como chave única, gravada **na mesma transaction** do efeito; violação de chave = duplicata, ignore (`transactional-outbox`, seção do consumer idempotente).
3. **Chave de idempotência** em chamadas externas (pagamento) repassada ao provedor.

**Dual write é o pior erro:** gravar no database **e** publicar no broker são dois sistemas, sem transação comum. Se publicar falha depois do commit (ou o contrário), o estado fica inconsistente e **ninguém percebe**. A solução é o **transactional outbox** — **leia `transactional-outbox` antes de publicar eventos a partir de uma mudança de dados.** Para transações de negócio que atravessam serviços veja `saga-pattern`; para a idempotência dos consumers e das APIs, `idempotency`; para o desenho geral (quando dividir em serviços), `microservices`.

**Ordenação.** Garantida só dentro de uma **unidade**: partição (Kafka, escolha a **key** = id do agregado), fila FIFO/message group (SQS FIFO), fila única com um consumer (RabbitMQ). Mais consumers concorrentes ⇒ menos ordem. Desenhe consumers que **tolerem desordem** (versão/timestamp do agregado, ignore evento antigo) sempre que possível.

---

## 5. Falhas: retry, DLQ e poison messages

- **Erros transitórios** (rede, deadlock, serviço externo fora): **retry com backoff exponencial e jitter**, número **limitado** de tentativas. Retry infinito imediato derruba o consumer e o downstream.
- **Erros permanentes** (payload inválido, regra de negócio violada): **não retente** — vá direto para a DLQ. Diferencie as exceptions (`NotRetryable`).
- **DLQ (dead-letter queue/topic) obrigatória em todo consumer**, com alarme em "mensagens na DLQ > 0" e **processo definido** para analisar e reprocessar (redrive) depois de corrigir a causa. Sem DLQ, uma *poison message* trava a fila (Kafka: bloqueia a partição) ou é perdida.
- **Retry não bloqueante** (retry topics/filas com TTL) evita parar a fila inteira por uma mensagem lenta — Kafka `@RetryableTopic`, RabbitMQ TTL+DLX, SQS visibility timeout.
- **Timeout** em tudo que o consumer chama; consumer lento sem timeout vira *rebalance* (Kafka) ou mensagem reentregue (SQS).
- **Backpressure:** limite a concorrência e o prefetch/`max.poll.records` ao que o database e as APIs downstream aguentam (`jvm-performance`: pool de conexões).
- **Não faça I/O externo demorado dentro de uma transaction** do consumer.

## 6. Observabilidade

Monitore o **atraso**, não só se o processo está de pé:
- **Lag** do consumer (Kafka `records-lag-max`; SQS `ApproximateAgeOfOldestMessage`; RabbitMQ `messages_ready`) — o alerta mais importante.
- **Profundidade da fila e da DLQ**, taxa de publicação × consumo, taxa de erro, tempo de processamento (`Timer` Micrometer — `observability`).
- **Trace e correlation id** propagados nos *headers* da mensagem (o Micrometer Tracing instrumenta Kafka/RabbitMQ/JMS quando `observation` está habilitada).
- Logue `eventId`/`eventType`/chave a cada processamento (sem payload sensível).
- Liveness **não** depende do broker; readiness pode depender se o pod é inútil sem ele (`observability`, `kubernetes`).

## 7. Segurança

- **TLS** em trânsito; autenticação (Kafka SASL/SCRAM ou IAM no MSK; RabbitMQ usuários/TLS; SQS/SNS por **IAM** — nunca access keys, `aws-eks`).
- **Menor privilégio por tópico/fila**: o serviço produtor só publica, o consumer só consome (ACLs/IAM por recurso).
- **Sem dado pessoal desnecessário** na mensagem (LGPD); mensagens ficam retidas e replicadas — criptografe em repouso (KMS/SSE) quando sensível.
- **Valide e desserialize com segurança:** nunca aceite tipos arbitrários na desserialização (Kafka `spring.json.trusted.packages` **restrito**, nunca `*`); trate o conteúdo da mensagem como **input não confiável**.
- Credenciais do broker no Secrets Manager/Secret, não no Git (`aws-rds-secrets-manager`, `kubernetes`).

## 8. Package layout (estende `code-organization`)

```
br.com.edimilsonldutra/
└── messaging/
    ├── event/                  # records dos eventos (contrato público)
    │   └── BookCreatedEvent.java
    ├── publisher/              # quem publica (usa o broker)
    │   └── BookEventPublisher.java
    ├── listener/               # quem consome
    │   └── BookEventListener.java
    └── config/                 # beans do broker (tópicos/filas, converters, error handlers)
        └── KafkaConfig.java
```
Nomes: `*Event`, `*EventPublisher`, `*EventListener`. O **service** chama o publisher (ou grava no outbox); o **controller** nunca fala com o broker. Listener é fino: valida, delega ao **service** e deixa o `@Transactional` lá.

## 9. Testes

- **Unit:** o service e o listener (`testing`) com o publisher/dependências mockados.
- **Integration com o broker real em container** (Testcontainers + `@ServiceConnection`): Kafka (`org.testcontainers.kafka.KafkaContainer`), RabbitMQ (`org.testcontainers.rabbitmq.RabbitMQContainer`), LocalStack para SQS/SNS (`aws-s3-sqs`). Teste: publica → o consumer processa → o efeito aparece (use **Awaitility**, nunca `Thread.sleep`); duplicata não duplica o efeito; mensagem inválida vai para a DLQ.
- Teste de **contrato** do evento (um JSON de exemplo desserializa no consumer) para pegar quebra de schema.

## 10. Anti-patterns

- **Dual write** (salvar e publicar sem outbox).
- Consumer **não idempotente**; confiar em "exactly-once" fim a fim.
- **Sem DLQ**, ou retry infinito/imediato.
- Publicar **entities** ou payloads gigantes; evento sem `eventId`/versão.
- Usar a fila como **banco de dados** ou para request/reply síncrono sem necessidade.
- **Integração por database compartilhado** disfarçada de mensageria.
- Tópicos/filas **criados à mão** em cada ambiente, nomes inconsistentes, sem versão.
- Deserialização com `trusted.packages=*`.
- Mais de um broker sem justificativa; não monitorar lag/DLQ.
- Evento que é na verdade um **comando** disfarçado ("`UpdateStockEvent`").

---

## Regras principais

- Só use mensageria com motivo concreto (desacoplar, picos, fan-out, replay); senão chame síncrono ou use eventos internos.
- Um broker por necessidade; escolha pela árvore da seção 2 e registre em um ADR.
- Evento = fato no passado, com `eventId` único, versão, `occurredAt`, `correlationId`; record dedicado, **nunca entity**; evolução só compatível.
- **At-least-once + consumer idempotente.** Projete para duplicata e desordem.
- **Nunca dual write:** `transactional-outbox` para eventos originados no database.
- Retry limitado com backoff, DLQ obrigatória com alarme e processo de reprocessamento; erros permanentes não retentam.
- Monitore lag, profundidade da fila/DLQ e idade da mensagem mais antiga; propague trace/correlation id.
- TLS, IAM/ACL por recurso com menor privilégio, sem dado pessoal desnecessário, desserialização restrita.
- Testes com o broker real em container, Awaitility, e casos de duplicata e DLQ.
- **Sem Lombok** — deliberado.
