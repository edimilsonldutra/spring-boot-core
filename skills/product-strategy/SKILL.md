---
name: product-strategy
description: Estratégia de produto — visão, kernel da estratégia (diagnóstico, política, ações), posicionamento e proposta de valor, análise competitiva, TAM/SAM/SOM sem inventar números, unit economics, business case e build/buy/partner. Use quando definir a direção do produto ou justificar um investimento.
---

Antes de aplicar este pattern, leia também [`../product-discovery/SKILL.md`](../product-discovery/SKILL.md), [`../prioritization/SKILL.md`](../prioritization/SKILL.md), [`../product-roadmap/SKILL.md`](../product-roadmap/SKILL.md), [`../product-metrics/SKILL.md`](../product-metrics/SKILL.md) e [`../technical-product-management/SKILL.md`](../technical-product-management/SKILL.md) (build vs buy, custo de nuvem).

# Estratégia de produto

**Estratégia é escolher onde jogar e como ganhar — e, principalmente, o que NÃO fazer.** Sem estratégia, o produto vira uma **soma de pedidos** (de clientes, vendas, diretoria) sem direção: cresce em largura, perde em profundidade e ninguém sabe dizer **por que** está construindo o que constrói. A estratégia é o **critério** que torna a priorização possível (`prioritization`).

> **Nunca invente dados.** Tamanho de mercado, participação de concorrentes, preços, custos e taxas **vêm de fontes reais** (relatórios, dados internos, pesquisas) — **com a fonte citada**. Onde só há **suposição**, o artefato diz **"hipótese"** e mostra o raciocínio. Um business case com números fabricados dá **falsa segurança**.

## 1. Visão, missão e estratégia — três coisas diferentes

| Conceito | Pergunta | Horizonte | Exemplo (biblioteca) |
|---|---|---|---|
| **Visão** | **Onde queremos chegar?** O futuro que o produto cria | Longo (3–10 anos) | "Que ninguém deixe de ler por burocracia" |
| **Missão** | **Por que existimos / o que fazemos** e para quem | Duradoura | "Tornar o acesso a livros simples para toda a comunidade" |
| **Estratégia** | **Como vamos chegar lá** com **recursos limitados**, **escolhas e abdicações** | Médio (1–3 anos, revista) | "Ganhar o sócio recorrente pela **conveniência digital** antes de expandir o acervo" |

Visão e missão **inspiram**; a **estratégia decide**. Uma "estratégia" que é só um desejo ("ser líder de mercado") **não é estratégia**.

## 2. O kernel da estratégia (Richard Rumelt)

Uma boa estratégia tem **três partes** coerentes:
1. **Diagnóstico**: **qual é o desafio central?** (a **natureza do problema**, simplificando a complexidade) — **não** uma lista de metas.
2. **Política orientadora (*guiding policy*)**: a **abordagem geral** para enfrentar o desafio — **o que escolhemos e o que descartamos**.
3. **Ações coerentes**: **passos concretos e coordenados** que implementam a política.
```
Diagnóstico:   Sócios abandonam a biblioteca por fricção (precisam ir ao balcão), não por falta de acervo.
               [evidência: churn por motivo, entrevistas — com fonte]
Política:      Competir por CONVENIÊNCIA DIGITAL, não por tamanho de acervo. Resolver o ciclo
               "pegar → acompanhar → renovar → devolver" sem ir ao balcão.
Ações:         1) renovação e avisos online; 2) reserva e retirada com autoatendimento;
               3) integração de identidade única; 4) NÃO fazer: ampliar o acervo físico neste ano.
```
**Sinais de má estratégia** (*bad strategy*): **fluff** (jargão sem conteúdo), **não enfrentar o desafio** (só listar objetivos), **objetivos errados confundidos com estratégia** ("crescer 20%" é meta, não estratégia), **lista de desejos** sem escolhas. **Teste:** *se a "estratégia" não obriga a **dizer não** a nada, não é estratégia.*

