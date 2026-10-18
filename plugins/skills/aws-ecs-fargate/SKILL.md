---
name: aws-ecs-fargate
description: Spring Boot no Amazon ECS com Fargate — task definition (execution × task role, secrets, logs), service com ALB e circuit breaker com rollback, auto scaling, graceful shutdown, deploy por GitHub Actions, ECS Exec, custos e troubleshooting. Use quando rodar containers na AWS sem Kubernetes ou quando uma task não sobe.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../docker-and-docker-compose/SKILL.md`](../docker-and-docker-compose/SKILL.md), [`../observability/SKILL.md`](../observability/SKILL.md) e [`../aws-sdk-java/SKILL.md`](../aws-sdk-java/SKILL.md). O ECR e o ALB seguem [`../aws-eks/SKILL.md`](../aws-eks/SKILL.md) (seções 1 e 4).

# Amazon ECS + Fargate

**ECS** é o orquestrador de containers da AWS; com **Fargate** você não gerencia nenhum servidor: define **quanta CPU/memória** o container precisa e a AWS roda. É o caminho **mais simples** para rodar uma API Spring Boot em container na AWS: sem control plane Kubernetes para aprender, atualizar e pagar, integração direta com ALB, IAM, Secrets Manager e CloudWatch.

## ECS/Fargate, EKS ou Lambda?

| | ECS + Fargate | EKS (`aws-eks`) | Lambda (`aws-lambda`) |
|---|---|---|---|
| Complexidade | **Baixa** | Alta | Mínima |
| Quando | Time pequeno/médio, poucas aplicações, quer containers sem operar cluster | Já usa Kubernetes, ecossistema (Helm, operators), multi-cloud/portabilidade, muitos serviços | Event handlers e carga esporádica |
| Portabilidade | Específico da AWS | **Padrão aberto** | Específico |
| Custo fixo | Sem control plane | Control plane por cluster/hora | Zero ocioso |
| Escala | Auto Scaling de tasks | HPA + nodes (Karpenter) | Automática |

**Regra prática:** *uma ou poucas APIs, sem necessidade de Kubernetes → ECS/Fargate.* Muitos serviços/times e plataforma interna → EKS. Pergunte "precisamos de Kubernetes?" antes de assumir que sim (`architect`).

## Conceitos

- **Cluster** (agrupamento lógico) → **Service** (mantém N **tasks** rodando, integra com ALB e faz deploy) → **Task** (uma execução da **task definition**, com 1+ containers) → **Task definition** (a "receita": imagem, CPU, memória, roles, env, logs).
- **`awsvpc`**: cada task ganha **sua própria interface de rede (ENI)** e IP privado, com **security group próprio** — modelo obrigatório no Fargate.

---

## Task definition

```json
{
  "family": "library-api",
  "requiresCompatibilities": ["FARGATE"],
  "networkMode": "awsvpc",
  "cpu": "512",
  "memory": "1024",
  "runtimePlatform": { "cpuArchitecture": "ARM64", "operatingSystemFamily": "LINUX" },
  "executionRoleArn": "arn:aws:iam::123456789012:role/library-api-execution",
  "taskRoleArn": "arn:aws:iam::123456789012:role/library-api-task",
  "containerDefinitions": [
    {
      "name": "app",
      "image": "123456789012.dkr.ecr.us-east-1.amazonaws.com/library-api:1.4.2",
      "essential": true,
      "portMappings": [{ "containerPort": 8080, "protocol": "tcp" }],
      "environment": [
        { "name": "SPRING_PROFILES_ACTIVE", "value": "prod" },
        { "name": "JAVA_TOOL_OPTIONS", "value": "-XX:MaxRAMPercentage=75" }
      ],
      "secrets": [
        {
          "name": "SPRING_DATASOURCE_PASSWORD",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:123456789012:secret:library/prod/db-AbCdEf:password::"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/library-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "app"
        }
      },
      "stopTimeout": 30
    }
  ]
}
```
- **CPU/memória (Fargate, combinações válidas):** `256` CPU → 0,5–2 GB; `512` → 1–4 GB; `1024` → 2–8 GB; `2048` → 4–16 GB; `4096` → 8–30 GB (em saltos de 1 GB). Comece com `512/1024` para uma API Spring pequena (`jvm-performance`: ajuste com as métricas reais). A memória é **limite duro** do container: `-XX:MaxRAMPercentage=75` deixa a JVM dimensionar o heap por ela (`docker-and-docker-compose`). Estourar = task morta (`OutOfMemoryError: Container killed`).
- **ARM64 (Graviton)**: ~20% mais barato e normalmente mais rápido; a **imagem precisa ser `linux/arm64`** (build multi-arch ou `--platform linux/arm64` no `docker build`; imagens `eclipse-temurin` já são multi-arch). Para x86, `X86_64`.
- **Duas roles, papéis diferentes — confusão frequente:**
  | Role | Quem usa | Para quê |
  |---|---|---|
  | **`executionRoleArn`** | O **agente do ECS/Fargate**, *antes* de iniciar | Puxar a imagem do ECR, escrever logs no CloudWatch, **ler os `secrets`** (injetados como variáveis de ambiente) |
  | **`taskRoleArn`** | A **sua aplicação**, em runtime | Acessar DynamoDB, S3, SQS, etc. (`aws-sdk-java`: a credentials chain pega a task role sozinha) |

  Policies **mínimas** em cada uma. A execution role precisa de `secretsmanager:GetSecretValue` (e `kms:Decrypt` se KMS próprio) **nos ARNs dos segredos**; a task role, só das ações/ARNs que o código usa. **Nunca access keys** na task.
- **`secrets`**: o ECS injeta o valor do Secrets Manager/Parameter Store como **variável de ambiente** na criação da task. O formato `…:secret:nome-AbCdEf:chave::` extrai **uma chave do JSON**. O Spring lê `SPRING_DATASOURCE_PASSWORD` por *relaxed binding* (`kubernetes`): o `application.yml` não muda. A rotação só chega ao reiniciar a task (`aws-rds-secrets-manager`). **Nunca** coloque segredo em `environment`.
- **`stopTimeout: 30`** (padrão 30 s, máx. 120 s): o tempo entre o `SIGTERM` e o `SIGKILL`. Deve ser **maior** que `spring.lifecycle.timeout-per-shutdown-phase` (+ folga) — veja "Graceful shutdown".
- **Logs**: `awslogs` envia stdout para o CloudWatch Logs; **crie o log group com retenção** (por IaC) — a execution role precisa de `logs:CreateLogStream`/`PutLogEvents`. Logs em JSON (`observability`).
- **Filesystem:** `readonlyRootFilesystem: true` é uma boa defesa, mas a JVM/Tomcat escrevem em `/tmp` → monte um **volume** (bind mount efêmero) em `/tmp` com `mountPoints`/`volumes` na task definition.
- **`user`**: rode como não-root (imagem com `USER app` — `docker-and-docker-compose`).
- **Health check do container** (`healthCheck` com `curl`) exige o `curl` na imagem (imagens JRE enxutas não têm); em geral, o **health check do target group do ALB** basta (abaixo).

Registro: `aws ecs register-task-definition --cli-input-json file://taskdef.json` (cria uma **nova revisão**; o service passa a apontar para ela).

