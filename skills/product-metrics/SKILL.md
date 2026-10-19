---
name: product-metrics
description: Métricas de produto e experimentação — North Star e métricas de entrada, AARRR e HEART, vaidade × acionável, guardrails, funil e coortes, tracking plan sem PII, A/B test (MDE, amostra, duração, peeking, SRM) e como o backend emite eventos de negócio. Use quando definir como medir o sucesso de uma funcionalidade ou planejar um experimento.
---

Antes de aplicar este pattern, leia também [`../prd-writing/SKILL.md`](../prd-writing/SKILL.md) (as metas do PRD), [`../product-roadmap/SKILL.md`](../product-roadmap/SKILL.md) (OKRs) e, do lado técnico, [`../observability/SKILL.md`](../observability/SKILL.md) e [`../aws-observability/SKILL.md`](../aws-observability/SKILL.md) (métricas técnicas), [`../privacy-lgpd/SKILL.md`](../privacy-lgpd/SKILL.md) (dados pessoais em analytics) e [`../transactional-outbox/SKILL.md`](../transactional-outbox/SKILL.md) (eventos confiáveis).

# Métricas de produto

**O que não se mede, não se gerencia — e o que se mede errado, se gerencia errado.** Métricas boas respondem **"estamos entregando valor ao usuário e ao negócio?"**; métricas ruins dão **conforto sem informação**. Esta skill cobre **o que medir**, **como instrumentar** e **como experimentar** com rigor.

> **Nunca invente números.** Linhas de base, metas e resultados vêm de **medição real**. Onde ainda não há dado, o artefato diz **"a medir"** e o **primeiro passo é instrumentar** (seção 5), não chutar uma meta.

## 1. O que é uma boa métrica

| Propriedade | Significado |
|---|---|
| **Acionável** | Mudar o comportamento da equipe muda a métrica; dá para saber **o que fazer** quando se move |
| **Ligada a valor** | Reflete valor **entregue ao usuário** ou resultado de negócio, não atividade |
| **Compreensível e comparável** | Taxa/razão/média por usuário > total absoluto; comparável no tempo e entre coortes |
| **Sensível e oportuna** | Move em tempo útil para orientar decisões |
| **Difícil de manipular** | Não dá para "melhorá-la" sem melhorar o produto de verdade |

**Vaidade × acionável:** *downloads, pageviews, cadastros totais, "usuários registrados"* só **sobem** e não dizem se há valor. Prefira *% de usuários que **ativam** em 7 dias, **retenção** na semana 4, **tempo até o primeiro valor**, taxa de conclusão da tarefa*.

**Leading × lagging:** **lagging** (resultado tardio: receita, churn) confirma, mas **tarde demais** para agir; **leading** (preditoras: ativação, uso da funcionalidade-chave) **antecipam**. Acompanhe **ambas** e entenda a relação entre elas.

**Média esconde a cauda** — para tempo/latência use **percentis (p50/p95/p99)**; para comportamento, **distribuição e coortes**, não só média.

## 2. Frameworks (use como lente, não como camisa de força)

### North Star Metric (NSM) + métricas de entrada
A **North Star** é **uma** métrica que captura **o valor central que o usuário recebe** e que se correlaciona com o crescimento sustentável do negócio. **Exemplos de formato:** *"empréstimos concluídos sem multa por semana"* (biblioteca), *"sócios que usaram ≥ 1 serviço na semana"*. Ela é decomposta em **métricas de entrada** (*input metrics*) que **as equipes podem mover**:
```
North Star: empréstimos concluídos sem multa / semana
├── Amplitude:   novos sócios ativos / semana
├── Frequência:  empréstimos por sócio ativo
├── Eficiência:  % de empréstimos renovados ou devolvidos no prazo
└── Qualidade:   NPS/CSAT pós-empréstimo
```
Uma boa NSM **não é receita** (é resultado), **não é vaidade** e **todas as equipes conseguem influenciá-la** por alguma entrada.

