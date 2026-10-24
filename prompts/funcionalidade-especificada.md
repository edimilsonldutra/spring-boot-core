# Funcionalidade já especificada

**Quando usar:** PRD, histórias com critérios de aceite ou design doc já existem.
**Pipeline:** `tech-lead` → `developer` (por tarefa) → `qa` → `code-reviewer` (revisão + verificação da spec).
**Como rodar:** `claude --agent squads:orchestrator` e cole o prompt.
**Aprovações:** plano · commit/push.

## Prompt

```text
Implemente a funcionalidade especificada em: <caminho do PRD, design doc ou histórias>.

Critérios de aceite que precisam de teste: <todos | lista de CA-n>
Decisões já tomadas: <ADR ou trechos que não devem ser rediscutidos>
Restrições: <prazo, contratos que não podem quebrar, módulos que não devem ser tocados>
Fora de escopo: <o que fica para depois>
Branch: <nome da branch | crie uma nova>

Perfil de modelo: <auto | economico | equilibrado | qualidade-maxima>
```

## Exemplo preenchido

```text
Implemente a funcionalidade especificada em: docs/design/DD-003-renovacao.md.

Critérios de aceite que precisam de teste: todos (CA-1 a CA-6)
Decisões já tomadas: ADR-004 (limite de renovação no banco, sem cache)
Restrições: não alterar o contrato de GET /api/v1/loans
Fora de escopo: notificação por e-mail
Branch: crie feature/renovacao-online

Perfil de modelo: equilibrado
```

## Dicas

- Desvio que muda contrato, dados, critério, segurança ou rollout volta ao `architect` e a você **antes** de seguir.
- O relatório final traz a matriz critério → tarefa → prova e a verificação da spec feita pelo `code-reviewer` (provas re-executadas no código final, cobertura dos conjuntos); critério sem prova aparece como ⚠️ não provado.
