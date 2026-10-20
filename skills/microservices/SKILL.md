---
name: microservices
description: Ponto de partida de arquitetura de microsserviços — quando adotar (e quando não), monolito modular primeiro, decomposição por bounded context, dados por serviço, distributed monolith, pré-requisitos de plataforma, catálogo de padrões com a skill de cada um, Strangler Fig e checklist de decisão. Use quando discutir dividir um sistema em serviços.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) e [`../code-style/SKILL.md`](../code-style/SKILL.md). Esta skill é o **mapa**: decide **se** e **como dividir**, e aponta para as skills que implementam cada padrão: `ddd-hexagonal`, `modular-monolith`, `api-gateway`, `service-communication`, `resilience`, `saga-pattern`, `cqrs-event-sourcing`, `contract-testing`, `idempotency`, `messaging`, `transactional-outbox`.

# Microsserviços

**Microsserviços** são um conjunto de serviços **pequenos, autônomos e implantáveis de forma independente**, cada um dono de uma **capacidade de negócio** e dos **seus dados**, que cooperam por **APIs e eventos**. O ganho é **autonomia** (times que entregam sem coordenar releases, escala e falha isoladas). O custo é **complexidade distribuída**: rede que falha, consistência eventual, observabilidade difícil, muitos pipelines. **Microsserviços resolvem um problema organizacional e de escala, não técnico** — adotá-los sem esse problema só troca complexidade de código por complexidade de operação.

---

## 1. Você precisa de microsserviços?

**Comece por um monolito (modular).** Quase todo sistema bem-sucedido nasceu monolítico, e dividir **depois**, com o domínio já entendido, é mais barato do que errar as fronteiras no início (fronteira errada em microsserviços é cara de corrigir: contratos, dados e deploys já espalhados). Veja `modular-monolith`.

| Sinal de que **vale** dividir | Sinal de que **não** vale |
|---|---|
| Vários **times** pisando uns nos outros no mesmo código/deploy | Um time pequeno (< ~8–10 pessoas) |
| Partes com **escala muito diferente** (busca × cadastro) ou **ciclo de release** muito diferente | Carga uniforme e moderada |
| Necessidade de **isolar falhas** ou **conformidade** (pagamento isolado) | O domínio ainda é **instável/pouco entendido** |
| Tecnologia/ownership **diferentes** por capacidade | Não há CI/CD, observabilidade e plataforma de containers **maduros** |
| O monolito modular **já está bem separado** e dói só o deploy/escala | "Está na moda" / currículo / "para escalar" sem número que prove |

**O custo (o "microservice premium"):** cada serviço precisa de repositório/pipeline, deploy, monitoramento, alertas, segredos, versionamento de API, contratos, tratamento de falha parcial, tracing e *on-call*. Se a equipe **não consegue operar 3 serviços bem**, não vai operar 30.

### Pré-requisitos de plataforma ("você precisa ser alto o bastante")

Antes de dividir, tenha **automatizado**: build/teste/deploy por serviço (`github-actions-aws`, `argocd`), containers e orquestração (`docker-and-docker-compose`, `kubernetes`/`aws-ecs-fargate`), **observabilidade** (logs/métricas/traces com `traceId` — `observability`, `aws-observability`), infraestrutura como código (`aws-terraform`), gestão de segredos, **testes automatizados** confiáveis (`testing`, `contract-testing`) e **cultura de on-call/SLO**. Sem isso, o resultado típico é o *distributed monolith* (abaixo).

---

## 2. Decomposição: onde cortar

**Corte por capacidade de negócio / bounded context (DDD)**, **não** por camada técnica nem por tabela.

- ✅ `catalog` (livros), `lending` (empréstimos), `membership` (sócios), `billing` — cada um tem **linguagem própria** ("Book" no catálogo é um título; no empréstimo é um exemplar físico) e **regras próprias**.
- ❌ `controller-service`, `database-service` (corte técnico).
- ❌ "**Entity service**" (um serviço CRUD por tabela: `book-service`, `author-service`, `price-service`): vira uma coleção de CRUDs acoplados onde toda operação de negócio atravessa 4 serviços.

