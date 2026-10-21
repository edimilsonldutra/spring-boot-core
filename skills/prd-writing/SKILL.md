---
name: prd-writing
description: PRD que a engenharia consegue executar — template completo (problema, objetivos e não-objetivos, requisitos funcionais e NFRs com números, critérios Given/When/Then, métricas e guardrails, riscos, lançamento, perguntas em aberto), exemplo preenchido e handoff ao tech lead. Use quando escrever, revisar ou atualizar um PRD. Não use para o desenho técnico (design-docs).
---

O PRD define o quê e o porquê; em features médias e grandes, o **como** técnico vem depois, no design doc do `architect` (`design-docs`), que parte dos requisitos numerados deste PRD.

Antes de aplicar este pattern, leia também [`../product-discovery/SKILL.md`](../product-discovery/SKILL.md) (de onde vêm o problema e as hipóteses), [`../user-stories/SKILL.md`](../user-stories/SKILL.md), [`../product-metrics/SKILL.md`](../product-metrics/SKILL.md) e [`../technical-product-management/SKILL.md`](../technical-product-management/SKILL.md) (requisitos não funcionais). Quem recebe o PRD: o agent `tech-lead` (planeja) e `architect` (decisões estruturais).

# PRD

O **PRD** responde **o quê** e **por quê** (problema, público, resultado esperado, escopo) — e deixa para a engenharia o **como**. Um bom PRD é **curto o suficiente para ser lido** e **preciso o suficiente para ser testado**: qualquer pessoa da engenharia e do QA sai dele sabendo **o que significa "pronto"**. Documento longo que ninguém lê não alinha ninguém.

> **Não invente dados no PRD.** Números (usuários afetados, metas, custos) vêm de **fonte medida**; o que for **suposição** é marcado como tal ("**hipótese**: ~15% dos sócios — a medir"). Um PRD com número fabricado dá falsa precisão ao plano.

## Quando escrever (e o tamanho)

| Situação | Formato |
|---|---|
| Mudança pequena e clara | **História** com critérios de aceite (`user-stories`) — sem PRD |
| Funcionalidade com impacto de usuário/negócio, várias histórias | **PRD de 1–3 páginas** (este template) |
| Iniciativa grande/multi-time | PRD **+** seções de dependências, plano de lançamento e riscos detalhados; ainda **enxuto** |

**Escreva depois da descoberta** (`product-discovery`): o PRD registra **o que foi validado**, não substitui validar. **Documento vivo**: versione, registre mudanças de escopo e decisões.

---

## Template

```markdown
# PRD: <nome da iniciativa>

| Campo | Valor |
|---|---|
| Autor / PM | <nome> |
| Status | Rascunho · Em revisão · Aprovado · Em entrega · Lançado |
| Última atualização | AAAA-MM-DD |
| Engenharia (tech lead) | <nome> · Design: <nome> · QA: <nome> |
| Stakeholders / aprovadores | <nomes e papéis (RACI/DACI)> |

## 1. Contexto e problema
<Quem sofre, qual a dor, a evidência (com fonte), o que fazem hoje, o custo de não resolver.
 Link para a descoberta (entrevistas, dados).>

## 2. Objetivo e resultado esperado
<O OUTCOME em linguagem de comportamento/negócio — não "lançar a feature".>
- Objetivo: <ex.: reduzir multas por atraso>
- Como saberemos que deu certo: ver "Métricas de sucesso" (seção 7)

## 3. Não-objetivos (o que NÃO vamos fazer agora)
<Tão importante quanto os objetivos. Evita scope creep e alinha expectativa.>
- <ex.: pagamento online de multas (fica para depois)>

## 4. Público e personas
<Quem vai usar; o job to be done de cada um; segmentos prioritários.>

## 5. Requisitos funcionais
| ID | Requisito | Prioridade (Must/Should/Could) | Critério de aceite |
|---|---|---|---|
| RF-1 | <o sistema deve ... (uma frase, verificável)> | Must | <Given/When/Then ou condição objetiva> |

## 6. Requisitos não funcionais
<Com NÚMEROS e condições. "Rápido" não é requisito.>
- Desempenho: <ex.: p95 < 300 ms para 200 req/s>
- Disponibilidade: <ex.: 99,9% mensal (SLO)>
- Segurança e privacidade: <autorização, dados pessoais envolvidos, base legal, retenção — LGPD>
- Acessibilidade, i18n, compatibilidade: <...>
- Auditoria/observabilidade: <o que precisa ser registrado/medido>

## 7. Métricas de sucesso (e guardrails)
| Tipo | Métrica | Linha de base | Meta | Prazo | Fonte |
|---|---|---|---|---|---|
| Primária (outcome) | <% de empréstimos com multa> | <X% (medido em ...)> | <−30%> | <8 semanas pós-lançamento> | <dashboard/query> |
| Secundária | <taxa de renovação online> | — | <≥ 25%> | <4 semanas> | |
| **Guardrail** (não pode piorar) | <tickets de suporte; latência; erros 5xx> | | <não aumentar> | | |

## 8. Fluxo / experiência
<Jornada do usuário (passos), protótipo/links de design, estados de erro e vazios.>

## 9. Riscos, premissas e dependências
| Item | Tipo | Impacto | Mitigação / responsável |
|---|---|---|---|
| <sistema legado só expõe batch> | Dependência técnica | Alto | <spike do tech lead> |

## 10. Plano de lançamento
<Estratégia de rollout (flag, % progressivo), público piloto, critérios de go/no-go e de aborto,
 plano de rollback, comunicação (suporte, clientes), documentação — ver release-management.>

## 11. Perguntas em aberto
| # | Pergunta | Responsável | Prazo |
|---|---|---|---|

## 12. Histórico de decisões e mudanças
| Data | Decisão/mudança | Quem | Motivo |
|---|---|---|---|
```

