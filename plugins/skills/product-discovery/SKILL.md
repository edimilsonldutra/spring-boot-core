---
name: product-discovery
description: Descoberta de produto antes de construir — os quatro riscos, enquadramento do problema, Jobs to be Done, entrevistas sem viés (The Mom Test), síntese, árvore de oportunidades, hipóteses testáveis, experimentos baratos e a decisão de seguir, ajustar ou parar. Use antes de escrever um PRD ou quando o pedido chega como solução pronta.
---

Antes de aplicar este pattern, leia também [`../product-strategy/SKILL.md`](../product-strategy/SKILL.md) (a direção que a descoberta serve) e, adiante, [`../prd-writing/SKILL.md`](../prd-writing/SKILL.md) e [`../product-metrics/SKILL.md`](../product-metrics/SKILL.md) (como o que foi descoberto vira requisito e meta). Dados pessoais de pesquisa: `privacy-lgpd`.

# Descoberta de produto

**Construir a coisa certa vem antes de construir a coisa direito.** A maior fonte de desperdício em software não é código ruim: é **código bom para um problema que ninguém tinha**. A descoberta reduz esse risco **antes** de gastar semanas de engenharia.

> **Esta skill não inventa dados.** Pesquisa, números de mercado, citações de usuários e estatísticas **precisam vir de fontes reais** (entrevistas feitas, métricas medidas). Onde faltar evidência, o artefato registra **"hipótese / não validado"**, nunca um número plausível.

## 1. Os quatro riscos de um produto (Marty Cagan)

Toda ideia de funcionalidade carrega quatro riscos; a descoberta existe para reduzi-los **na ordem do mais barato de testar**:

| Risco | Pergunta | Como reduzir |
|---|---|---|
| **Valor** | Os usuários **vão querer/usar**? | Entrevistas, fake door, protótipo, dados de uso |
| **Usabilidade** | Eles **conseguem** usar? | Teste de usabilidade com protótipo clicável |
| **Viabilidade** | **Conseguimos** construir (tempo, tecnologia, dados)? | Conversa cedo com `tech-lead`/`architect`, spike técnico |
| **Negócio** | **Serve** ao negócio (receita, custo, legal, marca, LGPD)? | Business case (`product-strategy`), jurídico/DPO (`privacy-lgpd`) |

Quem **só** valida a viabilidade técnica entrega funcionalidades que ninguém usa. Envolva **engenharia e design desde o início** da descoberta — eles enxergam riscos e alternativas que o PM não vê.

## 2. Enquadre o problema (antes de falar de solução)

Se o pedido chega como solução ("precisamos de um botão de renovar"), **volte ao problema**. Pergunte "por quê?" até a causa:
```
Problema:      <quem> tem dificuldade de <fazer o quê> porque <causa>, o que resulta em <consequência mensurável>
Quem sofre:    <segmento/persona — com contagem aproximada, se houver dado>
Evidência:     <o que você VIU/MEDIU: entrevistas (n=?), tickets, métricas, observação — com a fonte>
Hoje se faz:   <o contorno atual (planilha, ligar para o suporte, desistir)>
Se não fizermos: <o custo de não resolver>
Sucesso seria:  <resultado de comportamento/negócio, não "lançar a feature">
```
Exemplo (biblioteca): *"Sócios com livros emprestados esquecem de renovar e pagam multa (causa: não há aviso nem forma de renovar fora do balcão), gerando 180 tickets/mês de reclamação [fonte: export do suporte, set/2025]."* Note: **dado com fonte**; se você não tem o número, escreva "[a medir]".

**Outcome, não output.** *Output* = o que se entrega ("tela de renovação"). *Outcome* = a mudança de comportamento/resultado ("−50% de multas por atraso"). Descoberta mira **outcomes**.

## 3. Jobs to be Done (JTBD)

Pessoas "contratam" um produto para fazer um **trabalho** em um **contexto**. Foque no **trabalho**, não no perfil demográfico:
```
Quando <situação>, eu quero <motivação/tarefa>, para que <resultado esperado>.
```
*"Quando estou perto do fim do prazo de devolução e não vou à biblioteca, quero estender o empréstimo sem ir ao balcão, para não pagar multa."* O JTBD revela **alternativas** (ligar, pedir a um amigo, ignorar) e os **critérios de decisão** reais (esforço, custo, tempo). Mapeie o job em passos (definir, localizar, preparar, confirmar, executar, monitorar, modificar, concluir) e procure **onde dói**.

## 4. Entrevistas com usuários (e como não ser enganado)

