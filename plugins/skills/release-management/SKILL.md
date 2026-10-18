---
name: release-management
description: Lançamentos seguros — deploy × release, feature flags, entrega progressiva (piloto, canary, percentual), critérios de sucesso e de aborto definidos antes, rollback e seu limite com o banco, go/no-go, comunicação, deprecação de APIs e revisão pós-lançamento. Use quando planejar o lançamento de uma funcionalidade ou a retirada de uma API.
---

Antes de aplicar este pattern, leia também [`../prd-writing/SKILL.md`](../prd-writing/SKILL.md) (o plano de lançamento do PRD), [`../product-metrics/SKILL.md`](../product-metrics/SKILL.md) (medir o lançamento), [`../stakeholder-communication/SKILL.md`](../stakeholder-communication/SKILL.md) (comunicados e release notes) e, do lado técnico, [`../argocd/SKILL.md`](../argocd/SKILL.md), [`../aws-parameter-store/SKILL.md`](../aws-parameter-store/SKILL.md) (AppConfig), [`../flyway-migrations/SKILL.md`](../flyway-migrations/SKILL.md) e [`../kubernetes/SKILL.md`](../kubernetes/SKILL.md). Quem executa o deploy: `developer`/plataforma; **decide go/no-go**: o PM com o `tech-lead`.

# Gestão de lançamento

**Lançar é um processo, não um evento.** O jeito mais seguro de lançar software não é "testar muito e rezar", é **reduzir o raio de explosão**: liberar para **poucos**, **medir**, **ampliar** — e poder **desligar rápido**. Esta skill une **decisão de produto** (quem recebe, quando, com que critério) e **mecanismos técnicos** (flags, canary, rollback).

## 1. Deploy ≠ Release

| | **Deploy** | **Release (lançamento)** |
|---|---|---|
| O que é | Colocar o **código em produção** | Tornar a funcionalidade **disponível aos usuários** |
| Quem decide | Engenharia (técnico, frequente, de baixo risco) | **Produto** (de negócio, deliberado) |
| Como separar | Código novo entra **desligado** atrás de uma **feature flag** | Liga-se a flag para um público, gradualmente |

Separar os dois muda tudo: **o deploy deixa de ser um evento de risco** (feito várias vezes ao dia, o código está "dormente"), e o **lançamento vira uma decisão de produto reversível** (ligar/desligar a flag, **sem novo deploy**). É a base de lançar **pequeno, frequente e seguro** (`agile-delivery`: DORA).

## 2. Feature flags

Uma **feature flag** é um interruptor em configuração que liga/desliga um comportamento **em runtime**. Tipos (e a vida útil de cada um):
| Tipo | Uso | Vida |
|---|---|---|
| **Release flag** | Esconder funcionalidade em construção; **lançamento gradual** | **Curta** — **remova** após 100% estável |
| **Experiment flag** | **A/B test** (`product-metrics`) | Duração do experimento |
| **Ops flag / kill switch** | **Desligar** rápido algo arriscado (integração externa, recurso caro) | Longa (controle operacional) |
| **Permission flag** | Funcionalidade por plano/cliente/região | Longa (é parte do produto) |

**Como implementar na pilha do pacote:** **AWS AppConfig** (`aws-parameter-store`, seção AppConfig) entrega flags/configuração com **rollout gradual, validação e rollback automático por alarme**; a aplicação **consulta periodicamente e cacheia** (nunca por request). Alternativas: Parameter Store/ConfigMap (flag simples, com restart), ferramentas dedicadas (Unleash, LaunchDarkly, OpenFeature como padrão aberto). No código (`developer`): a flag é lida **de um ponto único** (um `FeatureFlags` bean tipado), o caminho novo **desligado por padrão** e **testado nos dois estados**.

**Higiene de flags (a dívida invisível):**
- **Toda release flag nasce com data de remoção** e um **dono**. Flag esquecida vira **código morto e combinação de estados** impossível de testar.
- **Remova** a flag e o caminho antigo **depois do lançamento estável** (item no backlog, com prioridade — `prioritization`).
- **Evite flags aninhadas/interdependentes** (explosão combinatória).
- **Nunca use flag para segurança/controle de acesso** (use autorização real — `authentication`).
- Documente o **estado das flags** em produção (quem liga o quê, quando).

## 3. Entrega progressiva — reduzir o raio de explosão