## 3. Princípios de produto (as "regras de decisão")

Poucas frases (3–6) que **resolvem disputas** sem reunião — o time as usa para decidir sozinho:
> "**Simples antes de completo.** Escolhemos o fluxo que o sócio entende sem ajuda." · "**O dado do usuário é dele.** Coletamos o mínimo (`privacy-lgpd`)." · "**Confiabilidade é funcionalidade.** Não lançamos o que degrada o SLO (`technical-product-management`)." · "**Resolva a dor do 80% antes do caso raro.**"
Bons princípios têm **trade-off real** (alguém poderia razoavelmente escolher o oposto) — "ter qualidade" não é princípio, todo mundo concorda.

## 4. Cliente, problema e proposta de valor

- **Segmento-alvo**: **para quem exatamente** (e para quem **não**)? "Todo mundo" é **ninguém**. Comece por um segmento onde a **dor é intensa** (`product-discovery`).
- **Job to be done** e **alternativas atuais** (inclusive "não fazer nada"/planilha/concorrente).
- **Proposta de valor**: o **benefício principal** que o produto entrega **melhor** que as alternativas, na linguagem do cliente. Teste: *um cliente reconhece o próprio problema nela?*
```
Para <segmento> que <precisa/dor>, <produto> é <categoria> que <benefício principal>.
Diferente de <alternativa>, nosso produto <diferencial real e verificável>.
```
- **Diferencial defensável**: o que **concorrentes não copiam fácil** (dados, rede/efeito de escala, integração profunda, marca/confiança, custo estrutural, regulação). **Velocidade de execução** sozinha raramente é diferencial duradouro.

## 5. Posicionamento (April Dunford — os componentes)

Posicionar é **definir o contexto** em que o cliente entende e valoriza o produto:
1. **Alternativas competitivas** — o que o cliente faria **sem** você.
2. **Atributos únicos** — o que você tem que elas **não** têm.
3. **Valor** que esses atributos geram **para o cliente**.
4. **Clientes que mais se importam** com esse valor (o **segmento-alvo**).
5. **Categoria de mercado** em que você se encaixa (ela **define as expectativas** do cliente).
Ordem importa: comece pelas **alternativas** e **atributos**, não pelo slogan. Posicionamento ruim faz um bom produto parecer **fraco ou confuso**.

## 6. Análise competitiva e de mercado

### Concorrentes (diretos, indiretos e "não consumo")
Mapeie **quem resolve o mesmo problema** (inclusive de forma diferente) e **o que o cliente usa hoje**:
| Critério | Nós | Concorrente A | Concorrente B | Alternativa "manual" |
|---|---|---|---|---|
| Facilidade de renovar | <fato> | <fato> | <fato> | Ir ao balcão |
| Preço | <fato com fonte> | | | |
| Pontos fortes / fracos | | | | |

**Fatos, não opiniões**: cada célula vem de **fonte verificável** (site, teste do produto, entrevista, relatório). Destaque **onde há diferença que o cliente valoriza** — e onde **estamos atrás**. Análise de concorrência serve para **entender o terreno**, não para **copiar** (copiar o concorrente garante, no máximo, ser o segundo).

### Tamanho de mercado — TAM, SAM, SOM (com honestidade)
- **TAM** (*Total Addressable Market*): a demanda **total** do produto/categoria. **SAM** (*Serviceable Available*): a parcela que seu **modelo/geografia/segmento** consegue atender. **SOM** (*Serviceable Obtainable*): o que você **realisticamente captura** no horizonte.
- **Prefira bottom-up** (nº de clientes-alvo × receita por cliente, com **premissas explícitas e fonte**) a **top-down** ("o mercado é de R$ 10 bi, se pegarmos 1%…" — **a falácia clássica**, sem base nenhuma). **Mostre as premissas** e a **sensibilidade** (o que muda se errarmos).
- **Não invente números.** Sem dado confiável, apresente **faixas** e **marque como hipótese**; o exercício vale pelo **raciocínio**, não pela cifra.

