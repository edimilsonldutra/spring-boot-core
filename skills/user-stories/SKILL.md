---
name: user-stories
description: Histórias de usuário e fatias verticais — formato, INVEST, critérios Given/When/Then, story mapping, padrões de fatiamento, histórias habilitadoras, DoR e DoD, three amigos e como as histórias viram tarefas do tech lead e casos de teste do QA. Use quando quebrar um épico ou escrever critérios de aceite. Não use para o PRD completo (prd-writing).
---

Antes de aplicar este pattern, leia também [`../prd-writing/SKILL.md`](../prd-writing/SKILL.md) (de onde vêm os requisitos), [`../agile-delivery/SKILL.md`](../agile-delivery/SKILL.md) (refinamento e cadência) e [`../prioritization/SKILL.md`](../prioritization/SKILL.md). Para a testabilidade dos critérios: `testing`.

# Histórias de usuário

Uma **história de usuário** é uma **unidade pequena de valor entregável**, descrita pela perspectiva de quem a usa, que serve de **ponto de partida para uma conversa** (não de especificação completa). O texto da história é **lembrete**; o valor está na **conversa** entre PM, engenharia, design e QA e nos **critérios de aceite** que fecham o entendimento.

## Formato

```
Como <papel/persona>,
quero <capacidade/ação>,
para que <benefício/resultado>.
```
> *Como sócio da biblioteca, quero renovar um empréstimo pela web, para não pagar multa por esquecer de devolver.*

- O **"para que"** é a parte mais importante: ele dá o **porquê**, permite à engenharia propor **alternativas mais simples** que entregam o mesmo benefício, e permite **cortar** a história se o benefício não compensar.
- **"Como um usuário"** genérico é sinal de que você não sabe **quem** é. Seja específico (sócio, bibliotecário, administrador).
- **Não descreva a solução técnica** ("como sistema, quero uma tabela `renewal`…"): a história descreve **comportamento observável**.

## INVEST — o teste de uma boa história

| Letra | Critério | Pergunta | Se falhar |
|---|---|---|---|
| **I** | **Independent** (independente) | Dá para entregar sem depender de outra em andamento? | Reordene/reagrupe ou divida de outro jeito |
| **N** | **Negotiable** (negociável) | O "como" ainda está em aberto para conversar? | Você escreveu uma especificação, não uma história |
| **V** | **Valuable** (valiosa) | Entrega valor a um usuário/ao negócio? | É tarefa técnica disfarçada — ver "habilitadoras" |
| **E** | **Estimable** (estimável) | A equipe entende o bastante para planejar? | Faça um **spike** (investigação com timebox) |
| **S** | **Small** (pequena) | Cabe em alguns dias, dentro de uma iteração? | **Divida** (padrões abaixo) |
| **T** | **Testable** (testável) | Há critério objetivo para dizer "pronto"? | Escreva os critérios de aceite |

**Tamanho:** uma história que não cabe em **poucos dias** de um desenvolvedor (e em uma sprint, no máximo) é **grande demais** — divida. Histórias grandes escondem risco, atrasam o feedback e viram "90% pronto" por semanas.

## Critérios de aceite

Os **critérios de aceite** definem **quando a história está pronta** e são a ponte para o teste. Dois formatos:

**Given/When/Then** (comportamento — o preferido):
```
Cenário: renovação dentro das regras
  Dado um empréstimo ativo com vencimento em 3 dias e sem renovações
  Quando o sócio solicita a renovação
  Então o novo vencimento é 14 dias após o atual
  E o sócio vê a confirmação com a nova data

Cenário: renovação negada por reserva de outro sócio
  Dado um empréstimo ativo cujo livro tem reserva de outro sócio
  Quando o sócio solicita a renovação
  Então a renovação é recusada com o motivo "livro reservado"
  E o vencimento não muda

Cenário: limite de renovações
  Dado um empréstimo já renovado 2 vezes
  Quando o sócio solicita uma nova renovação
  Então a renovação é recusada informando o limite de 2
```
**Checklist** (regras simples): *"- Só o titular renova. - Mostra o novo vencimento. - Falha com mensagem clara se o sistema estiver indisponível."*

Boas práticas: **3–7 critérios**; cubra **caminho feliz, regras de negócio, erros e limites**; escreva **antes** do desenvolvimento (no refinamento); **sem detalhes de implementação**; **inclua os não-funcionais relevantes** da história ("responde em < 500 ms", "só o titular acessa" — `prd-writing`). **O `qa` deriva os casos de teste daqui** (`testing`); o `developer` usa como **definição de pronto** da história.

