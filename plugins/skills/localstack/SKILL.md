---
name: localstack
description: LocalStack para desenvolver e testar integrações AWS sem conta — o que ele prova e o que NÃO prova (IAM, desempenho), docker-compose com init scripts, profile local com trava contra a AWS real, Testcontainers, Terraform contra o emulador, CI e fidelidade por serviço. Use quando rodar ou testar S3, SQS, SNS, DynamoDB e afins localmente.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../testing/SKILL.md`](../testing/SKILL.md) e [`../aws-sdk-java/SKILL.md`](../aws-sdk-java/SKILL.md) (clients, credenciais, `endpointOverride`). Esta skill é a **referência única de LocalStack**: as skills `aws-s3-sqs`, `aws-sns-sqs`, `aws-dynamodb`, `aws-eventbridge`, `aws-ses`, `aws-parameter-store` e `aws-lambda` apontam para cá nos seus testes.

# LocalStack

O **LocalStack** emula serviços da AWS (S3, SQS, SNS, DynamoDB, EventBridge, Secrets Manager, SSM, SES, Lambda, Kinesis, API Gateway e outros) em **um único container** que responde na porta **4566**. Você desenvolve e testa a integração com a AWS **sem conta, sem custo, sem internet e sem risco** de apagar algo de verdade.

> **Licenciamento e imagem:** o modelo do LocalStack (edição *Community* gratuita × planos pagos, e se a imagem exige **conta/auth token**) **mudou ao longo do tempo**. **Confirme na documentação atual** qual imagem usar, se um token é necessário e quais serviços estão em cada edição **antes** de padronizar a equipe. Nunca commite o token (variável de ambiente / secret do CI).

## O que o LocalStack prova — e o que NÃO prova

| Prova ✅ | **Não** prova ❌ |
|---|---|
| Que **seu código** chama a API certa com os parâmetros certos (nome do bucket, formato da mensagem, expressão do DynamoDB) | **IAM/permissões**: por padrão o LocalStack **não aplica** policies — tudo "funciona" local e dá `AccessDenied` na AWS |
| Serialização, mapeamento, tratamento de erro da sua aplicação | **Desempenho**, latência, *throttling*, cotas e limites reais |
| O fluxo ponta a ponta (publica → fila → consumer → efeito) | **Consistência eventual** real (ex.: GSI do DynamoDB atualiza "na hora" no emulador) |
| Infra como código (`terraform plan/apply`) sintaticamente correta | **Rede**: VPC, security groups, endpoints privados, DNS real |
| Testes que rodam **rápido e offline** no CI | **Cold start** de Lambda, SnapStart, comportamento de ECS/EKS/RDS reais |

**Regra de ouro:** LocalStack é para a **camada de integração do seu código**, **não** para validar permissões, desempenho ou infraestrutura de rede. Esses pontos você valida **numa conta AWS de desenvolvimento** (teste de integração real em job separado, `github-actions-aws`) e com ferramentas próprias — **IAM Access Analyzer / policy simulator** para as policies. Um teste verde no LocalStack **não** significa "funciona em produção".

---

## 1. Ambiente local (docker-compose)

```yaml
services:
  localstack:
    image: localstack/localstack:4.0.0
    ports:
      - "127.0.0.1:4566:4566"
    environment:
      SERVICES: s3,sqs,sns,dynamodb,events,ssm,secretsmanager
      LOCALSTACK_AUTH_TOKEN: ${LOCALSTACK_AUTH_TOKEN:-}
    volumes:
      - ./localstack/init:/etc/localstack/init/ready.d
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4566/_localstack/health"]
      interval: 5s
      timeout: 5s
      retries: 20
```
(`4.0.0` é só ilustração: **fixe uma tag de versão testada pela equipe** — nunca `latest`, que muda comportamento sem aviso e quebra o CI do nada.)
- **`127.0.0.1:4566`**: publica a porta **somente no loopback** — o emulador não deve ficar acessível na rede do escritório/Wi-Fi.
- **`SERVICES`** limita o que sobe (inicialização mais rápida, menos memória). Liste só o que o projeto usa.
- **Lambda e outros serviços que executam containers** precisam do socket do Docker (`- /var/run/docker.sock:/var/run/docker.sock`). **Isso dá ao container controle do Docker do host** — monte **só** quando for usar Lambda, e nunca em máquina/CI compartilhados sem necessidade.
- Persistência de dados entre reinícios é recurso de **edição paga** em alguns modelos; por padrão o estado **some** ao parar o container (o que é bom para testes: **reprodutível**). Recrie o estado por **init scripts**.

### Init scripts — recursos criados no startup

Todo script em `/etc/localstack/init/ready.d` roda **quando o LocalStack está pronto**. Assim o ambiente local sobe **sempre igual** (`localstack/init/01-resources.sh`):
```bash
#!/bin/bash
set -euo pipefail

