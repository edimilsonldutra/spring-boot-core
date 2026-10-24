---
name: design-docs
description: Design doc técnico (tech spec / SDD) usado como spec no desenvolvimento orientado a especificação — quando escrever (e quando um ADR basta), relação com PRD, ADR, threat model e plano, template completo (contexto, objetivos e não-objetivos, desenho, contratos de API, dados e migrations, decisões irreversíveis e alternativas, segurança, rollout, observabilidade, testes), critérios de aceite numerados e testáveis, cobertura dos conjuntos enumerados, status e ciclo de vida, desvios durante a implementação, matriz critério → tarefa → prova, verificação independente, revisão, anti-padrões e regras de diagramas Mermaid (tipo por pergunta, densidade, fronteiras). Use antes de construir uma feature média ou grande, quando o PRD estiver aprovado e faltar o "como", ou quando a implementação precisar seguir uma especificação verificável. Não use para o quê e o porquê do produto (prd-writing) nem para uma decisão isolada (ADR do architect).
---

Antes de aplicar este pattern, leia também [`../prd-writing/SKILL.md`](../prd-writing/SKILL.md) (o "quê" e o "porquê" que o design doc parte), [`../user-stories/SKILL.md`](../user-stories/SKILL.md) (critérios Given/When/Then), [`../threat-modeling/SKILL.md`](../threat-modeling/SKILL.md) e [`../code-organization/SKILL.md`](../code-organization/SKILL.md). Conforme o desenho: `api-versioning`, `flyway-migrations`, `release-management`, `observability`, `microservices`.

# Design docs (spec técnica)

O **design doc** descreve **como** uma feature será construída, antes de construí-la: o desenho, os contratos, os dados, as alternativas descartadas, os riscos e **como saberemos que ficou pronta**. Ele é a **spec** do desenvolvimento orientado a especificação: depois de aprovado, o plano sai dele, a implementação o segue, os testes provam cada critério e a revisão confere o código contra ele.

Ele **não** é burocracia: o objetivo é que uma discussão de 30 minutos no documento evite duas semanas de retrabalho no código. Se ninguém vai ler nem verificar contra ele, não escreva.

## 1. Quando escrever

| Situação | O que escrever |
|---|---|
| Correção pequena, ajuste de texto, CRUD igual a outros já existentes | **Nada** — o PR e a descrição bastam |
| Uma decisão estrutural isolada (escolher um broker, trocar o banco de um serviço) | **ADR** (template do agent `architect`) |
| Feature média: alguns endpoints, uma tabela nova, sem integração nova | **Design doc curto** (1–2 páginas: seções marcadas como obrigatórias no template) |
| Feature grande, integração externa, novo serviço, mudança de contrato público, migração de dados, várias equipes | **Design doc completo** (todas as seções) |
| Mudança que toca autenticação, dados pessoais, dinheiro, arquivos ou integrações | Design doc **+ threat model** (`threat-modeling`), linkados |

Regra prática: **se o plano do `tech-lead` passaria de ~5 tarefas, ou se alguém de outro time precisa concordar, escreva o design doc.**

---

## 2. Onde ele se encaixa

```
PRD (product-manager)            o quê e por quê, critérios de produto
   └─▶ Design doc (architect)    como: desenho, contratos, dados, critérios técnicos  ◀── esta skill
          ├─▶ ADRs               uma decisão estrutural cada (o design doc linka, não repete)
          ├─▶ Threat model       ameaças e mitigações (o design doc linka e traz as mitigações como critérios)
          └─▶ Plano (tech-lead)  tarefas que cobrem cada critério do design doc
                 └─▶ Código + testes (developer, qa) ─▶ Revisão contra o doc (code-reviewer)
```
- O design doc **não repete o PRD**: resume o problema em um parágrafo e linka.
- Decisões estruturais com alternativas pesadas viram **ADR próprio**; o design doc cita "ver ADR-007".
- Sistema existente e desconhecido: comece pelo mapa do repositório (`repository-understanding`) e linke-o.

---

## 3. Template — `docs/design/DD-NNN-titulo-em-kebab.md`

As seções marcadas com ★ são obrigatórias mesmo na versão curta.