## 7. Modelo de negócio e noções de precificação

- **Como o produto gera valor para o negócio?** Receita (assinatura, uso, transação, licença), **redução de custo**, retenção, estratégia de plataforma.
- **Unit economics** — a economia **por cliente**:
  - **CAC** (custo de aquisição de cliente) = custo de marketing+vendas ÷ clientes novos.
  - **LTV** (valor do tempo de vida) ≈ margem por cliente × tempo médio de vida (ou receita média ÷ taxa de churn, ajustada pela **margem**).
  - **LTV/CAC** e **payback do CAC** (meses para recuperar o CAC) mostram se **escalar dá lucro ou prejuízo** — **calcule com dados reais** (`product-metrics`: coortes, retenção); **não** com otimismo.
- **Margem e custo de servir**: inclua o **custo de nuvem por usuário/transação** (`technical-product-management`, FinOps) — um produto com receita crescente e **margem negativa** não escala.
- **Precificação** (noções): **baseada em valor** (o que o cliente **ganha**) em vez de só **custo + margem**; **comparação com alternativas/concorrentes**; **estrutura** (planos/tiers que **segmentam** disposição a pagar, limites de uso); **testar** (entrevistas de disposição a pagar, experimentos — `product-discovery`, `product-metrics`); **cuidado** com mudanças de preço (comunicação, clientes existentes — `release-management`). **Gratuito** tem custo real (suporte, infraestrutura).

## 8. Business case — justificando um investimento

Para uma iniciativa que exige **recursos relevantes**, estruture a decisão (`stakeholder-communication`: one-pager):
```markdown
# Business case: <iniciativa>
**Problema e oportunidade** (com evidência/fonte): ______
**Proposta** (o quê, não o como): ______
**Benefícios esperados** (mensuráveis, com base e premissa):
  - Receita/retenção: ______  - Redução de custo: ______  - Risco evitado: ______  - Estratégico: ______
**Custos**: desenvolvimento (estimativa do tech lead, com incerteza) + **operação recorrente** (nuvem, suporte, licenças) + custo de oportunidade
**Retorno**: payback ≈ ___ meses; cenários **conservador / base / otimista** (e as premissas de cada um)
**Riscos principais** (valor, viabilidade, negócio, legal/LGPD) e mitigações: ______
**Alternativas consideradas** (incluindo **não fazer** e **comprar**): ______
**Como mediremos o sucesso** (métrica, meta, prazo) e **critério de parada**: ______
**Decisão necessária e prazo**: ______
```
**Apresente cenários e premissas, não uma única cifra "certa"**; **quem calcula o custo** de engenharia é o **`tech-lead`**; **riscos legais** passam por **jurídico/DPO** (`privacy-lgpd`). Business case é **ferramenta para pensar**, não para **justificar uma decisão já tomada** (viés de confirmação). Defina um **critério de parada** ("se após 8 semanas a métrica X não passar de Y, **paramos**") — *sunk cost* é inimigo.

## 9. Build, buy ou partner — e escolhas estratégicas

(`technical-product-management`, seção 5.) **Construa o que diferencia, compre/faça parceria no que é commodity.** Considere também **parcerias** (distribuição, integração) e **plataformas** (construir sobre o ecossistema de alguém: **risco de dependência**). Registre decisões estratégicas relevantes (`stakeholder-communication`: decision log; `architect`: ADR para as técnicas).

## 10. Da estratégia ao dia a dia