## Story mapping — enxergar o todo antes de fatiar

Uma lista plana de histórias perde a visão da **jornada**. O **story map** (Jeff Patton) organiza em duas dimensões:
```
JORNADA (esq → dir):  Descobrir livro → Pegar emprestado → Usar/Acompanhar → Devolver/Renovar
                         │                 │                   │                  │
Prioridade ↓ (topo = essencial)  buscar     retirar no          ver prazo          devolver no balcão
(Release 1: o mínimo   por título          balcão               atual              renovar online  ◄── (esta iniciativa)
 que faz a jornada                                               
 funcionar)             filtros avançados   reservar online     receber aviso      renovar 2x
(Release 2...)                                                   de vencimento
```
- **Eixo horizontal:** os **passos da jornada** do usuário (a "espinha"). **Eixo vertical:** as histórias de cada passo, **da mais essencial (topo) para a opcional (base)**.
- **Fatie "horizontalmente" por release**: o **primeiro release** é uma **linha** que cobre a jornada **de ponta a ponta com o mínimo** (um *walking skeleton*) — e **não** "todas as telas do passo 1". Entrega valor completo e permite aprender cedo.
- O mapa evidencia **lacunas** (passos sem história) e **dependências**, e ajuda a **negociar escopo** ("o que o mínimo que faz sentido precisa ter?").

## Padrões para dividir histórias grandes

**Divida por valor, em fatias verticais** (atravessam **todas as camadas**: tela/API/regra/dados), **nunca por camada técnica** ("fazer o banco", "fazer a tela"): uma fatia vertical é **entregável e demonstrável**; uma fatia horizontal **não entrega valor** até as outras chegarem.

| Padrão | Como dividir | Exemplo |
|---|---|---|
| **Passos do fluxo** | Um passo (ou o fluxo mais simples) por vez, de ponta a ponta | "Renovar" → primeiro o caso sem reserva; depois a verificação de reserva |
| **Regras de negócio** | Uma regra/variação por história | Limite de 2 renovações; bloqueio por reserva; sócio com multa |
| **Variações de dados** | Um tipo de dado/perfil por vez | Renovar livro físico; depois e-book |
| **Caminho feliz × infeliz** | Primeiro o feliz; depois erros e exceções | Renovação ok; depois falhas e mensagens |
| **CRUD** | Criar, ler, atualizar, apagar separados (se o valor for diferente) | Criar reserva; cancelar reserva |
| **Interface/plataforma** | O mais simples primeiro | Web antes de mobile |
| **Esforço agora × depois** | Aceite uma versão "boa o bastante" e melhore depois | Aviso por e-mail antes de WhatsApp |
| **Spike** | **Investigação com timebox** para reduzir incerteza técnica | "Descobrir como consultar reservas do `catalog` (2 dias)" |
| **Desempenho/NFR** | Funcionar primeiro, depois cumprir a meta de escala | Suportar 50 → 2.000 req/h |

**Teste da divisão:** cada pedaço **entrega valor**, é **demonstrável** e **pequeno**; juntos somam a história original.

## Histórias habilitadoras e técnicas

Nem todo trabalho é "valor visível ao usuário": migração de banco, observabilidade, atualizar o Boot, pagar dívida técnica. Não esconda-os nem os force no formato "Como usuário…". Trate-os como **itens do backlog explícitos**, com **justificativa de valor** (risco evitado, velocidade futura, custo reduzido) e **priorizados** junto com os demais (`prioritization`, `technical-product-management`):
> *Habilitadora:* "Para garantir que a renovação nunca seja cobrada/feita duas vezes por retry, **tornar o endpoint idempotente**" (`idempotency`) — o **valor** é correção; o **critério de aceite** é testável (mesma chave 2× → um efeito).
Requisitos **não funcionais** que valem para **todas** as histórias (segurança, desempenho, acessibilidade, LGPD) entram na **Definition of Done**, não repetidos em cada história.

## Definition of Ready e Definition of Done

**Definition of Ready (DoR)** — a história **só entra na iteração se**: tem **valor claro** ("para que"); **critérios de aceite** escritos; **dependências** conhecidas e destravadas; **design/protótipo** disponível (se aplicável); **dúvidas de negócio** respondidas; **cabe numa iteração** (pequena); a equipe **entende** o bastante para estimar. *(Não vire burocracia: a DoR serve para **evitar surpresa**, não para barrar o trabalho.)*

