# Padrão Spring Boot — Agents e Skills para o Claude Code

Plugin para o [Claude Code](https://claude.com/claude-code) que ensina a construir, testar, containerizar e implantar REST APIs com **Spring Boot 4 / Java 25** no padrão do curso.

Ele traz um **time de 7 agents** — product manager, architect, tech lead, developer, QA, code reviewer e um orquestrador que coordena todos — e as **88 skills** que esses agents seguem (Spring Boot, API, arquivos e e-mail, especificação, segurança e design de código, testes, mensageria, microsserviços, CI/CD, Kubernetes, AWS e produto). Os agents fazem o trabalho; as skills definem o padrão.

```
Você ──▶ orchestrator ──▶ product-manager → architect → tech-lead → developer → qa → code-reviewer
                              (cada agent carrega as skills da sua etapa)
```

Você também pode chamar um agent sozinho (`@code-reviewer`) ou uma skill direto (`/padrao-spring-boot:spring-data-jpa`).

## Instalação

Pré-requisitos: Claude Code e Git instalados. Não é preciso conta no GitHub.

Em um terminal, fora do Claude Code:

```
claude plugin marketplace add edimilsonldutra/spring-boot-core
claude plugin install padrao-spring-boot@padrao
```

Ou, dentro do Claude Code:

```
/plugin marketplace add edimilsonldutra/spring-boot-core
/plugin install padrao-spring-boot@padrao
```

Para conferir, digite `/padrao-spring-boot` no Claude Code e veja as skills no autocomplete.

## Atualização

Dentro do Claude Code: `/plugin` → **Marketplaces** → `padrao` → **Enable auto-update**. Ou, à mão: `/plugin marketplace update padrao`.

## Documentação

O guia completo — como agents e skills se conectam, o fluxo de trabalho e os pipelines do orquestrador, a instalação passo a passo, as perguntas iniciais, o catálogo de skills com exemplos de prompt e a solução de problemas comuns — está em **[plugins/README.md](plugins/README.md)**.