awslocal s3 mb s3://library-uploads

awslocal sqs create-queue --queue-name library-events-dlq
awslocal sqs create-queue --queue-name library-events \
  --attributes '{"VisibilityTimeout":"60","RedrivePolicy":"{\"deadLetterTargetArn\":\"arn:aws:sqs:us-east-1:000000000000:library-events-dlq\",\"maxReceiveCount\":\"5\"}"}'

awslocal sns create-topic --name library-book-events

awslocal dynamodb create-table \
  --table-name books-local \
  --attribute-definitions AttributeName=id,AttributeType=S \
  --key-schema AttributeName=id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```
- O **account id** padrão do LocalStack é **`000000000000`** (usado nos ARNs). A região padrão: `us-east-1`.
- **`awslocal`** é o `aws` CLI já apontado para `localhost:4566` (instale com `pip install awscli-local`; dentro do container do LocalStack ele já existe). Sem ele: `aws --endpoint-url=http://localhost:4566 ...`.
- **Windows:** o script precisa de **final de linha LF** e bit executável — `CRLF` quebra o `bash` (`/bin/bash^M: bad interpreter`). Garanta com `.gitattributes`: `*.sh text eol=lf`.
- Para **espelhar a produção**, mantenha os nomes/atributos do script **iguais aos do IaC** (`aws-terraform`) — ou aplique **o próprio Terraform** contra o LocalStack (seção 5) e deixe de duplicar.
- Verifique o estado: `curl http://localhost:4566/_localstack/health` (serviços) e `curl http://localhost:4566/_localstack/init/ready` (init scripts concluídos).

Comandos úteis:
```bash
docker compose up -d localstack
awslocal sqs list-queues
awslocal sqs receive-message --queue-url http://sqs.us-east-1.localhost.localstack.cloud:4566/000000000000/library-events
awslocal s3 ls s3://library-uploads
awslocal dynamodb scan --table-name books-local
docker compose logs -f localstack
```
(`dynamodb scan` é aceitável **aqui, para depurar**; na aplicação, não — `aws-dynamodb`.)

---

## 2. Spring Boot: profile `local`

```yaml
spring:
  cloud:
    aws:
      endpoint: http://localhost:4566
      region:
        static: us-east-1
      credentials:
        access-key: test
        secret-key: test
      s3:
        path-style-access-enabled: true

app:
  aws:
    bucket: library-uploads
    queue: library-events
    topic: library-book-events
```
Em **`application-local.yml`** (ativado por `SPRING_PROFILES_ACTIVE=local`). As credenciais `test/test` são **as falsas do LocalStack** — o único caso em que credencial fixa em arquivo é aceitável, e **somente** neste profile.
- **`path-style-access-enabled: true`** para o S3: com `localhost` o endereçamento por subdomínio (`bucket.localhost`) não resolve; path-style (`localhost:4566/bucket`) funciona.
- **Nunca** coloque `endpoint`/credenciais no `application.yml` base nem em profile de produção.

**SDK puro** (serviços sem starter, como EventBridge — `aws-sdk-java`): torne o `endpointOverride` **opcional e à prova de erro**:
```java
@Configuration
public class AwsClientsConfig {

    @Value("${app.aws.endpoint-override:}")
    private String endpointOverride;

    @Bean(destroyMethod = "close")
    EventBridgeClient eventBridgeClient() {
        var builder = EventBridgeClient.builder();
        if (!endpointOverride.isBlank()) {
            var uri = URI.create(endpointOverride);
            Assert.isTrue("localhost".equals(uri.getHost()) || "localstack".equals(uri.getHost()),
                    "endpoint-override may only point to a local emulator, but was " + uri);
            builder.endpointOverride(uri)
                    .region(Region.US_EAST_1)
                    .credentialsProvider(StaticCredentialsProvider.create(AwsBasicCredentials.create("test", "test")));
        }
        return builder.build();
    }
}
```
**A trava (`Assert.isTrue`) é a parte importante:** se alguém copiar a property de endpoint para um ambiente real por engano, a aplicação **não sobe** em vez de silenciosamente enviar para o lugar errado — e o contrário também não ocorre: sem a property, o client usa a **default chain** (IRSA/task role), sem nenhuma credencial fixa.

