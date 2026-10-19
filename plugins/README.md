# Padrão Spring Boot — Guia de referência

Guia de referência do plugin `padrao-spring-boot` para o Claude Code: instalação, configuração do projeto, formas de uso, time de agents, catálogo de skills e solução de problemas. Este arquivo acompanha o plugin instalado. A visão geral do projeto e o fluxo individual de cada agent estão no [README do repositório](https://github.com/edimilsonldutra/spring-boot-core#readme).

**Sumário:** [Visão geral](#visão-geral) · [Instalação](#instalação) · [Configuração do projeto](#configuração-do-projeto) · [Formas de uso](#formas-de-uso) · [Agents](#agents) · [Catálogo de skills](#catálogo-de-skills) · [Atualização](#atualização) · [Problemas comuns](#problemas-comuns)

---

## Visão geral

O plugin leva para o Claude Code um padrão único de construção de APIs REST com **Java 25 e Spring Boot 4** — package layout, code style, segurança, testes, documentação e entrega — em duas camadas:

- **Skills (88)** — o *como*. Cada skill documenta uma maneira específica de fazer algo: uma entity, uma migration, um teste de integração, um design doc, um pipeline. São a **fonte de verdade do padrão**: agents e o próprio Claude Code as carregam sob demanda, em vez de responder de memória.
- **Agents (7)** — o *quem*. Especialistas com papel, permissões e formato de entrega próprios: `product-manager`, `architect`, `tech-lead`, `developer`, `qa` e `code-reviewer`, coordenados pelo `orchestrator`. Cada agent carrega as skills da sua tarefa antes de agir.

```
Você ──pede──▶ orchestrator ──delega──▶ agents especialistas ──carregam──▶ skills (o padrão)
   ▲                │                                                          │
   └── aprova nos ──┘◀───────────── entrega verificada (código, testes, docs) ◀─┘
       gates humanos
```

---

## Instalação

O plugin é distribuído pelo repositório público [github.com/edimilsonldutra/spring-boot-core](https://github.com/edimilsonldutra/spring-boot-core), registrado no Claude Code como o marketplace **`padrao`**.

### Requisitos

| Para | Requisito |
|---|---|
| Instalar o plugin | [Claude Code](https://claude.com/claude-code) e Git (`git --version`). Não é necessária conta no GitHub |
| Executar os projetos gerados | JDK 25, Maven ou Gradle (o wrapper acompanha o projeto) e Docker (Testcontainers) |

### Instalar o plugin

No terminal:
```bash
claude plugin marketplace add edimilsonldutra/spring-boot-core
claude plugin install padrao-spring-boot@padrao
```

Ou dentro de uma sessão do Claude Code:
```
/plugin marketplace add edimilsonldutra/spring-boot-core
/plugin install padrao-spring-boot@padrao
```

O primeiro comando registra o marketplace (a confirmação esperada é `Successfully added marketplace: padrao`); o segundo instala o plugin. O formato da instalação é `<plugin>@<marketplace>` — o nome do marketplace vem do `marketplace.json`, não do nome do repositório.

### Escopo da instalação

| Escopo | Disponibilidade | Recomendado para |
|---|---|---|
| **User** (padrão do CLI) | Todos os projetos do usuário nesta máquina | Uso individual em vários projetos |
| **Project** | Apenas este projeto, compartilhado pelo `.claude/settings.json` versionado | Times: todos que abrirem o repositório recebem o plugin |
| **Local** | Apenas este projeto, apenas para o usuário atual | Ajustes locais que não devem ser compartilhados |

Para padronizar um time inteiro em um repositório, use o escopo **Project** e versione o `.claude/settings.json` gerado.

### Verificar

Digite `/padrao-spring-boot` em uma sessão e confira as skills no autocomplete, ou rode `/plugin list`. Se nada aparecer, veja [Problemas comuns](#problemas-comuns).

### Só as skills, em outras ferramentas (npx skills)

Os passos acima instalam o **plugin completo** no Claude Code: agents, skills e atualização automática. Se você usa **outra ferramenta de IA** (Cursor, Codex, Gemini CLI, GitHub Copilot…) ou quer **só as skills**, o CLI [`skills`](https://github.com/vercel-labs/skills) instala direto do repositório. Ele precisa de **Node.js** (o `npx` vem junto).

Na pasta do projeto onde as skills vão ficar, rode:

```
npx skills add edimilsonldutra/spring-boot-core --skill '*'
```

O `'*'` instala **as 88 skills de uma vez** — e é o recomendado, porque as skills se referenciam umas às outras (a `design-docs` aponta para `prd-writing` e `threat-modeling`, por exemplo) e esses links só funcionam quando todas estão instaladas lado a lado. O CLI pergunta para quais ferramentas instalar.

| Quero… | Comando |
|---|---|
| Todas as skills no projeto atual | `npx skills add edimilsonldutra/spring-boot-core --skill '*'` |
| Todas, valendo para qualquer projeto (nível do usuário) | `npx skills add edimilsonldutra/spring-boot-core --skill '*' -g` |
| Todas, para uma ferramenta específica, sem perguntas | `npx skills add edimilsonldutra/spring-boot-core --skill '*' -a cursor -y` |
| Todas, para todas as ferramentas detectadas, sem perguntas | `npx skills add edimilsonldutra/spring-boot-core --all` |
| Ver a lista de skills sem instalar nada | `npx skills add edimilsonldutra/spring-boot-core --list` |
| Uma skill só | `npx skills add edimilsonldutra/spring-boot-core --skill design-docs` |
| Atualizar as skills instaladas | `npx skills update` |

No PowerShell, mantenha as aspas simples em `'*'`.

**O que muda em relação ao plugin:**
- **Os agents não vêm junto.** O CLI só instala skills, então o orquestrador e o time não existem nesse modo — as skills são usadas por pedido direto ou pelo nome.
- **As skills não têm o prefixo** `padrao-spring-boot:` — no Claude Code, a skill se chama `/design-docs`, não `/padrao-spring-boot:design-docs`.
- **Uma skill instalada sozinha** funciona, mas as referências dela a outras skills ficam sem destino. Prefira instalar todas.
- **A atualização** é pelo `npx skills update`, não pela atualização automática do plugin.
- **No Claude Code, escolha uma das duas formas.** Plugin e `npx skills` juntos deixam cada skill duplicada. Para o Claude Code, o plugin é o recomendado.

---

## Configuração do projeto

Na primeira utilização em um projeto, o Claude Code coleta as **preferências do projeto** (skill `code-organization`) e as aplica em todas as skills e agents. Toda pergunta tem um padrão — "usar os padrões" é uma resposta válida:

| Preferência | Opções (padrão primeiro) |
|---|---|
| Comentários no código gerado | **Não** / Sim |
| Database | **MySQL** / PostgreSQL / SQL Server / Oracle / MariaDB |
| Annotations do Swagger | **Interface `*ControllerDocs` separada** / direto no controller |
| Build tool | **Maven** / Gradle (Groovy ou Kotlin DSL) |
| Versão do Java | **Última LTS** / qualquer LTS a partir da 17 / outra (não-LTS gera aviso) |
| Arquivo de configuração | **`application.yml`** / `application.properties` |
| Idioma do texto voltado ao client (mensagens de validação e erro, Swagger) | **Inglês** / idioma do time — identificadores de código são sempre em inglês |
| Mapper Entity ↔ DTO | **Dozer** / MapStruct |
| Dependency injection | **Field (`@Autowired`)** / constructor |

Somente o necessário é perguntado: database e mapper apenas quando há persistência; posição das annotations apenas quando há Swagger. As respostas podem ser salvas na seção `## Project preferences` do `CLAUDE.md` do projeto. **Lombok não é usado** e não é uma opção.

**Observações:**
- **Interface `*ControllerDocs` e Bean Validation:** com a interface, as annotations de validação (`@Valid`, `@Min`…) precisam ser declaradas na interface — no override do controller, o Hibernate Validator rejeita e o endpoint responde 500. O Claude Code avisa ao configurar.
- **Databases:** MySQL é o caminho validado de ponta a ponta. Os demais são suportados (driver, módulo do Flyway, Testcontainers, imagem Docker, sintaxe SQL), mas ainda não tiveram um projeto completo construído e testado com eles — revise a saída com atenção redobrada.
- **Build tools:** Maven e Gradle são suportados e foram executados de verdade; `scaffold`, `maven-config`, `docker-and-docker-compose` e `github-actions-aws` trazem os equivalentes de Gradle.

---

## Formas de uso

| Forma | Quando | Como |
|---|---|---|
| **Pedido direto** | Tarefa pequena e clara | Descreva em linguagem natural; o Claude Code identifica as skills pela `description` de cada uma. Ex.: *"Crie um CRUD para `Book` com Flyway migration e Swagger"* aplica `spring-data-jpa`, `flyway-migrations` e `swagger` |
| **Skill pelo nome** | Para garantir qual skill será usada | `/padrao-spring-boot:<skill>` — ex.: `/padrao-spring-boot:authentication` |
| **Agent** | Um papel específico (revisar, testar, planejar, desenhar) | `@developer`, ou *"use o agent qa para montar o plano de testes do BookService"* |
| **Orquestrador** | Entrega de ponta a ponta, com várias etapas e aprovações | `claude --agent padrao-spring-boot:orchestrator` e descreva o objetivo — ex.: *"Entregue a renovação online de empréstimo."* |

---

## Agents

Cada agent tem papel, permissões e formato de entrega próprios. Todos leem `code-organization` (layout e preferências do projeto) e carregam as skills da tarefa com a ferramenta `Skill` — nunca descrevem uma skill de memória. O fluxo individual de cada agent (entrada, etapas, skills, entrega e próximo passo) está no [README do repositório](https://github.com/edimilsonldutra/spring-boot-core#fluxo-individual-de-cada-agent).

| Agent | Papel | Pode alterar | Skills que guiam o trabalho |
|---|---|---|---|
| `orchestrator` | Coordenar o time, verificar entregas, parar nos gates humanos | Nada (delega e lê) | Não carrega skills: **cita no brief** de cada agent as skills da tarefa (ex.: mensageria → `messaging` + a do broker + `transactional-outbox` + `idempotency`) |
| `product-manager` | O **quê**, o **porquê** e o **quão bom** | `docs/product/` (com confirmação) | As 12 de produto (`product-discovery`, `prd-writing`, `user-stories`, `prioritization`, `product-roadmap`, `product-metrics`, `release-management`, `privacy-lgpd`…), `backlog-refinement` e `threat-modeling` (casos de abuso) |
| `architect` | Decisões estruturais e especificação técnica | `docs/design/`, `docs/adr/`, `docs/security/` (com confirmação) | `design-docs` (a spec), `threat-modeling`, `application-security`; **começa por `microservices`**; compara opções com as tabelas "quando usar × quando não" de `modular-monolith`, `ddd-hexagonal`, `messaging` e brokers, `kubernetes`/`aws-eks` × `aws-ecs-fargate` × `aws-lambda`, `spring-data-jpa` × `aws-dynamodb` × `aws-keyspaces`, `authentication` × `aws-cognito`; critérios de `technical-product-management` e `privacy-lgpd` |
| `tech-lead` | Plano, tarefas, riscos, estimativa, DoD | Nada (somente leitura) | Planeja a partir dos critérios do design doc; **atribui uma skill a cada tarefa** do plano, para o `developer` e o `qa` executarem no padrão; DoD com `test-coverage` (90%); `repository-understanding`, `refactoring`, `backlog-refinement` |
| `developer` | Implementar e corrigir, com testes e build real | Código e testes | **Sempre** `code-organization` + `code-style`, e `application-security` em todo endpoint; depois a skill da área (`spring-data-jpa`, `flyway-migrations`, `bean-validation`, `exception-handling`, `swagger`, `authentication`, `maven-config`…); `aws-sdk-java` antes de qualquer AWS; `testing`, `test-patterns`, `integration-testing`. Padrões estruturais (saga, CQRS, hexagonal) **só com ADR** |
| `qa` | Provar que funciona e achar o que quebra | Somente testes | `testing`, `test-patterns`, `integration-testing`, `test-coverage`, `application-security` (IDOR, permissão, limites); cada ameaça do threat model vira teste; a skill da área diz **o que provar** (`idempotency`, `resilience`, `contract-testing`, `localstack`, `saga-pattern`…); **cada critério Given/When/Then** de `prd-writing`/`user-stories` vira caso de teste |
| `code-reviewer` | Revisar o diff e dar o veredito | Nada (somente leitura) | `code-organization` + `code-style`; revisa contra o design doc quando existe; para cada área do diff, usa a seção **"Regras principais"** da skill correspondente como **checklist** (violação = achado) |

### Fluxo completo de uma feature

Cada etapa traz o agent e as skills que ele carrega; os losangos são aprovações humanas.

```mermaid
flowchart TD
    U(["Você: pedido de alto nível"]) --> O["orchestrator<br/>lê o contexto e escolhe o pipeline"]
    O --> PM["product-manager<br/>product-discovery · prd-writing · user-stories<br/>threat-modeling (abusos) · privacy-lgpd"]
    PM --> G1{"Aprovar escopo<br/>(PRD)"}
    G1 -->|"feature média/grande<br/>ou sensível"| AR["architect<br/>design-docs · threat-modeling · ADR<br/>microservices e skills de comparação"]
    G1 -->|"feature pequena"| TL
    AR --> G2{"Aprovar design doc<br/>(critérios CA-n)"}
    G2 --> TL["tech-lead<br/>tarefas a partir dos critérios<br/>uma skill por tarefa · DoD"]
    TL --> G3{"Aprovar plano"}
    G3 --> DEV["developer<br/>code-organization · code-style · application-security<br/>+ skill de cada tarefa · build real"]
    DEV --> QA["qa<br/>um teste por critério · integration-testing<br/>test-patterns · test-coverage"]
    QA --> CR["code-reviewer<br/>diff contra o design doc<br/>Regras principais de cada skill"]
    CR -->|"blocker (máx. 3 ciclos)"| DEV
    CR -->|"aprovado"| G4{"Aprovar commit / push / deploy"}
    G4 --> FIM(["Entrega + relatório do orchestrator"])
```

**Spec-driven:** em features médias e grandes, o design doc aprovado (`design-docs`) é a especificação. O plano cobre cada critério de aceite (`CA-1`, `CA-2`…), a implementação segue o documento, o `qa` escreve um teste por critério e o `code-reviewer` confere o código contra ele. Mudança de contrato, dados, critério, segurança ou rollout durante a implementação volta ao documento e à aprovação antes de seguir.

### Pipelines

O orquestrador usa sempre **o menor pipeline que resolve**:

| Pedido | Pipeline | Gates humanos |
|---|---|---|
| Nova funcionalidade (do zero) | `product-manager` → *(feature média/grande, estrutural ou sensível)* `architect` (design doc, ADR e/ou threat model) → `tech-lead` → `developer` → `qa` → `code-reviewer` | Escopo · Design doc/ADR/threat model · Plano · commit/push |
| Funcionalidade já especificada | `tech-lead` → `developer` → `qa` → `code-reviewer` | Plano · commit/push |
| Correção de bug | `qa` (teste que reproduz) → `developer` (causa raiz) → `code-reviewer` | commit/push |
| Refatoração / dívida técnica | *(se o escopo não está claro)* `tech-lead` → `qa` (testes de caracterização **antes**) → `developer` → `code-reviewer` | Plano · commit |
| Revisão de código/PR | `code-reviewer` | — |
| Decisão de arquitetura | *(se faltam requisitos)* `product-manager` → `architect` | ADR |
| Planejamento / estimativa | *(se falta escopo)* `product-manager` → `tech-lead` | Plano |
| Plano de testes / cobertura | `qa` | — |
| Entender / mapear um repositório | `architect` (grava o mapa) *ou* `tech-lead` (mapa só no relatório) | Gravar o mapa |
| Prontidão para lançamento (go/no-go) | `product-manager` + `tech-lead` + `qa` + `code-reviewer` em paralelo (só leitura) | Go/no-go é seu |

### Regras do orquestrador

- **Não faz o trabalho dos especialistas** nem decide por eles: quando dois agents divergem, **leva as opções a você**.
- **Gates humanos:** para e pede sua aprovação para o **escopo** (PRD), o **design doc**, a **decisão estrutural** (ADR), o **plano** e **qualquer ação irreversível ou externa** (`commit`, `push`, deploy, `kubectl`, `aws`, `terraform apply`). Ele **não executa** essas ações.
- **Verifica**: lê o que mudou e exige a saída real dos testes; "funciona" sem evidência volta para o agent. O que ficou **sem verificação** aparece marcado como tal no relatório.
- **Loops limitados:** revisão com bloqueio → `developer` corrige → `code-reviewer` revisa de novo, no **máximo 3 ciclos**; depois escala a você.
- **Como iniciar:** o melhor é abrir a sessão com ele como agent principal (`claude --agent padrao-spring-boot:orchestrator`), para que ele fale com você direto nos gates. Chamado como subagent ele também funciona, mas devolve cada aprovação no relatório em vez de perguntar. Se a ferramenta `Agent` não estiver disponível, ele **não finge delegar**: entrega um **runbook** com o brief de cada agent para você invocar.

**Comportamento como subagent:** os agents não fazem perguntas no meio do trabalho nem conversam entre si — quando falta uma preferência, assumem o default da skill e dizem isso no relatório; dúvidas para outro agent também voltam no relatório. Salve suas preferências no `CLAUDE.md` (`project-claude-md`) para evitar suposições. Todos pedem confirmação antes de ações destrutivas ou externas (`git push`, `kubectl apply`, comandos `aws` que alteram recursos), nunca imprimem segredos e relatam honestamente o que **não** conseguiram verificar.

---

## Catálogo de skills

Skills que os agents carregam e que também podem ser usadas diretamente (pedido em linguagem natural ou `/padrao-spring-boot:<skill>`). Cada grupo diz quais agents o usam.

**Fundação (12 skills)**

*Usadas por:* todos os agents leem `code-organization`; `developer` e `code-reviewer` leem também `code-style` e a skill da área (CRUD, migration, validation, erros, Swagger); `tech-lead` as atribui às tarefas; `qa` usa `spring-data-jpa`, `bean-validation` e `exception-handling` para testar o contrato.

| Skill | Comando | Descrição | Exemplo de prompt |
|---|---|---|---|
| `guide` | `/padrao-spring-boot:guide` | Explica para que serve este pacote, como as skills se agrupam e qual usar para cada necessidade — o "índice" do pacote inteiro. | "O que este plugin faz, e qual skill eu preciso para adicionar login com JWT?" |
| `scaffold` | `/padrao-spring-boot:scaffold` | Cria um projeto Spring Boot novo do zero, a partir do Spring Initializr. **Ele pergunta** o group e o nome do projeto, a versão do Java (sugere a última LTS — se você escolher uma versão que não é LTS, ele avisa que não é uma boa ideia para produção), Maven ou Gradle (Groovy ou Kotlin DSL), YAML (default) ou `.properties`, e o idioma das mensagens que o client lê — depois pergunta quais building blocks opcionais incluir: persistence (Spring Data JPA + um database), Flyway migrations, exception handling, web config (CORS/content negotiation), Swagger/OpenAPI e Bean Validation, cada um ligado por default mas fácil de recusar um de cada vez. Ele escreve código real para o que você mantiver (usando um exemplo `Book` compartilhado), faz o build do projeto e roda os testes para provar que funciona. A application class é sempre `Startup`. | "Crie um novo projeto Spring Boot chamado library-api." |
| `code-organization` | `/padrao-spring-boot:code-organization` | Faz as perguntas acima, depois decide onde cada arquivo vai no seu projeto (folder layout) e as regras de naming das classes. É a base sobre a qual toda outra skill se apoia. | "Explique a package structure que este padrão usa." |
| `code-style` | `/padrao-spring-boot:code-style` | As regras exatas de formatação Java usadas em todo o pacote (sem Lombok, como escrever `equals()`/`hashCode()`, estilo de logger, etc.). Também é usada automaticamente, na maior parte, pelas outras skills. | "Revise esta classe e corrija seu estilo para seguir a convenção do projeto." |
| `maven-config` | `/padrao-spring-boot:maven-config` | Configura o `pom.xml` do seu projeto — dependencies, plugins, o setup de testes e como consultar as versões mais recentes. | "Configure o pom.xml para um novo projeto Spring Boot com as dependencies do padrão." |
| `spring-data-jpa` | `/padrao-spring-boot:spring-data-jpa` | Cria entities (sem Lombok), relationships, repositories com queries custom e DTOs com mapper Dozer ou MapStruct — o núcleo de qualquer feature de CRUD. Também resolve N+1 e `LazyInitializationException` e testa os repositories contra um banco real. | "Crie um CRUD completo para uma entity `Book`: title, author, price, launch date." |
| `exception-handling` | `/padrao-spring-boot:exception-handling` | Configura como sua API responde quando algo dá errado (404s, 400s, erros customizados), em um único lugar central. | "Adicione um exception handling adequado para quando um Book não for encontrado." |
| `flyway-migrations` | `/padrao-spring-boot:flyway-migrations` | Escreve os arquivos de SQL migration que criam/alteram as tabelas do seu database, na sintaxe do database que você escolheu. | "Crie a Flyway migration para a tabela books." |
| `web-config` | `/padrao-spring-boot:web-config` | Configura CORS (quais sites têm permissão para chamar sua API) e permite que sua API responda em JSON, XML ou YAML se você quiser mais de um formato. **Ele vai fazer uma pergunta de sim/não sobre isso antes de fazer qualquer coisa** — é só responder. | "Configure o web config para este projeto." |
| `swagger` | `/padrao-spring-boot:swagger` | Adiciona documentação interativa da API que você pode navegar em uma página web (Swagger UI). | "Adicione documentação Swagger aos endpoints de Book." |
| `bean-validation` | `/padrao-spring-boot:bean-validation` | Rejeita input inválido na porta de entrada: uma request com title em branco recebe uma mensagem `400` clara por campo, em vez de um `500` vindo do database. Valida o body, path variables e query parameters, com as mensagens no idioma que você escolheu. | "Valide a request de Book: title obrigatório, price positivo." |
| `project-claude-md` | `/padrao-spring-boot:project-claude-md` | Escreve o arquivo `CLAUDE.md` do seu projeto (comandos, notas de teste, suas preferências salvas) para que o Claude Code conheça seu projeto em toda sessão futura. | "Crie o CLAUDE.md para este projeto." |

**API: paginação, links, versões e documentação avançada (4 skills)**

*Usadas por:* `developer` (implementar), `tech-lead` (atribuir às tarefas), `architect` (contrato e evolução da API), `qa` (limites, links e versões) e `code-reviewer` (paginação sem limite, quebra de contrato).

| Skill | Comando | Descrição | Exemplo de prompt |
|---|---|---|---|
| `pagination` | `/padrao-spring-boot:pagination` | Listagens paginadas com `page`, `size` (com máximo) e `direction`, ordenação só por campos permitidos, formato estável (HAL ou `PagedModel`), custo do `count` e keyset para páginas profundas. | "Pagine a listagem de Book com no máximo 100 itens por página." |
| `hateoas` | `/padrao-spring-boot:hateoas` | Links nas respostas (`_links` em HAL): DTO com `RepresentationModel` e `@Relation`, links montados no service, links condicionais por estado, XML/YAML e testes. | "Adicione links HATEOAS aos endpoints de Book." |
| `api-versioning` | `/padrao-spring-boot:api-versioning` | Quando criar uma versão nova, v1 → v2 convivendo (um service, DTO e controller por versão), versionamento nativo do Spring 7, deprecação com `Deprecation`/`Sunset` e desligamento. | "Preciso trocar author por uma lista de authors sem quebrar quem usa a v1." |
| `swagger-advanced` | `/padrao-spring-boot:swagger-advanced` | OpenAPI como contrato: grupos por versão, respostas de erro comuns sem repetição, exemplos, `openapi.json` gerado no build com lint e detecção de breaking change, geração de clients. | "Separe a documentação por versão e bloqueie breaking changes no CI." |

**Arquivos e e-mail (4 skills)**

*Usadas por:* `developer` (implementar), `architect` (onde guardar arquivos, qual provedor de e-mail), `qa` (path traversal, linha inválida, rollback sem e-mail) e `code-reviewer` (upload inseguro, relay de spam, formula injection).

| Skill | Comando | Descrição | Exemplo de prompt |
|---|---|---|---|
| `file-upload-download` | `/padrao-spring-boot:file-upload-download` | Upload e download seguros: nome gerado, proteção contra path traversal, tipo validado pela assinatura do arquivo, limites (413), download em stream com `Content-Disposition` correto e dono do arquivo checado. | "Crie os endpoints de upload e download da capa do livro." |
| `file-import-export` | `/padrao-spring-boot:file-import-export` | Importa XLSX/CSV validando cada linha (tudo ou nada, com o número da linha nos erros) e exporta uma página de dados em XLSX/CSV pelo header `Accept`, com proteção contra CSV injection. | "Crie a importação em massa de livros por planilha e a exportação em XLSX e CSV." |
| `pdf-reports` | `/padrao-spring-boot:pdf-reports` | Relatórios PDF com JasperReports 7: templates no formato novo, compilação com cache, sub-relatório, QR code, fontes no container e testes. | "Gere o relatório PDF da listagem de livros e o PDF de um livro com QR code." |
| `email` | `/padrao-spring-boot:email` | E-mail por SMTP com Spring Mail: timeouts, HTML com Thymeleaf, anexos, envio depois do commit e fora da request, Mailpit no desenvolvimento e GreenMail nos testes. Na AWS, veja `aws-ses`. | "Envie um e-mail de boas-vindas quando um usuário se cadastrar." |

**Especificação, segurança e design de código (5 skills)**

*Usadas por:* `architect` (escreve o design doc e o threat model, desenha os módulos), `developer` (segue o design doc; `application-security` em todo endpoint; `solid` e `design-patterns` ao desenhar classes), `tech-lead` (planeja a partir dos critérios do design doc; mitigações viram tarefas), `qa` (cada critério e cada ameaça mitigada vira teste), `code-reviewer` (revisa contra o design doc; checklist de segurança e de design) e `product-manager` (revisa os critérios de produto; casos de abuso no PRD).

| Skill | Comando | Descrição | Exemplo de prompt |
|---|---|---|---|
| `design-docs` | `/padrao-spring-boot:design-docs` | O **design doc** (tech spec / SDD) que serve de **spec** no desenvolvimento orientado a especificação: template em `docs/design/`, critérios de aceite numerados (`CA-1`…) e testáveis, aprovação antes do plano, desvios registrados e a matriz critério → tarefa → teste. | "Escreva o design doc da renovação online de empréstimo a partir do PRD." |
| `application-security` | `/padrao-spring-boot:application-security` | Segurança da API pelo **OWASP API Security Top 10**: autorização por objeto (IDOR), mass assignment, limites e rate limit, injeção, SSRF, desserialização, security headers, segredos, logs de segurança, dependências e SBOM, e testes (incluindo SAST, secret scanning e ZAP). | "Faça uma revisão de segurança dos endpoints de empréstimo." |
| `threat-modeling` | `/padrao-spring-boot:threat-modeling` | Pensa em como a feature pode ser abusada **antes** de construir: diagrama com fronteiras de confiança, STRIDE, casos de abuso, prioridade e uma decisão por ameaça — cada mitigação vira tarefa e teste. Grava em `docs/security/`. | "Faça o threat model da renovação online de empréstimo." |
| `solid` | `/padrao-spring-boot:solid` | Os cinco princípios SOLID no código Spring Boot do pacote, com antes/depois, mais DRY, KISS, YAGNI e Lei de Demeter — e quando **não** aplicar (CRUD simples continua simples). | "Este BookService está difícil de testar. O que viola SOLID e como corrigir?" |
| `design-patterns` | `/padrao-spring-boot:design-patterns` | Padrões de projeto que aparecem de verdade numa API Spring Boot (Strategy, Factory, Adapter, Proxy/AOP, Observer, State, Specification…), onde o Spring já os usa, a armadilha da auto-invocação e os anti-padrões. | "Qual padrão usar para calcular multas diferentes por tipo de sócio?" |

**Java/Spring Boot, Kubernetes e AWS (13 skills)**

*Usadas por:* `developer` (implementar), `architect` (escolher plataforma, cache, identidade), `code-reviewer` (checklists de segurança, Docker, Kubernetes, CI) e `tech-lead`; `qa` usa `testing`, `authentication` e `jvm-performance`.

| Skill | Comando | Descrição | Exemplo de prompt |
|---|---|---|---|
| `authentication` | `/padrao-spring-boot:authentication` | Login stateless com JWT e Spring Security 7: access/refresh token, senhas com BCrypt, autorização por permission. Para login gerenciado (MFA, social), veja `aws-cognito`. | "Adicione autenticação JWT a este projeto." |
| `testing` | `/padrao-spring-boot:testing` | Unit tests de service (JUnit 5 + Mockito + AssertJ, sem Spring) e slice tests de controller (`@WebMvcTest` + `@MockitoBean`), com `@ParameterizedTest`, `ArgumentCaptor` e o que testar ou não. | "Escreva os testes do BookService e do BookController." |
| `caching` | `/padrao-spring-boot:caching` | Cache com Caffeine (local) ou Redis/ElastiCache (distribuído), com TTL, invalidação e métricas. | "Cacheie o findById de Book com Redis." |
| `java-modern-features` | `/padrao-spring-boot:java-modern-features` | Java 17–25: records, sealed interfaces, pattern matching, text blocks, virtual threads e Scoped Values, e quando usar cada um. | "Devo ligar virtual threads neste projeto?" |
| `jvm-performance` | `/padrao-spring-boot:jvm-performance` | Tuning da JVM em container, pool de conexões, queries, startup, diagnóstico e teste de carga. | "A API está lenta e o pod leva OOMKilled. Me ajude a investigar." |
| `observability` | `/padrao-spring-boot:observability` | Actuator, health probes (liveness/readiness), métricas Micrometer/Prometheus, tracing e logs JSON. | "Adicione health checks e métricas a este projeto." |
| `docker-and-docker-compose` | `/padrao-spring-boot:docker-and-docker-compose` | Dockerfile (simples ou multi-stage com layers), usuário não-root, e docker-compose com o database. | "Dockerize este projeto com o MySQL." |
| `kubernetes` | `/padrao-spring-boot:kubernetes` | Manifests de Deployment, Service, Ingress, HPA, PDB, probes, secrets, Kustomize e troubleshooting. | "Crie os manifests do Kubernetes para este projeto." |
| `helm-charts` | `/padrao-spring-boot:helm-charts` | Chart Helm com values por ambiente, `--atomic` upgrade e rollback. | "Transforme estes manifests em um Helm chart." |
| `aws-eks` | `/padrao-spring-boot:aws-eks` | ECR, cluster EKS, permissões por pod (IRSA) em vez de chaves, ALB Ingress, logs e custos. | "Prepare o cluster EKS e o ECR para este projeto." |
| `aws-rds-secrets-manager` | `/padrao-spring-boot:aws-rds-secrets-manager` | RDS seguro (subnet privada, TLS, pool) e senhas no Secrets Manager, entregues sem ir para o Git. | "Conecte a aplicação ao RDS PostgreSQL com a senha no Secrets Manager." |
| `aws-s3-sqs` | `/padrao-spring-boot:aws-s3-sqs` | Upload/download no S3 (presigned URLs) e filas SQS com DLQ, testados com LocalStack. | "Guarde os uploads no S3 e publique um evento no SQS." |
| `github-actions-aws` | `/padrao-spring-boot:github-actions-aws` | Pipeline GitHub Actions → ECR → EKS autenticando por OIDC (sem access keys), com rollback automático. | "Crie o pipeline de CI/CD para o EKS." |

**Ordem sugerida para ir à AWS:** `docker-and-docker-compose` → `observability` → `kubernetes` → `aws-eks` → `aws-rds-secrets-manager` → `github-actions-aws` (e `aws-s3-sqs`, `caching`, `jvm-performance` conforme a necessidade).

**Mensageria (6 skills)**

*Usadas por:* `architect` (decidir se e qual broker), `developer` (implementar com outbox e consumer idempotente), `qa` (duplicata, DLQ, desordem) e `code-reviewer` (dual write, DLQ, serialização).

| Skill | Comando | Descrição | Exemplo de prompt |
|---|---|---|---|
| `messaging` | `/padrao-spring-boot:messaging` | **Comece por aqui.** Diz se você precisa de mensageria, compara Kafka, RabbitMQ, Artemis, SQS/SNS e outras, e define as regras comuns (idempotência, DLQ, schema, segurança). | "Preciso notificar vários serviços quando um livro é criado. Qual broker devo usar?" |
| `kafka` | `/padrao-spring-boot:kafka` | Apache Kafka com Spring: producer seguro, `@KafkaListener`, keys/partições, DLT e retry, tópicos, MSK/Strimzi e testes. | "Publique BookCreated no Kafka e consuma em outro serviço." |
| `rabbitmq` | `/padrao-spring-boot:rabbitmq` | RabbitMQ com Spring AMQP: exchanges, quorum queues, DLQ, publisher confirms, retry com atraso e testes. | "Crie uma fila de processamento de pedidos no RabbitMQ com DLQ." |
| `activemq-artemis` | `/padrao-spring-boot:activemq-artemis` | JMS com ActiveMQ Artemis: `JmsTemplate`, `@JmsListener`, queues vs topics, redelivery e dead-letter no broker. | "Integre com o sistema legado via JMS usando Artemis." |
| `aws-sns-sqs` | `/padrao-spring-boot:aws-sns-sqs` | Fan-out SNS → várias filas SQS, filtros, DLQ/redrive, FIFO e IAM mínimo. | "Faça o fan-out do evento BookCreated para três filas SQS." |
| `transactional-outbox` | `/padrao-spring-boot:transactional-outbox` | Publica eventos **sem dual write** (outbox na mesma transaction) e torna o consumer idempotente. Vale para qualquer broker. | "Garanta que o evento só seja publicado se o livro for salvo, e nunca se perca." |

**Ordem sugerida:** `messaging` → a skill do broker escolhido → `transactional-outbox` (sempre que o evento nascer de uma mudança no banco) → `observability` (lag, DLQ) → `kubernetes`/`aws-eks`.

**AWS: serviços e integração com Spring Boot (12 skills)**

Complementam as skills `aws-eks`, `aws-rds-secrets-manager`, `aws-s3-sqs`, `aws-sns-sqs` e `github-actions-aws` listadas acima.

*Usadas por:* `architect` (comparar ECS × EKS × Lambda, RDS × DynamoDB × Keyspaces), `developer` (sempre `aws-sdk-java` primeiro) e `tech-lead`; `qa` usa `localstack` e `aws-terraform`; `code-reviewer` checa credenciais, IAM e Terraform.

| Skill | Comando | Descrição | Exemplo de prompt |
|---|---|---|---|
| `aws-sdk-java` | `/padrao-spring-boot:aws-sdk-java` | **A base de todas as skills AWS:** SDK v2, credenciais sem chaves (IRSA/task role), clients singleton, timeouts, retries, LocalStack. | "Como configuro o SDK da AWS neste projeto do jeito certo?" |
| `localstack` | `/padrao-spring-boot:localstack` | Emula a AWS no seu computador e nos testes (S3, SQS, SNS, DynamoDB…): docker-compose, profile `local` com trava de segurança, Testcontainers, CI — e deixa claro o que ele **não** prova (IAM, desempenho). | "Configure o LocalStack para eu rodar e testar a integração com S3 e SQS sem conta AWS." |
| `aws-dynamodb` | `/padrao-spring-boot:aws-dynamodb` | DynamoDB com o Enhanced Client: modelagem por padrões de acesso, chaves, GSI, optimistic locking, paginação, IaC e testes. | "Guarde os pedidos no DynamoDB e busque por cliente." |
| `aws-keyspaces` | `/padrao-spring-boot:aws-keyspaces` | Amazon Keyspaces (Cassandra) com Spring Data Cassandra: conexão TLS/SigV4, modelagem por consulta, limitações. | "Migre o modelo Cassandra para o Amazon Keyspaces." |
| `aws-lambda` | `/padrao-spring-boot:aws-lambda` | Lambda em Java: handler puro ou Spring Cloud Function, cold start e SnapStart, SQS com falha parcial, Powertools, SAM. | "Crie uma Lambda que processa a fila SQS de livros." |
| `aws-ecs-fargate` | `/padrao-spring-boot:aws-ecs-fargate` | ECS + Fargate: task definition, execution role vs task role, ALB, circuit breaker, auto scaling, deploy por CI. | "Publique a API no ECS Fargate com ALB e rollback automático." |
| `aws-cognito` | `/padrao-spring-boot:aws-cognito` | Login gerenciado (MFA, social) com a API validando o JWT do Cognito via Spring Security Resource Server. | "Troque o JWT próprio pelo Cognito." |
| `aws-parameter-store` | `/padrao-spring-boot:aws-parameter-store` | Config externa no Parameter Store (SecureString) e feature flags com AppConfig, via `spring.config.import`. | "Mova a configuração para o Parameter Store." |
| `aws-ses` | `/padrao-spring-boot:aws-ses` | E-mail com SES: domínio/DKIM, sandbox, envio assíncrono, bounces e reputação, IAM por remetente. | "Envie e-mail de boas-vindas pelo SES sem bloquear a request." |
| `aws-eventbridge` | `/padrao-spring-boot:aws-eventbridge` | Barramento de eventos: regras, targets com DLQ, `PutEvents` seguro, Scheduler no lugar de `@Scheduled`, replay. | "Publique BookCreated no EventBridge e roteie para uma fila." |
| `aws-observability` | `/padrao-spring-boot:aws-observability` | Logs (retenção!), métricas (e o custo delas), traces com X-Ray/OpenTelemetry e alarmes acionáveis. | "Monte os alarmes essenciais da API na AWS." |
| `aws-terraform` | `/padrao-spring-boot:aws-terraform` | Infra como código: estado remoto, módulos por ambiente, IAM mínimo, plan/apply no CI com OIDC, scanners. | "Declare em Terraform o ECR, a fila e a tabela deste serviço." |

**Ordem sugerida:** `aws-sdk-java` → `aws-terraform` → a plataforma (`aws-ecs-fargate` *ou* `aws-eks` *ou* `aws-lambda`) → dados (`aws-rds-secrets-manager`, `aws-dynamodb`/`aws-keyspaces`) → integração (`aws-s3-sqs`, `aws-sns-sqs`, `aws-eventbridge`, `aws-ses`, `aws-cognito`, `aws-parameter-store`) → `aws-observability` → `github-actions-aws`.

**CI/CD e GitOps (3 skills)**

*Usadas por:* `developer` (escrever os workflows), `architect` (escolher entre deploy direto e GitOps), `tech-lead`, `qa` (validação de manifests) e `code-reviewer` (permissões, OIDC, segredos no pipeline).

| Skill | Comando | Descrição | Exemplo de prompt |
|---|---|---|---|
| `github-actions` | `/padrao-spring-boot:github-actions` | **O CI, para qualquer destino:** build e testes (com Testcontainers), cobertura, imagem no GitHub Container Registry sem segredo extra, release por tag, CodeQL, Dependabot, permissões mínimas e proteção da branch. | "Crie o pipeline de CI deste projeto." |
| `github-actions-cloud` | `/padrao-spring-boot:github-actions-cloud` | Deploy no **Google Cloud** (Cloud Run, GKE) ou no **Azure** (Container Apps, AKS) com OIDC, sem chaves no GitHub, com segredos no Secret Manager/Key Vault e rollback. Na AWS, o equivalente é `github-actions-aws`. | "Faça o deploy da API no Cloud Run a cada push na main, com aprovação para produção." |
| `argocd` | `/padrao-spring-boot:argocd` | Entrega por **GitOps**: o Argo CD no cluster aplica o que está no Git. Cobre o repositório de configuração, Application/AppProject/ApplicationSet, migration do Flyway como `PreSync` hook, CI que só atualiza a tag da imagem, promoção por pull request, rollback por `git revert`, segredos fora do Git e a segurança do próprio Argo CD. | "Configure o Argo CD para implantar a API em dev, staging e prod, com aprovação por PR em produção." |

**Ordem sugerida:** `github-actions` (CI) → o deploy: `github-actions-aws` (AWS), `github-actions-cloud` (GCP/Azure) ou `argocd` (GitOps em qualquer Kubernetes, que usa os manifests de `kubernetes`/`helm-charts` e troca o job de "`kubectl apply`" por um que só commita a nova tag) → smoke pós-deploy com `postman-newman`.

**Arquitetura de microsserviços (10 skills)**

*Usadas por:* `architect` **decide** (começando por `microservices`) e registra o ADR; `tech-lead` planeja a partir da decisão; `developer` só aplica um padrão estrutural **com ADR**; `qa` testa falha parcial, contratos e compensações; `code-reviewer` cobra o ADR de todo padrão novo.

| Skill | Comando | Descrição | Exemplo de prompt |
|---|---|---|---|
| `microservices` | `/padrao-spring-boot:microservices` | **Comece por aqui.** Quando dividir em serviços (e quando não), decomposição por bounded context, dados privados por serviço, o "distributed monolith", pré-requisitos de plataforma, migração com Strangler Fig e um checklist de decisão. | "Devemos migrar este monolito para microsserviços? Como dividir?" |
| `modular-monolith` | `/padrao-spring-boot:modular-monolith` | Monolito modular com **Spring Modulith**: módulos com fronteiras verificadas no build, eventos entre módulos, e o caminho para extrair um serviço depois. | "Organize esta aplicação em módulos por domínio, sem microsserviços." |
| `ddd-hexagonal` | `/padrao-spring-boot:ddd-hexagonal` | DDD tático e arquitetura hexagonal: aggregates, value objects (records), ports e adapters, ArchUnit — e quando **não** usar (CRUD). | "Modele o domínio de empréstimos com aggregates e hexagonal." |
| `api-gateway` | `/padrao-spring-boot:api-gateway` | Gateway e BFF com Spring Cloud Gateway: o que fazer e o que **não** fazer na borda, auth, rate limit, headers de identidade seguros, composição. | "Crie um gateway com rotas, JWT e circuit breaker para os serviços." |
| `service-communication` | `/padrao-spring-boot:service-communication` | Chamadas entre serviços: `RestClient`/`@HttpExchange`, timeouts, ACL de erros, descoberta sem Eureka, **auth serviço-a-serviço (zero trust)**, gRPC e service mesh. | "Faça o serviço de empréstimos chamar o catálogo com segurança." |
| `resilience` | `/padrao-spring-boot:resilience` | Timeout, retry (sem retry storm), circuit breaker, bulkhead e fallback honesto com Resilience4j e os recursos nativos do Spring 7, e como testar falhas. | "Proteja a chamada ao catálogo contra lentidão e falhas." |
| `saga-pattern` | `/padrao-spring-boot:saga-pattern` | Transação de negócio entre serviços com compensações: coreografia × orquestração, estado persistido, timeouts, Temporal/Step Functions. | "Implemente a criação de pedido com estoque e pagamento usando saga." |
| `cqrs-event-sourcing` | `/padrao-spring-boot:cqrs-event-sourcing` | CQRS em três níveis (comece pelo mais simples), projeções idempotentes e reconstruíveis, e Event Sourcing com event store, snapshots e LGPD — e quando **não** usar. | "A listagem está lenta e complexa. Devo usar CQRS?" |
| `contract-testing` | `/padrao-spring-boot:contract-testing` | Contratos entre serviços com **Pact** (broker, `can-i-deploy`) ou Spring Cloud Contract, contratos de eventos e detecção de breaking change do OpenAPI. | "Garanta que mudar o catálogo não quebre o serviço de empréstimos." |
| `idempotency` | `/padrao-spring-boot:idempotency` | `Idempotency-Key` em `POST` (replay, 409/422), consumers idempotentes, concorrência resolvida pelo banco e testes. | "Faça o endpoint de pagamento seguro contra retry e clique duplo." |

**Ordem sugerida:** `microservices` (decidir) → `modular-monolith` ou os serviços → `ddd-hexagonal` (se o domínio for rico) → `api-gateway` e `service-communication` → `resilience` + `idempotency` → `messaging` + `transactional-outbox` → `saga-pattern` / `cqrs-event-sourcing` (só se necessário) → `contract-testing` → `argocd`/`kubernetes`. Para decisões de arquitetura, peça ao agent `architect`.

**Produto: skills do perfil de PM (12 skills)**

*Usadas por:* `product-manager` (todas); `tech-lead` e `qa` consomem `prd-writing` e `user-stories` (critérios de aceite → tarefas e casos de teste); `release-management` e `privacy-lgpd` são usadas pelos 7 agents. São skills de **processo e documento** (sem código): trazem templates, critérios e os erros a evitar. **Nenhuma delas inventa dados** — números e pesquisa vêm de fontes reais; o resto é marcado como hipótese.

| Skill | Comando | Descrição | Exemplo de prompt |
|---|---|---|---|
| `product-strategy` | `/padrao-spring-boot:product-strategy` | Visão e estratégia (diagnóstico → política → ações), posicionamento, análise competitiva, TAM/SAM/SOM sem inventar número, unit economics e business case. | "Monte o business case para a renovação online." |
| `product-discovery` | `/padrao-spring-boot:product-discovery` | Entender o problema antes de construir: quatro riscos, JTBD, entrevistas sem viés, hipóteses, experimentos baratos e a decisão seguir/ajustar/parar. | "Planeje a descoberta sobre por que sócios pagam multa." |
| `prd-writing` | `/padrao-spring-boot:prd-writing` | PRD que a engenharia consegue executar: problema, não-objetivos, requisitos testáveis, NFRs com números, métricas, riscos, plano de lançamento. | "Escreva o PRD da renovação de empréstimo." |
| `user-stories` | `/padrao-spring-boot:user-stories` | Histórias INVEST com critérios Given/When/Then, story mapping, fatias verticais, DoR/DoD e three amigos. | "Quebre este épico em histórias pequenas." |
| `prioritization` | `/padrao-spring-boot:prioritization` | RICE (com exemplo calculado), ICE, MoSCoW, Kano, WSJF; capacidade para dívida técnica; como dizer não; vieses. | "Priorize estes 12 pedidos contra o objetivo do trimestre." |
| `product-roadmap` | `/padrao-spring-boot:product-roadmap` | Roadmap Now/Next/Later orientado a resultado, OKRs bem escritos, planejamento trimestral e como responder pedidos de data. | "Monte o roadmap e os OKRs do próximo trimestre." |
| `product-metrics` | `/padrao-spring-boot:product-metrics` | North Star, AARRR/HEART, guardrails, plano de rastreamento sem PII, e A/B test com cálculo de amostra. | "Defina as métricas e o plano de instrumentação desta funcionalidade." |
| `agile-delivery` | `/padrao-spring-boot:agile-delivery` | Scrum/Kanban na prática, refinamento, forecast por vazão (Monte Carlo), métricas de fluxo, interrupções, dependências, retrospectiva e a parceria PM ↔ tech lead. | "Como planejar a sprint sem prometer data que não temos?" |
| `release-management` | `/padrao-spring-boot:release-management` | Deploy ≠ release: feature flags, rollout progressivo, critérios de aborto definidos antes, rollback (e seu limite com o banco), go/no-go e deprecação de API. | "Planeje o lançamento progressivo da renovação online." |
| `technical-product-management` | `/padrao-spring-boot:technical-product-management` | NFRs com número, SLO e error budget, API como produto, dívida técnica como decisão de produto, build × buy e custo de nuvem. | "Quais requisitos não funcionais devemos exigir deste serviço?" |
| `privacy-lgpd` | `/padrao-spring-boot:privacy-lgpd` | LGPD para produto e engenharia: bases legais, minimização, direitos do titular, eliminação ponta a ponta e checklist para o PRD. **Não é aconselhamento jurídico.** | "Quais requisitos de privacidade esta funcionalidade precisa?" |
| `stakeholder-communication` | `/padrao-spring-boot:stakeholder-communication` | Status com semáforo honesto, resumo executivo, decision log, release notes, comunicado de atraso, DACI e como negociar escopo. | "Escreva o comunicado de atraso do piloto." |

**Ordem sugerida:** `product-strategy` → `product-discovery` → `prd-writing` + `user-stories` → `prioritization` → `product-roadmap` → (handoff ao `tech-lead`) → `agile-delivery` → `release-management` → `product-metrics`; `privacy-lgpd`, `technical-product-management` e `stakeholder-communication` valem em todas as etapas.

**Testes: padrões, integração, cobertura e testes de API (4 skills)**

Complementam a skill `testing` (unit e slice). *Usadas por:* `qa` (o dono do tema), `developer` (testes junto com o código), `code-reviewer` (qualidade dos testes e cobertura) e `tech-lead` (DoD com 90%).

| Skill | Comando | Descrição | Exemplo de prompt |
|---|---|---|---|
| `test-patterns` | `/padrao-spring-boot:test-patterns` | Os padrões que separam teste bom de teste ruim: Given/When/Then, **stub × mock × fake**, Test Data Builder, `@Nested`, valores-limite, property-based (jqwik), TDD/BDD, **test smells** e **testes flaky** (causas e cura). | "Revise estes testes: estão frágeis? Que padrões aplicar?" |
| `integration-testing` | `/padrao-spring-boot:integration-testing` | Testes de integração com **banco real em container** (Testcontainers singleton, nunca H2), `@SpringBootTest` + REST Assured, **isolamento de dados**, contrato de erro, segurança, migrations e cache de contexto. | "Escreva os testes de integração do CRUD de Book." |
| `test-coverage` | `/padrao-spring-boot:test-coverage` | **JaCoCo** (Maven e Gradle), branch coverage, **padrão de 90%** de linha e branch (com cobertura do código novo + catraca para subir um legado), gate no CI (Codecov/Sonar) e **mutation testing (PIT)** para provar que os testes pegariam um bug. | "Configure a cobertura com gate no pipeline e me diga o que está descoberto." |
| `postman-newman` | `/padrao-spring-boot:postman-newman` | Coleção Postman versionada e executada pelo **Newman** contra a aplicação rodando: login JWT automático, ids encadeados, contrato de erro, sem segredos no Git, no CI com docker compose e como **smoke test pós-deploy**. Complementa (não substitui) os testes de integração. | "Monte uma coleção Postman do CRUD de Book e rode no pipeline com o Newman." |

**Ordem sugerida:** `testing` → `test-patterns` → `integration-testing` → `test-coverage` (→ `contract-testing` entre serviços; → `postman-newman` contra a aplicação implantada). Lembre: **cobertura mostra o que não foi testado; não prova qualidade**.

**Entender, refatorar e refinar (3 skills)**

*Usadas por:* `repository-understanding` — `architect` (grava o mapa), `tech-lead`, `developer`, `qa` e `code-reviewer`; `refactoring` — `qa` (rede de segurança), `developer` e `code-reviewer`; `backlog-refinement` — `product-manager` com `tech-lead` e `qa`.

| Skill | Comando | Descrição | Exemplo de prompt |
|---|---|---|---|
| `repository-understanding` | `/padrao-spring-boot:repository-understanding` | Entende um repositório desconhecido **só lendo**: builda/testa de verdade, entrypoints, dados pelas migrations, integrações, hotspots no Git, uma fatia vertical rastreada, riscos com evidência e aderência ao padrão; entrega `docs/architecture/repository-map.md`. | "Mapeie este repositório e me diga os maiores riscos." |
| `refactoring` | `/padrao-spring-boot:refactoring` | Refatoração segura: rede de segurança (characterization tests), passos pequenos e verdes, catálogo de smells → refatoração, Parallel Change/Strangler/expand → contract e como revisar o PR. | "Refatore o `LoanService` sem mudar o comportamento." |
| `backlog-refinement` | `/padrao-spring-boot:backlog-refinement` | Sessão de refinamento de backlog: preparação, roteiro de 60 min, DoR estendida (privacidade, NFRs, contrato, migration, rollout, métricas), Example Mapping, fatiamento, estimativa e card refinado. Também usada pelo agent `product-manager`. | "Refine estes 5 itens do topo do backlog." |

**Total: 88 skills, todas neste plugin.** Na dúvida sobre qual usar, pergunte à skill `guide` — ela lê o que está realmente instalado e indica a skill certa para cada necessidade.

---

## Atualização

Novas versões são publicadas no mesmo repositório; uma atualização chega a quem já instalou quando a `version` do `plugin.json` muda.

| Modo | Como |
|---|---|
| **Automático** (recomendado) | `/plugin` → **Marketplaces** → `padrao` → **Enable auto-update**. O Claude Code verifica novas versões ao iniciar |
| **Manual, na sessão** | `/plugin marketplace update padrao` |
| **Manual, no terminal** | `claude plugin update padrao-spring-boot@padrao` |
| **Skills instaladas via `npx skills`** | `npx skills update` |

Depois de atualizar, confirme com `/plugin list` (veja [Verificar](#verificar)). Se as skills novas não aparecerem, reinicie a sessão do Claude Code.

---

## Problemas comuns

| Sintoma | Causa provável | Como resolver |
|---|---|---|
| `/plugin marketplace add` falha com erro de `git` | O Git não está instalado, ou a cópia pelo GitHub via SSH falhou | Rode `git --version`; se der erro, instale o Git. Se o Git existe, registre pelo endereço HTTPS completo: `/plugin marketplace add https://github.com/edimilsonldutra/spring-boot-core.git`. |
| `/plugin install` diz que o plugin não foi encontrado | O nome depois do `@` está errado | O comando é exatamente `/plugin install padrao-spring-boot@padrao` — o nome do marketplace não é o nome do repositório. Confira com `/plugin marketplace list`. |
| Nada aparece ao digitar `/padrao-spring-boot` | O Claude Code ainda não recarregou o plugin | Feche e abra o Claude Code. Depois confira com `/plugin list`. |
| As skills funcionam em um projeto, mas não em outro | O plugin foi instalado com o scope **Project** ou **Local** | Rode `/plugin uninstall padrao-spring-boot` e instale de novo escolhendo o escopo **User**. Você também pode gerenciar tudo pelo menu que abre ao digitar só `/plugin`. |
| Uma skill nova anunciada não aparece | O plugin ainda não foi atualizado | Siga [Atualização](#atualização). |
| O Claude Code faz as perguntas de preferência em toda conversa | As respostas não foram salvas no `CLAUDE.md` do projeto | Aceite quando ele oferecer salvar, ou peça: "Crie o CLAUDE.md para este projeto" (`project-claude-md`). |
| Cada skill aparece duas vezes no Claude Code (`/design-docs` e `/padrao-spring-boot:design-docs`) | O plugin e o `npx skills` foram instalados juntos | Fique com o plugin e remova as skills soltas: `npx skills remove --all` (ou `npx skills remove --all -g` se instalou com `-g`). |
| Uma skill citada nesta documentação não aparece no autocomplete | O plugin instalado está desatualizado | Siga [Atualização](#atualização) e confira com `/plugin list` se a versão instalada é a mais recente. |