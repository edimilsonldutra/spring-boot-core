# Nova funcionalidade

**Quando usar:** feature do zero, ainda sem PRD.
**Pipeline:** `product-manager` → *(média/grande ou sensível)* `architect` → `tech-lead` → `developer` → `qa` → `code-reviewer`.
**Como rodar:** `claude --agent squads:orchestrator` e cole o prompt.
**Aprovações:** escopo (PRD) · design doc/ADR/threat model · plano · commit/push.

## Prompt

```text
Entregue a funcionalidade: <nome curto>.

Problema: <o que dói hoje, para quem, e como sabemos (dado, reclamação, ticket)>
Usuários: <quem usa e em que situação>
Resultado esperado: <o que precisa ser verdade quando estiver pronto>
Métrica de sucesso: <número que deve mudar, ex.: "reduzir chamados de X em 30%">

Requisitos de qualidade:
- Carga e latência: <ex.: 50 req/s, p95 < 300 ms | não sei>
- Disponibilidade: <ex.: 99,9% | não sei>
- Dados pessoais ou sensíveis: <sim: quais | não>
- Integrações externas: <sistemas/APIs | nenhuma>

Restrições: <prazo, tecnologia obrigatória, contrato que não pode quebrar>
Fora de escopo: <o que NÃO entra nesta entrega>
Referências: <issue, documentos, endpoints ou classes existentes>

Perfil de modelo: <auto | economico | equilibrado | qualidade-maxima>
```

## Exemplo preenchido

```text
Entregue a funcionalidade: renovação online de empréstimo.

Problema: hoje o leitor precisa ir à biblioteca para renovar; 40% dos atendimentos de balcão são renovações (relatório de março).
Usuários: leitores com empréstimo ativo, pelo app e pelo site.
Resultado esperado: o leitor renova pela API até 2 vezes por empréstimo, desde que não haja reserva nem multa.
Métrica de sucesso: renovações no balcão caem 50% em 60 dias.

Requisitos de qualidade:
- Carga e latência: pico de 20 req/s, p95 < 300 ms
- Disponibilidade: 99,5%
- Dados pessoais ou sensíveis: sim, identificação do leitor
- Integrações externas: nenhuma

Restrições: não quebrar o contrato atual de GET /api/v1/loans.
Fora de escopo: pagamento de multa.
Referências: LoanController, LoanService, migration V7__create_loan.sql.

Perfil de modelo: auto
```

## Dicas

- Dados pessoais, dinheiro, autenticação, arquivos ou integração externa tornam a feature **sensível**: o pipeline inclui threat model e `opus` na arquitetura e na revisão.
- Se você já tem o PRD, use [`funcionalidade-especificada.md`](funcionalidade-especificada.md) e economize uma etapa.