### AARRR ("Pirate Metrics") — funil do ciclo de vida
**A**cquisition (chegam) → **A**ctivation (têm a **primeira experiência de valor**) → **R**etention (voltam) → **R**evenue (pagam) → **R**eferral (indicam). Ajuda a achar **onde o funil vaza** — frequentemente a **ativação** e a **retenção** (e não a aquisição) são o gargalo. **Ativação** é o "momento aha": defina-a **por comportamento** ("renovou ou pegou o primeiro livro em 7 dias"), não por cadastro.

### HEART (Google) — experiência do usuário
**H**appiness (satisfação: NPS, CSAT), **E**ngagement (uso), **A**doption (novos usuários de uma feature), **R**etention, **T**ask success (taxa de sucesso, tempo, erros na tarefa). Combine com **Goals–Signals–Metrics**: para cada **objetivo** de produto, qual **sinal** de comportamento o indica, e qual **métrica** mede o sinal.

## 3. Guardrails — o que não pode piorar

Ao otimizar uma métrica, **outra pode degradar**. **Defina guardrails** (métricas que **não podem piorar** além de um limite) **antes** de lançar:
- Aumentar a **conversão** sem aumentar **reembolsos/tickets**.
- Mais **notificações** sem mais **opt-outs/desinstalações**.
- Nova funcionalidade sem **piorar a latência (p95)** ou a **taxa de erro** (`observability`: SLOs como guardrail técnico).
Todo PRD tem **métrica primária + secundárias + guardrails** (`prd-writing`).

## 4. Funil e coortes

- **Funil:** etapas sequenciais e a **conversão entre elas** (visitou → cadastrou → ativou → renovou). Mostra **onde** perdem usuários; investigue o **maior vazamento** com dados qualitativos (`product-discovery`).
- **Coortes de retenção:** agrupe usuários pela **semana em que entraram** e acompanhe quantos **voltam** na semana 1, 2, 3… A **curva** mostra se a retenção **estabiliza** (produto com valor) ou **cai a zero** (sem valor sustentado). Compare **coortes** para ver se uma mudança melhorou a retenção **de quem entrou depois dela** — a média geral engana (mistura safras).
- **Segmente** (por canal, persona, plano): médias escondem que um segmento vai muito bem e outro muito mal.

## 5. Instrumentação — o plano de rastreamento (tracking plan)

Sem eventos bem definidos, não há análise. **Antes de implementar, escreva o plano**:
| Evento | Quando dispara | Propriedades | Obs. |
|---|---|---|---|
| `loan_renewed` | Renovação concluída com sucesso | `loan_id`, `renewal_number`, `channel` (`web`/`email_link`), `days_to_due` | Evento **de negócio**, vindo do **backend** |
| `renewal_denied` | Renovação recusada | `loan_id`, `reason` (`reserved`/`limit`/`overdue`) | Para entender **por que** falha |
| `renewal_reminder_sent` | Aviso enviado | `loan_id`, `channel` | Cruze com `loan_renewed` para medir o efeito |

Regras:
- **Nomes consistentes** (`objeto_ação` em passado, `snake_case`), **catálogo único** versionado, dono definido — sem `click_button_1`.
- **Propriedades úteis para segmentar** (canal, plano, versão), mas **baixa cardinalidade** quando virarem dimensão de métrica (`observability`: cardinalidade).
- **Identificador de usuário pseudonimizado**; **nunca** e-mail/CPF/nome em propriedade de evento (`privacy-lgpd`). **Consentimento** (cookies/analytics) respeitado; **retenção** definida.
- **Eventos de negócio vêm do backend** (fonte da verdade, à prova de bloqueador de anúncios e de falha de rede do cliente); eventos de **interface** vêm do front.
- **Teste a instrumentação** (QA verifica que o evento dispara **uma vez**, com as propriedades certas, também em falha/retry — `idempotency`: evento duplicado distorce a métrica).
- **Qualidade de dados**: monitore volume de eventos (queda brusca = bug de instrumentação), duplicatas, campos nulos.