Entrevista ruim **confirma** o que você já acha. Regras do *The Mom Test* (Rob Fitzpatrick):
1. **Fale do passado e do concreto**, não do hipotético. ❌ "Você usaria um app de renovação?" (todos dizem "sim", é educação). ✅ "Conte a **última vez** que você atrasou uma devolução. O que aconteceu?"
2. **Não pitche a ideia.** Ouça. Quanto mais você fala da solução, mais viciada fica a resposta.
3. **Procure compromisso, não elogio.** "Legal!" não vale nada. Vale: tempo, dinheiro, reputação ("posso te mostrar o protótipo na terça?", "pode me apresentar ao seu gerente?"), ou uma **solução alternativa que ele já tenta** (prova de dor real).
4. **Cave a causa:** "e o que você fez depois?", "por quê?", "quanto custou isso?", "o que mais você tentou?".
5. **Observe o comportamento** mais do que a opinião (o que as pessoas **fazem** ≠ o que dizem que fariam).
6. **Anote fatos e citações literais**, separados de **suas interpretações**.

**Roteiro mínimo (30–45 min):** contexto da pessoa → a última vez que tentou resolver o problema → o que fez, o que usou, o que doeu → o que já tentou/pagou → quem mais está envolvido → fechamento ("quem mais devo ouvir?"). **Quantas entrevistas?** Como ponto de partida, **5–8 por segmento** até os padrões se repetirem (saturação) — não é regra estatística; é "pare quando parar de aprender". Entreviste **não-usuários e ex-usuários** também (viés de sobrevivência). **Cadência:** descoberta **contínua** (uma conversa por semana), não um projeto único.

**Privacidade:** peça **consentimento** para gravar, **anonimize** as notas, não guarde dados pessoais além do necessário e **apague** conforme prometido (`privacy-lgpd`). Pesquisa com dados reais de clientes segue as mesmas regras de qualquer tratamento.

## 5. Sintetize: de notas a oportunidades

1. **Extraia observações** (fatos, citações) por entrevista, **sem julgamento**.
2. **Agrupe por tema** (affinity mapping): as dores/necessidades/contextos que **se repetem**. Um relato isolado é anedota; padrão em vários é **sinal**.
3. **Formule oportunidades** como **necessidades/dores do usuário** ("não sei quando vence o prazo"), **não** como soluções ("notificação por e-mail").
4. **Árvore de oportunidades** (Teresa Torres — *Continuous Discovery Habits*): no topo o **outcome** desejado; abaixo as **oportunidades** (dores); abaixo, as **soluções candidatas**; e por fim os **experimentos** para testar cada uma.
```
Outcome: reduzir multas por atraso em 50%
├── Oportunidade: "não sei quando vence"         ├── Solução: lembrete por e-mail  ──► teste: smoke test
│                                                 └── Solução: lembrete por WhatsApp ──► teste: protótipo
├── Oportunidade: "não consigo renovar sem ir lá" └── Solução: renovação online      ──► teste: fake door
└── Oportunidade: "a multa é surpresa"            └── Solução: aviso de multa prevista
```
Compare **mais de uma solução** por oportunidade (a primeira ideia raramente é a melhor) e **mais de uma oportunidade** (escolha a de maior impacto no outcome — `prioritization`).

## 6. Suposições e hipóteses

Toda solução repousa em **suposições** (sobre valor, usabilidade, viabilidade, negócio). **Liste e ranqueie** pelo cruzamento **"quanto importa se estiver errada" × "quão pouco sabemos"**; teste primeiro as **críticas e desconhecidas** (*leap-of-faith assumptions*).
```
Suposição:  Sócios renovariam online se pudessem.
Hipótese:   Acreditamos que oferecer renovação online para sócios com empréstimo ativo
            vai reduzir as multas por atraso em ≥ 30%.
Saberemos que estamos certos quando: ≥ 25% dos sócios com prazo a vencer renovarem online em 4 semanas,
            e a taxa de multa cair ≥ 30% frente ao grupo de controle.
Se errados: <o que faremos — mudar, parar>.
```
Uma boa hipótese é **específica, mensurável, com prazo e com critério de falha definido de antemão** (evita racionalizar depois).

## 7. Experimentos baratos (do menor custo ao maior)

