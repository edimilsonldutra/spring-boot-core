# Correção de bug

**Quando usar:** comportamento errado em produção, homologação ou teste.
**Pipeline:** `qa` (teste que reproduz) → `developer` (corrige a causa raiz) → `code-reviewer`.
**Como rodar:** `claude --agent squads:orchestrator` e cole o prompt.
**Aprovações:** commit/push.

## Prompt

```text
Corrija o bug: <título curto>.

Comportamento atual: <o que acontece>
Comportamento esperado: <o que deveria acontecer>
Como reproduzir:
1. <passo>
2. <passo>
Ambiente e frequência: <local, homologação, produção; sempre, intermitente, sob carga>
Evidências: <stack trace, log, request/response, ID de correlação — sem dados pessoais reais>
Desde quando: <versão, commit ou data | não sei>
Suspeita (opcional): <classe, método ou mudança recente>

Perfil de modelo: <auto | economico | equilibrado | qualidade-maxima>
```

## Exemplo preenchido

```text
Corrija o bug: renovação aceita empréstimo com reserva pendente.

Comportamento atual: POST /api/v1/loans/{id}/renew retorna 200 mesmo quando o livro tem reserva.
Comportamento esperado: 409 com ExceptionResponse "Livro reservado por outro leitor".
Como reproduzir:
1. Crie um empréstimo do livro 10 para o leitor A.
2. Crie uma reserva do livro 10 para o leitor B.
3. Renove o empréstimo do leitor A.
Ambiente e frequência: homologação, sempre.
Evidências: log com correlationId 7f3a... mostrando a renovação gravada.
Desde quando: depois do commit a1b2c3d.
Suspeita (opcional): LoanService.renew não consulta ReservationRepository.

Perfil de modelo: auto
```

## Dicas

- Bug intermitente, de concorrência ou performance sobe `qa` e `developer` para `opus` no modo automático.
- O teste que reproduz entra **antes** da correção e fica como regressão.
