---
name: aws-observability
description: Observabilidade na AWS para Spring Boot — CloudWatch Logs com retenção e Logs Insights, métricas (Micrometer CloudWatch, EMF, Prometheus gerenciado) e seu custo, traces OpenTelemetry/ADOT para o X-Ray, alarmes acionáveis, dashboards e SLOs por plataforma (ECS, EKS, Lambda). Use quando levar logs, métricas e alarmes para a AWS; a base de Actuator está em observability.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md) e [`../observability/SKILL.md`](../observability/SKILL.md) (Actuator, Micrometer, probes, logs JSON, tracing — **a base, não repetida aqui**). Esta skill mostra **para onde esses sinais vão na AWS** e como alarmar.

# Observabilidade na AWS

A aplicação já produz **logs JSON, métricas Micrometer e traces** (`observability`). Na AWS, o trabalho é: **coletar**, **reter a custo controlado**, **consultar**, **alarmar** e **notificar** — sem estourar a conta.

| Sinal | Destino AWS (opções) |
|---|---|
| **Logs** | **CloudWatch Logs** (padrão em ECS/Lambda; em EKS via Fluent Bit/CloudWatch Observability add-on) |
| **Métricas** | **CloudWatch Metrics** (Micrometer CloudWatch ou **EMF**), ou **Amazon Managed Prometheus** + Grafana |
| **Traces** | **AWS X-Ray** via **OpenTelemetry (ADOT collector)** |
| **Alarmes/notificação** | **CloudWatch Alarms** → **SNS** (e-mail, Slack/Chatbot, PagerDuty) |

## 1. Logs — CloudWatch Logs

- **stdout → CloudWatch.** ECS: driver `awslogs` (`aws-ecs-fargate`); Lambda: automático (`aws-lambda`); EKS: **Fluent Bit** DaemonSet ou o add-on **Amazon CloudWatch Observability** (`aws-eks`). A aplicação **não** escreve arquivo de log nem fala com a API do CloudWatch.
- **JSON estruturado** (`logging.structured.format.console: ecs`, `observability`): permite consultar por campo (`level`, `traceId`, `userId`) em vez de grep.
- **Retenção SEMPRE definida** no *log group* (ex.: 30 dias app, 365 auditoria): o **padrão é "nunca expirar"** e vira custo crescente para sempre. Defina por **IaC** (`aws-terraform`: `aws_cloudwatch_log_group { retention_in_days = 30 }`), não pelo console. Dados antigos de longo prazo → exporte para **S3** (barato, com lifecycle).
- **Custo:** o CloudWatch cobra por **GB ingerido** (a maior parte da conta) e por consulta/armazenamento. **Reduza o ingest:** nível `INFO` em produção (nunca `DEBUG` permanente), sem logar payloads inteiros, sem *health checks* poluindo (filtre `/actuator/health` do log de acesso), **sem stack trace repetido** em loop. Alarme de **volume de ingestão** anormal.
- **Dado sensível:** nada de senha, token, CPF, cartão (LGPD). Quem lê logs tem acesso por **IAM**; aplique **data protection policies** do CloudWatch Logs para **mascarar** padrões sensíveis (e-mail, CPF) na ingestão como defesa extra.
- **Logs Insights** (consulta SQL-like sobre JSON):
```
fields @timestamp, level, message, traceId
| filter level = "ERROR"
| sort @timestamp desc
| limit 50
```
```
filter @message like /Exception/
| stats count(*) as errors by bin(5m)
```
- **Metric filters**: transformam um padrão de log em **métrica** (ex.: contar linhas `"level":"ERROR"` por minuto) para alarmar sem instrumentar código. Úteis, mas **prefira métricas reais** do Micrometer para o que importa.
- **Correlação:** o `traceId` no log (`observability`) liga logs ↔ traces ↔ o erro devolvido ao client (`exception-handling`). No Logs Insights, filtre por `traceId` para ver **toda** a história de uma request.

## 2. Métricas