```markdown
# DD-NNN: <título>

- Status: rascunho | em revisão | aprovado | em implementação | implementado | substituído por DD-XXX
- Autor: <nome/papel> · Revisores: <nomes/papéis> · Data: AAAA-MM-DD
- Links: PRD <link> · ADRs <links> · Threat model <link> · Épico/issue <link>

## 1. Contexto ★
<o problema em um parágrafo, com link para o PRD; o estado atual do sistema que importa para a mudança>

## 2. Objetivos e não-objetivos ★
- Objetivos: <o que esta mudança entrega>
- Não-objetivos: <o que fica explicitamente de fora — evita escopo crescendo em silêncio>

## 3. Critérios de aceite ★
| # | Critério (Given/When/Then) | Origem |
|---|---|---|
| CA-1 | Dado um empréstimo ativo do sócio, quando ele chama POST /api/loan/v1/{id}/renew, então 200 e a data de devolução avança 14 dias | PRD R2 |
| CA-2 | Dado o empréstimo de outro sócio, quando chamo renew com o id dele, então 404 e nada muda | Threat model T1 |
| CA-3 | Renovação responde em p95 < 300 ms com 50 req/s | PRD NFR-1 |

### Cobertura dos conjuntos ★
| Conjunto (seção de origem) | Membros | Critério(s) |
|---|---|---|
| Status de POST /api/loan/v1/{id}/renew (§5) | 200, 404, 409, 422 | 200 → CA-1 · 404 → CA-2 · 409 (limite de renovações) → **lacuna** · 422 → **lacuna** |
| Papéis com acesso à renovação (§8) | SOCIO, ATENDENTE | SOCIO → CA-1 · ATENDENTE → **lacuna** |
<cada **lacuna** vira critério novo (CA-4, CA-5…) ou não-objetivo declarado antes de pedir aprovação>

## 4. Desenho proposto ★
<visão geral em poucas linhas + diagrama (Mermaid) dos componentes e fluxos que mudam>
<onde cada parte entra no layout do projeto: controllers, services, repository, eventos — seguindo code-organization>

## 5. Contratos de API ★
<endpoints novos/alterados: método, rota, request, response, status codes e erros; versão (api-versioning);
exemplos JSON curtos; compatibilidade com clients existentes>

## 6. Dados e migrations ★ (quando houver)
<tabelas/colunas novas ou alteradas, índices, constraints; migrations Flyway em sequência;
compatibilidade com a versão anterior (expand → contract); backfill e volume>

## 7. Decisões irreversíveis e alternativas ★ (quando houver decisão cara de desfazer)
| Decisão irreversível | Forma literal | Alternativa rejeitada e por quê |
|---|---|---|
| Coluna nova em tabela com dados | `loan.renewal_count SMALLINT NOT NULL DEFAULT 0` | Contador em tabela separada: um JOIN a mais em toda leitura |
| Campo novo no contrato público | `"renewalsLeft": 2` (inteiro, nunca nulo) | `"canRenew": true`: perde o "quantas restam", que o app precisa |
<só o que é caro de reverter depois de publicado: schema de dado existente, contrato público, nome de tópico/evento,
formato de ID ou de chave. Nome de classe, divisão de métodos e estrutura interna são reversíveis e ficam no diff.>

| Opção (desenho geral) | Prós | Contras | Por que não |

## 8. Segurança e privacidade ★
<autenticação/autorização (por função e por objeto), dados pessoais, link para o threat model e
as mitigações que viraram critérios de aceite>

## 9. Rollout e rollback
<feature flag, ordem do deploy (migration antes do código), canário/piloto, critério de aborto,
como desfazer — release-management>

## 10. Observabilidade
<métricas, logs e alertas que provam que funciona em produção — observability; eventos de produto — product-metrics>

## 11. Plano de testes ★
<por camada (unit, slice, integração, contrato, smoke); qual teste prova cada critério de aceite>

## 12. Riscos e perguntas em aberto ★
| Risco/pergunta | Impacto | Dono | Prazo |

## 13. Rastreabilidade e prova (preenchida no plano, na implementação e na verificação)
| Critério | Tarefa(s) | Prova (comando) | Asserção que decide | Status |
|---|---|---|---|---|
| CA-1 | T2, T3 | `./mvnw test -Dtest=LoanRenewalIT#renewsAnActiveLoan` | LoanRenewalIT.java:48 | ✅ |
| CA-2 | T3 | `./mvnw test -Dtest=LoanRenewalIT#renewOfAnotherMembersLoanReturns404` | LoanRenewalIT.java:71 | ⚠️ não provado |

