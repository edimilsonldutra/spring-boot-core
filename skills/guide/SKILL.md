---
name: guide
description: Índice do plugin squads — o que o pacote faz, quais skills estão realmente instaladas, como se agrupam e qual usar para cada necessidade. Use quando o desenvolvedor perguntar o que o plugin sabe fazer, qual skill usar ou por onde começar, ou parecer inseguro sobre o próximo passo.
---

# squads — guide

Esta skill não gera nenhum código — ela apenas explica o pacote. Diferente de todas as outras skills daqui, ela não precisa que `code-organization`/`code-style` sejam lidas antes.

---

## O que é este plugin

Skills de backend Spring Boot 4.1 / Java 25, um tópico por skill, todas em um único padrão validado: packages flat-by-layer sob `br.com.edimilsonldutra`, sem Lombok em lugar nenhum, constructors/getters/setters explícitos, logging com SLF4J, auth JWT feita de um jeito específico, um único contrato de erro `ExceptionResponse`/`ProblemDetail`, Flyway dono do schema. Cada skill pode ser chamada diretamente (`/squads:<name>`) ou encontrada automaticamente a partir de uma descrição em linguagem natural da tarefa — as duas formas funcionam; este guide é para quando o desenvolvedor quer o mapa em vez de adivinhar um nome. A versão em Kotlin deste exato pacote é um plugin separado, `squads-kt` (todo nome de skill ganha um prefixo `kt-` lá); mencione-o somente se o desenvolvedor estiver trabalhando em Kotlin.

---

## Por onde começar

**Ainda não tem projeto?** Comece com `scaffold` — ele faz as perguntas base (versão do Java, build tool, config file, idioma do texto voltado ao usuário) mais, uma de cada vez, se deve adicionar persistence, Flyway, exception handling, web config, Swagger e Bean Validation (cada um tem default "sim"; recusar todos gera uma API mínima vazia). Ele faz o build e verifica o projeto antes de passar o bastão.

**O projeto já existe** (gerado por scaffold aqui ou trazido de outro lugar)? Vá direto para `code-organization` — ela executa um questionário curto de preferências, uma única vez (comentários, database, posição do Swagger, mapper, estilo de injection) e define o package layout que todas as outras skills assumem; depois vá para a skill de tópico que corresponde à tarefa em mãos.

---

## Veja o que está realmente instalado

Antes de descrever a lista de skills, verifique o que realmente está presente em vez de recitar de memória a tabela de referência abaixo: liste as pastas irmãs ao lado desta (o diretório desta skill tem outras ao lado, uma por tópico) e leia a linha `description` do frontmatter de cada `SKILL.md`. Reporte *isso* como o conjunto instalado; nunca afirme que uma skill está disponível sem ter de fato encontrado a pasta dela.

---

## Como as skills se agrupam

