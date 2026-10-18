---
name: stakeholder-communication
description: Comunicação com stakeholders — mapa de stakeholders, conclusão primeiro, modelos prontos (status com RAG, resumo executivo, decision log, release notes, comunicado de atraso, one-pager), RACI/DACI, dizer não, reuniões, escalonamento e incidentes. Use quando escrever um status, dar uma má notícia ou registrar uma decisão.
---

Antes de aplicar este pattern, leia também [`../product-roadmap/SKILL.md`](../product-roadmap/SKILL.md) (o que se comunica), [`../prioritization/SKILL.md`](../prioritization/SKILL.md) (como justificar o "não"), [`../release-management/SKILL.md`](../release-management/SKILL.md) (comunicação de lançamento) e [`../agile-delivery/SKILL.md`](../agile-delivery/SKILL.md) (status baseado em fluxo).

# Comunicação com stakeholders

O PM raramente **manda** em alguém; ele **influencia** — e o instrumento da influência é a **comunicação clara, honesta e previsível**. A maior parte dos conflitos de produto não é de discordância técnica, é de **expectativas desalinhadas** e **surpresas**. A regra de ouro: **sem surpresas** — más notícias **cedo**, com **fatos, impacto e proposta**.

> **Honestidade acima de conforto.** Não prometa o que não controla, não "arredonde" um prazo ou número para agradar, e não esconda risco. Comunicar incerteza **com clareza** gera mais confiança do que uma promessa que quebra. Dados citados precisam de **fonte**; hipótese é dita como hipótese.

## 1. Mapeie os stakeholders

Quem **afeta ou é afetado** pelo produto? Para cada um: **o que querem**, **o que temem**, **quanta influência/interesse** têm e **como prefere ser informado**.
| Stakeholder | Interesse | Influência | Precisa de | Frequência/canal |
|---|---|---|---|---|
| Diretoria | Resultado, risco | Alta | Resumo executivo, decisões a tomar | Mensal/trimestral, 1 página |
| Engenharia (tech lead, devs) | Clareza, foco, contexto | Alta (na entrega) | Problema, critérios de aceite, prioridades | Contínuo, refinamento |
| Vendas / Comercial | Promessas a clientes | Média | O que vem, **o que pode dizer** | Quinzenal, roadmap com confiança |
| Suporte / CS | Reduzir tickets, preparar-se | Média | Aviso de lançamento, FAQ, mudanças | Antes de cada release |
| Jurídico / DPO | Conformidade | Alta (poder de veto) | **Cedo**: dados pessoais, termos (`privacy-lgpd`) | No PRD, antes de congelar o escopo |
| Clientes/usuários | Valor, estabilidade | — | Direção, notas de versão, deprecações | Notas de versão, comunicados |

Classifique em **gerenciar de perto** (alta influência, alto interesse), **manter satisfeito**, **manter informado**, **monitorar**. **Envolva cedo** quem pode **vetar** (jurídico, segurança, DPO) — descobrir o veto no fim custa caro.

## 2. Escreva para a audiência — a conclusão primeiro (BLUF)

**BLUF — *Bottom Line Up Front*:** comece pela **conclusão e pelo que você precisa** da pessoa; os detalhes vêm depois, para quem quiser.
- ❌ "Reunimos com o time e vimos várias opções, a primeira seria… (3 parágrafos) … então precisamos de uma decisão."
- ✅ "**Preciso de uma decisão até sexta:** adiar o aviso por WhatsApp (recomendo) ou cortar o escopo da renovação. **Motivo:** a integração do provedor atrasou 2 semanas. **Impacto:** …"
Princípios: **uma ideia principal por mensagem**; **a audiência certa** (executivo quer decisão e risco; engenheiro quer contexto e critério); **curto** (se passa de uma tela, estruture com títulos e resumo no topo); **escrito > falado** para decisões (registra, escala sem reunião); **sem jargão** para quem não é do time; **específico** (datas, números, nomes — "em breve" não é informação).

## 3. Modelos prontos

### Status semanal (curto, com semáforo — RAG)
```markdown
# Status — <iniciativa> — semana de DD/MM

**Resumo (1 linha):** 🟡 No prazo para o piloto de 17/04, com 1 risco em aberto.

| Objetivo / KR | Meta | Atual | Tendência |
|---|---|---|---|
| Multas por atraso | ≤ 7,5% | 11% (base, ainda sem efeito) | — |

**Feito na semana:** renovação básica em homologação; critérios de aceite da regra de reserva fechados.
**Próxima semana:** teste com 5 sócios; revisão de privacidade com o DPO.
**Riscos / bloqueios:**
- 🟡 API de reservas do `catalog` ainda sem contrato estável — responsável: <nome> — decisão até 12/04.
**Decisões necessárias:** <o quê, de quem, até quando>
**Mudanças de escopo/prazo:** nenhuma.
```
**Semáforo honesto:** 🟢 no caminho · 🟡 em risco (há um plano, mas **pode** escorregar) · 🔴 **vai** atrasar/falhar sem intervenção. **Não** pinte tudo de verde até estourar: **amarelo cedo** é **sinal saudável**; "melancia" (verde por fora, vermelho por dentro) destrói a confiança. Cada cor tem **motivo e plano**.

