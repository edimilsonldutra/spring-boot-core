---
name: backlog-refinement
description: Sessão de refinamento de backlog — preparação do PM, roteiro de 60 minutos com saídas por item, Definition of Ready estendida (privacidade, NFRs, contrato, migration, rollout, métricas), Example Mapping, fatiamento, estimativa e template de card refinado. Use quando preparar ou conduzir um refinamento ou avaliar se um item está pronto.
---

Antes de aplicar este pattern, leia também [`../user-stories/SKILL.md`](../user-stories/SKILL.md) (formato, INVEST, critérios de aceite, DoR/DoD, three amigos, fatiamento), [`../agile-delivery/SKILL.md`](../agile-delivery/SKILL.md) (cadência, estimativa e forecast), [`../prioritization/SKILL.md`](../prioritization/SKILL.md) (a ordem do backlog) e [`../prd-writing/SKILL.md`](../prd-writing/SKILL.md) (de onde vêm os itens). Itens técnicos: `refactoring`, `technical-product-management`.

# Refinamento de backlog

**Refinamento é o trabalho contínuo de deixar os itens do topo do backlog *prontos para serem construídos*:** entendidos por todos, pequenos o bastante, com critérios de aceite, com os riscos e dependências conhecidos e com o "como validar" claro. É o que impede que a sprint comece com surpresas ("não sabíamos que dependia do time X", "isso era três histórias").

> **O que NÃO é:** *planejamento* (escolher o que entra na sprint e quanto cabe — `agile-delivery`); *descoberta* (decidir **se** vale construir — `product-discovery`); nem *o PM escrevendo histórias sozinho e entregando*. Refinar **é uma conversa entre PM e engenharia (e QA/design)** sobre itens que **já foram priorizados** como candidatos.

## 1. Onde o refinamento se encaixa

```
Descoberta (vale fazer?) → PRD/ideia priorizada → REFINAMENTO (como é, quão grande, como validar) → Planejamento da sprint → Entrega
        product-discovery        prd-writing            ← esta skill                 agile-delivery
```
- Entra no refinamento: itens **do topo** do backlog, **já priorizados** (`prioritization`) e com **hipótese validada** (dupla trilha — `agile-delivery`).
- Sai do refinamento: itens **Ready** (prontos), **devolvidos** com perguntas, **dividos**, convertidos em **spike**, ou **descartados**.
- **Quanto à frente:** mantenha **~2 sprints** de itens Ready (nem 0, nem 6). Refinar longe demais envelhece e é desperdício (o contexto muda); refinar tarde demais gera planejamento caótico.
- **Custo:** costuma consumir **até ~10% da capacidade do time**; se passa muito disso, os itens chegam mal preparados ou as sessões são ineficientes.

## 2. Quem participa (e quem não precisa)

| Papel | Contribui com |
|---|---|
| **PM / PO** | O **problema, o valor, a prioridade**, as regras de negócio; responde "por quê?"; **decide** escopo (corta ou mantém) |
| **Tech lead / desenvolvedores** | **Viabilidade, riscos técnicos, alternativas mais simples**, dependências, **tamanho** (com incerteza) — **não** projetam a solução em comitê |
| **QA** | "E se…?": **casos de borda e de erro**, como testar, dados de teste, critérios de aceite testáveis |
| **Design/UX** | Fluxo, **estados** (vazio, erro, carregando), acessibilidade |
| **Segurança / DPO / jurídico** | **Só quando o item envolve dado pessoal, segurança ou regulação** — chamados para o item específico, não para a sessão toda |
| **Todos** | Mantenha a sessão **pequena** (4–8 pessoas); quem não agrega, **recebe o resultado por escrito** |

Itens **grandes** ou de **domínio novo** podem pedir uma **sessão própria** com as pessoas certas, em vez de ocupar o time inteiro.

## 3. Preparação (o PM, antes da sessão)

