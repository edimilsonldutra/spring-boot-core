---
name: product-roadmap
description: Roadmap orientado a resultado e OKRs — Now/Next/Later em vez de datas, temas e outcomes, horizontes de confiança, OKRs mensuráveis, ligação OKR ↔ roadmap ↔ backlog, planejamento trimestral, capacidade, versões por audiência e como responder pedidos de data. Use quando montar ou revisar roadmap e OKRs.
---

Antes de aplicar este pattern, leia também [`../product-strategy/SKILL.md`](../product-strategy/SKILL.md) (a direção), [`../prioritization/SKILL.md`](../prioritization/SKILL.md) (a ordem), [`../product-metrics/SKILL.md`](../product-metrics/SKILL.md) (como medir os Key Results) e [`../stakeholder-communication/SKILL.md`](../stakeholder-communication/SKILL.md) (como comunicar). A capacidade e os prazos vêm do `tech-lead`.

# Roadmap de produto e OKRs

Um **roadmap** comunica **para onde o produto vai e por quê**, não um **contrato de entrega por data**. O erro mais comum é transformá-lo em uma **lista de funcionalidades com datas** (um *release plan*): ele vira promessa, a incerteza some do papel e o time passa a **entregar saídas** em vez de **resolver problemas**.

## 1. Output × Outcome

| | **Output** (saída) | **Outcome** (resultado) |
|---|---|---|
| O que é | O que **entregamos** ("renovação online") | A **mudança** que isso causa ("−30% de multas por atraso") |
| Quem controla | A equipe | O comportamento do usuário (a equipe **influencia**) |
| Risco | Entregar e **não mudar nada** (*feature factory*) | Incerteza sobre **como** chegar lá — e é isso que a descoberta resolve |

Um roadmap **de outcomes** diz *"vamos reduzir o abandono do cadastro"* e **descobre** a solução; um roadmap **de outputs** diz *"entregar o novo formulário em maio"* e torce para funcionar. **Prefira outcomes** (`product-discovery`).

## 2. Now / Next / Later — o formato recomendado

Em vez de colunas de datas, **horizontes de confiança**:
```
┌──────────────────────┬──────────────────────────┬──────────────────────────┐
│ AGORA (em andamento) │ PRÓXIMO (priorizado)     │ DEPOIS (explorando)      │
│ Confiança: alta      │ Confiança: média         │ Confiança: baixa         │
├──────────────────────┼──────────────────────────┼──────────────────────────┤
│ Reduzir multas       │ Aumentar a retenção de   │ Expandir para bibliotecas│
│  por atraso          │  novos sócios            │  parceiras               │
│  • renovação online  │  • onboarding guiado     │  • (hipótese em descoberta)│
│  • aviso de vencimento│ • recomendações          │                          │
│                      │                          │                          │
│ Escopo definido,     │ Problema definido,       │ Apenas direção/hipótese; │
│ em entrega           │ solução a descobrir      │ pode mudar ou sumir      │
└──────────────────────┴──────────────────────────┴──────────────────────────┘
```
- **Agora**: o que está em **desenvolvimento** — escopo claro, alta confiança. Pode ter data **do release atual** (se tiver).
- **Próximo**: **problemas/outcomes priorizados**, solução ainda a **descobrir**; confiança média; **sem data**.
- **Depois**: direções e apostas **exploratórias**; confiança baixa; **pode mudar**.
**Por que funciona:** deixa **explícito** que quanto mais longe, **menos certeza** (a verdade honesta); evita comprometer datas sobre o que ainda não se entende; e permite **mudar de rumo** sem "quebrar promessas". **Cada item é um problema/outcome**, com o **objetivo** a que serve — não um nome de feature.

**Alternativas de formato:** por **temas/objetivos** (colunas = objetivos do trimestre); **linha do tempo** (Gantt) **só** para quem **precisa de data** (ex.: lançamento com marketing/jurídico), **claramente rotulada** com o nível de confiança. **Nunca** um Gantt de 12 meses de features como se fosse certo.

### O que cada item do roadmap contém
```
Tema/Objetivo:   <o que queremos alcançar — o problema/outcome>
Para quem:       <persona/segmento>
Evidência:       <por que acreditamos que importa — link para a descoberta/dados>
Métrica:         <como saberemos que funcionou (Key Result)>
Estágio:         <Descoberta · Definido · Em entrega · Lançado · Medindo>
Confiança:       <Alta · Média · Baixa>
```

