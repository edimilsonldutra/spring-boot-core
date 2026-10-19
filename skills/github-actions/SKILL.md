---
name: github-actions
description: CI com GitHub Actions para Spring Boot, sem depender de nuvem — build e testes com Testcontainers (Maven e Gradle), cache, cobertura no PR, imagem no GitHub Container Registry com GITHUB_TOKEN, tags por commit e por versão, permissões mínimas, actions fixadas, Dependabot, CodeQL, branch protection, concurrency, workflows reutilizáveis e release por tag. Use quando criar ou revisar o pipeline de integração contínua de um projeto, antes de escolher onde fazer o deploy.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../maven-config/SKILL.md`](../maven-config/SKILL.md) (comandos Maven/Gradle), [`../docker-and-docker-compose/SKILL.md`](../docker-and-docker-compose/SKILL.md) (o Dockerfile) e [`../test-coverage/SKILL.md`](../test-coverage/SKILL.md) (gate de 90%). Deploy: [`../github-actions-aws/SKILL.md`](../github-actions-aws/SKILL.md) (AWS), [`../github-actions-cloud/SKILL.md`](../github-actions-cloud/SKILL.md) (GCP e Azure) ou [`../argocd/SKILL.md`](../argocd/SKILL.md) (GitOps).

# GitHub Actions — integração contínua

O **CI** responde a uma pergunta em todo push e pull request: *este commit está pronto para ir adiante?* Build, testes (inclusive os de integração com banco real), cobertura, análise de segurança e, na `main`, uma **imagem imutável** publicada. O **deploy** é outra etapa, com skill própria para cada destino — este pipeline termina na imagem.

**Pergunte até onde o pipeline vai** (e salve): só build + testes; + análise de segurança; + imagem no registry; + release por tag. Os jobs abaixo são independentes para você remover o que não precisa.

## 1. Workflow de CI

`.github/workflows/ci.yml`:
```yaml
name: ci

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

permissions:
  contents: read

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  build-test:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          distribution: temurin
          java-version: 25
          cache: maven
      - name: Build and test
        run: ./mvnw -B clean verify
      - name: Upload coverage report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: jacoco-report
          path: target/site/jacoco/
      - name: Upload test results
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: surefire-reports
          path: target/surefire-reports/

  image:
    needs: build-test
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    steps:
      - uses: actions/checkout@v4
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - id: meta
        uses: docker/metadata-action@v5
        with:
          images: ghcr.io/${{ github.repository }}
          tags: |
            type=sha,format=long
      - uses: docker/setup-buildx-action@v3
      - uses: docker/build-push-action@v6
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```
Pontos que importam:
- **`./mvnw -B clean verify`** roda unit **e** integração (Testcontainers) numa fase só (`maven-config`, `integration-testing`); o `ubuntu-latest` já tem Docker. Com o JaCoCo configurado (`test-coverage`), o `verify` **falha** abaixo de 90% — o gate de cobertura é o próprio build. **Gradle:** `./gradlew clean build` e `cache: gradle`; os relatórios ficam em `build/reports/`.
- **Wrapper executável:** criado no Windows, o `mvnw`/`gradlew` perde o bit de execução e o runner Linux falha com `Permission denied` — `git add --chmod=+x mvnw` antes do commit (`scaffold`).
- **`timeout-minutes`**: um teste travado não consome 6 horas de runner.
- **`GITHUB_TOKEN` com `packages: write`** publica no **GitHub Container Registry** sem nenhum segredo extra — o token vale só durante o job. Nenhuma credencial de nuvem aqui.
- **Tag = SHA do commit** (imutável, rastreável do commit ao container); nunca `latest` como referência de deploy.
- **Pull requests** rodam só `build-test`: código de fork não recebe `packages: write` nem segredos.
- **Cancelamento** só em PR: um push novo no PR cancela a execução antiga; na `main`, cada commit termina (evita imagem pela metade).

---

## 2. Release por tag

Ao criar uma tag `v1.4.2`, publique a imagem com a versão semântica e uma release do GitHub:
```yaml
on:
  push:
    tags: ['v*.*.*']