Uma sessão ruim começa com **item mal preparado**. Para cada item (3–6 por sessão), o PM leva:
- **Problema e valor** em 2–3 linhas, **com evidência e fonte** (nunca número inventado — `product-discovery`) e o **objetivo/KR** a que serve (`product-roadmap`).
- **Rascunho de critérios de aceite** (Given/When/Then — `user-stories`), **regras de negócio** conhecidas, **protótipo/design** se houver.
- **Lista do que NÃO sabe** (perguntas abertas) e **dependências** que enxerga.
- **Contexto técnico mínimo** (consultar o código só para **fundamentar** — endpoints/dados existentes — sem decidir a solução; veja `repository-understanding`).
Envie o **pré-leitura com 24 h** de antecedência; **corte** o que não está pronto para discutir (não gaste a sessão descobrindo o básico).

## 4. Roteiro da sessão (60 minutos, 3–6 itens)

```
[5 min]  Objetivo da sessão e ordem dos itens (por prioridade)
[por item, 10–15 min]
   1. PM: problema, valor, para quem (2 min)                 → "por quê?"
   2. Perguntas de esclarecimento (livre, timebox)           → entender, ainda sem soluções
   3. Critérios de aceite: revisar e completar (Given/When/Then)
   4. QA: casos de borda, erros, dados de teste
   5. Tech: abordagem em alto nível, opções, riscos, dependências (sem desenhar em comitê)
   6. Fatiar: cabe em poucos dias? INVEST? Se não, dividir (fatias verticais)
   7. Tamanho: P/M/G (ou "cabe numa sprint? sim/não"), com confiança
   8. SAÍDA: Ready · Precisa de informação (dono + data) · Precisa de spike · Dividir · Descartar
[5 min]  Resumo, ações (dono + data), atualizar o quadro
```
**Regras da sessão:**
- **Timebox por item**: se estoura, **estacione** (*parking lot*) e crie a ação — não vire debate eterno.
- **Uma conversa por vez**; o PM **não** impõe a solução, a engenharia **não** redefine o valor.
- **Discordância técnica** → **spike** com timebox (e pergunta clara) em vez de opinião contra opinião.
- **Registre ao vivo** (a card refinada, abaixo) — quem não estava vê o resultado.
- **Termine no horário.** Sessão de 3 horas é sintoma de itens mal preparados ou escopo grande demais.

## 5. Definition of Ready estendida (checklist por item)

Um item está **Ready** quando **todas** as respostas aplicáveis são "sim" (`user-stories` traz a base; abaixo, o que os times costumam esquecer):
**Entendimento e valor**
- [ ] O **problema/valor** está claro (o "para quê") e ligado a um objetivo.
- [ ] **Critérios de aceite** escritos e **testáveis** (feliz, regras, erros, limites).
- [ ] **Fora de escopo** explícito (o que **não** faremos aqui).
**Tamanho e dependências**
- [ ] **Pequeno** (cabe em poucos dias; INVEST) e **estimável** (a equipe entende).
- [ ] **Dependências** conhecidas e **destravadas** (outro time/serviço/fornecedor; contrato combinado — `contract-testing`).
**Risco, qualidade e operação**
- [ ] **Dados pessoais** envolvidos? Base legal/minimização/retenção definidas (`privacy-lgpd`).
- [ ] **Segurança/autorização** (quem pode o quê; dono do recurso/IDOR — `authentication`).
- [ ] **Não funcionais** com números quando relevante (latência, volume, SLO — `technical-product-management`).
- [ ] **Mudança de dados/contrato**: migration compatível com a versão anterior (`flyway-migrations`); mudança de API **aditiva** ou versionada (`service-communication`).
- [ ] **Idempotência/reprocessamento** se há `POST` repetível ou mensagem (`idempotency`).
- [ ] **Como validar**: abordagem de teste (`test-patterns`) e **dados de teste**.
- [ ] **Observabilidade/métricas**: o que medir/instrumentar para saber se funcionou (`product-metrics`, `observability`).
- [ ] **Rollout**: precisa de **feature flag**/lançamento gradual/comunicação? (`release-management`).
**UX**
- [ ] **Estados** definidos: vazio, erro, carregando, sem permissão; textos de erro.
**Se algo é "não" e não pode ser resolvido na sessão:** vira **ação com dono e data**, e o item **não entra** na sprint até ficar Ready. **DoR não é burocracia**: é a lista do que, quando esquecido, vira atraso.