## 3. OKRs — Objectives and Key Results

**OKR** conecta **direção** (Objetivo) a **resultado mensurável** (Key Results), em ciclos curtos (normalmente trimestrais).
- **Objective (O)**: **qualitativo, inspirador, ambicioso, com prazo** — *para onde queremos ir*. Responde "o que queremos alcançar?".
- **Key Results (KR)**: **3–5** resultados **quantitativos e mensuráveis** que mostram **se chegamos lá**. Cada um tem **linha de base e meta** (de X para Y) e uma **fonte de medição**. Não são tarefas.

```
O:  Sócios nunca mais são surpreendidos por multas de atraso.
KR1: Reduzir % de empréstimos que terminam com multa de 11% para ≤ 7,5%.
KR2: ≥ 25% dos sócios com prazo a vencer renovam pela web.
KR3: Reduzir os tickets de suporte sobre multa de 180/mês para ≤ 90/mês.
```
(Números **ilustrativos** do formato; os reais vêm de **medição** — `product-metrics`.)

### Erros comuns

| ❌ Erro | ✅ Correção |
|---|---|
| **KR é tarefa/entrega** ("lançar a renovação online") | KR é **resultado** ("−30% de multas"); a entrega é a **iniciativa** que tenta movê-lo |
| Objetivo é **métrica** ("aumentar a receita em 10%") | O é **qualitativo/inspirador**; a métrica é o KR |
| **Sem linha de base** | "De X para Y" — sem X não há como saber se avançou |
| **10 OKRs por time** | **1–3 Objetivos**, **3–5 KRs** cada — foco |
| KRs **fáceis** (100% batido sempre) | OKRs ambiciosos: **~70% de atingimento é sucesso** (se bate sempre 100%, a meta é conservadora) — **mas não use OKR como avaliação de desempenho individual** (mata a ambição) |
| **Metas de vaidade** (downloads, pageviews) | **Resultados de comportamento/valor** (`product-metrics`) |
| **"Definir e esquecer"** | **Check-in semanal/quinzenal**: progresso, confiança, bloqueios; **retrospectiva** no fim do ciclo |
| **OKR sem ligação com o roadmap** | Cada item do Agora/Próximo **aponta para o KR que quer mover** |

### Da estratégia ao trabalho
```
Estratégia / Visão (anos)         → product-strategy
   └─ OKR da empresa/produto (trimestre)   → Objectives + Key Results
        └─ Roadmap (Now/Next/Later)         → problemas/outcomes que movem os KRs
             └─ Iniciativas / PRD            → prd-writing
                  └─ Histórias / tarefas      → user-stories, tech-lead
```
Se um item do backlog **não** liga a nenhum KR/objetivo, **questione** (`prioritization`: sem objetivo, não há como priorizar).

## 4. Planejamento trimestral

1. **Revise o ciclo anterior**: o que aprendemos? KRs atingidos? por quê (não)? (**retrospectiva honesta**, sem culpa).
2. **Reafirme/ajuste a estratégia** e o **contexto** (mercado, clientes, restrições, dívida técnica).
3. **Proponha Objetivos** (PM + liderança); os **times propõem KRs** (*bottom-up* e *top-down* se encontram).
4. **Estime a capacidade** com o `tech-lead` (pessoas disponíveis, férias, **reserva para dívida/incidentes** — `prioritization`).
5. **Escolha as iniciativas** que mais movem os KRs (RICE etc.), **dentro da capacidade**; o que não cabe vai para **"Próximo"/"Depois" explicitamente**.
6. **Identifique dependências** entre times/serviços (`microservices`) e **riscos**; trave cedo o que for inter-times.
7. **Comunique** o plano (versões por audiência — seção 6) e **combine a cadência de check-in**.

## 5. Capacidade, dívida técnica e plataforma no roadmap

O roadmap **não é só features**: inclua **explicitamente** o trabalho de **confiabilidade, segurança, dívida técnica e plataforma** (atualizar o Spring Boot, observabilidade, migração de banco) — **ligado a um outcome** ("reduzir incidentes", "diminuir o lead time") e **justificado** (`technical-product-management`). Esconder esse trabalho garante que ele **estoure como incidente** depois. **Reserve capacidade** (`prioritization`) em vez de "encaixar se sobrar tempo".

## 6. Um roadmap, várias audiências

