---
name: monolith-decomposition
description: Análise somente leitura de um monolito Spring Boot existente antes de modularizar ou extrair serviços — inventário e tamanho das capacidades, regra de negócio duplicada, classes sem dono, acoplamento em três dimensões (força, distância, volatilidade), agrupamento em domínios com mapa de donos das tabelas e um roadmap incremental com rollback por passo, entregando o relatório em docs/architecture/decomposition-NOME-DO-SISTEMA.md. Use quando perguntarem como dividir um monolito, o que extrair primeiro, quais módulos estão acoplados demais ou se uma extração vale o custo. Não use em projeto novo (modular-monolith, ddd-hexagonal) nem para executar as mudanças (refactoring).
---

Antes de aplicar este pattern, leia também [`../repository-understanding/SKILL.md`](../repository-understanding/SKILL.md) (o mapa do repositório é a entrada desta análise), [`../microservices/SKILL.md`](../microservices/SKILL.md) (se e quando dividir; Strangler Fig), [`../modular-monolith/SKILL.md`](../modular-monolith/SKILL.md) (o destino padrão: módulos no mesmo deploy) e [`../code-organization/SKILL.md`](../code-organization/SKILL.md) (o layout flat-by-layer). Para o modelo de domínio dentro de cada módulo, `ddd-hexagonal`; para executar os passos, `refactoring`; para registrar a decisão, o ADR do agent `architect`.

# Decomposição de monolito — análise antes da extração

Dividir um monolito **pelo que parece** ("este pacote é grande", "isso deveria ser um serviço") produz o pior dos dois mundos: o **distributed monolith**, com o acoplamento de antes e o custo de rede de depois. Esta skill **mede antes de cortar**: cinco análises em ordem, cada uma usando o resultado da anterior, e um roadmap que começa **modularizando no mesmo deploy**. É **somente leitura**: nada aqui altera o código; o único artefato é o relatório em `docs/architecture/`, gravado **com confirmação**.

> **Evidência ou nada.** Cada afirmação do relatório cita `arquivo:linha`, o comando que a produziu ou a métrica calculada. Marque como no mapa do repositório: ✅ **verificado** · 🔎 **inferido** (diga de onde) · ❓ **desconhecido**. Métrica é **sinal**, não veredito: "33% do código" pede investigação, não extração.

## Quando usar (e quando não)

| Use | Não use |
|---|---|
| Monolito existente que dói: deploys que travam times, mudanças que se propagam, partes com escala ou ciclo diferentes | Projeto novo — desenhe com `modular-monolith`/`ddd-hexagonal` desde o início |
| Decidir **o que** extrair primeiro e **em que ordem** | CRUD pequeno (≲ 5 capacidades): o custo da análise supera o ganho |
| Avaliar se uma extração já proposta **vale o custo** | Decisão já tomada e registrada em ADR — vá para a execução (`refactoring`, `microservices` §7) |
| Preparar um monolito para virar **monolito modular** | Duplicação de código linha a linha (use linter/Sonar) |

## 0. Escopo e pré-requisitos

1. **Objetivo e motivo concreto** (vem do `product-manager`/usuário, não da moda): *"o time de cobrança não consegue fazer deploy sem o time de catálogo"*, *"o relatório derruba a API"*. Sem motivo, o resultado mais provável e **legítimo** é "não divida; modularize" — diga isso.
2. **Mapa do repositório**: use `docs/architecture/repository-map.md` se existir e estiver atualizado (veja o commit no cabeçalho); senão, rode as fases 1–4 e 9 de `repository-understanding` primeiro.
3. **Build verificado**: `jdeps` lê `target/classes`, então compile (`./mvnw -q -DskipTests compile`). Se não compilar, a análise de dependências fica ❓ — diga.
4. **Timebox** (ex.: 2–4 h para um monolito médio) e **registre o que ficou fora**. Se o usuário limitar o escopo a uma análise só, rode-a, mas **declare** que as conclusões das seguintes ficam limitadas.

## 1. Inventário e tamanho das capacidades

**Componente = capacidade de negócio**, não pacote técnico. Como identificá-lo depende do layout:

| Layout | Um componente é… | Como listar |
|---|---|---|
| **Flat-by-layer** (padrão do pacote) | O conjunto de classes com a **mesma raiz de negócio** em todas as camadas: `BookController`, `BookService`, `BookRepository`, `Book`, `BookDTO`, `BookMapper` + as migrations e tabelas de `book` | Raízes de nome dos controllers, services e repositories (comando abaixo) |
| **Por módulo** (`modular-monolith`) | O package de primeiro nível (`…lending`, `…catalog`) | `package-info.java` com `@ApplicationModule`; ou os diretórios do pacote base |
| **Hexagonal** (`ddd-hexagonal`) | O bounded context (`…lending.domain/application/adapter`) | Diretórios de contexto |
| **Sem padrão** | Agrupe pelo vocabulário (entities e tabelas) e marque 🔎 | — |