### Como o backend Spring Boot entrega isso
- **Eventos de domínio** (`loan_renewed`) publicados por **outbox** (`transactional-outbox`) → broker (`messaging`) → **data lake/warehouse** (S3 + Athena/Redshift, ou ferramenta de produto) — **confiáveis** (sem perda por dual write) e **idempotentes** por `eventId`.
- **Métricas de negócio em tempo real** no Micrometer (`observability`): *counter* `loans.renewed` com tags de **baixa cardinalidade** (`channel`, `result`); alarmes de **guardrail** (`aws-observability`). **Não** coloque `userId` como tag.
- **Métricas técnicas** (latência p99, erro, saturação) são o **guardrail de saúde** do produto — PM e engenharia olham o mesmo painel (`technical-product-management`).
- A **fonte da verdade** de uma métrica de negócio deve ser **uma só**, documentada (a query/definição), para que **"multas por atraso"** signifique a mesma coisa em todo dashboard.

## 6. Experimentos (A/B tests)

Um **A/B test** compara **A (controle)** e **B (variante)** com **usuários aleatoriamente divididos** para medir o **efeito causal** de uma mudança. É a ferramenta certa quando há **volume suficiente** e a pergunta é "**B é melhor que A?**" — para a pergunta "**vale construir?**", comece pelos experimentos baratos de `product-discovery`.

### Antes de rodar
1. **Hipótese**: *"Acreditamos que o lembrete 3 dias antes aumentará a renovação online em ≥ 2 p.p."*
2. **Métrica primária** (uma), **guardrails** e **população** (quem entra, por qual regra).
3. **MDE (Minimum Detectable Effect)**: o **menor efeito que vale a pena detectar**. Efeito pequeno exige **muito mais amostra**.
4. **Tamanho de amostra** por variante. **Regra prática** (poder 80%, significância 5%, para taxa/conversão):
   ```
   n por variante ≈ 16 × p × (1 − p) / δ²        (p = taxa base; δ = efeito absoluto a detectar)
   ```
   **Exemplo:** base 10% (p = 0,10); detectar **+1 p.p.** (δ = 0,01): n ≈ 16 × 0,10 × 0,90 / 0,0001 = **14.400 por variante** (28.800 no total). Detectar **+3 p.p.** exigiria ≈ 1.600 por variante — **efeitos menores custam amostra quadraticamente**. (Aproximação; use uma calculadora de poder para decisões reais.)
5. **Duração**: o tempo para atingir a amostra, **no mínimo ciclos semanais completos** (comportamento muda por dia da semana) — e **fixada de antemão**.
6. **Randomização** por **usuário** (não por sessão), estável (o mesmo usuário vê a mesma variante).

### Durante e depois — erros que invalidam o teste
| Erro | Por quê é um problema | Correção |
|---|---|---|
| **Peeking** (olhar e parar quando "deu significante") | Inflaciona falsos positivos | **Decida a duração/amostra antes** e só conclua no fim (ou use métodos sequenciais próprios) |
| **Muitas métricas/variantes** | Alguma dá "significante" por acaso | **Uma primária** pré-definida; correção para múltiplas comparações |
| **SRM** (*Sample Ratio Mismatch*: a divisão real ≠ a planejada, ex.: 50/50 vira 48/52) | **Bug na randomização/rastreamento** — o resultado não é confiável | **Verifique a proporção** antes de interpretar; investigue a causa |
| **Contaminação / efeito de rede** | A variante afeta o controle (ex.: sócios compartilham livros) | Randomize em um nível adequado (grupo/região) |
| **Efeito de novidade** | O interesse inicial passa | Rode o bastante; olhe a tendência |
| **Significância ≠ relevância** | p < 0,05 com efeito minúsculo, sem valor de negócio | Olhe o **tamanho do efeito e o intervalo de confiança** vs o MDE e o custo |
| **Mudar a meta após ver o resultado** | Racionalização | Critério de sucesso **registrado antes** |