Em vez de 0% → 100%, **escada de exposição**:
```
Interno (funcionários) → Piloto/beta (clientes escolhidos) → 1–5% → 25% → 50% → 100%
        ↑ em cada degrau: MEDIR os critérios → avançar, segurar ou voltar
```
- **Piloto/beta fechado**: poucos clientes **dispostos**, **canal de feedback** direto; ótimo para validar **usabilidade e valor** (`product-discovery`).
- **Percentual por usuário** (estável: o mesmo usuário sempre vê a mesma versão) — via flag/AppConfig; ou por **coorte** (região, plano, filial).
- **Canary de infraestrutura**: parte do **tráfego** vai à versão nova do serviço (`kubernetes`: rolling update; **Argo Rollouts** com `setWeight` e **análise automática** de métricas e **abort** — `argocd`). Cobre o **risco técnico** (a versão nova quebra?), enquanto a flag cobre o **risco de produto** (os usuários gostam?).
- **Shadow traffic / dark launch**: a versão nova **processa cópias** do tráfego real **sem afetar** a resposta ao usuário — compara resultados e desempenho **antes** de expor. Útil em migrações (`microservices`: Strangler Fig).
- **Blue/green**: dois ambientes; troca o tráfego de uma vez e **volta rápido** se algo der errado (ECS/EKS — `aws-ecs-fargate`).
Cada degrau tem **tempo mínimo de observação** (ex.: um ciclo completo de uso — no mínimo um dia útil) e **critérios objetivos** para avançar.

## 4. Critérios de sucesso e de aborto — definidos ANTES

O erro clássico é decidir o que fazer **depois de ver os números, sob pressão**. **Escreva antes** (no PRD — `prd-writing`, seção 10):
```markdown
## Plano de rollout — Renovação online

| Degrau | Público | Duração mínima | Para avançar (TODOS) | Abortar/voltar se (QUALQUER) |
|---|---|---|---|---|
| 1 | Interno | 2 dias úteis | 0 erros críticos; fluxo completo OK | Erro bloqueante |
| 2 | 5% dos sócios | 3 dias úteis | Erro 5xx < 1%; p95 < 500 ms; tickets estáveis | 5xx ≥ 2% por 10 min; p95 > 1 s; +20% de tickets |
| 3 | 25% | 1 semana | Taxa de renovação ≥ 15%; sem piora nos guardrails | Guardrail piora de forma consistente |
| 4 | 100% | — | Meta do PRD após 4 semanas | — |

Quem decide avançar/abortar: <PM + tech lead>.   Quem pode desligar a flag sem pedir permissão: <on-call>.
```
- **Métricas técnicas** (erro, latência, saturação — `observability`, `aws-observability`) **e de produto** (conversão, uso, tickets — `product-metrics`) **juntas**, incluindo **guardrails**.
- **Ligue alarmes** para os critérios de aborto (ou **automatize o rollback** — AppConfig com alarme, Argo Rollouts com análise).
- **Um "botão de pânico"**: qualquer pessoa de plantão pode **desligar a flag** sem precisar de aprovação em emergência; **depois** discute-se.

## 5. Plano de rollback — e o que ele não desfaz

Todo lançamento tem **um plano de volta, testado**, **antes** de ir.
| Mecanismo | Velocidade | Observação |
|---|---|---|
| **Desligar a feature flag** | Segundos | **O primeiro recurso**; por isso o código novo entra atrás de flag |
| **Reverter o tráfego** (blue/green, canary abort) | Segundos–minutos | Infra |
| **Reverter a versão** (`argocd`: `git revert` → sync; `kubectl rollout undo`; ECS circuit breaker com rollback — `aws-ecs-fargate`) | Minutos | Requer **a versão antiga funcionar com o estado atual** |
| **Restaurar dados** (backup/PITR) | Horas | **Último recurso**, perda de dados desde o backup |

**O limite do rollback: banco de dados e efeitos externos.** Reverter o **código** é fácil; reverter **dados já escritos** **não**. Por isso:
- **Migrations compatíveis com a versão anterior** — **expand → contract** (`flyway-migrations`): a versão antiga **continua funcionando** com o schema novo; **nunca** remova/renomeie coluna na mesma release que o código que a deixa de usar.
- **Cuidado com dados escritos pela versão nova** que a antiga não entende (formatos novos, estados novos): planeje a **compatibilidade para trás**.
- **Efeitos externos irreversíveis** (e-mails enviados, cobranças, mensagens publicadas): **não voltam** — por isso são **idempotentes** (`idempotency`) e vão **depois do ponto sem retorno** (`saga-pattern`); a flag desliga **novos** efeitos, mas não **desfaz** os feitos.
- **Rollback de dados** é decisão de negócio (perder o que foi escrito desde o lançamento?) — **rehearse** o procedimento em ambiente de teste.

