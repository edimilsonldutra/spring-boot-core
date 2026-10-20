# Refatoração e dívida técnica

**Quando usar:** melhorar a estrutura sem mudar o comportamento.
**Pipeline:** *(escopo incerto)* `tech-lead` → `qa` (testes de caracterização, **antes** de mexer) → `developer` (passos pequenos) → `code-reviewer`.
**Como rodar:** `claude --agent squads:orchestrator` e cole o prompt.
**Aprovações:** plano · commit.

## Prompt

```text
Refatore: <classe, módulo ou área>.

Problema atual: <o que dificulta: duplicação, classe gigante, acoplamento, teste impossível, performance>
Objetivo: <como deve ficar, ex.: "regra de multa isolada e testável">
Comportamento que NÃO pode mudar: <contratos de API, formato de dados, mensagens>
Cobertura atual: <boa | fraca | não sei>
Estratégia preferida: <passos pequenos | Strangler Fig | Branch by Abstraction | deixe o tech-lead propor>
Limites: <arquivos ou módulos que não devem ser tocados; tamanho máximo do diff por passo>

Perfil de modelo: <auto | economico | equilibrado | qualidade-maxima>
```

## Exemplo preenchido

```text
Refatore: LoanService.

Problema atual: 900 linhas, mistura cálculo de multa, renovação e envio de e-mail; testes lentos e frágeis.
Objetivo: cálculo de multa em FineCalculator puro e testável; e-mail fora da transação.
Comportamento que NÃO pode mudar: respostas de /api/v1/loans e valores de multa.
Cobertura atual: fraca
Estratégia preferida: passos pequenos
Limites: não mexer em migrations; até ~200 linhas de diff por passo

Perfil de modelo: auto
```

## Dicas

- Refatoração que atravessa vários módulos sobe um nível de modelo no modo automático.
- Sem testes de caracterização verdes, o `developer` não começa.
