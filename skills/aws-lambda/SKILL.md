---
name: aws-lambda
description: AWS Lambda em Java — handler puro, Spring Cloud Function ou serverless-java-container, redução de cold start (SnapStart, init fora do handler, memória, arm64), SQS com partial batch failure, Powertools, RDS Proxy, concorrência, IAM, SAM e testes. Use quando criar ou otimizar uma função Lambda ou decidir entre Lambda e containers.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../aws-sdk-java/SKILL.md`](../aws-sdk-java/SKILL.md) e [`../messaging/SKILL.md`](../messaging/SKILL.md) (garantias de entrega e idempotência valem para Lambda).

# AWS Lambda com Java

Lambda executa seu código **sob demanda**, sem servidor para gerenciar, escala de 0 a milhares de execuções e **cobra por duração e invocação** (milissegundos de execução × memória). Ótimo para **handlers de eventos** (SQS, SNS, S3, EventBridge, DynamoDB Streams, agendamentos) e APIs de tráfego baixo/irregular. O ponto fraco do Java é o **cold start** (JVM + classes + framework) — grande parte desta skill trata dele.

## Lambda, ECS ou EKS?

| Critério | Lambda | ECS/Fargate (`aws-ecs-fargate`) | EKS (`aws-eks`) |
|---|---|---|---|
| Carga | Esporádica/picos, **escala a zero** | Estável/contínua | Estável, ecossistema Kubernetes |
| Duração máxima | **15 min** por execução | Ilimitada | Ilimitada |
| Latência | Cold start (mitigável) | Sempre quente | Sempre quente |
| Custo com tráfego alto constante | **Mais caro** | Mais barato | Mais barato |
| Operação | Mínima | Baixa | Alta |
| Bom para | Event handlers, glue, cron, APIs de baixo volume | APIs/serviços Spring completos | Plataforma multi-time |

**Um serviço Spring Boot completo e movimentado** raramente é bom candidato a Lambda: prefira ECS/EKS. Lambda é excelente para **funções pequenas e focadas**. Não passe uma API CRUD inteira para Lambda "porque é serverless".

---

## Três formas de escrever em Java

1. **Handler puro** (`aws-lambda-java-core`/`-events`) — **a melhor para cold start e para a maioria dos event handlers.** Sem framework; inicialização mínima.
2. **Spring Cloud Function** — funções como beans (`Function<I,O>`), com injeção de dependência e *configuration* do Spring; adapta para o Lambda (`FunctionInvoker`). Cold start maior (contexto Spring sobe), mas reaproveita código e padrões do pack.
3. **`aws-serverless-java-container`** — roda uma aplicação **Spring MVC** (controllers) atrás do API Gateway/Function URL. **Cold start mais pesado**; só para migração/prototipagem ou APIs pequenas com **SnapStart**. (Confirme o suporte à sua versão do Spring Boot na documentação do projeto.)

**Recomendação:** event handlers → **handler puro**. Quer reutilizar o modelo de dependências do Spring → **Spring Cloud Function + SnapStart**. API grande → **ECS/EKS**.

Mantenha o código Lambda em um **módulo Maven separado** (`lambda/` ou repositório próprio), com seu próprio `pom.xml` enxuto — **não** empacote o monolito Spring Boot inteiro para uma função.

---

## Cold start — as alavancas (da mais efetiva para a menos)

1. **SnapStart** (runtimes Java gerenciados): a AWS tira um **snapshot** da função **já inicializada** na publicação da versão e restaura dele — corta o cold start em ordem de grandeza (de segundos para centenas de ms) **sem mudar o código**. Cuidados (tem *hooks* via **CRaC**, `org.crac`):
   - Estado criado no init é **compartilhado entre restores**: não guarde nada "único" (UUID, `SecureRandom` seeds, timestamps, conexões de rede) criado no init sem reinicializar no hook `afterRestore`.
   - Conexões abertas no snapshot (database, HTTP) **estão mortas** após restaurar → reabra em `afterRestore`.
   - Funciona em **versões publicadas/aliases**, não em `$LATEST`.
2. **Inicialize fora do handler**: clients do SDK, `JsonMapper`, pools e configuração como **campos `static`/construtor** — executam **uma vez** por ambiente de execução e são **reutilizados** nas invocações seguintes (*warm*). Criar `S3Client` dentro do `handleRequest` paga o custo a cada chamada.
3. **`UrlConnectionHttpClient`** nos clients AWS (`aws-sdk-java`): JAR menor e init muito mais rápido que Apache/Netty. Exclua os HTTP clients não usados.
4. **Menos classes, menos reflexão, menos framework**: sem classpath scanning, sem autoconfiguration pesada, `lazy` onde possível. **Handler puro** elimina a maior parte do custo.
5. **Memória = CPU.** Lambda aloca CPU proporcional à memória: **mais memória costuma deixar mais barato** (menor duração × preço/ms). Meça com **AWS Lambda Power Tuning**; comece com 512 MB–1 GB.
6. **arm64 (Graviton)**: mais barato (~20%) e geralmente mais rápido — use `arm64` salvo dependência nativa x86.
7. **JVM flags** (`JAVA_TOOL_OPTIONS`): `-XX:+TieredCompilation -XX:TieredStopAtLevel=1` acelera o início (menos otimização de pico) — vale para funções curtas **sem** SnapStart; com SnapStart, avalie.
8. **GraalVM native image** (runtime `provided.al2023` com bootstrap): cold start de dezenas de ms; custo: build mais lento/complexo, reflexão/proxies exigem configuração (hints), ecossistema Spring AOT. Só quando SnapStart não basta.
9. **Provisioned concurrency**: mantém N ambientes **sempre prontos** (sem cold start), **pago por hora** — para APIs sensíveis a latência. Combina com SnapStart.

Meça o cold start real (log `Init Duration` no relatório da invocação / métrica no CloudWatch) **antes e depois** de cada mudança (`jvm-performance`: uma alteração por vez).

---

## Handler puro — SQS com *partial batch failure*

```xml
<dependency>
    <groupId>com.amazonaws</groupId>
    <artifactId>aws-lambda-java-core</artifactId>
    <version>${aws-lambda-core.version}</version>