## 6. Checklist de go/no-go

Reunião curta **antes de cada degrau relevante** (e do lançamento amplo). **Go** exige **todos** os itens aplicáveis:
```markdown
## Go/No-Go — <iniciativa> — <degrau>
**Produto**
- [ ] Critérios de aceite do PRD atendidos e **demonstrados** (aceite do PM/design)
- [ ] Métricas de sucesso, guardrails e **dashboards** prontos; **critérios de aborto** definidos e **alarmes** ligados
- [ ] Plano de **rollout progressivo** e de **rollback testado** documentados
**Engenharia/Qualidade**
- [ ] Testes passando (unit, integração, **contrato** — `contract-testing`); **cobertura ≥ 90%** (gate do CI — `test-coverage`); revisão de código aprovada (`code-reviewer`)
- [ ] Desempenho verificado na carga esperada (`jvm-performance`); migrations **compatíveis** com a versão anterior
- [ ] Observabilidade: logs/métricas/alertas/traces (`observability`); **runbook** de on-call atualizado
- [ ] Flag **desligada por padrão**, **testada nos dois estados**, com **data de remoção**
**Segurança, privacidade, legal**
- [ ] Revisão de **segurança** e de **privacidade/LGPD** concluída (`privacy-lgpd`); termos/avisos atualizados se preciso
**Comunicação e operação**
- [ ] **Suporte/CS** treinados e com **FAQ**; **vendas** sabem o que pode ser dito
- [ ] **Clientes impactados avisados** (mudanças que quebram, janelas, deprecações) e **release notes** prontas
- [ ] **On-call** definido para o período; **quem decide** abortar e **quem desliga** a flag está claro
**Decisão:** ☐ GO · ☐ NO-GO (motivo/condição para revisar: ______)
```
**No-go não é fracasso:** é o processo funcionando. **Evite lançar na sexta à tarde, vésperas de feriado, ou sem on-call** (a menos que a mudança seja trivial e **reversível por flag**).

## 7. Comunicação do lançamento

(`stakeholder-communication` tem os modelos.) **Por audiência, antes e depois:**
- **Suporte/CS/Vendas — antes**: o que muda, **para quem**, quando, **FAQ**, como **reverter**, o que **podem e não podem dizer**, quem escalar. Eles recebem o impacto **primeiro**.
- **Clientes — antes** (se houver mudança que os afete): **antecedência** compatível com o esforço deles; **depois**: **release notes** pelo ângulo do benefício.
- **Liderança**: resumo, riscos, métricas que serão observadas, **quando haverá o primeiro resultado**.
- **Durante** o rollout: **status** curto nos marcos (subiu para 25%, métricas ok/atenção).
- **Se abortar**: comunique **rápido e com clareza** (o que houve, impacto, próximos passos) — sem minimizar.

## 8. Versionamento e política de deprecação de APIs

Para **APIs** consumidas por outros times/clientes (`service-communication`, `contract-testing`, `technical-product-management`):
- **SemVer** para o contrato (`MAJOR.MINOR.PATCH`): **MAJOR** = mudança que **quebra**; **MINOR** = adição compatível; **PATCH** = correção. No path/versão pública costuma expor-se só o **MAJOR** (`/api/v2/...`).
- **Mudanças aditivas** dentro de uma versão; **quebra de contrato = nova versão MAJOR** com **convivência**.
- **Política de deprecação explícita e publicada**: **anúncio** → **janela de convivência** (ex.: 6–12 meses para API pública; menos para interna) → **desligamento**. Cabeçalhos HTTP `Deprecation` e `Sunset` sinalizam na própria resposta; **notifique** os consumidores (use as **métricas de uso por consumidor**/o broker de contratos para saber **quem ainda usa**).
- **Nunca desligue** uma versão **sem confirmar que ninguém a usa** (ou ter avisado e acordado o prazo); **ofereça guia de migração** e, se possível, **ferramentas**.
- **Registre no changelog** (`CHANGELOG.md`, release notes) toda mudança relevante.
- **Descontinuar funcionalidade para usuários finais** (não só API) segue o mesmo princípio: aviso **antecipado**, alternativa, **export dos dados** do usuário.

## 9. Migração de usuários e dados

Migrações (nova plataforma, novo modelo de dados, troca de provedor) são **lançamentos de alto risco**:
- **Coexistência**: o antigo e o novo funcionam **juntos** por um período (Strangler Fig — `microservices`), com **roteamento gradual**.
- **Migre em ondas** (piloto → coortes) com **verificação** (comparar resultados antigo × novo, contagem/checksum de dados) e **reversão** possível em cada onda.
- **Comunicação** com o usuário **antes**, **durante** e **depois**; suporte reforçado; **janela** adequada.
- **Dados pessoais**: a migração é um **tratamento** — verifique base legal, minimização e segurança (`privacy-lgpd`).