```bash
grep -rhoE 'class [A-Z][A-Za-z]+(Controller|Service|Repository)\b' src/main/java \
  | sed -E 's/class //;s/(Controller|Service|Repository)$//' | sort | uniq -c | sort -rn
```
Uma raiz que aparece nas três camadas é um componente; uma raiz só em `services` (`ReportService` sem entity) é candidata a classe sem dono (seção 3).

Para cada componente, meça:
- **Statements** (aproximação: linhas que terminam em `;`, sem `import`/`package`): `grep -h ';\s*$' <arquivos> | grep -vcE '^\s*(import|package) '`.
- **Arquivos**, **% do total**, **tabelas** que escreve, **entrypoints** (endpoints, listeners, `@Scheduled`).

Sinais (Richards & Ford, *Software Architecture: The Hard Parts*):
- ⚠️ **Grande demais**: > 2 desvios-padrão acima da média, ou > 10% do código (com 20+ componentes) / > 30% (com < 10). Candidato a **dividir dentro do monolito** antes de qualquer extração.
- 🔍 **Pequeno demais**: < 1% — talvez seja parte de outro (ex.: `Login` dentro de `Authentication`).

```markdown
| Componente | Classes (camadas) | Statements | % | Tabelas | Entrypoints | Sinal |
|---|---|---|---|---|---|---|
| Loan | LoanController, LoanService, LoanRepository, Loan, LoanDTO | 4.312 | 18% | loan, loan_history | 7 HTTP, 1 @Scheduled | ✅ OK |
```

## 2. Regra de negócio duplicada (domínio comum)

Duplicação de **conhecimento** (a mesma regra em dois lugares) é o acoplamento mais traiçoeiro: os componentes **não se importam**, mas precisam mudar juntos (`solid`, DRY). Procure:
- **A mesma regra** em vários services: cálculo de multa, elegibilidade, validação de CPF, arredondamento de dinheiro. `Grep` por nomes de método e constantes iguais ou parecidos (`isPremium`, `calculateFee`, `MAX_RENEWALS`).
- **A mesma capacidade técnica de negócio** espalhada: `JavaMailSender`, `S3Client`, auditoria, notificação usados por vários componentes, cada um com seu template e regra.
- **Enums e status** copiados entre componentes.

Para cada ocorrência: onde (`arquivo:linha` de cada cópia), se as cópias **já divergiram** (bug latente) e a recomendação:
- **Consolidar em um componente dono** (ex.: `notification`, consumido por evento) — quando a regra é a mesma e muda pelo mesmo motivo.
- **Manter separado e documentar** — quando as cópias são parecidas mas **mudam por motivos diferentes** (unificar criaria o acoplamento errado).
- ❌ **Nunca** "resolver" com uma biblioteca `common` de regras de negócio compartilhada entre serviços: é acoplamento funcional com deploy em bloco.

## 3. Classes sem dono e componentes mal recortados

Uma extração falha quando metade do código não tem dono claro. Procure:
- **Classes sem capacidade**: `Utils`, `Helper`, `CommonService`, `GenericService` com regra de negócio dentro; services que não batem com nenhuma entity.
- **God service**: um service que atende várias capacidades (`LoanService` com multa, notificação e relatório). Liste os **grupos de métodos** por capacidade — eles são os cortes.
- **Em layout por módulo**: classes de regra no package base do módulo (API pública) que deveriam estar em subpackage interno, e vice-versa (`modular-monolith` §1).
- **`shared/` virando depósito**: só fica o que é transversal e estável (`Money`, erros comuns); o que tem regra ganha dono.

Saída: para cada classe, **o dono proposto** e o movimento (mover, dividir, manter), com prioridade.

## 4. Acoplamento em três dimensões

Use o modelo de *Balancing Coupling in Software Design* (Vlad Khononov). Para cada dependência entre componentes, avalie três dimensões:

**Força (o que é compartilhado)**, da mais forte para a mais fraca:

| Força | Sinais em Spring Boot |
|---|---|
| **Intrusiva** | `BookRepository` injetado em `LoanService`; JPQL/SQL nativo nas tabelas de outro componente; `@ManyToOne` para a entity de outro componente; acesso por reflection |
| **Funcional** | Regra duplicada (seção 2); `@Transactional` que escreve nas tabelas de dois componentes; ordem obrigatória de chamadas entre eles |
| **De modelo** | A **entity** de outro componente recebida ou devolvida (`Book` no método de `LoanService`); enum interno compartilhado |
| **De contrato** | DTO de integração, interface pública pequena, evento (`LoanStarted`), API versionada — ✅ o padrão correto |

**Distância (onde vive o acoplamento)**: mesma classe < mesmo componente < componentes diferentes no mesmo deploy < serviços diferentes < outro time ou sistema externo. **Avalie também a distância futura**: acoplamento intrusivo entre dois componentes do mesmo deploy é barato **hoje** e vira o problema central **se um deles for extraído**.

**Volatilidade (com que frequência muda)**: pelo tipo de subdomínio (**Core** muda muito; **Supporting** pouco; **Generic** quase nada) e pelo Git:
```bash
git log --since="12 months ago" --name-only --pretty=format: -- src/main/java | sort | uniq -c | sort -rn | head -30
```
Some o churn por componente. **Co-change** (arquivos de componentes diferentes que mudam no mesmo commit) revela acoplamento funcional que o código não declara:
```bash
git log --since="12 months ago" --name-only --pretty=format:'--' -- src/main/java
```
Agrupe a saída por commit (blocos separados por `--`), troque cada arquivo pelo seu componente e conte os pares que aparecem juntos.

**Grafo de dependências** (o JDK já traz o `jdeps`; troque o pacote base):
```bash
jdeps -verbose:class -e 'br\.com\.edimilsonldutra\..*' target/classes
```
Se o projeto já usa Spring Modulith, `ApplicationModules.of(Startup.class)` e o `Documenter` dão o grafo por módulo. **Não adicione dependências** para fazer a análise.

**Diagnóstico por par**:

| Força | Distância (atual ou futura) | Volatilidade | Diagnóstico |
|---|---|---|---|
| Alta | Alta | Alta | 🔴 **Crítico** — mudança cara que se propaga longe |
| Alta | Alta | Baixa | 🟡 Aceitável — forte, mas estável |
| Alta | Baixa | qualquer | 🟢 Coesão — muda junto, vive junto |
| Baixa | Alta | qualquer | 🟢 Baixo acoplamento — separados e independentes |
| Baixa | Baixa | Alta | 🟠 Atenção — coisas sem relação misturadas |
| Baixa | Baixa | Baixa | 🟡 Aceitável — ruído de baixo custo |

O 🔴 é o problema que bloqueia a extração. Volatilidade estimada sem Git fica 🔎; distância organizacional (outro time) **pergunte**.

## 5. Agrupamento em domínios e donos das tabelas

Agrupe os componentes em **domínios candidatos** (bounded contexts — `ddd-hexagonal` §1) usando, juntos:
1. **Linguagem**: os termos do glossário do mapa; sinônimos conflitantes (`Member` × `User`) indicam fronteira.
2. **Acoplamento**: o que tem força alta e volatilidade alta **fica junto** (seção 4).
3. **Dados**: **cada tabela tem um único componente que escreve nela**. Monte o mapa:

```markdown
| Tabela | Escrita por | Lida por | FK de/para outro domínio | Ação |
|---|---|---|---|---|
| book | Catalog | Catalog, Lending (JOIN) | loan.book_id → book.id | Lending passa a guardar só o id e consultar Catalog pela API do módulo |
```
Tabela **escrita por dois domínios** é a primeira coisa a resolver; **sem ela resolvida não há extração**.

Classifique cada domínio em **Core**, **Supporting** ou **Generic**. Isso define a **intensidade de DDD** no destino: modelo rico (aggregates, invariantes) só onde há regra que justifique (`ddd-hexagonal`, "quando não usar"); Generic fica simples ou vira produto pronto (build × buy, `technical-product-management`).

Valide cada grupo: dá para descrevê-lo em uma frase de negócio? Ele é dono dos seus dados? As dependências que saem dele são de contrato?

## 6. Roadmap incremental

A ordem padrão é **modularizar no mesmo deploy primeiro** e **extrair depois, só se o motivo da seção 0 persistir**:

| Fase | O que entrega | Skill |
|---|---|---|
| **1. Preparar** | Rede de segurança: characterization tests nas áreas que vão mudar, cobertura do que será movido | `refactoring`, `test-patterns`, `test-coverage` |
| **2. Recortar** | Classes sem dono movidas, god services divididos, regra duplicada consolidada (seções 2–3) | `refactoring` |
| **3. Modularizar** | Componentes agrupados em módulos com fronteira **verificada no build**, acoplamento intrusivo trocado por API do módulo ou evento, tabelas com um só dono | `modular-monolith` |
| **4. Extrair (opcional)** | Um módulo por vez, via Strangler Fig, com banco próprio e tráfego gradual | `microservices` §7, `service-communication`, `transactional-outbox`, `contract-testing` |