Registre o resultado (**mesmo o negativo**): "não funcionou" é **aprendizado valioso**. Em **baixo volume** (poucos usuários), A/B não detecta efeitos pequenos — use **testes qualitativos, métricas antes/depois com cautela, ou experimentos maiores** (`product-discovery`). Experimentos exigem **feature flags e rollout** (`release-management`) e **cuidado ético/LGPD** (`privacy-lgpd`): não teste algo que **prejudique** o usuário nem use dado sem base legal.

## 7. Dashboards e rituais

- **Um dashboard por pergunta**, não por todas as métricas possíveis: **NSM + métricas de entrada**, **funil/coortes**, **guardrails**. Quem olha sabe **o que fazer** com o que vê.
- **Defina cada métrica** (fórmula, fonte, dono, atualização) em um **dicionário de métricas** — acaba com "cada dashboard calcula de um jeito".
- **Revisão em cadência** (semanal das métricas de entrada; mensal do NSM/coortes; trimestral dos OKRs — `product-roadmap`) com **perguntas**, não só gráficos: *o que mudou? por quê? o que faremos?*
- **Alertas** em quedas anormais (instrumentação quebrada **ou** problema real).
- **Aprenda e feche o ciclo:** após lançar (`release-management`), **meça o resultado** frente à meta do PRD (1 dia, 1 semana, 1 mês) e **registre** o aprendizado.

## 8. Anti-patterns

- **Métricas de vaidade** (totais que só sobem) como sucesso.
- **Sem linha de base** (impossível saber se melhorou) ou **meta inventada**.
- **Sem guardrails** (otimiza uma métrica estragando outra).
- **Instrumentação tardia/inconsistente**, **PII nos eventos**, **eventos duplicados** distorcendo números, **sem plano de rastreamento**.
- **Média** onde se precisa de percentil/coorte; **mistura de coortes**.
- **A/B test sem hipótese**, **sem cálculo de amostra**, **com peeking**, **sem checar SRM**, ou **com volume insuficiente**.
- **Confundir correlação com causalidade** ("quem usa a feature retém mais" ≠ "a feature causa retenção").
- **Dezenas de dashboards ninguém usa**; **cada time com a sua definição** da mesma métrica.
- **Medir pessoas** (produtividade individual) com métricas de produto — gera manipulação.

---

## Regras principais

- **Nunca invente números**: sem dado, **"a medir"** e **instrumente primeiro**.
- Métrica boa é **acionável, ligada a valor, comparável, oportuna e difícil de manipular**; **vaidade ≠ valor**; acompanhe **leading e lagging**; **percentis** e **coortes**, não só médias.
- **North Star** (valor central entregue) decomposta em **métricas de entrada** movíveis pelas equipes; **AARRR** para achar o vazamento (ativação e retenção costumam ser o gargalo); **HEART/Goals-Signals-Metrics** para experiência.
- **Guardrails sempre** (o que não pode piorar), junto da métrica primária no PRD.
- **Tracking plan antes de codar**: nomes consistentes, propriedades segmentáveis, **ID pseudonimizado e sem PII**, **consentimento**, eventos de negócio **do backend**, **testados** e **idempotentes**; eventos por **outbox**; métricas Micrometer de **baixa cardinalidade**.
- **A/B test**: hipótese + métrica primária + **MDE + amostra calculada** (`n ≈ 16·p(1−p)/δ²`) + duração fixa (ciclos semanais) + randomização por usuário; **sem peeking**, **checar SRM**, **significância ≠ relevância**, registrar também os negativos; com pouco volume, outras técnicas.
- **Uma fonte da verdade e um dicionário de métricas**; dashboards por pergunta; revisão em cadência com **decisões**, e **medir o resultado pós-lançamento** contra a meta.
- **Sem Lombok** — deliberado (skill de produto, sem código).