**Como achar as fronteiras:**
1. **Event Storming / mapeamento do domínio** com quem conhece o negócio: eventos (`LoanStarted`), comandos, agregados, e onde a **linguagem muda**.
2. **Coesão alta, acoplamento baixo:** o que muda **junto** fica junto; se duas partes sempre mudam no mesmo PR, são o mesmo serviço.
3. **Um time é dono de um ou poucos serviços** (a Lei de Conway: a arquitetura reflete a comunicação da organização — desenhe os dois juntos).
4. **Tamanho:** "pequeno o bastante para um time **entender por inteiro** e reescrever em semanas", não "N linhas". Serviço pequeno demais (nano-serviço) = sobrecarga sem ganho.
5. **Em dúvida, junte.** Dividir um serviço depois é mais fácil que fundir dois.

Veja `ddd-hexagonal` para bounded contexts, agregados e *context map* (como os contextos se relacionam).

---

## 3. Dados: cada serviço é dono dos seus

**Regra inegociável: banco de dados privado por serviço.** Nenhum outro serviço lê ou escreve nas tabelas dele — só pela **API** ou por **eventos**.

| Prática | Por quê |
|---|---|
| **Sem banco compartilhado** | Banco compartilhado = acoplamento total (mudar uma coluna quebra N serviços), deploys em bloco: é o pior sintoma de *distributed monolith* |
| **Sem JOIN entre serviços** | Para consultar dados de outro contexto: **API composition** (o gateway/BFF compõe — `api-gateway`), **read model** replicado por eventos (`cqrs-event-sourcing`) ou **dados duplicados** controlados |
| **Sem transação distribuída (2PC)** | Frágil e lenta. Consistência entre serviços é **eventual**: `saga-pattern` + `transactional-outbox` + `idempotency` |
| **Banco certo por serviço** (poliglota **com critério**) | Relacional (`spring-data-jpa`) por padrão; DynamoDB/Redis/Elasticsearch **quando o padrão de acesso exige** (`aws-dynamodb`, `caching`). Cada banco novo é custo de operação |
| **Referências por ID, não por FK** | `lending` guarda `bookId` (um identificador), não uma FK para a tabela do `catalog`; valida/consulta pela API ou mantém uma cópia mínima por eventos |

**Duplicar dados entre serviços é normal** (o `lending` guarda o título do livro no momento do empréstimo): a duplicação é **de leitura**, com **uma fonte de verdade** (o dono do dado publica; os outros assinam e mantêm cópia). Evolução do schema do banco segue `flyway-migrations` (expand → contract), **por serviço**.

---

## 4. Como os serviços se falam

| Necessidade | Estilo | Skill |
|---|---|---|
| Preciso da **resposta agora** (consulta, validação) | **Síncrono**: REST (`RestClient`), gRPC | `service-communication` |
| **Notificar** que algo aconteceu; vários interessados; desacoplar no tempo | **Assíncrono**: eventos/mensagens | `messaging`, `kafka`, `rabbitmq`, `aws-sns-sqs`, `aws-eventbridge` |
| Operação que atravessa **vários serviços** com consistência eventual | **Saga** | `saga-pattern` |
| Evento originado de **mudança no banco** | **Outbox** | `transactional-outbox` |
| Cliente externo (web/mobile) | **API Gateway / BFF** | `api-gateway` |

**Preferência:** **eventos para propagar fatos, chamadas síncronas só para o que exige resposta imediata.** Cada chamada síncrona é **acoplamento temporal** (se o outro cai, você cai — a menos que haja `resilience`). **Evite cadeias** A → B → C → D: a disponibilidade é o **produto** das disponibilidades (4 serviços a 99,9% ≈ 99,6%) e a latência é a **soma**.

---

## 5. O distributed monolith — o anti-pattern mais comum

Você tem **a complexidade dos microsserviços e nenhum dos benefícios**. Sintomas:
- **Deploys em lockstep**: mudar o serviço A exige implantar B e C juntos.
- **Banco compartilhado** ou serviços lendo tabelas uns dos outros.
- **Cadeias síncronas profundas** e chamadas dentro de loops (N+1 entre serviços).
- **Biblioteca compartilhada com regra de negócio/entidades**: uma mudança nela força redeploy de todos. (Compartilhe **somente contratos** — DTOs/eventos versionados — e utilitários técnicos estáveis.)
- **Serviços que não funcionam sozinhos** nem em teste (precisa subir 12 para testar 1).
- **Um time só** dono de todos, sem autonomia real.
- Mudanças pequenas no negócio exigem **PRs em 5 repositórios**.
**Teste de independência:** *posso implantar este serviço sozinho, agora, sem avisar ninguém e sem quebrar os outros?* Se não, ele não é independente. A cura é **corrigir as fronteiras e os contratos** (`contract-testing`), não adicionar mais ferramentas.