**O que extrair primeiro**: o módulo com **motivo concreto** (escala, deploy ou time diferente), **fronteira já limpa** (sem 🔴, dono único das tabelas) e **risco baixo**. **Não** comece pelo mais emaranhado nem pelo Core mais volátil. Se nenhum módulo tem motivo para sair, o roadmap **termina na fase 3** — e isso é um resultado legítimo.

**Cada passo** do roadmap tem: objetivo · pré-condição · mudanças (com `arquivo:linha` do estado atual) · rede de testes · **rollback** (como desfazer, inclusive dados: expand → contract em `flyway-migrations`) · critério de pronto · tamanho (P/M/G). Passo sem rollback **não entra** no roadmap.

---

## O artefato: `docs/architecture/decomposition-<sistema>.md`

Mostre o conteúdo ao usuário e **peça confirmação antes de gravar** (nunca sobrescreva um relatório existente sem ler e mostrar a diferença). Estrutura:
```markdown
# Decomposição: <sistema>
> Gerado em AAAA-MM-DD por <quem>, commit <sha>. Legenda: ✅ verificado · 🔎 inferido · ❓ desconhecido.

## 1. Resumo
Motivo da análise · recomendação em 3 linhas (ex.: "modularizar; extrair só Reporting") · maior bloqueio.

## 2. Inventário das capacidades
| Componente | Classes | Statements | % | Tabelas | Entrypoints | Sinal |

## 3. Regra de negócio duplicada
| Regra | Onde (arquivo:linha de cada cópia) | Divergiu? | Recomendação |

## 4. Classes sem dono e god services
| Classe | Problema | Dono proposto | Movimento | Prioridade |

## 5. Acoplamento
Grafo (Mermaid) · tabela por par:
| De → Para | Força (evidência) | Distância atual/futura | Volatilidade | Diagnóstico |

## 6. Domínios candidatos
| Domínio | Tipo (Core/Supporting/Generic) | Componentes | Frase de negócio |
Mapa de donos das tabelas · context map (Mermaid)

## 7. Roadmap
| # | Fase | Passo | Pré-condição | Rede de testes | Rollback | Pronto quando | Tamanho |

## 8. Riscos e perguntas em aberto
| # | Pergunta | Para quem | Por que importa |
```

**Depois do relatório**: a decisão estrutural (modularizar, extrair o quê) vira **ADR** do `architect`; o `tech-lead` transforma o roadmap em tarefas; o `developer` executa **um passo por vez** com `refactoring`.

## Anti-patterns

- **Dividir por camada técnica** (serviço de "controllers", serviço de "repositories") ou **pelo organograma** sem olhar o acoplamento.
- **Extrair antes de modularizar**: as dependências escondidas só aparecem quando a fronteira é verificada.
- **Um microsserviço por entity**: fragmenta o que muda junto e cria cadeias de chamadas síncronas.
- **Métrica como veredito** ("33% → extrair") sem olhar o acoplamento e o motivo.
- **Biblioteca `common` com regra de negócio** compartilhada entre serviços.
- **Banco compartilhado depois da extração**: é o sintoma nº 1 do distributed monolith (`microservices`).
- **Roadmap sem rollback** ou com passos grandes que não podem ser revertidos.
- **Afirmar acoplamento sem evidência** (`arquivo:linha`, saída do `jdeps`, contagem do Git).

---

## Regras principais

- **Somente leitura**; motivo concreto antes de começar; o único artefato é `docs/architecture/decomposition-<sistema>.md`, **gravado com confirmação**.
- **Em ordem**: inventário → regra duplicada → classes sem dono → acoplamento → domínios e donos das tabelas → roadmap; cada etapa usa a anterior.
- **Componente = capacidade de negócio** (no flat-by-layer, a mesma raiz de nome em todas as camadas), não pacote técnico.
- **Acoplamento em três dimensões**: força × distância (atual **e futura**) × volatilidade; 🔴 é força alta + distância alta + volatilidade alta.
- **Cada tabela tem um único dono que escreve**; tabela com dois escritores bloqueia a extração.
- **Modularize no mesmo deploy primeiro** (`modular-monolith`); extraia só com motivo, um módulo por vez, via Strangler Fig, e **todo passo com rollback**.
- **Evidência em tudo** (✅/🔎/❓); "não dividir" é um resultado legítimo.