```
Com o `docker/metadata-action`, acrescente `type=semver,pattern={{version}}` e `type=semver,pattern={{major}}.{{minor}}` às `tags`. Um job com `permissions: contents: write` cria a release (`gh release create "$GITHUB_REF_NAME" --generate-notes`). A versão do `pom.xml`/`build.gradle` deve casar com a tag — verifique no job e falhe se divergir.

---

## 3. Segurança do pipeline

- **Permissões mínimas:** `permissions: contents: read` no topo; cada job pede só o que usa (`packages: write`, `security-events: write`, `id-token: write`). Sem `permissions`, o token pode ter escrita ampla, dependendo da configuração do repositório.
- **Fixe as actions por SHA** em repositórios sensíveis (`uses: actions/checkout@<sha> # v4.x`): uma tag pode ser movida por quem comprometer a action, e ela roda com as permissões do job. As tags `@v4` dos exemplos são por legibilidade — confirme as versões mais recentes.
- **Dependabot** (`.github/dependabot.yml`) para as actions, o Maven/Gradle e o Dockerfile:
```yaml
version: 2
updates:
  - package-ecosystem: github-actions
    directory: /
    schedule:
      interval: weekly
  - package-ecosystem: maven
    directory: /
    schedule:
      interval: weekly
  - package-ecosystem: docker
    directory: /
    schedule:
      interval: weekly
```
(`gradle` no lugar de `maven` quando for o caso.)
- **CodeQL** (análise estática de segurança) em PR e semanalmente: workflow `github/codeql-action` com `languages: java-kotlin` e `build-mode: autobuild` (ou `manual` com o `./mvnw -B -DskipTests package`), `permissions: security-events: write`. Os alertas aparecem na aba Security.
- **Secret scanning e push protection** ligados nas configurações do repositório: bloqueiam o push de credenciais conhecidas.
- **Scan da imagem e das dependencies:** Trivy no job `image` antes do push (falhar em vulnerabilidade `CRITICAL` corrigível) e o `dependency-check`/Dependabot alerts (`maven-config`).
- **`pull_request_target`** roda com segredos e permissões de escrita no contexto da base — **nunca** faça checkout e build do código do PR dentro dele.
- **Não imprima segredos:** o GitHub mascara `secrets.*`, mas não valores derivados; nada de `set -x` perto deles.

---

## 4. Proteção da branch principal

Nas configurações do repositório (*Rules/Branch protection*) da `main`:
- exigir PR e pelo menos uma aprovação (o `code-reviewer` ajuda, não substitui);
- exigir os **status checks** `build-test` (e CodeQL) verdes e a branch atualizada;
- bloquear push direto e force push.

Sem isso, o CI é só uma sugestão.

---

## 5. Organização e velocidade

- **Cache** do Maven/Gradle pelo `setup-java` e das camadas Docker com `type=gha`.
- **Workflows reutilizáveis** (`on: workflow_call`) quando vários serviços compartilham o mesmo pipeline: um `build.yml` central chamado por cada repositório, em vez de copiar YAML.
- **Matrix** (`strategy.matrix.java: [21, 25]`) só se o projeto realmente suporta várias versões; normalmente uma LTS basta.
- Suíte lenta: separe unit e integração em jobs paralelos por tag (`integration-testing`, seção 7) — e ajuste o merge de cobertura (`test-coverage`).
- **Testes de API de caixa-preta** contra a imagem: job `api-tests` com docker compose + Newman (`postman-newman`).
- **`workflow_dispatch`** para execuções manuais (reconstruir uma tag, rodar a suíte completa).

---

## 6. Depois do CI: o deploy

| Destino | Skill |
|---|---|
| AWS (ECR, EKS, ECS) com OIDC | `github-actions-aws`, `aws-ecs-fargate` |
| Google Cloud (Artifact Registry, Cloud Run, GKE) ou Azure (ACR, AKS, Container Apps) | `github-actions-cloud` |
| Qualquer Kubernetes por GitOps | `argocd` (o CI só atualiza a tag no repositório de configuração) |

O job de deploy consome a **mesma imagem** (mesmo SHA) que passou no CI — nunca reconstrua para implantar.

---

## Regras principais

- `./mvnw -B clean verify` (ou `./gradlew clean build`) roda todos os testes, inclusive Testcontainers, e o gate de cobertura; nenhuma imagem é publicada se falhar.
- `permissions: contents: read` no topo e só o necessário por job; PRs não recebem permissões de escrita nem segredos.
- Imagem no GHCR com `GITHUB_TOKEN` e tag = SHA do commit; semver por tag; nunca `latest` como referência.
- Actions fixadas por SHA em repositórios sensíveis e atualizadas pelo Dependabot (actions, Maven/Gradle, Docker).
- CodeQL, secret scanning com push protection, scan da imagem e das dependencies.
- `main` protegida: PR obrigatório, status checks obrigatórios, sem push direto.
- `timeout-minutes` nos jobs; `concurrency` cancelando só execuções de PR.
- O deploy usa a imagem que passou no CI, com a skill do destino.