## 6. Técnicas que funcionam

### Example Mapping (Matt Wynne) — a melhor ferramenta para esclarecer um item
Em 25 minutos, com **cartões de 4 cores**:
- 🟡 **História** (o item) — no topo.
- 🔵 **Regras** (critérios de negócio que governam o item) — uma coluna por regra.
- 🟢 **Exemplos** (casos concretos que ilustram cada regra) — sob a regra.
- 🔴 **Perguntas** (o que ninguém sabe responder agora) — cartões vermelhos.
```
🟡 Sócio renova empréstimo online
 ├─ 🔵 Regra: máximo 2 renovações
 │    ├─ 🟢 1ª renovação → aceita, +14 dias
 │    └─ 🟢 3ª tentativa → recusada com a regra explicada
 ├─ 🔵 Regra: livro reservado não renova
 │    └─ 🟢 reserva de outro sócio → recusada ("livro reservado")
 └─ 🔴 Pergunta: o prazo de 14 dias vale para todos os tipos de livro?   ← dono: PM, até quinta
```
**Leitura do resultado:** **muitos vermelhos** → o item **não está pronto** (volta para descoberta/PM); **muitas regras** → **divida** (cada regra é uma fatia candidata); **poucos exemplos por regra** → casos de borda faltando. Os **exemplos viram os critérios de aceite** (Given/When/Then) e os **casos de teste** do QA.

### Three Amigos (PM + Dev + QA)
Três perspectivas por item: *"o que queremos?"* (PM), *"como poderia funcionar e o que pode dar errado?"* (Dev), *"e se…?"* (QA). Pode ser **mini-sessões antes** da sessão geral para itens complexos (`user-stories`).

### Fatiamento
Divida em **fatias verticais** (atravessam todas as camadas) por **fluxo, regra, variação de dado, feliz × infeliz, esforço agora × depois** e **spikes** para incerteza (`user-stories`: padrões completos). **Sinal de que precisa dividir:** "depende" demais, muitos "e", mais de ~5 critérios independentes, ou a equipe discorda do tamanho por **muito**.

### Spike
Investigação com **timebox** (1–3 dias) que **responde uma pergunta** ("a API de reservas do `catalog` permite consulta por livro em lote?"), com **saída definida** (decisão + custo estimado) — **não** produz entrega de valor, e **não** vira "projeto". Sem pergunta clara e prazo, não é spike, é deriva.

### Estimativa e right-sizing
- **Estimativa é previsão incerta** (`agile-delivery`): **P/M/G**, ou "cabe numa sprint? sim/não", com **confiança** (voto de "dedos": 1–5; baixa confiança → spike ou divisão).
- **Planning poker** serve para **expor divergência** (quando um vota 2 e outro 13, **a conversa é o valor** — alguém sabe algo que o outro não), **não** para chegar a um número "certo". Se todos concordam rápido, siga.
- **Right-sizing por fluxo**: em vez de estimar tudo, **mantenha os itens pequenos e parecidos** e **conte itens** (forecast por vazão — `agile-delivery`): é mais previsível que estimar cada um.
- **A estimativa inclui testes, revisão, migrations e rollout**, não só "codar" (`test-patterns`, `release-management`).
- **Nunca** pressione a estimativa para caber no prazo: **negocie escopo** (`prioritization`, MoSCoW).

## 7. Refinando tipos diferentes de item

