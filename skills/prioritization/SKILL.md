---
name: prioritization
description: Priorização de backlog e iniciativas — RICE com exemplo calculado, ICE, Value × Effort, MoSCoW, Kano, WSJF/Cost of Delay, capacidade para dívida técnica, dependências, como dizer não, vieses e revisão periódica. Use quando ordenar pedidos concorrentes contra um objetivo ou justificar o que fica de fora.
---

Antes de aplicar este pattern, leia também [`../product-discovery/SKILL.md`](../product-discovery/SKILL.md) (a evidência que alimenta a pontuação), [`../product-strategy/SKILL.md`](../product-strategy/SKILL.md) (o critério estratégico), [`../product-roadmap/SKILL.md`](../product-roadmap/SKILL.md) e [`../technical-product-management/SKILL.md`](../technical-product-management/SKILL.md) (dívida técnica e NFRs). A estimativa de esforço vem do `tech-lead`.

# Priorização

**Priorizar é escolher o que NÃO fazer.** Capacidade é finita e a lista de pedidos é infinita; **dizer "sim" a tudo é dizer "não" à qualidade e ao foco**. A boa priorização é **transparente, baseada em evidência e ligada a um objetivo** — não quem grita mais alto.

> **Os frameworks organizam o raciocínio; não o substituem.** Pontuação dá **falsa precisão** quando as entradas são chutes. Use-os para **tornar as suposições explícitas e comparáveis**, **revise os resultados com bom senso** e **nunca apresente uma estimativa como fato** (`product-discovery`: nunca invente dados).

## 1. Antes dos frameworks: o critério vem da estratégia

Sem **objetivo**, não há como priorizar — tudo parece importante. Comece pelo **resultado que importa agora** (o OKR/outcome do trimestre — `product-roadmap`, `product-strategy`) e pergunte, para cada item: **"quanto isto move o resultado que escolhemos?"** Itens que não movem **nenhum** objetivo atual são candidatos a **"não agora"**, por mais que alguém peça.

Considere sempre o **custo de oportunidade**: fazer A significa **não** fazer B. A pergunta certa não é "isto é bom?", é "**isto é a melhor coisa para fazer agora?**".

## 2. Os frameworks

### RICE — Reach, Impact, Confidence, Effort
```
RICE = (Reach × Impact × Confidence) / Effort
```
| Fator | O que é | Escala |
|---|---|---|
| **Reach** | Quantas pessoas/eventos afetados **por período** (ex.: usuários/trimestre) — **um número medido** | contagem |
| **Impact** | Quanto move o objetivo **por pessoa** | 3 = massivo · 2 = alto · 1 = médio · 0,5 = baixo · 0,25 = mínimo |
| **Confidence** | **Quão sólida é a evidência** das estimativas acima | 100% = dados · 80% = alguma evidência · 50% = intuição |
| **Effort** | Esforço **total** (todos os papéis) em **pessoa-mês** — vem do **`tech-lead`** | pessoa-mês |

**Exemplo calculado** (três candidatos):
| Item | Reach/trim | Impact | Confidence | Effort (p-m) | RICE |
|---|---|---|---|---|---|
| A — Renovação online | 2.000 | 2 | 80% | 2 | (2.000 × 2 × 0,8) / 2 = **1.600** |
| B — Aviso por WhatsApp | 500 | 3 | 50% | 1 | (500 × 3 × 0,5) / 1 = **750** |
| C — Novo filtro de busca | 8.000 | 0,5 | 100% | 4 | (8.000 × 0,5 × 1) / 4 = **1.000** |

**Ordem:** A (1.600) → C (1.000) → B (750). Note o efeito da **Confidence**: B tem impacto alto, mas **evidência fraca** (50%), então cai — o framework **empurra você a validar antes** (`product-discovery`) em vez de apostar. **Quando usar:** comparar muitas iniciativas de **produto/feature** quando há **dados de alcance**.

### ICE — Impact, Confidence, Ease
`ICE = Impact × Confidence × Ease` (cada um de 1 a 10). **Mais rápido e mais subjetivo** que RICE (sem alcance). Bom para **triagem de ideias/experimentos** (growth). Cuidado: dois PMs pontuam diferente — **calibre em grupo**.

### Value vs Effort (2×2)
Eixo Y: **valor**; eixo X: **esforço**. Quadrantes: **Quick wins** (alto valor, baixo esforço → faça já), **Projetos grandes** (alto valor, alto esforço → planeje/divida), **Preenchimento** (baixo valor, baixo esforço → só se sobrar capacidade), **Armadilhas** (baixo valor, alto esforço → **não faça**). **Quando usar:** conversa **visual** rápida em workshop; menos preciso.

