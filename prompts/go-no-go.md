# Prontidão para lançamento (go/no-go)

**Quando usar:** antes de liberar uma versão ou ativar uma feature flag.
**Pipeline:** `product-manager` (checklist e critérios de aborto) + `tech-lead` + `qa` + `code-reviewer`, em paralelo e somente leitura; o orquestrador consolida.
**Como rodar:** `claude --agent squads:orchestrator` e cole o prompt.
**Aprovação:** a decisão de go/no-go é sua.

## Prompt

```text
Avalie a prontidão para lançar: <feature ou versão>.

O que vai ao ar: <branch, tag ou PRs>
Especificação: <PRD, design doc>
Estratégia de rollout: <feature flag, canário, % de usuários, big bang>
Janela e responsáveis: <data, hora, quem acompanha>
Critérios de aborto: <ex.: erro 5xx > 1% por 5 min | defina>
Observabilidade: <dashboards e alarmes existentes | não sei>
Rollback: <como desfazer | não sei>
```

## Exemplo preenchido

```text
Avalie a prontidão para lançar: renovação online.

O que vai ao ar: tag v2.4.0
Especificação: docs/product/prd-renovacao.md, docs/design/DD-003-renovacao.md
Estratégia de rollout: feature flag renewal.online, 10% → 50% → 100% em 3 dias
Janela e responsáveis: terça 10h, time de empréstimos
Critérios de aborto: defina
Observabilidade: dashboard "Loans API" no CloudWatch
Rollback: desligar a flag; migration é aditiva
```

## Dicas

- Qualquer ⚠️ (não verificado) ou ❌ em aberto aparece no relatório — o orquestrador não declara "pronto" com pendências.
- Migration não aditiva ou sem rollback claro é motivo forte para no-go.