| Tipo | O que o refinamento precisa fechar |
|---|---|
| **História de usuário** | O de cima: valor, critérios de aceite, fatia vertical, DoR estendida |
| **Bug** | **Passos de reprodução**, esperado × obtido, ambiente/versão, **logs/trace** (`observability`), **severidade e impacto** (P1/P2/P3 — `agile-delivery`), **duplicata?**, **teste que reproduz** (`qa`) como critério de pronto |
| **Item técnico / habilitador** | **Valor justificado** (risco evitado, velocidade, custo — `technical-product-management`), **escopo e critério de parada**, **como medir**; refatoração → `refactoring` (rede de segurança, passos, DoD) |
| **Spike** | A **pergunta**, o **timebox**, a **saída** esperada |
| **Dívida/atualização de plataforma** | **Custo de atraso** (CVE, fim de suporte — `prioritization`), prazo, risco de **migração** (`release-management`) |
| **Item de dados/migração** | Compatibilidade com a versão anterior, plano de **rollback**, volume e janela (`flyway-migrations`) |

## 8. Higiene do backlog

- **Um** backlog, **ordenado** por prioridade (o topo é o que se refina). Sem backlogs paralelos "por fora".
- **Poda regular**: itens **antigos** (ex.: > 6 meses sem movimento) são **fechados com comentário** ("não vamos fazer por X; reabra com evidência") — backlog de 800 itens **dá falsa esperança** e esconde o que importa.
- **Itens duplicados/obsoletos** viram um só ou são removidos; **vincule** itens relacionados.
- **Rótulos úteis**: tipo (`feature`, `bug`, `tech`, `spike`), **objetivo/KR**, **dependência**, **Ready**.
- **Quadro de refinamento** (colunas): `Novo` → `Precisa de informação` → `Ready` → `Na sprint`. **Limite o WIP de "Ready"** (~2 sprints): mais que isso = refinando cedo demais.
- **Itens "Precisa de informação" têm dono e data**; sem isso apodrecem.

## 9. Como saber se o refinamento funciona