| Técnica | O que testa | Custo | Exemplo |
|---|---|---|---|
| **Entrevista / observação** | Existe a dor? Qual a alternativa? | Muito baixo | 6 sócios que atrasaram |
| **Fake door / smoke test** | Há **interesse real**? | Baixo | Botão "Renovar online" que registra o clique e mostra "em breve" — mede **intenção** (eticamente: avise que está em desenvolvimento) |
| **Landing page / pré-cadastro** | Demanda e proposta de valor | Baixo | Página com a promessa + lista de espera |
| **Protótipo clicável** | **Usabilidade** e entendimento | Baixo–médio | Figma testado com 5 pessoas |
| **Concierge** | O **valor** de verdade, sem automação | Médio (manual) | A equipe renova **à mão** por WhatsApp para 20 sócios |
| **Wizard of Oz** | Experiência "automática" com humanos por trás | Médio | Aparenta ser um sistema, mas é manual |
| **MVP funcional / feature flag** | Valor em uso real, para poucos | Alto | Renovação real para 5% dos sócios (`release-management`) |
| **A/B test** | Efeito **causal** de uma mudança | Alto (precisa de volume) | `product-metrics` |

**Princípio:** use o **experimento mais barato que reduz a incerteza que importa**. Não construa o MVP funcional para descobrir se alguém **quer** — isso se descobre com um fake door. Defina **antes** o **critério de sucesso** e o **tamanho da amostra/tempo**; **não mude a meta depois de ver o resultado**.

## 8. Decida: seguir, ajustar ou parar

Ao fim de cada ciclo, **uma decisão registrada** (`stakeholder-communication`: decision log):
- **Seguir** — evidência suficiente nos quatro riscos → escreva o PRD (`prd-writing`) e priorize (`prioritization`).
- **Ajustar** — a dor existe, mas a solução não funcionou → nova solução na mesma oportunidade.
- **Parar** — não há dor/valor/viabilidade suficientes → **economizou meses**. **Parar bem é um resultado de sucesso da descoberta.**
Evite o **viés de confirmação** (procurar só quem concorda), o **viés do "sunk cost"** ("já investimos") e a **pressão de stakeholder** ("o diretor quer"): leve **a evidência**, não a opinião.

## 9. Dupla trilha: descoberta e entrega andam juntas

Em times maduros, **descoberta e entrega acontecem em paralelo**: enquanto a engenharia entrega o que **já foi validado**, o PM + design + um engenheiro **descobrem o próximo**. O backlog de entrega só recebe itens **com hipótese validada** e **requisitos claros** (`user-stories`, `agile-delivery`). Isso evita "fábrica de funcionalidades" (*feature factory*): entregar sem aprender.

## 10. Anti-patterns

- **Solução primeiro**: aceitar "faça X" sem entender o problema.
- **Perguntar "você usaria?"** e tratar o "sim" como validação.
- **Falar só com quem já é cliente** (e só com os mais engajados).
- **Descoberta como projeto único** de 3 meses, depois nunca mais.
- **Hipótese vaga** ("melhorar a experiência") **sem critério de falha**; **mudar a meta após ver o resultado**.
- **Validar só a viabilidade** (ou só o valor) — esquecer usabilidade e negócio.
- **Inventar ou "arredondar" números** para convencer; citar "pesquisas" sem fonte.
- **Ignorar dados que já existem** (tickets de suporte, analytics, logs — `observability`, `product-metrics`).
- **Gravar usuários sem consentimento** / guardar dados pessoais de pesquisa indefinidamente (`privacy-lgpd`).

---

## Regras principais

- **Problema antes de solução**, **outcome antes de output**; o artefato de partida é o **enquadramento do problema com evidência e fonte**.
- Reduza os **quatro riscos** (valor, usabilidade, viabilidade, negócio), do **mais barato** de testar ao mais caro; **engenharia e design desde o início**.
- **JTBD** para entender o trabalho e as alternativas; entrevistas sobre o **passado concreto**, sem pitch; busque **compromisso**, não elogio; observe comportamento; **5–8 por segmento** até saturar; descoberta **contínua**.
- Sintetize em **padrões** → **oportunidades (dores, não soluções)** → **árvore de oportunidades** com **várias soluções** comparadas.
- **Hipóteses específicas, mensuráveis, com prazo e critério de falha definidos antes**; teste primeiro as suposições críticas e desconhecidas.
- Use o **experimento mais barato** que responde à dúvida (entrevista → fake door → protótipo → concierge → MVP com flag → A/B); **não mude a meta depois do resultado**.
- Decisão registrada: **seguir, ajustar ou parar** (parar é sucesso); leve **evidência**, não opinião de cargo.
- **Nunca invente dado**: sem fonte, escreva "hipótese/a medir". Pesquisa com pessoas exige **consentimento, anonimização e retenção limitada**.
- **Sem Lombok** — deliberado (e sem código aqui: esta é uma skill de produto).
