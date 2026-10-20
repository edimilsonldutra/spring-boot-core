# Planejamento e estimativa

**Quando usar:** quebrar uma feature em tarefas pequenas, levantar riscos, definir MVP e Definition of Done, estimar.
**Quem roda:** `squads:tech-lead` (somente leitura). Sem escopo definido, use o `squads:orchestrator`, que chama o `product-manager` antes.
**Entrega:** tarefas ordenadas com skill e agent de cada uma, riscos e incógnitas, MVP, estimativa e DoD.

## Prompt

```text
Planeje: <feature ou objetivo>.

Especificação: <caminho do PRD/design doc | descrição curta>
Critérios de aceite: <lista ou caminho>
Prazo ou capacidade: <ex.: 2 sprints com 2 devs | não sei>
Restrições: <dependências de outros times, contratos, janelas de deploy>
Quero também: <MVP | estimativa em faixas | riscos com plano de mitigação | ordem de entrega incremental>
```

## Exemplo preenchido

```text
Planeje: renovação online de empréstimo.

Especificação: docs/product/prd-renovacao.md
Critérios de aceite: CA-1 a CA-6 do PRD
Prazo ou capacidade: 1 sprint com 2 devs
Restrições: deploy só às terças; contrato de GET /api/v1/loans congelado
Quero também: MVP, estimativa em faixas e riscos com mitigação
```

## Dicas

- Cada tarefa do plano vira uma delegação para o `developer`; tarefas pequenas e verificáveis saem mais baratas e mais certas.
- Estimativa vem em faixas e com as premissas; incógnitas grandes viram spike.