</dependency>
<dependency>
    <groupId>com.amazonaws</groupId>
    <artifactId>aws-lambda-java-events</artifactId>
    <version>${aws-lambda-events.version}</version>
</dependency>
```
(`com.amazonaws:aws-lambda-java-*` são as **libs de runtime do Lambda**, não o SDK v1 — são as corretas; versões em `<properties>`, resolva as atuais.)
```java
public class BookEventHandler implements RequestHandler<SQSEvent, SQSBatchResponse> {

    private static final JsonMapper JSON = JsonMapper.builder().build();
    private static final BookIndexService SERVICE = new BookIndexService();

    @Override
    public SQSBatchResponse handleRequest(SQSEvent event, Context context) {
        var failures = new ArrayList<SQSBatchResponse.BatchItemFailure>();
        for (var record : event.getRecords()) {
            try {
                var payload = JSON.readValue(record.getBody(), BookCreatedEvent.class);
                SERVICE.index(record.getMessageId(), payload);
            } catch (Exception e) {
                context.getLogger().log("Failed message " + record.getMessageId() + ": " + e.getMessage());
                failures.add(new SQSBatchResponse.BatchItemFailure(record.getMessageId()));
            }
        }
        return new SQSBatchResponse(failures);
    }
}
```
- **`SQSBatchResponse` com `batchItemFailures`** (e `ReportBatchItemFailures` no *event source mapping*): só as mensagens que **falharam** voltam à fila; as bem-sucedidas são deletadas. Sem isso, **uma** mensagem ruim faz o **lote inteiro** ser reprocessado (duplicando efeito das boas).
- Entrega **at-least-once** → processamento **idempotente** (`transactional-outbox`, seção do consumer idempotente; ou **Powertools idempotency**, abaixo).
- Os campos `static` (JSON mapper, service/clients) são o "init fora do handler".
- **Log:** nunca imprima payload sensível; prefira **logging estruturado** (Powertools Logging) com o *request id*.
- **Timeout da função** curto e coerente (não o máximo de 15 min por padrão). Para fila SQS de origem, o **visibility timeout da fila ≥ 6× o timeout da função** (recomendação da AWS, para evitar reentrega durante o processamento) e **DLQ** com `maxReceiveCount` na fila (`aws-sns-sqs`).

## Spring Cloud Function (alternativa)

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-function-adapter-aws</artifactId>
</dependency>
```
```java
@SpringBootApplication
public class Startup {

    public static void main(String[] args) {
        SpringApplication.run(Startup.class, args);
    }

    @Bean
    public Function<BookCreatedEvent, Void> indexBook(BookIndexService service) {
        return event -> {
            service.index(event.eventId(), event);
            return null;
        };
    }
}
```
```yaml
spring:
  cloud:
    function:
      definition: indexBook
```
Handler do Lambda: `org.springframework.cloud.function.adapter.aws.FunctionInvoker::handleRequest`. **Sempre com SnapStart** (o contexto Spring leva segundos para subir). A versão do Spring Cloud Function segue o *release train* do Spring Cloud compatível com o Boot do projeto — confirme (`maven-config`). Use o **mesmo `Startup`/estilo do pack** no módulo da função (`scaffold`); o `StartupTests` carrega o contexto.