- **Fundação, lida por todas as outras:** `code-organization` (package layout, o questionário de preferências compartilhado), `code-style` (formatação, comentários, logging).
- **Construa a data layer:** `maven-config` (dependencies/build file), `spring-data-jpa` (entities, repositories, DTOs), `flyway-migrations` (schema como SQL versionado).
- **Deixe a API sólida:** `exception-handling` (um contrato de erro), `web-config` (CORS + JSON/XML/YAML), `bean-validation` (rejeitar input ruim com 400), `pagination` (listas paginadas com limite), `hateoas` (links HAL nas respostas), `api-versioning` (v1 → v2 sem quebrar clients; versionamento nativo do Spring 7).
- **Documente:** `swagger` (springdoc/OpenAPI), `swagger-advanced` (grupos por versão, erros comuns, exemplos, OpenAPI como contrato no CI, geração de clients).
- **Arquivos e e-mail:** `file-upload-download` (upload/download seguro), `file-import-export` (XLSX/CSV, criação em massa), `pdf-reports` (JasperReports 7, QR code), `email` (Spring Mail/SMTP, assíncrono depois do commit; na AWS, `aws-ses`).
- **Finalize um projeto novo:** `project-claude-md` gera o `CLAUDE.md` do próprio projeto do desenvolvedor.
- **Especificação:** `design-docs` (design doc / tech spec como spec do fluxo spec-driven: critérios `CA-n`, aprovação antes do plano, rastreabilidade critério → tarefa → teste).
- **Segurança e design de código:** `application-security` (OWASP API Security Top 10: IDOR, mass assignment, limites, injeção, SSRF, headers, segredos, SBOM), `threat-modeling` (STRIDE e casos de abuso antes de construir), `solid` (princípios e quando não aplicar), `design-patterns` (padrões no Spring, auto-invocação, anti-padrões).
- **Segurança e Java:** `authentication` (JWT + Spring Security 7), `caching` (Caffeine/Redis), `java-modern-features` (Java 17–25, virtual threads), `jvm-performance` (JVM em container, pool, queries, diagnóstico).
- **Testes:** `testing` (unit + slice), `test-patterns`, `integration-testing` (Testcontainers + REST Assured, banco real), `test-coverage` (JaCoCo, PIT), `postman-newman` (caixa-preta e smoke pós-deploy).
- **Docker e Kubernetes:** `docker-and-docker-compose`, `observability` (Actuator, Micrometer, probes), `kubernetes`, `helm-charts`.
- **CI/CD:** `github-actions` (CI genérico: build, testes, cobertura, imagem no GHCR, CodeQL, Dependabot), `github-actions-aws` (deploy na AWS com OIDC), `github-actions-cloud` (deploy no Google Cloud e no Azure com OIDC), `argocd` (GitOps).
- **Mensageria:** `messaging` (comece aqui: quando usar, qual broker, garantias, DLQ), `kafka`, `rabbitmq`, `activemq-artemis` (JMS), `aws-sns-sqs` (fan-out) e `transactional-outbox` (publicar sem dual write + consumer idempotente).
- ➕ **Extras — Produto (perfil de PM):** `product-strategy` (visão, estratégia, business case), `product-discovery`, `prd-writing`, `user-stories`, `prioritization` (RICE/MoSCoW/WSJF), `product-roadmap` (Now/Next/Later + OKRs), `product-metrics` (North Star, tracking plan, A/B), `agile-delivery`, `release-management` (flags, rollout, go/no-go), `technical-product-management` (NFRs, SLO, API como produto), `privacy-lgpd` e `stakeholder-communication`. O agent `product-manager` as usa.
- ➕ **Extras — Arquitetura de microsserviços:** `microservices` (**comece aqui**: quando dividir, decomposição, dados, migração), `modular-monolith` (Spring Modulith), `ddd-hexagonal` (domínio rico), `api-gateway` (gateway e BFF), `service-communication` (REST/gRPC, auth serviço-a-serviço), `resilience` (timeout, retry, circuit breaker), `saga-pattern`, `cqrs-event-sourcing`, `contract-testing` (Pact/SCC) e `idempotency`.
- ➕ **Extras — GitOps:** `argocd` (Argo CD: repo GitOps, Application/AppProject/ApplicationSet, migration como PreSync hook, promoção por PR, secrets e segurança).
- ➕ **Extras — AWS (serviços e integração):** `aws-sdk-java` (base: SDK v2, credenciais, clients, timeouts), `localstack` (emular a AWS local e em testes), `aws-dynamodb`, `aws-keyspaces`, `aws-lambda`, `aws-ecs-fargate`, `aws-cognito`, `aws-parameter-store` (+ AppConfig), `aws-ses`, `aws-eventbridge`, `aws-observability` (CloudWatch/X-Ray/alarmes), `aws-terraform` (infra como código) e `aws-architecture-diagram` (diagrama de infraestrutura AWS no draw.io).
- ➕ **Extras — AWS:** `aws-eks` (ECR, EKS, IRSA, ALB), `aws-rds-secrets-manager`, `aws-s3-sqs`, `github-actions-aws` (CI/CD com OIDC).

---