**Aplicação dentro do docker-compose** (não no IDE): o endpoint não é `localhost` (isso seria o próprio container da app) e sim o **nome do serviço**: `http://localstack:4566` (`docker-and-docker-compose`: use o nome do serviço, não `localhost`). Isso é a causa de "connection refused" mais comum. Garanta que o host `localstack` esteja na lista permitida da trava acima.

---

## 3. Testes de integração com Testcontainers

Como em `integration-testing`/`aws-s3-sqs`, o container do LocalStack sobe **pelo teste** (a mesma imagem/tag do compose, para o ambiente local e o CI se comportarem igual).

```xml
<dependency>
    <groupId>org.testcontainers</groupId>
    <artifactId>testcontainers-localstack</artifactId>
    <scope>test</scope>
</dependency>
```
**Container compartilhado** pela suíte inteira (subir um por classe é lento):
```java
@SpringBootTest
public abstract class AbstractAwsIntegrationTest {

    static final LocalStackContainer localstack = new LocalStackContainer(
            DockerImageName.parse("localstack/localstack:4.0.0"))
            .withServices("s3", "sqs", "sns", "dynamodb");

    static {
        localstack.start();
    }

    @DynamicPropertySource
    static void aws(DynamicPropertyRegistry registry) {
        registry.add("spring.cloud.aws.endpoint", localstack::getEndpoint);
        registry.add("spring.cloud.aws.region.static", localstack::getRegion);
        registry.add("spring.cloud.aws.credentials.access-key", localstack::getAccessKey);
        registry.add("spring.cloud.aws.credentials.secret-key", localstack::getSecretKey);
        registry.add("spring.cloud.aws.s3.path-style-access-enabled", () -> "true");
    }
}
```
- O container sobe em **porta aleatória**: sempre leia `getEndpoint()` (nunca fixe 4566 no teste, senão colide com o LocalStack do compose rodando).
- `withServices(...)` com **strings** (Testcontainers 2). O Spring Cloud AWS também oferece integração `@ServiceConnection` para LocalStack em módulo próprio — **confirme na versão** que usa; `@DynamicPropertySource` acima funciona em qualquer versão.
- Para reaproveitar o container entre execuções **na sua máquina**, `.withReuse(true)` + `testcontainers.reuse.enable=true` em `~/.testcontainers.properties` (acelera o ciclo; **não** use no CI).
- A **mesma tag de imagem** do compose evita "passa no meu, falha no CI".

**Provisione os recursos no teste** (não dependa de estado do compose):
```java
@BeforeAll
static void createResources() throws Exception {
    localstack.execInContainer("awslocal", "s3", "mb", "s3://test-uploads");
    localstack.execInContainer("awslocal", "sqs", "create-queue", "--queue-name", "test-events");
}
```
(Ou crie com os clients do SDK, ou **aplique o Terraform do projeto** — seção 5.) O nome do recurso vem da **configuração de teste** (`app.aws.bucket: test-uploads`).

**Isole os testes sem limpar o mundo todo:** nomes **únicos por teste** (`"test-events-" + UUID`) em vez de apagar recursos entre testes — evita interferência e dispensa cleanup frágil.

```java
class BookEventIntegrationTest extends AbstractAwsIntegrationTest {

    @Autowired
    private BookEventPublisher publisher;

    @Autowired
    private BookIndexRepository index;

    @Test
    void consumerProcessesTheEventOnlyOnce() {
        var event = new BookCreatedEvent(UUID.randomUUID().toString(), 42L, "Clean Code", Instant.now());

        publisher.bookCreated(event);
        publisher.bookCreated(event);

        await().atMost(Duration.ofSeconds(20))
                .untilAsserted(() -> assertThat(index.countByBookId(42L)).isEqualTo(1));
    }
}
```
- **Awaitility, nunca `Thread.sleep`**: o fluxo é assíncrono.
- Cubra o que o emulador **consegue** provar: caminho feliz, **duplicata/idempotência**, **mensagem inválida → DLQ**, tratamento de erro do SDK (bucket inexistente → exceção de domínio). Para o database use o **banco real em outro container** (`integration-testing`), não o emulador.
- **Poucos** testes com LocalStack (são integração, mais lentos): a regra de negócio fica em unit tests (`testing`).