| Sinal | Medida | Se ruim |
|---|---|---|
| **Prontidão** | % dos itens da **próxima sprint** que estavam Ready no planejamento (meta: ~100%) | Refinar mais cedo/melhor; reduzir tamanho |
| **Estoque de Ready** | Itens Ready ≈ 2 sprints | Pouco → risco de planejar no escuro; muito → desperdício |
| **Surpresas na sprint** | Itens que **mudam de escopo**/**travam por dependência** depois de entrar | Melhorar a DoR (dependências, perguntas) |
| **Itens divididos no meio da sprint** | Quantos | Fatiar melhor no refinamento |
| **Retrabalho por entendimento** | Itens devolvidos de QA/PM por "não era isso" | Critérios de aceite/exemplos mais fortes; mais QA/PM na sessão |
| **Tempo de ciclo** | Tendência por tipo de item | Itens grandes demais |
| **Duração e participação das sessões** | Estouram? Todos falam? | Preparação e timebox |

Revise na **retrospectiva** (`agile-delivery`): o refinamento é **processo** — melhore-o como qualquer outro.

## 10. Template de card refinado

```markdown
### <ID> — <título curto (comportamento/valor)>
**Tipo:** feature · bug · tech · spike  |  **Objetivo/KR:** ______  |  **Prioridade:** ______  |  **Tamanho:** P/M/G (confiança: ___)
**Para quem / por quê:** Como <persona>, quero <ação>, para <benefício>.  (evidência/fonte: ______)
**Critérios de aceite:**
- Dado ___, quando ___, então ___.
- Dado ___, quando ___, então ___ (erro/limite).
**Regras de negócio / exemplos (Example Mapping):** ______
**Fora de escopo:** ______
**Dependências:** ______ (contrato combinado? ☐)   **Riscos:** ______
**Dados pessoais?** ☐ não ☐ sim → base legal/retenção: ______    **Segurança/authz:** ______
**Não funcionais:** ______    **Migration/contrato:** ______    **Idempotência:** ______
**Como validar:** testes (unit/integração/contrato), dados de teste, métricas a observar: ______
**Rollout:** flag? gradual? comunicação a suporte/clientes? ______
**UX:** estados (vazio/erro/carregando/sem permissão), textos: ______
**Perguntas em aberto:** ______ (dono, data)
**Decisão do refinamento:** ☐ Ready  ☐ Precisa de informação  ☐ Spike  ☐ Dividir  ☐ Descartar    **Data:** ______
```

## 11. Refinamento com os agents do pacote

O refinamento combina bem com o time de agents (`orchestrator`):
1. **`product-manager`** prepara os itens (problema, evidência, rascunho de critérios, perguntas) e, ao final, **consolida** a card e o veredito.
2. **`tech-lead`** devolve **viabilidade, riscos, dependências, alternativas mais simples e tamanho com incerteza**; **`qa`** devolve **casos de borda/erro, abordagem de teste e dados**; **`architect`** só se houver **decisão estrutural**. Os três são **somente leitura/documentos** e **podem rodar em paralelo**.
3. **O PM decide** o que é Ready, o que se divide e o que se corta; **o humano** aprova. Nada é implementado.
O resultado é um conjunto de cards Ready (e ações para o resto), **não código**.

## 12. Anti-patterns

- **PM refina sozinho** e "entrega" histórias prontas (a engenharia só descobre os problemas na sprint).
- **Refinar no próprio planejamento** da sprint (vira planejamento caótico) ou **refinar 6 sprints à frente** (envelhece).
- **Sem critérios de aceite** ("a gente conversa depois"); **critérios vagos** ("deve ser rápido").
- **Estimar sem entender** (número por pressão); **pressionar a estimativa** em vez de negociar escopo.
- **Design por comitê**: a sessão vira desenho de solução de 2 horas.
- **Sessão de 3 horas com todo mundo** (ou sem preparação do PM); **debate eterno** sem timebox/estacionamento.
- **Itens "Ready" com dependência não resolvida** ou **pergunta aberta sem dono**.
- **Backlog gigante e velho**; **itens grandes** ("épicos") entrando na sprint sem fatiar.
- **Esquecer privacidade, segurança, migrations, rollout e métricas** até o desenvolvimento (descoberto tarde = caro).
- **Transformar refinamento em reunião de status.**
- **Spike sem pergunta nem timebox**; **item técnico sem valor/critério de parada**.

---

## Regras principais

- **Refinamento = deixar os itens do topo Ready** (entendidos, pequenos, com critérios de aceite, riscos e dependências conhecidos, "como validar" claro) — **contínuo**, ~2 sprints à frente, até ~10% da capacidade.
- **Não é** planejamento nem descoberta; é uma **conversa PM + engenharia + QA (+ design)** sobre itens **já priorizados e com hipótese validada**; **PM nunca refina sozinho**.
- **O PM prepara** (problema com evidência e fonte, rascunho de critérios, perguntas, dependências, pré-leitura 24 h antes); **sessão de ~60 min, 3–6 itens, timebox por item, parking lot**, saída **explícita** por item: **Ready / precisa de informação (dono+data) / spike / dividir / descartar**.
- **DoR estendida**: valor, critérios testáveis, fora de escopo, pequeno, dependências destravadas, **dados pessoais**, segurança/authz, NFRs, migration/contrato compatível, idempotência, como validar, métricas, rollout, **estados de UX**.
- **Example Mapping** (história · regras · exemplos · perguntas): muitos vermelhos = não está pronto; muitas regras = dividir; os **exemplos viram critérios de aceite e testes**. **Three Amigos**, **fatias verticais**, **spike com pergunta e timebox**.
- **Estimativa é previsão incerta** (P/M/G + confiança); planning poker expõe divergência; **mantenha itens pequenos e conte itens**; inclua testes/migrations/rollout; **negocie escopo, não estimativa**.
- **Cada tipo de item tem seu fechamento** (bug com reprodução e severidade; técnico com valor e critério de parada; spike com pergunta; migração com rollback).
- **Higiene**: um backlog ordenado, **poda** de itens velhos, rótulos, quadro com WIP de "Ready", "precisa de informação" com dono e data.
- **Meça** prontidão (~100% Ready no planejamento), estoque de Ready, surpresas na sprint, retrabalho por entendimento; melhore o processo na retro.
- **Com os agents**: `product-manager` prepara e consolida; `tech-lead`, `qa` (e `architect` se preciso) analisam em paralelo, **somente leitura**; o humano aprova; **nada é implementado**.
- **Sem Lombok** — deliberado (skill de processo, sem código).