---

## 6. Catálogo de padrões (e a skill de cada um)

| Problema | Padrão | Skill |
|---|---|---|
| Entrada única, auth, rate limit, composição para clientes | **API Gateway / BFF** | `api-gateway` |
| Chamar outro serviço bem (timeouts, clients, auth entre serviços) | **Comunicação síncrona** | `service-communication` |
| Falha parcial, lentidão em cascata | **Timeout, retry, circuit breaker, bulkhead** | `resilience` |
| Transação de negócio entre serviços | **Saga** (orquestração/coreografia) | `saga-pattern` |
| Leitura e escrita com necessidades muito diferentes | **CQRS** (e event sourcing com critério) | `cqrs-event-sourcing` |
| Publicar evento sem perdê-lo (sem dual write) | **Transactional Outbox** | `transactional-outbox` |
| Mensagem/requisição repetida não duplica efeito | **Idempotência** | `idempotency` |
| Mudar um serviço sem quebrar os consumidores | **Contract testing**, versionamento aditivo | `contract-testing` |
| Domínio rico, regras complexas, núcleo independente de framework | **DDD + Hexagonal** | `ddd-hexagonal` |
| Começar sem pagar o preço distribuído | **Monolito modular** | `modular-monolith` |
| Descoberta e configuração | **DNS do Kubernetes / Service Connect**, ConfigMap/Parameter Store | `service-communication`, `kubernetes`, `aws-parameter-store` |
| Enxergar a request entre serviços | **Tracing distribuído, logs correlacionados** | `observability`, `aws-observability` |
| Entregar muitos serviços com segurança | **GitOps** | `argocd` |
| Migrar de um monolito | **Strangler Fig** (abaixo) | esta skill |

Não adote o catálogo inteiro: **cada padrão resolve um problema que você precisa ter**. Um serviço CRUD simples não precisa de saga, CQRS nem hexagonal.

---

## 7. Migrando de um monolito: Strangler Fig

Substitua o monolito **gradualmente**, uma capacidade por vez, mantendo o sistema funcionando (nada de *big bang rewrite*):

1. **Coloque uma fachada na frente** do monolito (API Gateway/proxy — `api-gateway`): todo tráfego passa por ela; no começo, **tudo vai ao monolito**.
2. **Escolha uma capacidade** com fronteira clara e **valor** (ou dor) — não a mais emaranhada primeiro. Em monolito existente, meça antes com `monolith-decomposition` (acoplamento, donos das tabelas, ordem de extração). Dentro do monolito, **modularize-a antes** (`modular-monolith`) para revelar as dependências.
3. **Construa o novo serviço** (template do `scaffold`), com **seu banco**. Se precisa de dados do monolito: **sincronize por CDC/eventos** (`transactional-outbox`, Debezium) em vez de ler o banco legado — ou use um **Anti-Corruption Layer (ACL)**, uma camada que **traduz** o modelo legado para o seu modelo e impede que o legado "vaze" para o domínio novo.
4. **Roteie o tráfego gradualmente** pela fachada (por rota, por % — *canary*, ou *shadow traffic* para comparar respostas) e **compare resultados**.
5. **Migre os dados** (cópia + sincronização, depois corte de escrita) e **aposente** o código antigo daquele trecho.
6. **Repita** — o monolito encolhe até o que sobrar não valer a pena extrair (e **tudo bem** se sobrar um monolito pequeno e saudável).
Regras: nunca duas fontes de verdade para o mesmo dado ao mesmo tempo sem plano de reconciliação; **um capability por vez**; reverter deve ser fácil (a fachada volta a apontar para o monolito).

---

## 8. Governança sem engessar