---

## 4. Fidelidade por serviço (varia por edição e versão — confirme a tabela de cobertura atual)

| Serviço | Uso típico no LocalStack |
|---|---|
| **S3, SQS, SNS, DynamoDB** | **Muito bom** — o caso de uso principal; comportamento próximo do real |
| **EventBridge, Secrets Manager, SSM (Parameter Store), SES, Kinesis, CloudWatch Logs** | Bom para o **fluxo da aplicação**; recursos avançados podem ser parciais |
| **Lambda** | Funciona (executa em container; exige socket do Docker); **cold start/SnapStart não** são representativos |
| **API Gateway, Step Functions, Scheduler** | Cobertura parcial/variável |
| **Cognito, RDS, ElastiCache, ECS, EKS, MSK** | Normalmente **edição paga** ou emulação limitada — para RDS/Redis/Kafka prefira **containers reais** (`integration-testing`, `caching`, `kafka`); Cognito: mocks com `jwt()` (`aws-cognito`) e conta de dev |
| **IAM (aplicação de policies)** | **Não aplicado** por padrão (aplicar é recurso pago) — veja a seção 6 |
| **Keyspaces** | **Sem emulação fiel** — Cassandra em container + conta de dev (`aws-keyspaces`) |

---

## 5. Infraestrutura como código contra o LocalStack

O mesmo **Terraform** que cria a infra real pode rodar contra o emulador, validando sintaxe, dependências e a topologia (fila + DLQ + assinatura) **antes** de gastar na AWS (`aws-terraform`):
```hcl
provider "aws" {
  region                      = "us-east-1"
  access_key                  = "test"
  secret_key                  = "test"
  skip_credentials_validation = true
  skip_metadata_api_check     = true
  skip_requesting_account_id  = true

  s3_use_path_style = true

  endpoints {
    s3       = "http://localhost:4566"
    sqs      = "http://localhost:4566"
    sns      = "http://localhost:4566"
    dynamodb = "http://localhost:4566"
  }
}
```
Use este bloco **só** num diretório/ambiente `envs/local` (**nunca** no de prod; ele fica ao lado de `envs/dev`, `envs/prod` — `aws-terraform`). O wrapper **`tflocal`** gera essa configuração por você. Isso substitui o `01-resources.sh` por **a mesma fonte da verdade** do IaC. (Para CDK há o `cdklocal`; para SAM, `samlocal` — `aws-lambda`.)

---

## 6. Armadilhas (e como se proteger delas)

1. **IAM não é aplicado → falsa sensação de segurança.** Tudo passa no LocalStack e quebra com `AccessDenied` na AWS. *Proteção:* valide as policies com **IAM Access Analyzer / policy simulator**; mantenha a policy **mínima como código** (`aws-terraform`); rode **testes de integração reais na conta de dev** (job do CI). O `code-reviewer` checa as policies (`Action`/`Resource` exatos).
2. **Políticas de recurso (queue policy do SNS→SQS, policy do bucket) podem não ser verificadas** no emulador: mensagens "chegam" local e **não chegam** na AWS por falta da `Condition aws:SourceArn`. *Proteção:* escreva a policy **sempre** (`aws-sns-sqs`) e valide na conta de dev.
3. **Consistência é melhor do que a real:** GSI do DynamoDB, listagens do S3 etc. aparecem "instantaneamente". Seu teste não prova que o código tolera **eventual consistency**. *Proteção:* o código não deve depender de leitura imediata via GSI (`aws-dynamodb`); revise por design.
4. **Rede entre containers:** app em container → `http://localstack:4566`; app no IDE → `http://localhost:4566`. URL de fila devolvida pelo emulador usa o hostname `*.localhost.localstack.cloud` — se o seu código **usa a URL** retornada por `GetQueueUrl`, funciona; se **monta a URL à mão**, quebra. *Proteção:* sempre peça a URL à API ou use o **nome** da fila (o Spring Cloud AWS resolve).
5. **S3 sem path-style** → erro de DNS (`bucket.localhost`). *Proteção:* `path-style-access-enabled: true` / `forcePathStyle(true)` no profile `local`/teste.
6. **Estado sobra entre testes/execuções** (com `withReuse` ou volume): *Proteção:* nomes únicos por teste; init scripts idempotentes (`|| true` onde criar duas vezes falha, ou checar antes).
7. **Deriva de versão:** `latest` muda comportamento. *Proteção:* **tag fixa**, atualizada de propósito, a mesma no compose e nos testes.
8. **Apontar para a AWS real por engano** (ou o contrário: credencial real num teste). *Proteção:* a **trava** da seção 2; profile `local` explícito; nenhuma chave real fora do ambiente do CI; `AWS_PROFILE` não setado nos testes.
9. **Lambda lenta/instável no emulador:** não use para medir cold start; use para validar o **handler** (`aws-lambda`: unit test do handler + `sam local`).
10. **Teste verde ≠ produção:** o LocalStack **reduz** o risco de integração, **não** o elimina. Mantenha um conjunto pequeno de testes na conta de dev.