---

## Idempotência, observabilidade e config: Powertools for AWS Lambda (Java)

O **Powertools for AWS Lambda (Java)** resolve o que todo handler precisa, de forma enxuta:
- **Logging** estruturado em JSON com contexto da invocação (`@Logging`, correlation id).
- **Metrics** via **EMF** (Embedded Metric Format → métricas no CloudWatch **a partir de logs**, sem chamadas de API; `@Metrics`).
- **Tracing** (`@Tracing`) para o **X-Ray**.
- **Idempotency** (`@Idempotent`) com **DynamoDB** como store: a mesma entrada (chave por JMESPath, ex.: `messageId`) executa **uma vez** e as repetições devolvem o resultado salvo (`aws-dynamodb`).
- **Batch** (`SqsBatchProcessor`) — o *partial batch failure* pronto.
- **Parameters** — busca/cache de Secrets Manager e Parameter Store (`aws-parameter-store`), em vez de variável de ambiente com segredo.
Adote por **módulos** (só o que usa) e confirme a versão atual do Powertools V2.

## Banco de dados a partir do Lambda

**Lambda + RDS direto = explosão de conexões** (cada ambiente de execução abre sua conexão; mil execuções concorrentes = mil conexões, o RDS cai). Soluções:
- **RDS Proxy** na frente do RDS (agrupa e reutiliza conexões; autentica por Secrets Manager/IAM) — o caminho recomendado (`aws-rds-secrets-manager`).
- **Limite a concorrência**: *reserved concurrency* da função ao que o banco aguenta.
- Ou use um banco feito para isso: **DynamoDB** (`aws-dynamodb`), sem conexões.
- A função precisa estar na **VPC** para falar com o RDS privado (subnets privadas + security group); isso adiciona acesso à internet só com NAT/VPC endpoints para chamar serviços AWS (`aws-eks`: VPC endpoints).

## Concorrência e proteção

- **Reserved concurrency**: teto de execuções simultâneas da função (protege o banco/APIs downstream **e** limita o custo/descontrole).
- **Provisioned concurrency**: ambientes pré-aquecidos (sem cold start).
- **Falhas assíncronas** (S3/SNS/EventBridge): configure **retries** e **destino de falha / DLQ** (SQS/SNS). Fila SQS de origem: DLQ na própria fila.
- **Timeouts** em toda chamada de saída (`aws-sdk-java`), menores que o timeout da função.
- Evite **recursão acidental** (função que grava no bucket/fila que a dispara): a AWS detecta e interrompe loops simples, mas **desenhe** para não criar.

## IAM

Uma **role de execução por função**, **menor privilégio**: as ações e os ARNs exatos (`sqs:ReceiveMessage/DeleteMessage/GetQueueAttributes` na fila de origem; `dynamodb:PutItem` na tabela; `logs:*` só para o próprio *log group* via `AWSLambdaBasicExecutionRole`). **Nunca** `"Resource": "*"`/`AdministratorAccess`. Sem access keys — a role do Lambda fornece credenciais temporárias (`aws-sdk-java`). **Segredos**: Secrets Manager/Parameter Store lidos em runtime com cache, **não** em variáveis de ambiente em texto (visíveis no console).

## Empacotamento e deploy (SAM)