O **mesmo** conteúdo, com **níveis de detalhe diferentes** (`stakeholder-communication`):
| Audiência | O que precisa | Formato |
|---|---|---|
| **Liderança/executivos** | Direção, objetivos, resultados esperados, riscos | Temas/Objetivos, 1 página, **sem** detalhe de feature |
| **Engenharia/time** | Problemas, contexto, prioridade, o que vem a seguir | Now/Next/Later detalhado, com evidência |
| **Vendas/Suporte/CS** | O que vem e **quando se pode falar** (sem prometer) | "Agora/Próximo" **com avisos de confiança**; **nunca** datas não comprometidas |
| **Clientes/mercado** | O que melhora para eles | **Direção** e temas — **não** compromissos de data (a menos que contratados) |

**Regra:** **só comunique data para o que está "Em entrega" com alta confiança**; para o resto, **horizonte e confiança** ("estamos explorando X; sem data").

## 7. Lidando com pedidos de data

"Quando fica pronto?" é legítimo (marketing, vendas, jurídico). Responda **com honestidade sobre a incerteza**:
- **Para o que está em entrega:** uma **faixa/forecast** baseada em **dados** (vazão histórica, tamanho restante — `agile-delivery`), **não** uma data única: *"85% de chance até 30/abril; 50% até 15/abril."*
- **Para o que ainda é descoberta:** *"Ainda não sei — estamos validando X. Te dou uma estimativa depois do spike, em duas semanas."* **Não** invente uma data para acalmar.
- **Prazo com restrição real** (lei, evento): trate como **data fixa** e **negocie o escopo** (MoSCoW — `prioritization`): **data fixa, escopo variável**.
- **Compromisso de data é decisão de negócio**, registrada, com o **trade-off** (o que sai se atrasar).

## 8. Cadência de revisão

- **Semanal/quinzenal:** check-in dos KRs e do estágio das iniciativas (bloqueios).
- **Mensal:** revise o **Próximo/Depois** com novos aprendizados.
- **Trimestral:** planejamento e retrospectiva de OKRs.
- **Quando o contexto muda** (concorrente, incidente, mudança regulatória): **revise o roadmap** sem cerimônia — **o roadmap é um documento vivo**, e mudar com base em evidência **é o objetivo**, não um fracasso.
Mantenha **um** roadmap oficial, **versionado** e acessível (sem versões paralelas em slides desatualizados).

## 9. Anti-patterns

- **Roadmap = lista de features com datas** (promessas disfarçadas); Gantt de 12 meses.
- **Output em vez de outcome**; itens sem objetivo/evidência/métrica.
- **KRs que são tarefas**; objetivos que são métricas; **OKRs demais**; **sem linha de base**.
- **OKR como avaliação de desempenho individual** (anula a ambição).
- **Roadmap só de features** (sem dívida técnica/plataforma/confiabilidade).
- **Comunicar data para o que ainda é exploração.**
- **Roadmap imutável** (ou que muda sem registro/comunicação).
- **Versões paralelas** para cada audiência, divergentes entre si.
- **Planejar 100% da capacidade** (sem buffer para incidentes e aprendizado).

---

## Regras principais

- **Roadmap comunica direção e porquê, não contrato de entrega**; **outcomes** (resultado) acima de outputs (saídas).
- Formato **Now / Next / Later** com **horizontes de confiança**; datas **só** para o que está em entrega com alta confiança (e como **faixa**, com base em dados).
- Cada item: **problema/objetivo, para quem, evidência, métrica (KR), estágio, confiança**.
- **OKR**: Objective **qualitativo e inspirador**; **3–5 KRs** **mensuráveis com linha de base e meta**; **1–3 objetivos** por time; KR **não é tarefa**; ~70% é bom; **não** é avaliação individual; **check-in** regular.
- **Estratégia → OKR → roadmap → PRD → histórias**: todo item aponta para um objetivo/KR; sem ligação, questione.
- **Planejamento trimestral**: retrospectiva, capacidade **com o tech-lead** (incluindo buffer, dívida e plataforma), iniciativas dentro da capacidade, dependências e riscos mapeados.
- **Inclua dívida técnica, confiabilidade e plataforma** no roadmap, com outcome e justificativa.
- **Mesmo roadmap, detalhe por audiência**; nunca prometer data do que é exploração; **data fixa → escopo variável**.
- **Documento vivo**, versionado, revisado em cadência e **quando o contexto muda**.
- **Sem Lombok** — deliberado (skill de produto, sem código).