**Definition of Done (DoD)** — a história **só está pronta se** (acordo da **equipe**, mesma do `tech-lead`):
- [ ] Critérios de aceite **atendidos e demonstrados**.
- [ ] **Testes** automatizados passando (unit/integração/contrato — `testing`, `contract-testing`), com casos de borda e **cobertura do código novo ≥ 90%** (gate do CI — `test-coverage`).
- [ ] **Revisão de código** aprovada (`code-reviewer`).
- [ ] **Segurança e privacidade** verificadas (autorização, dados pessoais — `privacy-lgpd`).
- [ ] **Observabilidade** (logs úteis, métricas, alertas — `observability`).
- [ ] **Documentação** atualizada (Swagger, runbook).
- [ ] **Implantada** (ambiente de homologação/produção atrás de *feature flag*, se for o caso — `release-management`).
- [ ] **PM/Design aceitaram** a demonstração.
"Pronto" = **pronto para o usuário**, não "o código está no repositório".

## O "Three Amigos" (refinamento)

Antes da iteração, **PM + engenharia + QA** (+ design) conversam **cada história** por 15–30 min:
- **PM**: o problema, o valor, as regras; **engenharia**: viabilidade, riscos, alternativas mais simples; **QA**: "e se…?" — casos de borda, falhas, o que testar.
Saída: **critérios de aceite fechados**, dúvidas respondidas, **possível divisão** e uma **estimativa** (`agile-delivery`). Histórias **não refinadas** viram **surpresa no meio da iteração**.

## Das histórias às tarefas

- **O PM** escreve **histórias e critérios de aceite** (o quê/por quê).
- **O `tech-lead`** as **quebra em tarefas técnicas** (migration → entity → service → controller → testes → deploy), cada uma **com a skill que a guia**, e **estima** (P/M/G com incerteza).
- **O `qa`** transforma os critérios em **casos de teste**.
- **O `developer`** implementa; o `code-reviewer` revisa.
**PM não decide as tarefas técnicas; engenharia não decide o valor.**

## Exemplo — épico fatiado (renovação de empréstimo)

**Épico:** *Sócio renova empréstimo sem ir ao balcão.* Fatias verticais, em ordem de valor/risco:
1. **Renovar um empréstimo simples** (sem reserva, 1ª renovação) — web, ponta a ponta, com confirmação. *(walking skeleton)*
2. **Negar a renovação se há reserva** de outro sócio, com mensagem clara.
3. **Limitar a 2 renovações** por empréstimo.
4. **Aviso por e-mail 3 dias antes** do vencimento.
5. **Renovar direto do e-mail** (link seguro de uso único).
6. *(habilitadora)* **Idempotência** da renovação (retry/clique duplo não renova duas vezes).
7. *(spike, antes da 2)* **Descobrir** como consultar reservas no `catalog` (timebox 2 dias).
Cada uma entrega valor ou reduz risco, é demonstrável e cabe em poucos dias.

## Anti-patterns

- **História = tarefa técnica** ("criar tabela X"); **fatiar por camada** (frontend/backend/banco separados).
- **"Como usuário"** genérico; **sem "para que"**.
- **Épicos gigantes** disfarçados de história; histórias que atravessam várias iterações.
- **Sem critério de aceite**, ou critérios vagos ("deve funcionar bem").
- **Especificação técnica na história** (tirando a liberdade da engenharia).
- **DoD fraca** ("código commitado") ou **DoR como burocracia** que trava.
- **Refinar sozinho** (PM escreve sem engenharia/QA) e descobrir lacunas na sprint.
- **Esconder dívida técnica** fora do backlog, sem prioridade.

---

## Regras principais

- História = **Como… quero… para que…** — o **"para que"** é obrigatório; é o **início de uma conversa**, não uma especificação.
- **INVEST**: independente, negociável, valiosa, estimável, **pequena** (poucos dias), **testável**.
- **Critérios de aceite** (Given/When/Then, 3–7) cobrindo feliz, regras, erros e limites — escritos **antes**; o QA deriva os testes, o dev os usa como "pronto".
- **Fatie em fatias verticais** (nunca por camada), com **story map** para ver a jornada e um **primeiro release de ponta a ponta**; use os padrões de divisão e **spikes** para incerteza.
- **Habilitadoras/técnicas** são itens explícitos com **valor justificado**; NFRs transversais vão na **DoD**.
- **DoR** evita surpresa (sem burocracia); **DoD** é acordo da equipe e significa **pronto para o usuário**.
- **Three Amigos** (PM + eng + QA) refina cada história antes da iteração.
- **PM** define o **quê/por quê**; **tech-lead** quebra em **tarefas e estima**; **QA** vira casos de teste.
- **Sem Lombok** — deliberado (skill de produto, sem código).