---

## Service com ALB

```json
{
  "cluster": "library",
  "serviceName": "library-api",
  "taskDefinition": "library-api",
  "desiredCount": 3,
  "launchType": "FARGATE",
  "networkConfiguration": {
    "awsvpcConfiguration": {
      "subnets": ["subnet-private-a", "subnet-private-b", "subnet-private-c"],
      "securityGroups": ["sg-library-api"],
      "assignPublicIp": "DISABLED"
    }
  },
  "loadBalancers": [
    { "targetGroupArn": "arn:aws:elasticloadbalancing:...:targetgroup/library-api/abc", "containerName": "app", "containerPort": 8080 }
  ],
  "healthCheckGracePeriodSeconds": 120,
  "deploymentConfiguration": {
    "minimumHealthyPercent": 100,
    "maximumPercent": 200,
    "deploymentCircuitBreaker": { "enable": true, "rollback": true }
  },
  "enableExecuteCommand": true
}
```
- **Subnets privadas + `assignPublicIp: DISABLED`**: as tasks não têm IP público; só o **ALB** (em subnets públicas) recebe tráfego. Para puxar do ECR e falar com serviços AWS sem NAT, use **VPC endpoints** (ECR api/dkr, S3 gateway, CloudWatch Logs, Secrets Manager) — `aws-eks`, seção 6.
- **Security group da task** aceita a porta 8080 **somente do security group do ALB**; o SG do **RDS** aceita só o SG da task (`aws-rds-secrets-manager`).
- **Target group `ip`** (obrigatório com `awsvpc`), health check em **`/actuator/health/readiness`** (`observability`) — se o Actuator está em porta separada (9090), defina a **porta do health check** do target group para ela. Ajuste `deregistration_delay` do target group para ~30 s (o padrão de 300 s alonga os deploys).
- **`healthCheckGracePeriodSeconds`**: o ECS **ignora** as falhas de health check do ALB por esse tempo após a task iniciar. Spring Boot demora a subir (JVM + Flyway): defina **maior que o startup real**, ou o ECS mata a task antes de ela ficar pronta (loop de reinício).
- **Deploy rolling** com `minimumHealthyPercent: 100` / `maximumPercent: 200`: sobe tasks novas **antes** de remover as antigas (zero downtime) — as duas versões convivem (`flyway-migrations`: expand → contract).
- **`deploymentCircuitBreaker` com `rollback`**: se as tasks novas não estabilizam (falham ao subir/health check), o ECS **reverte automaticamente** para a revisão anterior. **Ligue sempre.** Alternativa mais sofisticada: **blue/green** (CodeDeploy / blue-green nativo do ECS) com tráfego de teste e *bake time*.
- **`enableExecuteCommand`**: **ECS Exec** abre um shell na task (via SSM, sem SSH nem porta aberta) para depurar: `aws ecs execute-command --cluster library --task <id> --container app --interactive --command "/bin/sh"`. Exige permissões SSM na **task role** e o agente na imagem; ligue em dev/staging e **avalie** em produção (auditável por CloudTrail).