- **"Golden path":** um **template de serviço** (o próprio `scaffold` + `code-organization` + `observability` + `Dockerfile` + pipeline) para que todo serviço novo nasça padronizado — autonomia **dentro de** trilhos.
- **Padronize o transversal**, não o interno: formato de **erro** (`ExceptionResponse`/`ProblemDetail`), **logs JSON com traceId**, **health probes**, **versionamento de API**, **timeouts**, **segurança**. Cada serviço escolhe o resto.
- **Decisões em ADR** (`architect`): por que dividimos assim, qual broker, qual padrão de consistência.
- **Contratos explícitos e versionados** (OpenAPI, esquemas de evento, `contract-testing`); mudanças **somente aditivas** na versão corrente; deprecação com prazo.
- **Repositório:** *polyrepo* (um por serviço — autonomia, pipelines simples) ou *monorepo* (mudanças atômicas, ferramentas para build incremental). Qualquer um serve; **o ponto é a independência de deploy**, não o repositório.
- **SLO por serviço** e dono definido (time/on-call) — "serviço sem dono" é o primeiro a apodrecer.
- **Teste:** muitos **unit**, **contract tests** entre serviços, **poucos** e-2-e (lentos e frágeis — só *smoke* dos fluxos críticos). Veja `testing`, `contract-testing`.
- **Segurança:** não confie na rede interna — **autenticação serviço-a-serviço** e menor privilégio (`service-communication`), segredos por serviço (`aws-rds-secrets-manager`).

---

## 9. Falhas — o que muda quando é distribuído

As **8 falácias da computação distribuída** (a rede é confiável, a latência é zero, a banda é infinita, a rede é segura, a topologia não muda, há um único administrador, o custo de transporte é zero, a rede é homogênea) **são todas falsas**. Consequências de projeto:
- **Toda chamada de rede pode falhar, demorar ou ter resultado desconhecido** → timeout, retry **idempotente**, circuit breaker (`resilience`, `idempotency`).
- **Consistência é eventual** entre serviços → desenhe a UX e o domínio para isso (estados `PENDING`/`CONFIRMED`; `saga-pattern`).
- **Ordem e duplicidade de mensagens** são realidade → consumers idempotentes (`messaging`).
- **Depuração exige correlação** → `traceId` em todo log e mensagem (`observability`).
- **Versões convivem** (rolling update, consumers antigos) → mudanças **compatíveis** (`flyway-migrations`, `contract-testing`).

---

## 10. Checklist de decisão (use no ADR)

- [ ] Existe um problema **concreto** (times, escala, isolamento, ciclo de release) que o monolito modular **não** resolve?
- [ ] O domínio está **entendido** o bastante para traçar fronteiras (event storming feito)?
- [ ] Cada serviço proposto é **dono de uma capacidade de negócio e dos seus dados** (sem banco compartilhado, sem corte técnico, sem entity service)?
- [ ] Consigo **implantar cada serviço sozinho**, e testá-lo sem subir os outros?
- [ ] Os pré-requisitos de plataforma existem (CI/CD, observabilidade, IaC, on-call)?
- [ ] Há **time dono** e SLO para cada serviço?
- [ ] A comunicação privilegia **eventos**, com chamadas síncronas mínimas e **sem cadeias profundas**?
- [ ] Sei como cada transação entre serviços será **consistente** (saga/outbox/idempotência)?
- [ ] O caminho de **migração** é gradual e **reversível** (Strangler Fig)?
Se algum item for "não": **fique no monolito modular** e revisite.

---

## Regras principais

- **Monolito modular primeiro**; divida quando houver dor real de time/escala/isolamento e o domínio estiver entendido. Microsserviço é solução organizacional, não técnica.
- **Fronteiras por bounded context/capacidade de negócio**, nunca por camada técnica nem entity service; em dúvida, **junte**.
- **Banco privado por serviço**; sem banco compartilhado, sem JOIN/FK entre serviços, sem 2PC; referências por ID; duplicação de leitura com **uma fonte de verdade**.
- **Eventos para propagar fatos, síncrono só para resposta imediata**; **sem cadeias** de chamadas; consistência **eventual** por saga + outbox + idempotência.
- Evite o **distributed monolith**: deploy independente, contratos versionados e compatíveis, só contratos em bibliotecas compartilhadas.
- Pré-requisitos de plataforma **antes** de dividir (CI/CD por serviço, observabilidade com `traceId`, IaC, testes de contrato, on-call).
- Migre por **Strangler Fig** (fachada, uma capacidade por vez, ACL, tráfego gradual, reversível).
- Padronize o **transversal** (erro, logs, probes, versionamento, segurança) com um *golden path*; decisões em **ADR**; cada serviço com **dono e SLO**.
- Poucos testes e-2-e; **contract tests** entre serviços.
- Adote só os padrões que resolvem um problema real — um CRUD simples não precisa de saga, CQRS nem hexagonal.
- **Sem Lombok** — deliberado.
