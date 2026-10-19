# TODO — retomar depois

Estado em 2026-10-19: plugin `padrao-spring-boot` versão **1.15.0** (estrutura achatada), 88 skills, 7 agents. Repositório publicado em `edimilsonldutra/spring-boot-core`.

## 1. Publicar o que está local
- [x] Commit e push das mudanças pendentes: remoção das menções a curso (1.14.1), READMEs reescritos em tom profissional (raiz + `plugins/README.md`), seção `npx skills`.
- [ ] Depois do push, conferir no GitHub se os 9 diagramas Mermaid do README da raiz e o do guia renderizam.

## 2. Achatar a estrutura do repositório (decidido, não executado)
Mover `agents/` e `skills/` para a raiz e eliminar `plugins/`. Validado em cópia temporária com `claude plugin validate` (marketplace e plugin passaram).
- [x] `git mv plugins/agents agents` e `git mv plugins/skills skills`
- [x] `git mv plugins/.claude-plugin/plugin.json .claude-plugin/plugin.json`
- [x] `git mv plugins/README.md docs/guide.md` (não pode haver dois README na raiz)
- [x] `.claude-plugin/marketplace.json`: `"source": "./plugins"` → `"source": "."`
- [x] Atualizar links `plugins/README.md` → `docs/guide.md` no README da raiz e as âncoras citadas (`#catálogo-de-skills`, `#só-as-skills-em-outras-ferramentas-npx-skills`)
- [x] Atualizar no README da raiz: "Estrutura do repositório", "Contribuindo" (`plugins/skills/...` → `skills/...`, `plugins/agents/*.md` → `agents/*.md`, `plugins/.claude-plugin/plugin.json` → `.claude-plugin/plugin.json`) e o comando de validação (só `claude plugin validate .`)
- [x] No guia (`docs/guide.md`): links para o README do repositório continuam valendo; revisar qualquer caminho relativo
- [x] Os agents usam `${CLAUDE_PLUGIN_ROOT}/skills/X/SKILL.md` — continua correto, não precisa mudar
- [x] Subir a versão para **1.15.0** no `plugin.json` e no badge do README da raiz
- [x] `claude plugin validate .` e testar `npx skills add edimilsonldutra/spring-boot-core --list` depois do push
- [x] Testar uma reinstalação/atualização real (`/plugin marketplace update padrao`) para confirmar que quem já instalou recebe a nova estrutura

## 3. Decisões em aberto
- [ ] **Licença:** o repositório não tem `LICENSE`. Escolher (MIT, Apache 2.0…) e adicionar seção no README.
- [ ] **Plugin Kotlin** (`padrao-spring-boot-kt`): a menção foi removida do guia por não estar confirmada. Recolocar só se ele existir.
- [ ] **Badge de versão** no README da raiz é fixo: atualizar junto com o `plugin.json` a cada release (ou trocar por um badge dinâmico).

## 4. Verificações que ficaram por fazer
- [ ] **Skills novas não foram executadas em projeto real** (revisadas por leitura): gerar um projeto com `scaffold` e testar pelo menos `file-upload-download`, `file-import-export`, `pdf-reports`, `email`, `pagination`/`hateoas`.
- [ ] **Fluxo spec-driven** (`design-docs`): rodar uma feature de exemplo com `claude --agent padrao-spring-boot:orchestrator` e conferir os gates (PRD → design doc → plano) e a matriz critério → tarefa → teste.
- [ ] `api-versioning`: confirmar os nomes das propriedades `spring.mvc.apiversion.*` na referência oficial do Spring Boot 4 (a skill usa a configuração Java, que foi confirmada no javadoc).
- [ ] Versões citadas nas skills (`actions/*@v4`, `postman/newman:6-alpine`, `axllent/mailpit:v1.21`, actions do GCP/Azure): confirmar as mais recentes.
- [ ] Comandos do `npx skills` que não foram executados: `--all`, `update`, `remove --all`, `-a cursor` (testados: `--list` e `--skill '*'`, 88 skills sem link quebrado).