## Spring Boot em ECS: graceful shutdown

Em um deploy/scale-in o ECS manda `SIGTERM`, espera `stopTimeout` e então `SIGKILL`; ao mesmo tempo o ALB **drena** a task (deregistration delay). Para não perder requests em voo:
```yaml
server:
  shutdown: graceful

spring:
  lifecycle:
    timeout-per-shutdown-phase: 25s
```
Garanta: **`timeout-per-shutdown-phase` (25 s) < `stopTimeout` (30 s)**, e o `ENTRYPOINT` em **forma exec** para o Java receber o `SIGTERM` (`kubernetes`). O `deregistration_delay` do target group também deve ser coerente.

---

## Auto Scaling

**Application Auto Scaling** ajusta o `desiredCount`:
```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs --resource-id service/library/library-api \
  --scalable-dimension ecs:service:DesiredCount --min-capacity 3 --max-capacity 12

aws application-autoscaling put-scaling-policy \
  --service-namespace ecs --resource-id service/library/library-api \
  --scalable-dimension ecs:service:DesiredCount --policy-name cpu-target \
  --policy-type TargetTrackingScaling \
  --target-tracking-scaling-policy-configuration file://cpu-policy.json
```
`cpu-policy.json`: `{"TargetValue": 65.0, "PredefinedMetricSpecification": {"PredefinedMetricType": "ECSServiceAverageCPUUtilization"}, "ScaleOutCooldown": 60, "ScaleInCooldown": 300}`. Alternativa por tráfego: `ALBRequestCountPerTarget`. **Mínimo ≥ 2–3 tasks em AZs diferentes** para disponibilidade. Some `max × pool` ≤ `max_connections` do banco (`aws-rds-secrets-manager`, `jvm-performance`). Para cargas previsíveis, **scheduled scaling**.

## Deploy por CI (GitHub Actions)

Estenda o pipeline de [`../github-actions-aws/SKILL.md`](../github-actions-aws/SKILL.md) (OIDC, build, push para o ECR) trocando o job de deploy:
```yaml
  deploy:
    needs: image
    runs-on: ubuntu-latest
    environment: production
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::123456789012:role/github-actions-ecs-deploy-prod
          aws-region: us-east-1
      - id: render
        uses: aws-actions/amazon-ecs-render-task-definition@v1
        with:
          task-definition: ecs/taskdef.json
          container-name: app
          image: ${{ needs.image.outputs.image }}
      - uses: aws-actions/amazon-ecs-deploy-task-definition@v2
        with:
          task-definition: ${{ steps.render.outputs.task-definition }}
          service: library-api
          cluster: library
          wait-for-service-stability: true
```
`render` troca só a **imagem** (tag = `github.sha`) no `taskdef.json` versionado; `deploy` registra a nova revisão e atualiza o service, e `wait-for-service-stability` faz o job **falhar** se o deploy não estabilizar (o circuit breaker já reverteu). A role de deploy precisa de `ecs:RegisterTaskDefinition`, `ecs:UpdateService`, `ecs:DescribeServices` e **`iam:PassRole`** restrito às **duas roles da task** (nada de `PassRole` em `*`). Versões das actions: confirme as atuais e fixe por SHA (`github-actions-aws`).

## Service-to-service e configuração