## Histórico de mudanças
| Data | Mudança | Aprovado por |
```
- **Numere** os documentos (`DD-001`, `DD-002`…; confira os existentes antes) e **nunca reescreva** um aprovado para outro propósito: crie um novo que o substitui.
- Grave **com confirmação**. Sem segredos, credenciais ou dados pessoais reais (é um arquivo do repositório).
- Textos no idioma do time; identificadores de código (rotas, classes, campos) como serão no código.

---

## 4. Critérios de aceite — o coração da spec

Um design doc só funciona como spec se os critérios forem **verificáveis**:
- **Numerados** (`CA-1`, `CA-2`…) e **estáveis**: tarefas, testes e revisões se referem a eles pelo número.
- **Testáveis**: Given/When/Then com dados, rota e resultado concretos — "deve ser rápido" não é critério; "p95 < 300 ms com 50 req/s" é.
- **Positivos e negativos**: o caminho feliz **e** os erros (400, 404, 409, 422), os limites e os **casos de abuso** do threat model.
- **Com origem**: de qual requisito do PRD, ameaça do threat model ou NFR vem cada um — critério sem origem é escopo que ninguém pediu.
- **Sem desenho embutido**: o critério diz **o que** observar, não qual classe implementar (isso fica na seção 4).
- **Completos por conjunto**: todo conjunto que o doc enumera (status de cada rota na seção 5, papéis e ameaças na seção 8, estados de uma entidade, valores de um enum, tipos de evento) entra na tabela **Cobertura dos conjuntos**, e **cada membro** aponta para um critério. A matriz critério → teste só mostra se os critérios escritos foram testados; a cobertura dos conjuntos mostra **o critério que ninguém escreveu**. Membro sem critério é **lacuna**: escreva o critério ou declare o membro fora de escopo nos não-objetivos.
- **Provados por execução**: na implementação, cada critério ganha uma **prova**, que é o comando que roda o teste e cujo código de saída decide o critério, mais o `arquivo:linha` da **asserção** que o discrimina. O nome do teste não basta, porque um teste pode existir, passar e não afirmar o critério. Sem prova, o status é **⚠️ não provado**.

Bons critérios cobrem, conforme a feature: contrato HTTP (status, corpo, erros — `exception-handling`), autorização (`application-security`), validação (`bean-validation`), persistência e migrations (`flyway-migrations`), idempotência (`idempotency`), eventos (`transactional-outbox`), desempenho (NFR com número), observabilidade (métrica ou log que precisa existir).

### Decisões irreversíveis
A seção 7 lista **só** o que é caro de desfazer depois de publicado ou aplicado: schema de dado existente (`flyway-migrations`, com backup antes de migration destrutiva), contrato público (`api-versioning`), nome de tópico, fila ou evento, e formato de ID ou de chave. Cada uma tem a **forma literal** (a DDL, o campo JSON, o nome exato) e a **alternativa rejeitada**. É o que os revisores mais precisam ler: o resto do desenho se corrige no próximo PR. Uma aposta estrutural ainda aberta (broker, banco, estilo de arquitetura) não entra aqui como decisão: vira ADR e é decidida **antes**.

---

## 5. Ciclo de vida (spec-driven)

| Status | Quem | O que acontece |
|---|---|---|
| **rascunho** | `architect` (com o `tech-lead`) | Escrito a partir do PRD aprovado; perguntas em aberto listadas |
| **em revisão** | Revisores | Comentários no PR do documento; time-box (ex.: 2 dias úteis) |
| **aprovado** | Usuário/responsável | **Gate humano.** O plano só começa daqui (`orchestrator`) |
| **em implementação** | `tech-lead` → `developer`, `qa` | Plano gerado a partir dos critérios; matriz de rastreabilidade entregue no plano e registrada no doc |
| **implementado** | `qa` (provas), `code-reviewer` (verificação) | Todo critério tem prova verde no código final, verificada por quem não escreveu o código nem os testes; nenhum membro de conjunto sem critério; o doc reflete o que foi construído |
| **substituído** | — | Um DD novo o substitui; o antigo fica como histórico |

### Desvios durante a implementação
A realidade sempre diverge um pouco do desenho. A regra:
- **Desvio que não muda contrato, dados nem critério** (nome de classe interna, divisão de métodos): siga e registre no PR.
- **Desvio que muda contrato de API, modelo de dados, critério de aceite, segurança ou rollout**: **pare**, atualize o design doc (seção afetada + histórico de mudanças) e obtenha nova aprovação **antes** de continuar. Código que diverge do doc aprovado sem registro é um achado de revisão.
- Descobriu que um critério é impossível ou errado: volte ao autor do critério (PM para critérios de produto, `architect` para técnicos) — não "ajuste" o teste para passar.

### Rastreabilidade
A seção 13 fecha o ciclo: **todo critério tem pelo menos uma tarefa e uma prova**, e todo teste novo relevante aponta para um critério. Critério sem prova fica marcado como **⚠️ não provado**, e a feature não está pronta (`tech-lead`, Definition of Done).

### Verificação independente (antes de declarar implementado)
Quem escreveu o código ou os testes não verifica o próprio trabalho. Depois da última mudança da feature e antes do commit, o `code-reviewer` (somente leitura, nunca autor) faz a **verificação da spec** sobre tudo o que mudou desde a base (commits e working tree):
1. **Re-executa cada prova** da seção 13 nesse estado e registra o resultado real (não o que o relatório do `developer` ou do `qa` disse).
2. **Lê a asserção** citada em cada linha: ela afirma o critério? Falharia com a implementação errada (o 404 do CA-2 com o empréstimo de outro sócio, não com um id inexistente)?
3. **Recalcula a cobertura dos conjuntos** a partir do diff: rota, status, papel ou estado que o código introduziu e não está na tabela também é lacuna.

O resultado é uma tabela por critério (✅ provado · ❌ prova falha · ⚠️ não provado), válida para o estado verificado: mudança depois dela pede nova verificação. A feature só passa a **implementado** sem ❌ nem ⚠️; o que for aceito como exceção vai para o histórico de mudanças, com quem aprovou.

---

## 6. Revisão do design doc

Revisores: quem vai implementar, quem testa, quem opera (plataforma/SRE quando houver infra) e o PM para os critérios de produto. Checklist:
- [ ] O problema e os não-objetivos estão claros; o escopo bate com o PRD.
- [ ] Todo critério é numerado, testável, tem origem — e os negativos/abusos estão lá.
- [ ] A tabela de cobertura lista todo conjunto enumerado no doc (status por rota, papéis, estados, ameaças), e nenhum membro está sem critério.
- [ ] A seção 7 traz cada decisão irreversível com a forma literal e a alternativa rejeitada; nenhuma aposta estrutural aberta está escondida nela.
- [ ] Contratos completos (status, erros, versão); compatível com clients existentes ou com versão nova (`api-versioning`).
- [ ] Migrations compatíveis com a versão anterior; volume e backfill pensados.
- [ ] Alternativas reais consideradas (inclusive "não fazer" e a mais simples).
- [ ] Segurança: autorização por objeto, dados pessoais, threat model linkado quando a feature é sensível.
- [ ] Rollout com critério de aborto e rollback; observabilidade que prova o funcionamento.
- [ ] Plano de testes cobre todos os critérios.
- [ ] Perguntas em aberto têm dono e prazo — nenhuma bloqueante sem resposta.

Revise **no PR do documento** (comentários por linha, histórico). Uma reunião só para destravar divergências que o texto não resolveu.

---

## 7. Como o time de agents usa

| Agent | Papel no design doc |
|---|---|
| `product-manager` | Entrega o PRD aprovado; revisa os critérios de produto; responde perguntas de escopo |
| `architect` | **Escreve** o design doc (e ADRs/threat model linkados) em `docs/design/`, com confirmação |
| `orchestrator` | Põe a **aprovação do design doc** como gate antes do plano; passa o caminho do doc em todos os briefs seguintes |
| `tech-lead` | Gera o plano **a partir dos critérios** — cada tarefa cita os `CA-n` que cobre — e entrega a matriz de rastreabilidade no plano (ele é somente leitura; o `architect` a registra no doc) |
| `developer` | Implementa seguindo o doc; desvio relevante → para e devolve a pergunta (não decide sozinho) |
| `qa` | Um teste por critério (positivo e negativo) e, para cada um, a prova (comando) e a asserção (`arquivo:linha`) da seção 13; marca o que ficou sem prova |
| `code-reviewer` | Confere o diff contra o doc (critério sem implementação, contrato diferente do especificado, desvio sem registro) e faz a **verificação da spec**: re-executa as provas, lê as asserções e recalcula a cobertura dos conjuntos |

---

## 8. Anti-padrões

- **Documento depois do código** (vira descrição, não decisão) ou **nunca atualizado** (vira mentira).
- **Romance**: dez páginas para uma feature de três tarefas. Use a versão curta.
- **Critérios vagos** ("deve ser seguro", "boa performance") ou **sem negativos**.
- **Matriz verde com conjunto incompleto**: todo critério escrito tem teste, mas o 409 da rota nunca virou critério. A tabela de cobertura existe para isso.
- **"Tem teste" como prova**: o teste existe, passa e afirma outra coisa (status 200 sem conferir a data nova). A prova é a asserção, não o nome.
- **Desenho sem alternativas** — se só há uma opção, provavelmente ninguém pensou nas outras.
- **Repetir o PRD** em vez de linkar; **esconder uma decisão estrutural** no meio do texto em vez de um ADR.
- **Aprovação de fachada**: revisores que não leram. Melhor um revisor que leu do que cinco que aprovaram.
- **Seguir o doc contra a evidência**: se a implementação mostrou que o desenho está errado, atualize o doc — a spec serve ao produto, não o contrário.

---

## 9. Diagramas

Vale para todo diagrama do time: design doc, ADR, threat model e mapa do repositório. **Mermaid no próprio Markdown** (o GitHub renderiza e o diff é revisável); ASCII quando o destino é o terminal.

| Pergunta que o diagrama responde | Tipo |
|---|---|
| Quais peças existem e onde estão as fronteiras (sistema, containers, confiança)? | `flowchart LR` com um `subgraph` por fronteira |
| Quem chama quem, em que ordem, e o caminho de erro? | `sequenceDiagram` |
| Como são as tabelas e as relações? | `erDiagram` |
| Por quais estados uma entidade passa (empréstimo: ativo → renovado → devolvido)? | `stateDiagram-v2` |
| Como um processo decide (regra com ramos)? | `flowchart TD` |

- **Um diagrama, uma pergunta.** No máximo **~15 nós**; passou disso, divida (visão geral + um diagrama por fluxo). Desenhe só o que a feature **muda** e o contexto mínimo para entendê-la.
- **IDs com significado e rótulos legíveis:** `loanService[LoanService]`, nunca `A` ou `s1`. **Seta com verbo e protocolo:** `-->|"POST /api/loan/v1/{id}/renew (HTTPS)"|`, `-->|"publica LoanRenewed (Kafka)"|`.
- **Fronteira de confiança é `subgraph`** com nome ("Internet", "VPC", "Parceiro"), e a mesma fronteira tem o mesmo nome no design doc e no threat model.
- **Visão C4 com `flowchart` + `subgraph`**, não com `C4Context`/`C4Container`: os blocos C4 do Mermaid ainda são experimentais e embaralham as setas.
- **Sem `%%{init}` com cores fixas:** o tema padrão funciona no modo claro e no escuro do GitHub; cor fixa com fundo branco fica ilegível no escuro. Para destacar o que é novo na feature, no máximo uma `classDef`.
- **Diagrama de sistema existente só com o que foi verificado** no código (`repository-understanding`); o inferido é marcado como tal.
- Confira que renderiza (preview do GitHub ou do IDE) antes de pedir aprovação: diagrama quebrado é seção vazia.

---

## Regras principais

- Escreva design doc para features médias e grandes (plano > ~5 tarefas, integração externa, mudança de contrato ou de dados, várias equipes); ADR para uma decisão isolada; nada para mudanças pequenas.
- Parte do PRD aprovado e linka PRD, ADRs e threat model — sem repeti-los.
- Template em `docs/design/DD-NNN-*.md` com status; seções ★ obrigatórias mesmo na versão curta; gravado com confirmação, sem segredos nem dados reais.
- Critérios de aceite **numerados, testáveis, com origem**, incluindo negativos, limites e casos de abuso.
- A aprovação do design doc é um **gate humano** antes do plano.
- Todo conjunto enumerado no doc tem cada membro ligado a um critério (tabela de cobertura); membro sem critério é lacuna ou não-objetivo declarado.
- Decisões irreversíveis (schema, contrato público, nome de evento, formato de ID) com forma literal e alternativa rejeitada; o reversível fica no diff.
- O plano cobre cada critério; cada critério tem prova (comando + asserção `arquivo:linha`); critério sem prova é ⚠️ não provado.
- Antes de **implementado** (e do commit), o `code-reviewer` (nunca o autor) re-executa as provas no estado final, lê as asserções e recalcula a cobertura.
- Desvio que muda contrato, dados, critério, segurança ou rollout → atualiza o doc e reaprova antes de seguir.
- O code review confere o código contra o design doc.
- Diagramas em Mermaid, um por pergunta, até ~15 nós, IDs e setas com significado, fronteiras como `subgraph`, sem cores fixas nem blocos C4 experimentais.
- Documento curto, vivo e verificado vale mais que documento longo e esquecido.