### MoSCoW — para **escopo** de uma entrega
**Must** (sem isso não lança), **Should** (importante, mas há contorno), **Could** (desejável se sobrar), **Won't (agora)** (acordado explicitamente fora). **Regra:** **Must ≤ ~60% da capacidade**, para ter folga; o "Won't" é **tão importante quanto o Must** (`prd-writing`: não-objetivos). Use para **decidir o escopo de um release/PRD**, não para ranquear o portfólio.

### Kano — o tipo de valor
Classifica features por **como satisfazem**: **Básicas** (esperadas; sem elas há insatisfação, com elas não há encantamento — ex.: o login funciona), **De desempenho** (mais é melhor — velocidade), **Encantadoras** (inesperadas; geram deleite). Ajuda a **balancear** "consertar o básico" × "encantar" e a entender que o que encanta hoje vira básico amanhã. Qualitativo (pesquisa).

### Cost of Delay e WSJF — quando **o tempo** pesa
**Cost of Delay (CoD)** = **quanto custa, por unidade de tempo, adiar** a entrega. **WSJF** (*Weighted Shortest Job First*, do SAFe):
```
WSJF = Cost of Delay / Job Duration         (CoD = valor de negócio + criticidade no tempo + redução de risco/oportunidade)
```
Prioriza itens de **alto custo de atraso e curta duração**. **Quando usar:** há **janela de oportunidade** ou **prazo regulatório** (uma exigência legal com data; um evento sazonal) e itens de **tamanhos muito diferentes**. Os três componentes de CoD costumam ser pontuados **relativamente** (Fibonacci) pela equipe.

### Quando cada um
| Situação | Use |
|---|---|
| Muitas iniciativas de produto, com dados de alcance | **RICE** |
| Muitas ideias/experimentos, pouca informação, rapidez | **ICE** |
| Alinhar o time em um workshop, conversa visual | **Value vs Effort** |
| Fechar o escopo de **um** release/PRD | **MoSCoW** |
| Entender o tipo de satisfação/segmento | **Kano** |
| Prazos, janelas, tamanhos muito diferentes | **WSJF / Cost of Delay** |

**Combine:** um **funil** é comum — ICE para triar ideias → **RICE** para ranquear as candidatas → **MoSCoW** para o escopo do release escolhido.

## 3. Capacidade: nem tudo é "feature nova"

Se 100% da capacidade vai para features, a **dívida técnica e a confiabilidade** acumulam juros até **parar o time**. **Reserve capacidade explícita** por categoria e **negocie-a**:
| Categoria | O que inclui | Observação |
|---|---|---|
| **Entrega de valor** (roadmap) | Features ligadas ao OKR | A maior fatia |
| **Confiabilidade e dívida técnica** | Bugs, desempenho, atualização de plataforma, segurança, observabilidade | Pelo `tech-lead`; **não é "tempo roubado"** — é o que mantém a velocidade (`technical-product-management`) |
| **Aprendizado/experimentos** | Descoberta, spikes, testes (`product-discovery`) | Evita apostas cegas |
| **Imprevistos/suporte/incidentes** | Buffer | **Sempre existe** — planeje-o em vez de fingir que não |

Uma divisão **ilustrativa** (ajuste ao seu contexto, **não é regra**): ~60–70% valor, ~20% dívida/confiabilidade, ~10% aprendizado, ~10% buffer. O importante é **ter a conversa** e **medir** (tempo de ciclo piorando = sinal de dívida demais — `agile-delivery`).

## 4. Dependências, riscos e sequenciamento

- **Dependências** (outro time, outro serviço, fornecedor) **mudam a ordem**: um item "barato" que **destrava** vários vale mais do que a pontuação diz. Mapeie-as cedo com o `tech-lead` (`microservices`: acoplamento entre serviços).
- **Risco primeiro:** itens com **alta incerteza técnica ou de valor** merecem **spike/experimento cedo** — descubra que é inviável **antes** de comprometer o release.
- **Fatias pequenas e valiosas** (`user-stories`) permitem **reordenar** com baixo custo.
- **Obrigações não negociáveis** (lei/LGPD, segurança crítica, contrato) **entram por dever**, fora do ranking de "valor" — mas **com prazo e escopo mínimo** discutidos (`privacy-lgpd`).

## 5. Pressão de stakeholders e como dizer "não"

O difícil da priorização é **social**, não matemático:
- **Seja transparente:** publique o **critério** (o objetivo do trimestre), a **pontuação** e as **suposições**. Decisão **visível e explicável** reduz a disputa por "quem é mais importante".
- **Diga "não" com contexto, não com negativa seca:** *"Entendo a urgência. Hoje o foco é reduzir multas (nosso objetivo). Este pedido atinge ~300 pessoas e custa 3 pessoa-mês; se entrarmos com ele, **o que tiramos**? Posso colocá-lo no *Next* e revisar em março com dados."* — o **trade-off explícito** devolve a decisão ao nível certo.
- **"Sim, e o que sai?"**: capacidade é fixa; entrar algo = **sair algo**.
- **Separe pedido de necessidade:** "queremos um relatório X" costuma esconder uma dor que **outra solução mais barata** resolve (`product-discovery`).
- **Quem decide, decide:** defina o **dono da decisão** (DACI — `stakeholder-communication`); consulte, **não** busque unanimidade. **Registre a decisão** e o motivo.
- **Backlog honesto:** itens que **nunca** serão feitos devem ser **descartados** (e comunicados), não deixados apodrecer em um backlog de 800 itens que dá falsa esperança.