### Resumo executivo (uma página)
```markdown
# <Iniciativa> — resumo executivo

**Em uma frase:** <o que é e por que importa>
**Situação:** 🟡 <estado> · **Próximo marco:** <o quê, quando>
**Resultados até agora:** <fatos/números com fonte>
**Riscos principais:** <1–3, com mitigação>
**Decisão/ajuda que preciso:** <explícito, com prazo>
**Próximos passos:** <3 itens>
```

### Decision log (registro de decisões — evita "mas ninguém decidiu isso?")
```markdown
| Data | Decisão | Opções consideradas | Motivo | Decisor | Impacto |
|---|---|---|---|---|---|
| 2026-03-10 | Adiar o aviso por WhatsApp para o trimestre seguinte | A) cortar renovação B) adiar WhatsApp | Provedor atrasado; renovação tem maior impacto no KR | Diretoria de Operações | −1 item no escopo; sem mudança de data |
```
Decisões **registradas, com motivo e decisor**, num lugar **acessível** — são a memória do time e a defesa contra reabrir assuntos fechados. Decisões **técnicas** estruturais viram **ADR** (`architect`).

### Comunicado de má notícia (atraso, mudança de escopo, falha)
```markdown
**Assunto:** [Atenção] Piloto da renovação online passa de 17/04 para 02/05

**O que mudou:** o piloto será em 02/05 (2 semanas depois).
**Por quê:** o contrato da API de reservas só foi estabilizado em 28/03, e o teste de segurança achou 1 problema a corrigir.
**Impacto:** a meta do trimestre (−30% de multas) segue possível, mas com **menos 2 semanas** de medição; risco de ficar em −25%.
**O que estamos fazendo:** corrigindo o problema (concluído até 21/04); reduzindo o escopo do piloto (sem o aviso por e-mail).
**O que preciso de você:** concordar com o novo escopo/data até quinta.
**Próxima atualização:** 21/04.
```
**Estrutura:** fato → causa → impacto → plano → o que se pede → próximo contato. **Sem culpa**, sem dramatização, sem minimizar. **Cedo** > perfeito.

### Release notes (para usuários e para o suporte)
```markdown
## Versão 2.4 — 02/05/2026
### Novo
- **Renove seu empréstimo pela web.** Em "Meus empréstimos", toque em "Renovar" — sem ir ao balcão.
- **Aviso antes de vencer.** Você recebe um e-mail 3 dias antes do vencimento.
### Melhorado
- A busca de livros ficou mais rápida.
### Corrigido
- Corrigido o erro que impedia a renovação de livros reservados por engano.
### Avisos
- O endpoint legado `/api/v1/loans/extend` será descontinuado em 01/09/2026 — migre para `/api/v2/...`.
```
Escreva pela perspectiva do **benefício para o usuário** (não do código), agrupe (Novo/Melhorado/Corrigido/Avisos), inclua **deprecações com prazo** (`release-management`). Versão **interna** (suporte/vendas) acrescenta: **quem é afetado, FAQ, como reverter, o que pode e não pode ser dito**.

### One-pager de proposta (para pedir decisão/recurso)
`Problema (com evidência e fonte) → Proposta (o quê, não o como) → Resultado esperado (métrica) → Alternativas consideradas (incl. "não fazer") → Custo e esforço (do tech lead) → Riscos → O que preciso (decisão/recurso) e até quando.`

## 4. Decisões: RACI e DACI

Quem decide? Sem clareza, tudo vira reunião sem fim.
- **RACI** (atividades): **R**esponsible (executa), **A**ccountable (**um** responde pelo resultado), **C**onsulted (consultado antes), **I**nformed (informado depois).
- **DACI** (decisões): **D**river (conduz o processo), **A**pprover (**decide**, um só), **C**ontributors (opinam), **I**nformed. **Um** *Approver*: decisão por comitê sem dono não sai. **Consulte** muito, **decida** com clareza, **registre** (decision log). **"Disagree and commit"**: quem discordou, após decidido, **executa** a decisão — depois de ter tido espaço para discordar.
Defina o DACI **antes** das decisões importantes (escopo, lançamento, prioridade entre times), não durante o conflito.

## 5. Dizer não e negociar

O PM diz "não" (ou "não agora") **muito mais** do que "sim". Como fazê-lo **sem queimar a relação**:
1. **Entenda a necessidade por trás do pedido** (`product-discovery`): o "preciso do relatório X" esconde uma dor que talvez outra solução mais barata resolva.
2. **Reconheça** o problema/urgência dele (empatia genuína, não retórica).
3. **Explique o critério** (o objetivo do trimestre) e o **trade-off**: *"Hoje o foco é reduzir multas. Este pedido custa ~3 pessoa-mês e atinge ~300 pessoas. Se entrar, **o que tiramos**?"* (`prioritization`).
4. **Ofereça alternativas**: versão menor, solução paliativa, **"Próximo" com revisão em data certa**, ou **como destravar** (dados que mudariam a decisão).
5. **Registre** a decisão e o **gatilho de revisão**.
**Nunca** diga "sim" para evitar o conflito: um "sim" que vira atraso destrói mais confiança que um "não" honesto. **Negocie escopo, não qualidade** (data fixa → escopo variável — `product-roadmap`).