## Consulta rápida — "Eu quero…"

| O desenvolvedor quer… | Skill |
|---|---|
| Um projeto novo | `scaffold` |
| CRUD para uma entity | `spring-data-jpa` |
| Schema migrations | `flyway-migrations` |
| Responses de erro limpas e consistentes | `exception-handling` |
| CORS, ou XML/YAML além de JSON | `web-config` |
| Documentação da API | `swagger` (grupos, exemplos, OpenAPI no CI, clients gerados: `swagger-advanced`) |
| Rejeitar input ruim com um 400 | `bean-validation` |
| Um `CLAUDE.md` de projeto gerado | `project-claude-md` |
| Login / JWT | `authentication` (login gerenciado: `aws-cognito`) |
| Revisão de segurança da API, IDOR, mass assignment, rate limit, security headers, SSRF | `application-security` |
| Pensar em ameaças e abusos antes de construir uma feature | `threat-modeling` |
| Design doc, tech spec, SDD, RFC; desenvolver seguindo uma especificação | `design-docs` (decisão isolada: ADR do agent `architect`) |
| Classe difícil de testar ou de mudar, princípios SOLID | `solid` |
| Qual padrão de projeto usar (Strategy, Adapter, Observer, State…), `@Transactional` que não funciona | `design-patterns` |
| Listas paginadas (page, size, direction, limite, ordenação) | `pagination` |
| Links HATEOAS (HAL) nas respostas | `hateoas` |
| Enviar e-mail | `email` (SMTP/Spring Mail); pela AWS: `aws-ses` |
| Importar/exportar XLSX ou CSV, criação em massa | `file-import-export` |
| Relatórios PDF (JasperReports), QR code | `pdf-reports` |
| Upload/download de arquivos | `file-upload-download`; guardando no S3: `aws-s3-sqs` |
| Dockerizar o projeto | `docker-and-docker-compose` |
| Um pipeline de CI (build, testes, imagem, segurança) | `github-actions` |
| Deploy por CI na AWS | `github-actions-aws` |
| Deploy por CI no Google Cloud ou no Azure | `github-actions-cloud` |
| Deploy no Kubernetes | `kubernetes` |
| Versionar a API (v1 → v2, versionamento nativo do Spring 7, deprecação) | `api-versioning` (deprecação também em `release-management`) |
| Retries / resilience | `resilience` |
| Metrics / health probes | `observability` |
| Uma suíte Postman/Newman, smoke test pós-deploy | `postman-newman` |
| Decidir se/qual mensageria usar | `messaging` |
| Eventos em escala, replay, streaming | `kafka` |
| Fila de tarefas com roteamento | `rabbitmq` |
| JMS / legado corporativo | `activemq-artemis` |
| Fan-out de eventos na AWS (SNS → SQS) | `aws-sns-sqs` |
| Publicar evento junto com a mudança no banco, sem perder | `transactional-outbox` |
| Cache (Caffeine/Redis/ElastiCache) | `caching` |
| Java 17–25: records, sealed, virtual threads | `java-modern-features` |
| API lenta, tuning de JVM/pool, OOMKilled | `jvm-performance` |
| Rodar no Kubernetes / empacotar com Helm | `kubernetes`, `helm-charts` |
| Imagem no ECR, cluster EKS, ALB, IRSA | `aws-eks` |
| RDS e senhas no Secrets Manager | `aws-rds-secrets-manager` |
| Filas SQS, LocalStack | `aws-s3-sqs`, `localstack` |
| Pipeline GitHub Actions → ECR → EKS (OIDC) | `github-actions-aws` |
| Começar com a AWS em Java (SDK v2, credenciais, timeouts) | `aws-sdk-java` |
| Rodar/testar a AWS localmente sem conta (LocalStack) | `localstack` |
| Unit e slice tests (JUnit, Mockito, `@WebMvcTest`) | `testing` |
| Padrões de teste: test doubles, builders, test smells, flaky, TDD/BDD, property-based | `test-patterns` |
| Testes de integração com banco real em container (Testcontainers, REST Assured) | `integration-testing` |
| Cobertura de testes (JaCoCo), diff coverage, gate no CI, mutation testing (PIT) | `test-coverage` |
| Deploy por GitOps, promoção dev → staging → prod, rollback por Git | `argocd` |
| Entender o problema do usuário antes de construir | `product-discovery` |
| Escrever o PRD / as histórias com critérios de aceite | `prd-writing`, `user-stories` |
| Decidir o que fazer primeiro (RICE, MoSCoW, WSJF) | `prioritization` |
| Roadmap e OKRs | `product-roadmap` |
| Métricas de produto, plano de rastreamento, A/B test | `product-metrics` |
| Estratégia, posicionamento, business case | `product-strategy` |
| Scrum/Kanban, forecast, retrospectiva | `agile-delivery` |
| Refinamento de backlog (sessão, DoR, Example Mapping, card refinado) | `backlog-refinement` |
| Entender um repositório desconhecido (mapa, hotspots, riscos, aderência) | `repository-understanding` |
| Analisar um monolito antes de dividir (acoplamento, donos das tabelas, o que extrair primeiro) | `monolith-decomposition` |
| Refatorar com segurança (smells, passos pequenos, Strangler/expand → contract) | `refactoring` |
| Lançar com segurança (flags, rollout, go/no-go, deprecação) | `release-management` |
| Requisitos não funcionais, SLO/error budget, dívida técnica, custo de nuvem | `technical-product-management` |
| LGPD: base legal, direitos do titular, retenção, eliminação, incidente | `privacy-lgpd` |
| Status, resumo executivo, decision log, release notes, dizer não | `stakeholder-communication` |
| Decidir entre monolito e microsserviços; como dividir | `microservices` |
| Começar sem pagar o custo distribuído (módulos com fronteiras verificadas) | `modular-monolith` |
| Domínio rico: aggregates, value objects, ports and adapters; quanto DDD cada subdomínio merece; modelo anêmico | `ddd-hexagonal` |
| Entrada única para clientes, BFF, rate limit na borda | `api-gateway` |
| Chamar outro serviço com segurança e timeouts; gRPC; service mesh | `service-communication` |
| Falha parcial, circuit breaker, retry sem retry storm | `resilience` |
| Transação entre serviços com compensação | `saga-pattern` |
| Leitura e escrita com modelos diferentes; histórico como fonte de verdade | `cqrs-event-sourcing` |
| Mudar uma API sem quebrar consumidores (contratos, `can-i-deploy`) | `contract-testing` |
| Retry/reentrega sem duplicar efeito (`Idempotency-Key`) | `idempotency` |
| Banco NoSQL serverless (chave-valor) | `aws-dynamodb` |
| Cassandra/CQL gerenciado | `aws-keyspaces` |
| Função serverless, cold start, SnapStart | `aws-lambda` |
| Containers sem Kubernetes (Fargate) | `aws-ecs-fargate` |
| Login gerenciado, MFA, login social (Cognito) | `aws-cognito` |
| Config externa, feature flags (Parameter Store/AppConfig) | `aws-parameter-store` |
| Enviar e-mail (SES), bounces e reputação | `aws-ses` |
| Barramento de eventos, Scheduler, eventos da AWS | `aws-eventbridge` |
| Logs, métricas, traces e alarmes na AWS | `aws-observability` |
| Infraestrutura como código (Terraform/CDK) | `aws-terraform` |
| Diagrama de arquitetura AWS (draw.io, ícones oficiais) | `aws-architecture-diagram` |

---

## Nota final

A linguagem natural continua funcionando sem este guide — a `description` do frontmatter de cada skill guia o auto-matching, então um pedido como "adicione uma Flyway migration para uma nova coluna" encontra `flyway-migrations` sozinho. Recorra a este guide quando o desenvolvedor quiser o mapa inteiro, não tiver certeza de que existe uma skill para sua necessidade, ou perguntar explicitamente o que o pacote sabe fazer.