**Opção A — Micrometer → CloudWatch** (a aplicação publica diretamente):
```xml
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-cloudwatch2</artifactId>
</dependency>
```
```yaml
management:
  cloudwatch:
    metrics:
      export:
        namespace: Library/Api
        step: 1m
        batch-size: 20
```
(O BOM do Boot gerencia a versão; o Boot 4 modularizou a auto-configuration — confirme o artifact/propriedades na versão resolvida, `maven-config`.) **Atenção a custo:** o CloudWatch cobra **por métrica customizada (cada combinação única nome + dimensões)** por mês e por chamada de API. **Cardinalidade alta (userId, orderId, URL com parâmetro) explode a fatura** — a regra de tags de `observability` vale **em dobro** aqui. Exporte só o que alarma/dashboard usa (filtros de meter: `management.metrics.enable.*`/`MeterFilter`), com `step` de 1 min.
- A role precisa de **`cloudwatch:PutMetricData`** (com `Condition` `cloudwatch:namespace` = `Library/Api`) — IRSA/task role, **nunca access keys**.

**Opção B — Embedded Metric Format (EMF):** a aplicação (ou o **Powertools Metrics** no Lambda) escreve um **log JSON em formato EMF** e o CloudWatch **extrai as métricas do log** — sem chamadas de API, baixa latência, ideal para **Lambda** (`aws-lambda`) e containers com o agente. As métricas custom continuam sendo cobradas por série.

**Opção C — Prometheus gerenciado + Grafana:** Prometheus (ou ADOT) raspa `/actuator/prometheus` (porta 9090 — `observability`, `kubernetes`) e grava no **Amazon Managed Service for Prometheus**; **Amazon Managed Grafana** para dashboards. Melhor para alta cardinalidade/muitos serviços e para quem já usa PromQL; mais peças que o CloudWatch puro. Em EKS é o caminho comum.

**Métricas dos serviços AWS (grátis, sem código):** ALB (`HTTPCode_Target_5XX_Count`, `TargetResponseTime`), ECS/Container Insights, RDS (`CPUUtilization`, `DatabaseConnections`, `FreeableMemory`), SQS (`ApproximateAgeOfOldestMessage`), Lambda (`Errors`, `Throttles`, `Duration`), DynamoDB (`ThrottledRequests`). **Comece por elas** — cobrem muito do que importa.

## 3. Tracing — X-Ray via OpenTelemetry

O X-Ray tem **SDKs próprios legados**; o caminho atual é **OpenTelemetry** (instrumentação do Spring/Micrometer Tracing → **OTLP**) enviado a um **AWS Distro for OpenTelemetry (ADOT) collector**, que exporta para o **X-Ray**.
```yaml
management:
  tracing:
    sampling:
      probability: 0.1
  otlp:
    tracing:
      endpoint: http://localhost:4318/v1/traces
```
(Confirme o starter/propriedades de OpenTelemetry do Boot 4 em `observability`.)
- **Onde roda o collector:** **ECS** → **sidecar** ADOT na task (`aws-ecs-fargate`); **EKS** → **DaemonSet** ou Deployment ADOT (add-on); **Lambda** → **Lambda layer** do ADOT ou `Tracing: Active` (X-Ray nativo) — `aws-lambda`.
- **Amostragem em produção** (5–20%); 100% só em dev. X-Ray também suporta **regras de amostragem** (por serviço/URL — sempre amostrar erros).
- **Propagação:** use os **builders do Spring** (`RestClient.Builder`) para propagar o contexto; o **ALB** injeta o header `X-Amzn-Trace-Id` (X-Ray o reconhece); **SQS/SNS/EventBridge** propagam via atributos/headers quando instrumentados.
- Permissões do collector: `xray:PutTraceSegments`, `xray:PutTelemetryRecords` (+ `xray:GetSamplingRules/Targets`).
- **CloudWatch Application Signals** coleta métricas de serviço (latência/erro/volume) e **SLOs** automaticamente a partir do OpenTelemetry — alternativa gerenciada para não montar tudo à mão.

## 4. Alarmes — o que alarmar e como

**Alarme bom é acionável** (alguém precisa fazer algo) e **raro**. Alarme que dispara todo dia é ignorado. Siga **RED/USE** (`observability`), no nível de **sintoma** (o usuário sofre?) antes de **causa**:

| Camada | Alarme | Por quê |
|---|---|---|
| Usuário | **Taxa de 5xx do ALB** (> 1–2% por 5 min) via **metric math** (`5XX / RequestCount`) | Erro percebido |
| Usuário | **Latência p99** (`TargetResponseTime`) acima do SLO | Lentidão percebida |
| Serviço | `UnHealthyHostCount > 0` / `RunningTaskCount < desired` | Capacidade perdida |
| Dados | RDS `CPUUtilization`, `DatabaseConnections` perto do limite, `FreeStorageSpace` | Gargalo/esgotamento (`aws-rds-secrets-manager`) |
| Mensageria | **`ApproximateAgeOfOldestMessage`** (consumer não acompanha), **DLQ > 0**, `FailedInvocations` do EventBridge | Atraso e perda (`messaging`) |
| Lambda | `Errors`, `Throttles`, `Duration` p99 perto do timeout | `aws-lambda` |
| Deploy | Evento de **rollback do ECS** / `SERVICE_DEPLOYMENT_FAILED` (EventBridge → SNS) | `aws-ecs-fargate`, `aws-eventbridge` |
| Custo | **AWS Budgets** + alarme de ingestão de logs / `EstimatedCharges` | Evitar susto |

- **Estatística certa:** use **percentis (p99)** para latência (média esconde a cauda) e `Sum`/taxa para erros. **`TreatMissingData`**: para métrica de tráfego, "sem dados" pode significar **queda total** — trate como `breaching` onde faz sentido.
- **Composite alarms** combinam alarmes (ex.: "5xx alto **E** latência alta") para reduzir ruído.
- **Alarme em múltiplos períodos** (`DatapointsToAlarm` 3 de 5) evita falso positivo por pico isolado.
- **Notificação:** alarme → **tópico SNS** → e-mail/**AWS Chatbot** (Slack/Teams)/PagerDuty-OpsGenie. Cada alarme referencia um **runbook** (o que checar primeiro). Defina **severidade** (página à noite × ticket no dia seguinte).
- **Tudo por IaC** (`aws-terraform`: `aws_cloudwatch_metric_alarm`), versionado e revisado — alarme criado no console some e ninguém sabe por quê.

## 5. Dashboards e SLOs

- **Um dashboard por serviço** com os quatro sinais dourados: **tráfego, erros, latência (p50/p95/p99), saturação** (CPU/memória/pool/fila), mais deploys marcados. CloudWatch Dashboards (por IaC) ou Grafana.
- **SLO** (ex.: "99,9% das requests < 500 ms e sem 5xx em 30 dias") e **error budget**: alarme por **burn rate** (consumo rápido do orçamento) é mais útil que limiar fixo. **Application Signals** ajuda a definir SLOs sem montar a métrica à mão.
- **Synthetics (canaries)**: script que chama sua API de fora (login, fluxo crítico) a cada minuto e alarma se falhar — pega o que métricas internas não veem (DNS, certificado expirado, WAF bloqueando).

## 6. Segurança e custo — resumo

- Acesso a logs/métricas por **IAM** de menor privilégio (leitura por log group/ambiente); logs de produção **não** acessíveis a todo mundo.
- **CloudTrail** (auditoria de chamadas de API) e **VPC Flow Logs/ALB access logs** em S3 com lifecycle — para segurança, não para depurar a aplicação.
- Regras de custo: **retenção** curta nos logs, **INFO** em produção, **tags de cardinalidade baixa**, métricas só do que se usa, amostragem de traces, exportar o frio para S3.

---

## Regras principais

- Logs **JSON** em stdout → CloudWatch Logs, com **retenção definida por IaC** (nunca o padrão infinito); nunca dado sensível; mascare com data protection quando preciso; **INFO** em produção.
- Métricas: comece pelas **dos serviços AWS**; Micrometer→CloudWatch/EMF/Prometheus gerenciado conforme o caso; **cardinalidade baixa** (cada série custa); `PutMetricData` restrito por namespace.
- Traces: **OpenTelemetry → ADOT collector → X-Ray**, amostragem 5–20% em produção, builders do Spring para propagar; sidecar (ECS) / DaemonSet (EKS) / layer (Lambda).
- Alarmes **acionáveis**, de **sintoma primeiro** (5xx%, p99, idade da fila, DLQ, tasks/hosts), com percentis, `DatapointsToAlarm`, composite quando preciso; notificação por SNS/Chatbot com **runbook** e severidade.
- **Tudo como código** (alarmes, dashboards, log groups, retenção) em Terraform; SLO e burn rate; canaries para o fluxo crítico.
- IAM mínimo, via IRSA/task role — **nunca access keys**; Budgets e alarme de ingestão para custo.
- **Sem Lombok** — deliberado.