```
Visão / Missão                       → direção duradoura
Estratégia (diagnóstico → política → ações)  → escolhas e abdicações        ← esta skill
   └─ OKRs do ciclo                          → product-roadmap
        └─ Roadmap (Now/Next/Later)           → problemas/outcomes
             └─ Descoberta → PRD → histórias   → product-discovery, prd-writing, user-stories
                  └─ Priorização (RICE…)        → prioritization (o critério é a estratégia)
                       └─ Entrega e lançamento   → agile-delivery, release-management
                            └─ Medição e aprendizado → product-metrics → revisa a estratégia
```
- **A estratégia dá o critério**: ao priorizar, pergunte "**isto avança a política orientadora?**". Pedidos que **não** avançam → **"não agora"** com a justificativa (`stakeholder-communication`).
- **Revise a estratégia** em cadência (anual, com checagens trimestrais) e **quando o contexto muda** (concorrente novo, mudança regulatória, dados que contradizem o diagnóstico) — **estratégia é hipótese sobre o mundo**; os **dados** (`product-metrics`) a confirmam ou a refutam. **Mudar de estratégia com evidência é força, não fraqueza.**
- **Comunique a estratégia** de forma que **qualquer pessoa do time a explique** em 1 minuto; se ninguém a repete, ela **não existe** na prática.

## 11. Anti-patterns

- **"Estratégia" que é lista de metas/desejos**, sem diagnóstico nem escolhas (**não obriga a dizer não**).
- **Estratégia = roadmap de funcionalidades** (ou soma dos pedidos de vendas).
- **"Para todo mundo"** (sem segmento-alvo); **proposta de valor genérica** ("melhor experiência").
- **Copiar o concorrente** como estratégia; **ignorar a alternativa "não fazer nada"**.
- **TAM top-down** ("1% de um mercado gigante"); **números sem fonte**; **business case de cifra única** justificando decisão tomada.
- **Ignorar unit economics e custo de servir**; crescer com margem negativa.
- **Visão/missão decorativas** sem efeito nas decisões; **princípios sem trade-off**.
- **Estratégia imutável** (ignora dados) ou **que muda a cada trimestre** (é só reação).
- **Estratégia secreta** (o time não sabe) ou **só na cabeça do PM**.
- **Decidir estratégia sem ouvir clientes** e **sem engenharia** (viabilidade/custo).

---

## Regras principais

- **Estratégia é escolher onde jogar e como ganhar — e o que não fazer**; é o **critério da priorização**. Se não obriga a dizer não, não é estratégia.
- **Visão** (onde chegar) ≠ **missão** (por que existimos) ≠ **estratégia** (como, com escolhas e abdicações).
- **Kernel de Rumelt**: **diagnóstico** (o desafio central, com evidência) → **política orientadora** (abordagem e o que se descarta) → **ações coerentes**; evite *fluff*, lista de metas e desejos.
- **Princípios de produto** (3–6, com trade-off real) resolvem disputas sem reunião.
- **Segmento-alvo específico**, **JTBD e alternativas** (inclusive "não fazer nada"), **proposta de valor** reconhecível pelo cliente, **diferencial defensável**; **posicionamento** parte das **alternativas e atributos** (Dunford).
- **Análise competitiva com fatos e fontes**; **TAM/SAM/SOM bottom-up com premissas explícitas**; **nunca invente números** — sem dado, **faixas e "hipótese"**.
- **Unit economics** (CAC, LTV, LTV/CAC, payback, **margem com custo de servir/nuvem**) com dados reais; **precificação por valor**, testada; grátis tem custo.
- **Business case** com benefícios mensuráveis, custos (do tech lead, **incluindo operação**), **cenários**, riscos, alternativas (inclusive **não fazer/comprar**), **métrica de sucesso e critério de parada**.
- **Construa o diferencial, compre a commodity**; parcerias com consciência da dependência.
- **Estratégia → OKR → roadmap → descoberta/PRD → priorização → entrega/lançamento → medição**, e a medição **revisa a estratégia**; revise em cadência e quando o contexto mudar; **comunique** de modo que qualquer pessoa a explique em 1 minuto.
- **Sem Lombok** — deliberado (skill de produto, sem código).