---

## Como escrever requisitos bons

**Cada requisito é uma frase única, verificável e sem solução embutida:**
| ❌ Ruim | ✅ Bom |
|---|---|
| "O sistema deve ser rápido" | "A listagem de livros responde em **p95 < 300 ms** com 200 req/s" |
| "Interface amigável" | "Um sócio novo conclui a renovação em **≤ 3 cliques** sem ajuda (teste com 5 usuários)" |
| "Usar Kafka para os avisos" *(solução)* | "O sócio recebe o aviso **até 1 h** depois de o empréstimo entrar nos 3 dias finais" |
| "Suportar muitos usuários" | "Suportar **2.000 renovações/hora** no pico" |
| "Seguro" | "Só o **próprio sócio** renova o seu empréstimo; ações registradas em auditoria" |

**Teste do requisito:** *dá para escrever um teste que passa ou falha?* Se não, é desejo, não requisito.
**Priorização MoSCoW** dentro do PRD: **Must** (sem isso não lança), **Should**, **Could**, **Won't (agora)** — o que vai para "não-objetivos" (`prioritization`).

### Critérios de aceite (Given/When/Then)

Escreva-os de modo que o **QA** consiga transformá-los em teste e o **developer** saiba quando terminou:
```
Cenário: renovar um empréstimo dentro das regras
  Dado um empréstimo ativo do sócio, com vencimento em 3 dias e sem renovações anteriores
  Quando o sócio solicita a renovação
  Então o novo vencimento é 14 dias após o vencimento atual
  E o sócio recebe a confirmação por e-mail

Cenário: renovação negada por reserva de outro sócio
  Dado um empréstimo ativo cujo livro tem uma reserva de outro sócio
  Quando o sócio solicita a renovação
  Então a renovação é recusada com a mensagem "livro reservado por outro sócio"
  E o vencimento não muda
```
Cubra **o caminho feliz, as regras de negócio, os erros e os limites** (nº máximo de renovações, empréstimo vencido, sócio bloqueado). O `qa` deriva destes cenários os casos de teste (`testing`); o `developer` os usa como definição de pronto.

---

## Exemplo preenchido (enxuto): Renovação online de empréstimo

```markdown
# PRD: Renovação online de empréstimo

Autor: PM · Status: Em revisão · Atualização: 2026-03-02 · Tech lead: <nome>

## 1. Contexto e problema
Sócios esquecem de devolver/renovar e pagam multa. O suporte recebeu 180 tickets/mês de reclamação de multa
[fonte: export do suporte, set/2025]. Hoje a renovação só é possível no balcão ou por telefone.
Em 6 entrevistas com sócios que atrasaram, 5 disseram que "só soube que venceu quando veio a multa" [notas: pasta de pesquisa].

## 2. Objetivo
Reduzir as multas por atraso, permitindo renovar sem ir ao balcão e avisando antes de vencer.

## 3. Não-objetivos
- Pagamento online de multas.
- Renovação por terceiros / procuração.
- App mobile nativo (apenas web responsivo).

## 5. Requisitos funcionais
| ID | Requisito | Prior. | Aceite |
|---|---|---|---|
| RF-1 | O sócio renova um empréstimo ativo pela web | Must | Cenário "renovar dentro das regras" |
| RF-2 | A renovação é negada se há reserva de outro sócio | Must | Cenário "negada por reserva" |
| RF-3 | Máximo de 2 renovações por empréstimo | Must | Terceira tentativa é recusada com a regra explicada |
| RF-4 | Aviso por e-mail 3 dias antes do vencimento | Should | E-mail enviado 1× por empréstimo, até 1 h após entrar na janela |

## 6. Requisitos não funcionais
- Desempenho: renovação p95 < 500 ms a 50 req/s.
- Segurança: só o titular do empréstimo renova (autorização por dono do recurso); chamada repetida não renova duas vezes (idempotência).
- Privacidade: e-mail do sócio usado apenas para esta finalidade; base legal e retenção validadas com o DPO.
- Auditoria: toda renovação registra quem, quando e o vencimento anterior/novo.

## 7. Métricas
| Tipo | Métrica | Base | Meta | Prazo |
|---|---|---|---|---|
| Primária | % de empréstimos que terminam com multa | [a medir: 11% em out/2025] | ≤ 7,5% (−30%) | 8 sem pós-lançamento |
| Secundária | % de sócios com prazo a vencer que renovam online | — | ≥ 25% | 4 sem |
| Guardrail | Tickets de suporte sobre empréstimo | 180/mês | não aumentar | contínuo |

## 9. Riscos e dependências
- Dependência: o cadastro de reservas é de outro serviço (`catalog`) — contrato a alinhar (Alto) — tech lead.
- Risco: regra de renovação difere entre filiais [a confirmar com operações].

## 10. Lançamento
Piloto com 5% dos sócios via feature flag → 25% → 100% se a taxa de erro < 1% e o guardrail de tickets estável. Rollback: desligar a flag.

## 11. Perguntas em aberto
| 1 | O prazo de renovação é 14 dias para todos os tipos de livro? | Operações | 10/03 |
```
(Os números do exemplo são **ilustrativos** do formato; em um PRD real, cada um tem a **sua fonte**.)