## 7. CI (GitHub Actions)

Com **Testcontainers** não há nada a configurar: `ubuntu-latest` já tem Docker — `./mvnw -B clean verify` sobe o LocalStack pelo teste (`github-actions-aws`). Para um LocalStack **compartilhado** por vários jobs/serviços:
```yaml
    services:
      localstack:
        image: localstack/localstack:4.0.0
        ports:
          - 4566:4566
        env:
          SERVICES: s3,sqs,sns,dynamodb
```
(Se a imagem/edição exige **auth token**, passe `LOCALSTACK_AUTH_TOKEN: ${{ secrets.LOCALSTACK_AUTH_TOKEN }}` — **secret do repositório**, nunca no YAML.) Em **pull requests de forks** os secrets não estão disponíveis — os testes devem **funcionar sem token** ou ser pulados nesses casos. Use a **mesma tag de imagem** do compose/teste. Cache de imagens do Docker ajuda no tempo.

## 8. Quando usar outra coisa

Para **um único serviço**, uma ferramenta dedicada pode ser mais leve e fiel:
| Serviço | Alternativa |
|---|---|
| S3 | **MinIO** (S3-compatible, imagem leve) |
| SQS | **ElasticMQ** |
| DynamoDB | **DynamoDB Local** (`amazon/dynamodb-local`, oficial da AWS) |
| SES | **GreenMail** (SMTP falso — já usado no pack, `aws-ses`) |
| RDS | **Testcontainers** com o banco real (`integration-testing`) |
| Redis/ElastiCache | **Testcontainers `redis`** (`caching`) |
| Kafka/MSK | **Testcontainers Kafka** (`kafka`) |

Prefira **LocalStack quando o fluxo envolve vários serviços AWS juntos** (SNS→SQS→Lambda→DynamoDB); a ferramenta dedicada quando é **um** serviço e você quer fidelidade máxima.

## 9. Registre no `CLAUDE.md` do projeto (`project-claude-md`)

Comandos que funcionam (`docker compose up -d localstack`, o profile `local`, `awslocal ...`), a **tag da imagem**, se há **auth token** (nome da variável — nunca o valor), os **recursos criados** pelos init scripts e **o que o LocalStack não cobre** (IAM, consistência) com o job da conta de dev que cobre.

---

## Regras principais

- LocalStack testa a **integração do seu código**; **não** prova IAM, desempenho, consistência eventual, rede nem cold start — valide isso na **conta de dev** (e policies com Access Analyzer).
- **Tag de imagem fixa**, a mesma no compose, nos testes e no CI; confirme o licenciamento/auth token atual; **nunca** commite token.
- Porta **somente em `127.0.0.1`**; socket do Docker só quando precisar de Lambda.
- Recursos por **init scripts** (LF, idempotentes) **ou pelo próprio Terraform** (`tflocal`) — mesma fonte da verdade que o IaC real.
- Profile **`local`**: `endpoint` + credenciais **falsas `test/test`** só ali; S3 **path-style**; **trava** que recusa `endpoint-override` fora de localhost/localstack.
- App em container usa `http://localstack:4566`, não `localhost`.
- Testes: **container compartilhado** (`@DynamicPropertySource`, porta aleatória), recursos provisionados no teste, **nomes únicos**, **Awaitility**, e casos de duplicata e DLQ; poucos testes de integração.
- Banco, Redis e Kafka **em containers reais**; Cognito por `jwt()`; Keyspaces sem emulador.
- Escreva as **policies de recurso** (queue policy, bucket policy) mesmo que o emulador não as exija.
- Documente comandos, tag e limitações no `CLAUDE.md`.
- **Sem Lombok** — deliberado.