## 10. Lançamentos com marketing, comercial e jurídico

Algumas entregas têm **data externa** (campanha, evento, contrato, **prazo regulatório**). Então: **trate a data como fixa e o escopo como variável** (`product-roadmap`, `prioritization` — MoSCoW); trave o **escopo mínimo** ("Must") cedo; **ensaie** o lançamento (**dry run**/ensaio geral em staging com os mesmos passos); mantenha a **flag** para ligar **no momento exato** (o deploy aconteceu dias antes); tenha **plano B** (adiar o anúncio sem adiar o código). **Jurídico/DPO** revisam **antes** de congelar o escopo, não na véspera.

## 11. Revisão pós-lançamento — fechar o ciclo

**Lançar não é o fim; é quando se aprende.** Agende **antes** do lançamento:
- **1 dia / 1 semana / 1 mês**: meça as **métricas do PRD** (primária, secundárias, **guardrails**) contra a **meta e a linha de base** (`product-metrics`); **sem mudar a meta** depois.
- **Feedback qualitativo** (suporte, entrevistas, comentários).
- **Retrospectiva do lançamento**: o que correu bem/mal no **processo** (comunicação, rollout, rollback), **ações** com dono.
- **Decisão**: **escalar, iterar ou reverter/descontinuar** — **registrada** (decision log) e comunicada. Funcionalidade que **não moveu** o resultado é **removida** (custo de manutenção!), não mantida por inércia.
- **Remover as flags** e o caminho antigo.
- Alimente o **roadmap** e a **descoberta** com o aprendizado.

## 12. Anti-patterns

- **Big-bang** (0 → 100% sem degraus, sem flag, sem rollback testado).
- **Sem critérios de aborto** definidos antes (decidir sob pressão); **só métricas técnicas** (ou só de produto).
- **Rollback "teórico"** nunca ensaiado; **ignorar o banco** (migração destrutiva no mesmo release).
- **Flags eternas**, aninhadas, sem dono; **flag como controle de acesso**.
- **Lançar sem avisar suporte/vendas/clientes**; **desligar API sem confirmar quem usa**.
- **Lançar na sexta à tarde / véspera de feriado / sem on-call**.
- **Nunca medir depois** ("lançamos, próximo!") e **manter o que não funciona**.
- **Confundir deploy com release**; deploys raros, grandes e arriscados.
- **Data prometida com escopo fixo** (a conta não fecha — data fixa → escopo variável).

---

## Regras principais

- **Deploy ≠ release**: código entra **desligado atrás de feature flag**; **lançar é decisão de produto**, reversível sem novo deploy.
- **Flags** com **dono e data de remoção**, lidas de um ponto único, testadas nos **dois estados**, **removidas** após o lançamento estável; **nunca** para segurança; AppConfig/Parameter Store/OpenFeature.
- **Entrega progressiva** (interno → piloto → 1–5% → 25% → 50% → 100%; canary/Argo Rollouts, blue/green, dark launch) com **tempo mínimo e critérios** por degrau.
- **Critérios de sucesso e de aborto definidos ANTES**, com métricas **técnicas e de produto + guardrails**, alarmes/rollback automático e um **"botão de pânico"** desligável por qualquer on-call.
- **Rollback testado**: flag → tráfego → versão → restore (último recurso); **migrations expand → contract**; efeitos externos **não voltam** (idempotência, depois do ponto sem retorno).
- **Go/no-go** com checklist (produto, qualidade, segurança/privacidade, comunicação, on-call); **no-go é processo saudável**; evite sexta à tarde/véspera de feriado/sem on-call.
- **Comunique antes** a suporte/CS/vendas e clientes impactados; release notes pelo **benefício**; se abortar, comunique rápido.
- **APIs**: SemVer, mudanças aditivas, **política de deprecação publicada** (`Deprecation`/`Sunset`), confirmar quem usa antes de desligar.
- **Migrações em ondas**, coexistência, verificação e reversão; dados pessoais com LGPD.
- Data externa → **data fixa, escopo variável**, ensaio geral, flag para ligar no momento exato.
- **Revisão pós-lançamento** (1 dia/1 semana/1 mês) contra a meta; **escalar, iterar ou descontinuar** com decisão registrada.
- **Sem Lombok** — deliberado (skill de produto, sem código).