Empacote como **ZIP** (`maven-shade-plugin`, jar único com dependências, ou `lib/` com jars) ou como **imagem de container** (ECR, até 10 GB — para dependências nativas grandes). Prefira ZIP para cold start. **AWS SAM** (`template.yaml`) descreve função, eventos e permissões:
```yaml
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Globals:
  Function:
    Runtime: java21
    Architectures:
      - arm64
    MemorySize: 1024
    Timeout: 30
    SnapStart:
      ApplyOn: PublishedVersions

Resources:
  BookEventFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: target/book-events.jar
      Handler: br.com.edimilsonldutra.lambda.BookEventHandler::handleRequest
      AutoPublishAlias: live
      Policies:
        - SQSPollerPolicy:
            QueueName: !GetAtt BookQueue.QueueName
      Events:
        BookQueueEvent:
          Type: SQS
          Properties:
            Queue: !GetAtt BookQueue.Arn
            BatchSize: 10
            FunctionResponseTypes:
              - ReportBatchItemFailures

  BookQueue:
    Type: AWS::SQS::Queue
    Properties:
      VisibilityTimeout: 180
      RedrivePolicy:
        deadLetterTargetArn: !GetAtt BookQueueDlq.Arn
        maxReceiveCount: 5

  BookQueueDlq:
    Type: AWS::SQS::Queue
    Properties:
      MessageRetentionPeriod: 1209600
```
(`java21` é exemplo: use o **runtime LTS que o Lambda suporta** na data — confirme na documentação se há runtime para a LTS do projeto; `Timeout: 30` × 6 = 180 de visibility timeout.) Comandos: `sam build`, `sam local invoke -e event.json`, `sam deploy --guided`. O deploy em CI usa **OIDC** (`github-actions-aws`): `sam deploy` na role de deploy. Para infraestrutura maior, **Terraform** (`aws-terraform`) ou CDK em Java.

## Observabilidade

Logs no **CloudWatch Logs** (grupo `/aws/lambda/<função>` — defina **retenção**), métricas padrão (`Invocations`, `Errors`, `Throttles`, `Duration`, `ConcurrentExecutions`, `IteratorAge` para streams) e **X-Ray** (`Tracing: Active`) — `aws-observability`. **Alarmes**: `Errors`, `Throttles`, `DLQ > 0`, `Duration` p99 perto do timeout, `ApproximateAgeOfOldestMessage` da fila de origem.

## Testes

- **Unit test do handler** como qualquer classe Java (instancie o handler, passe um `SQSEvent` montado em memória, assert na `SQSBatchResponse`) — sem Lambda, sem Docker (`testing`). Cubra: lote com uma mensagem ruim devolve **só aquela** em `batchItemFailures`; mensagem duplicada não duplica o efeito.
- **`sam local invoke`/`sam local start-api`** (Docker) para executar com o runtime real.
- **Integration** com LocalStack (Lambda, SQS) via Testcontainers quando precisar do wiring (`aws-sdk-java`); valide **o cold start e SnapStart na conta de dev**, não no emulador.

---

## Regras principais

- Lambda para **handlers de eventos e funções pequenas**; serviço Spring completo e movimentado → ECS/EKS. Duração máx. 15 min.
- **Handler puro** por padrão (melhor cold start); Spring Cloud Function **com SnapStart** quando o Spring agrega; módulo Maven **separado** do monolito.
- Cold start: **SnapStart** (cuidado com estado e conexões no restore), init **fora do handler**, `UrlConnectionHttpClient`, menos framework, **memória certa** (Power Tuning), **arm64**, provisioned concurrency só se preciso; **meça antes/depois**.
- SQS: **`ReportBatchItemFailures`** + `SQSBatchResponse`; visibility timeout ≥ 6× o timeout da função; **DLQ** na fila; processamento **idempotente** (Powertools Idempotency/tabela de processados).
- Lambda + RDS **só com RDS Proxy** e *reserved concurrency*; ou DynamoDB.
- Role de execução **por função**, menor privilégio; **nunca** access keys; segredos por Secrets Manager/Parameter Store em runtime, não env em texto.
- SAM/Terraform como IaC; deploy por OIDC; runtime LTS suportado confirmado na documentação.
- Logs estruturados com retenção; alarmes em Errors, Throttles, DLQ, Duration p99.
- Teste o handler como classe Java; `sam local` e LocalStack para o wiring; valide SnapStart na conta de dev.
- **Sem Lombok** — deliberado.