- **ECS Service Connect** (ou **Cloud Map**/DNS interno) para um serviço chamar outro por nome, com balanceamento, retries e métricas, sem ALB interno; para exposição pública, ALB.
- **Configuração** não sensível em `environment`; segredos em `secrets`; **parâmetros** em `secrets` do SSM (`aws-parameter-store`). A mesma imagem em todo ambiente.
- **Migrations (Flyway)**: o Flyway no startup é seguro com várias tasks (lock); para migrations longas, rode uma **task one-off** antes do deploy (`aws ecs run-task` com `--overrides` ou uma task definition de migração) — equivalente ao Job do `kubernetes`.
- **Tarefas agendadas**: **EventBridge Scheduler** → `ecs:RunTask` (em vez de `@Scheduled` em N réplicas) — `aws-eventbridge`.

## Observabilidade

- **Container Insights** (CPU/memória/rede por service/task) ligado no cluster; métricas do ALB (`HTTPCode_Target_5XX_Count`, `TargetResponseTime`, `UnHealthyHostCount`); **logs** no CloudWatch com retenção; Actuator/Prometheus ou **ADOT collector como sidecar** (traces para X-Ray, métricas) — `aws-observability`.
- **Alarmes:** CPU/memória do service, `RunningTaskCount < desired`, 5xx do ALB, latência, **deploy rollbacks** (evento do ECS `SERVICE_DEPLOYMENT_FAILED` no EventBridge → SNS).

## Custos

- **Fargate Spot** (até ~70% mais barato; a AWS pode **interromper** com aviso de 2 min): ótimo para workers/ambientes de dev/tolerantes; use **capacity provider strategy** misturando `FARGATE` (base ≥ 1–2 tasks) + `FARGATE_SPOT`. Seu app já precisa de graceful shutdown (`SIGTERM`).
- **ARM64**, **Savings Plans (Compute)**, dimensionar CPU/memória por dados reais, **desligar dev fora do horário** (`desiredCount 0`), retenção de logs, VPC endpoints no lugar de NAT (cada GB na NAT custa), ALB compartilhado por *listener rules*.

## Troubleshooting (task que não sobe ou cai)

```bash
aws ecs describe-services --cluster library --services library-api --query 'services[0].events[:10]'
aws ecs list-tasks --cluster library --service-name library-api --desired-status STOPPED
aws ecs describe-tasks --cluster library --tasks <task-id> --query 'tasks[0].{stop:stoppedReason,containers:containers[].reason}'
aws logs tail /ecs/library-api --follow
```
| `stoppedReason` / sintoma | Causa provável |
|---|---|
| `CannotPullContainerError` | Sem rota para o ECR (NAT/VPC endpoints), tag inexistente, execution role sem permissão ECR, **arquitetura da imagem ≠ `cpuArchitecture`** |
| `ResourceInitializationError: unable to pull secrets` | Execution role sem `GetSecretValue`/`kms:Decrypt`, ARN do segredo errado, sem rota ao Secrets Manager |
| `Essential container in task exited` (exit 1) | A aplicação caiu ao subir (config/secret ausente, Flyway falhou) → logs |
| `OutOfMemoryError: Container killed` (exit 137) | `memory` baixa para o heap/non-heap → aumente ou reduza `MaxRAMPercentage` |
| `Task failed ELB health checks` | Porta/path do health check errados, **grace period curto**, SG não permite o ALB, app lenta para subir |
| Deploy "preso" e revertido | Circuit breaker acionado: veja os eventos do service e os logs da task nova |

---

## Regras principais

- ECS/Fargate para containers **sem Kubernetes**; EKS quando o ecossistema K8s é necessário; Lambda para eventos.
- **Execution role** (ECR, logs, secrets) ≠ **task role** (a aplicação): policies **mínimas**, `PassRole` restrito; **nunca access keys**.
- Segredos via `secrets` (Secrets Manager/SSM), nunca em `environment`; mesma imagem em todo ambiente, **tag imutável** (`github.sha`), nunca `latest`.
- Tasks em **subnets privadas**, SG só do ALB → task → RDS; VPC endpoints.
- Service: **target group `ip`**, health check na **readiness**, `healthCheckGracePeriodSeconds` > startup, `minimumHealthy 100%/maximum 200%`, **circuit breaker com rollback sempre ligado**.
- **Graceful shutdown**: `timeout-per-shutdown-phase` < `stopTimeout`; ENTRYPOINT em forma exec; `deregistration_delay` curto.
- Auto Scaling por CPU/requests com mínimo ≥ 2–3 em AZs distintas; `max × pool ≤ conexões do banco`.
- CI com OIDC: render → deploy → `wait-for-service-stability`.
- Logs com **retenção**, Container Insights, alarmes em tasks/5xx/latência/rollbacks; ECS Exec para depurar.
- Fargate Spot + ARM64 + Savings Plans para reduzir custo.
- **Sem Lombok** — deliberado.
