# Prompts reutilizáveis

Modelos de pedido para o time de agents do plugin `squads`. Cada arquivo traz **quando usar**, **como rodar**, o **prompt** com campos `<entre sinais>` para preencher, um **exemplo preenchido** e dicas.

Copie o bloco **Prompt**, preencha os campos e apague as linhas que não se aplicam. Campo sem resposta? Deixe `não sei`: o agent assume o default da skill e declara a suposição.

| Prompt | Para quê | Quem roda |
|---|---|---|
| [`nova-funcionalidade.md`](nova-funcionalidade.md) | Feature do zero, da descoberta ao commit | `squads:orchestrator` |
| [`funcionalidade-especificada.md`](funcionalidade-especificada.md) | Feature com PRD/histórias já prontos | `squads:orchestrator` |
| [`correcao-de-bug.md`](correcao-de-bug.md) | Bug reproduzido por teste e corrigido pela causa raiz | `squads:orchestrator` |
| [`revisao-de-codigo.md`](revisao-de-codigo.md) | Revisar diff, branch ou PR | `squads:code-reviewer` |
| [`decisao-de-arquitetura.md`](decisao-de-arquitetura.md) | Escolher entre opções e registrar ADR | `squads:architect` |
| [`planejamento-e-estimativa.md`](planejamento-e-estimativa.md) | Quebrar em tarefas, riscos, estimativa e DoD | `squads:tech-lead` |
| [`plano-de-testes.md`](plano-de-testes.md) | Plano de testes, casos de borda e lacunas de cobertura | `squads:qa` |
| [`refatoracao.md`](refatoracao.md) | Refatorar com rede de segurança, em passos pequenos | `squads:orchestrator` |
| [`entender-repositorio.md`](entender-repositorio.md) | Mapear um repositório desconhecido | `squads:architect` ou `squads:tech-lead` |
| [`go-no-go.md`](go-no-go.md) | Prontidão para lançamento | `squads:orchestrator` |
| [`novo-projeto.md`](novo-projeto.md) | Criar um projeto Spring Boot no padrão do pacote | Sessão normal (skill `scaffold`) |
| [`preferencias-do-projeto.md`](preferencias-do-projeto.md) | Gerar o `CLAUDE.md` com as preferências e o perfil de modelo | Sessão normal (skill `project-claude-md`) |

## Como rodar

| Quem roda | Comando |
|---|---|
| Orquestrador | `claude --agent squads:orchestrator` e cole o prompt |
| Um agent | Na sessão: `@agent-squads:<agent>` + o prompt, ou "use o agent `<agent>` para…" |
| Sessão normal | `claude` e cole o prompt (as skills são escolhidas pela descrição) |

## Escolha de modelo

Todo prompt aceita a linha `Perfil de modelo:` com `auto` (padrão), `economico`, `equilibrado` ou `qualidade-maxima`. Para fixar uma etapa, escreva no próprio pedido, por exemplo "revise com opus". Detalhes em [README → Modelos e custo](../README.md#modelos-e-custo).

## Boas práticas

- **Resultado antes do caminho:** diga o que precisa estar verdadeiro no fim, não a lista de passos — o orquestrador escolhe o menor pipeline.
- **Números nos requisitos de qualidade:** "p95 < 300 ms com 200 req/s" decide arquitetura; "rápido" não.
- **Aponte artefatos:** caminhos de PRD, ADR, design doc, issue ou branch valem mais que um resumo.
- **Nunca cole segredos, tokens nem dados pessoais reais** — use exemplos fictícios.
- **Aprovações continuam suas:** escopo, design doc/ADR, plano, commit, push e deploy sempre param para confirmação.