---

## O que NÃO pertence ao PRD

- **Decisões técnicas e de arquitetura** ("use Kafka", "microsserviço novo", "tabela X"): são do `tech-lead`/`architect` (ADR). O PRD descreve o **requisito** ("aviso em até 1 h"); a **engenharia escolhe como**. Se há restrição **real** (ex.: "deve usar o SSO corporativo"), registre-a como **restrição** com o motivo.
- **Plano de tarefas e estimativas**: do `tech-lead`, a partir do PRD.
- **Especificação de pixels**: está no design; o PRD referencia.
- **Marketing/comercial** além do necessário ao lançamento.
Misturar **o quê** e **como** faz o PRD envelhecer e tira da engenharia a chance de achar solução melhor/mais barata.

## Revisão e handoff

1. **Revise com engenharia e design antes de aprovar** (30 min): eles apontam **riscos, lacunas e custo**; muitas vezes **cortam escopo** ou sugerem alternativa mais simples. Um PRD "jogado por cima do muro" produz retrabalho.
2. **Pergunte ao `tech-lead`**: "o que você precisa saber para planejar?", "qual o maior risco?", "o que cortaria para entregar mais cedo?".
3. **Revise a privacidade** (`privacy-lgpd`) e **segurança/NFRs** (`technical-product-management`) **antes** de congelar o escopo.
4. **Aprovação explícita** pelos aprovadores definidos (quem decide — `stakeholder-communication`, DACI).
5. **Congele o escopo** para a entrega; **mudanças** depois passam por **decisão registrada** (seção 12): o que entra, o que sai, o impacto no prazo.
6. **Handoff:** o PRD vai ao `tech-lead` (plano e tarefas — o plano cita as skills técnicas), ao `qa` (critérios de aceite → casos de teste) e, se houver decisão estrutural, ao `architect`.

## Anti-patterns

- **PRD que descreve a solução** e não o problema; **sem não-objetivos**; **sem métrica de sucesso** (impossível saber se deu certo).
- **Requisitos vagos** ("rápido", "intuitivo") e **sem critério de aceite**.
- **Números sem fonte**; apresentar hipótese como fato.
- **Documento gigante** que ninguém lê; **PRD congelado** que nunca é atualizado (e vira mentira).
- **Escrever sozinho**, sem engenharia/design/QA; **jogar por cima do muro**.
- **Esquecer NFRs, segurança, privacidade e dados** até o fim (custa caro).
- **Escopo que cresce sem decisão registrada** (scope creep).

---

## Regras principais

- O PRD diz **o quê e por quê**; a engenharia decide **como**. Sem decisões técnicas, **exceto restrições reais** (com motivo).
- Estrutura mínima: **problema com evidência e fonte**, **objetivo (outcome)**, **não-objetivos**, **requisitos** com **critério de aceite Given/When/Then**, **NFRs com números**, **métricas de sucesso + guardrails**, **riscos/dependências**, **plano de lançamento**, **perguntas em aberto**, **histórico de decisões**.
- **Requisito testável**: uma frase, verificável, sem solução embutida; MoSCoW; "se não dá para testar, não é requisito".
- **Nunca invente números**: marque **hipótese/a medir**; cada meta com **linha de base e fonte**.
- **Escreva depois da descoberta**, **revise com engenharia, design e QA** antes de aprovar; privacidade e NFRs **antes** de congelar o escopo.
- **Escopo congelado** na entrega; mudança = **decisão registrada** (o que entra/sai, impacto no prazo).
- Curto e vivo: **1–3 páginas**, versionado e atualizado.
- **Handoff** claro ao `tech-lead`, `qa` e `architect`.
- **Sem Lombok** — deliberado (skill de produto, sem código).
