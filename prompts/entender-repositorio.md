# Entender um repositório

**Quando usar:** chegou em um sistema desconhecido ou precisa de contexto antes de planejar.
**Quem roda:** `squads:architect` quando o mapa deve ser **gravado** em `docs/architecture/repository-map.md` (com confirmação); `squads:tech-lead` quando basta o mapa **no relatório**.
**Entrega:** mapa com módulos, fluxos principais, dados, integrações, build e deploy, riscos e dúvidas em aberto.

## Prompt

```text
Mapeie este repositório<, com foco em <área ou fluxo>>.

Objetivo: <onboarding | planejar a feature X | avaliar dívida técnica | preparar migração>
Perguntas que preciso responder:
- <ex.: onde está a regra de cálculo de multa?>
- <ex.: quais sistemas externos são chamados e como?>
Saída: <relatório | gravar em docs/architecture/repository-map.md>
```

## Exemplo preenchido

```text
Mapeie este repositório, com foco no fluxo de empréstimo.

Objetivo: planejar a renovação online
Perguntas que preciso responder:
- onde estão as regras de empréstimo e reserva?
- como os dados de empréstimo são versionados no banco (migrations)?
- há testes de integração e como rodam?
Saída: relatório
```

## Dicas

- Pedido só de leitura é bom candidato a `haiku` no perfil econômico; no automático o orquestrador já faz isso nas varreduras.
- O mapa gravado serve de contexto para todas as próximas delegações.