## 6. Vieses que distorcem a priorização

| Viés | Sintoma | Antídoto |
|---|---|---|
| **HiPPO** (opinião da pessoa mais bem paga) | "O diretor quer" vence a evidência | Critério e dados públicos; trade-off explícito |
| **Recência / "pedido mais barulhento"** | Prioriza o último cliente que reclamou | Reach medido; olhe o **conjunto** dos usuários |
| **Viés de projeto novo** | Construir > manter/consertar | Capacidade reservada para dívida e confiabilidade |
| **Sunk cost** | "Já gastamos 3 meses" | Decida pelo **custo futuro**, não pelo passado |
| **Otimismo de esforço** | Estimativas sempre baixas | Peça a estimativa ao `tech-lead`, com **incerteza** (P/M/G ±) |
| **Falsa precisão** | Brigar por 1.600 vs 1.580 | Trate pontuações próximas como **empate**; olhe a ordem de grandeza |
| **Confirmação** | Dar nota alta ao que você já queria | Calibração em grupo; registre as suposições |

## 7. Processo e cadência

1. **Coleta**: ideias de clientes, suporte, vendas, dados, engenharia — **um só funil** (sem pedidos por fora).
2. **Triagem**: alinha a algum objetivo? Duplica algo? **Dados mínimos**? Descarte/adie cedo.
3. **Pontue** (RICE/…): **PM + engenharia** juntos; **Effort do `tech-lead`**; registre as **suposições**.
4. **Calibre e discuta**: o ranking faz sentido? Dependências? Riscos? Ajuste com bom senso (e **registre o motivo** do ajuste).
5. **Decida e comunique**: o que entra, o que **não** entra e **por quê** (`stakeholder-communication`); atualize o roadmap (`product-roadmap`).
6. **Revise** em cadência (a cada ciclo/trimestre ou quando o contexto mudar): **prioridade é perecível**.
7. **Meça o resultado** (`product-metrics`) e **aprenda**: as apostas deram o retorno esperado? Ajuste a calibração da pontuação.

## 8. Anti-patterns

- **Priorizar por volume de pedidos** ou por **quem pede**, sem ligar a um objetivo.
- **Tudo é P0** (se tudo é prioridade, nada é).
- **Pontuação como oráculo** (falsa precisão), com **entradas chutadas** e sem registrar as suposições.
- **100% da capacidade em features** (dívida e confiabilidade ignoradas) — a velocidade cai até parar.
- **Backlog gigante** que ninguém lê, cheio de itens que nunca serão feitos.
- **Priorizar sozinho**, sem engenharia (esforço/risco) e sem as partes afetadas.
- **Decisões não registradas** que reaparecem a cada reunião.
- **Ignorar dependências e risco** (o item "barato" que trava tudo; o item incerto deixado para o fim).
- **Nunca revisar** a priorização depois do contexto mudar.

---

## Regras principais

- **Priorizar é escolher o que não fazer**; parta do **objetivo/outcome atual** e do **custo de oportunidade**.
- **RICE** (com Reach **medido**, **Confidence** honesta e **Effort do tech-lead**) para ranquear iniciativas; **ICE** para triagem; **Value vs Effort** para workshop; **MoSCoW** para o escopo de **um** release (Must ≤ ~60%); **Kano** para tipos de valor; **WSJF/Cost of Delay** quando o **tempo** pesa.
- Pontuação **organiza o raciocínio**, **não o substitui**: trate valores próximos como empate; **registre as suposições**; nunca apresente estimativa como fato.
- **Reserve capacidade explícita** para dívida técnica/confiabilidade, aprendizado e imprevistos — negocie e meça.
- Considere **dependências e risco** (spike/experimento cedo para as incertezas); **obrigações legais/segurança** entram por dever, com escopo mínimo.
- **Seja transparente**: critério e pontuação públicos; **"sim, e o que sai?"**; diga "não" com contexto e trade-off; defina **quem decide** (DACI) e **registre**.
- Combata os **vieses** (HiPPO, recência, sunk cost, otimismo, falsa precisão) com dados, calibração em grupo e trade-offs explícitos.
- **Reveja a priorização** em cadência e **meça o resultado** das apostas; **descarte** o backlog que nunca será feito.
- **Sem Lombok** — deliberado (skill de produto, sem código).