## 6. Reuniões que valem a pena

- **Toda reunião tem propósito e saída esperada** (decidir? informar? ideação?). Se é só informar, **mande por escrito**.
- **Agenda e pré-leitura** enviadas antes; **quem precisa estar** (e quem pode só receber a ata).
- **Tempo curto** (25/50 min), com **dono da condução** e **anotador**.
- **Termine com decisões e ações** (**quem faz o quê até quando**) registradas e enviadas **no mesmo dia**.
- **Demos** (sprint review) com **o usuário e o resultado** (não o código): mostrar funcionando, medir contra o critério de aceite, **coletar feedback**.
- Evite status "falado" em reunião longa: **assíncrono escrito** libera tempo para o que exige conversa.

## 7. Escalonamento

Escalar **não é denunciar**; é **pedir ajuda para destravar**, quando algo **está fora do seu alcance e ameaça o resultado**.
- **Primeiro** tente resolver **direto** com a pessoa/time (e **avise** que vai escalar, se não resolver).
- **Escale com fatos**: o problema, o impacto (prazo/KR), o que **já** foi tentado, **a decisão/ação** que precisa e **de quem**, e até **quando**.
- **Nunca surpreenda** o interlocutor com um escalonamento que ele não esperava.
- **Foque no problema, não na pessoa.**

## 8. Comunicação durante incidentes e lançamentos

- **Incidente** (`observability`, `release-management`): comunique **rápido e com frequência regular** (mesmo "sem novidade"), em **um canal oficial**: **o que sabemos**, **o que não sabemos**, **impacto**, **o que estamos fazendo**, **próxima atualização em X min**. **Nada de especulação.** Depois: **post-mortem sem culpa** (causas sistêmicas, ações, donos, prazos) compartilhado.
- **Lançamento:** avise **suporte, vendas e CS antes** (FAQ, o que mudou, como reverter, o que pode ser dito), os **clientes impactados** com antecedência (mudanças que quebram: `release-management`), e feche com **resultado medido** (`product-metrics`).
- **Dados pessoais/segurança:** incidente com dado pessoal tem **obrigações legais de comunicação** (ANPD e titulares — `privacy-lgpd`): acione **jurídico/DPO imediatamente**; **não** improvise o comunicado.

## 9. Anti-patterns

- **Surpresas** (más notícias tarde); **status "melancia"** (verde até estourar).
- **Prometer datas** sem base ou **comunicar dado de exploração como compromisso** (`product-roadmap`).
- **Sim para todos**, depois atraso e perda de confiança.
- **Mensagens longas sem conclusão no topo**; jargão para quem não é do time.
- **Decisões sem registro**/sem dono (reabertas sem fim); **decisão por comitê** sem *Approver*.
- **Reuniões sem propósito/saída**; **reuniões de status** que poderiam ser um texto.
- **Inventar ou arredondar números**; citar "pesquisa" sem fonte.
- **Escalonar sem avisar** ou **culpar pessoas** em vez de tratar o problema.
- **Esquecer o jurídico/DPO/segurança** até o fim do projeto.
- **Ignorar suporte/vendas** no lançamento (eles recebem o impacto primeiro).

---

## Regras principais

- **Sem surpresas**: más notícias **cedo**, com **fato → causa → impacto → plano → o que se pede → próximo contato**; **honestidade acima de conforto**; nunca invente/arredonde dados.
- **Mapeie stakeholders** (interesse, influência, formato preferido) e **envolva cedo quem pode vetar** (jurídico/DPO/segurança).
- **Conclusão primeiro (BLUF)**, uma ideia por mensagem, linguagem da audiência, específico (datas/números); **escrito para decisões**.
- Use modelos: **status semanal com RAG honesto** (amarelo cedo), **resumo executivo de 1 página**, **decision log**, **comunicado de má notícia**, **release notes** (benefício ao usuário + deprecações), **one-pager de proposta**.
- **DACI/RACI**: **um** *Approver*; consulte muito, decida claro, **registre**; *disagree and commit*.
- **Diga não com contexto e trade-off** ("e o que sai?"), ofereça alternativas, registre o gatilho de revisão; **data fixa → escopo variável**.
- Reuniões com **propósito, agenda, tempo curto, decisões e ações registradas no mesmo dia**; escale **com fatos, avisando, sobre o problema (não a pessoa)**.
- **Incidentes**: comunicação frequente, em canal oficial, sem especulação, **post-mortem sem culpa**; **lançamento**: avise suporte/vendas/CS **antes**; incidente com **dado pessoal** → jurídico/DPO **imediatamente**.
- **Sem Lombok** — deliberado (skill de produto, sem código).
