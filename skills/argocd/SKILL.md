---
name: argocd
description: Entrega contínua por GitOps com Argo CD no Kubernetes/EKS — repositório de configuração, Application/AppProject/ApplicationSet, sync policy, Flyway como PreSync hook, CI que só atualiza a tag, promoção por PR, rollback por git revert, segredos fora do Git e segurança do Argo CD. Use quando configurar ou depurar deploy GitOps (OutOfSync, Degraded).
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../kubernetes/SKILL.md`](../kubernetes/SKILL.md) (os manifests que o Argo CD aplica), [`../helm-charts/SKILL.md`](../helm-charts/SKILL.md), [`../github-actions-aws/SKILL.md`](../github-actions-aws/SKILL.md) (o CI que alimenta o Argo CD) e [`../aws-eks/SKILL.md`](../aws-eks/SKILL.md).

# Argo CD (GitOps)

**GitOps**: o **Git é a fonte da verdade** do que roda no cluster. Um controlador **dentro do cluster** (o Argo CD) compara continuamente o que está no Git com o que está rodando e **reconcilia** a diferença. Ninguém faz `kubectl apply` à mão; **mudar produção = mergear um pull request**.

## Por que GitOps (e por que Argo CD)

| | CI faz `kubectl apply` (push — `github-actions-aws`) | GitOps com Argo CD (pull) |
|---|---|---|
| Credenciais do cluster | **Saem do cluster** (o CI precisa de acesso ao API server) | **Ficam no cluster**; o CI só escreve no Git |
| Estado desejado | Implícito no último pipeline que rodou | **Explícito no Git**, versionado e auditável |
| Drift (alguém alterou à mão) | Invisível até o próximo deploy | **Detectado e (opcionalmente) corrigido** (`selfHeal`) |
| Rollback | Re-executar pipeline antigo | `git revert` — o mesmo fluxo de qualquer mudança |
| Auditoria | Logs de pipeline | **Histórico do Git** (quem, quando, por quê, quem aprovou) |
| Visibilidade | `kubectl get` | **UI** com árvore de recursos, diff e saúde |

O push com `kubectl apply` no CI (`github-actions-aws`) **funciona e é aceitável para um serviço pequeno**. Adote GitOps quando houver **vários serviços/ambientes/clusters**, exigência de **auditoria/aprovação**, ou dor com **drift**. Argo CD é o padrão de mercado (alternativa: **Flux**).

**Responsabilidades separadas:**
- **CI** (GitHub Actions): compila, testa, constrói e **publica a imagem** no ECR (`aws-eks`), e **atualiza a tag no repositório GitOps**. Não toca no cluster.
- **CD** (Argo CD): **aplica** o que está no repositório GitOps e relata saúde.

---

## 1. Dois repositórios

```
library-api/                      # repositório da APLICAÇÃO (código + Dockerfile + testes)
library-gitops/                   # repositório de CONFIGURAÇÃO (o que o Argo CD observa)
├── apps/
│   └── library-api/
│       ├── base/
│       │   ├── deployment.yaml
│       │   ├── service.yaml
│       │   ├── configmap.yaml
│       │   ├── hpa.yaml
│       │   ├── pdb.yaml
│       │   └── kustomization.yaml
│       └── overlays/
│           ├── dev/kustomization.yaml
│           ├── staging/kustomization.yaml
│           └── prod/kustomization.yaml
└── argocd/
    ├── appproject-library.yaml
    └── applicationset-library-api.yaml
```
**Por que separar:** (1) **ritmo diferente** — o código muda toda hora; a configuração de produção muda com revisão; (2) **permissões diferentes** — quem escreve código não necessariamente promove para produção; (3) **sem loop de CI** — o CI que **commita a tag** no mesmo repositório do código dispararia o próprio pipeline de novo (se usar um repositório só, filtre por `paths-ignore` e use o `[skip ci]`); (4) **histórico limpo** — o repo GitOps é um registro de **deploys**, sem ruído de código.

O conteúdo de `base/` e `overlays/` é **exatamente** o que `kubernetes` descreve (Deployment com probes, graceful shutdown, `maxUnavailable: 0`, HPA, PDB) — o Argo CD apenas o aplica. Com Helm, o repo guarda o chart ou os `values-*.yaml` (`helm-charts`). **Kustomize é o mais simples** para uma aplicação própria.

---

## 2. Instalação (resumo e cuidados)

```bash
kubectl create namespace argocd
kubectl apply -n argocd --server-side -f https://raw.githubusercontent.com/argoproj/argo-cd/<versão>/manifests/install.yaml
```
(Ou o **Helm chart** oficial do Argo CD. **Fixe uma versão** — nunca `stable`/`latest` num cluster real — e confirme o procedimento atual na documentação; para produção use o manifesto **HA** e gerencie o próprio Argo CD **por GitOps** ("app-of-apps"/bootstrap).)
- O usuário **`admin`** nasce com a senha em `kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d`. **Troque, configure SSO e desative o `admin`**, e apague esse secret.
- Exponha o `argocd-server` por **Ingress/ALB com TLS** (`aws-eks`) **atrás de SSO**, nunca aberto à internet com senha local.
- **Credenciais de repositório** (para ler o `library-gitops` privado): **GitHub App** ou **deploy key somente leitura** registradas como um `Secret` com o label `argocd.argoproj.io/secret-type: repository` — criado **fora do Git** (ou via External Secrets). Nunca um PAT pessoal com escopo amplo.

---

## 3. AppProject — a cerca de segurança

O **AppProject** limita **de onde** um grupo de aplicações pode ler, **para onde** pode implantar e **o que** pode criar. É o principal controle de blast radius.

```yaml
apiVersion: argoproj.io/v1alpha1
kind: AppProject
metadata:
  name: library
  namespace: argocd
spec:
  description: Library services
  sourceRepos:
    - https://github.com/minha-org/library-gitops.git
  destinations:
    - server: https://kubernetes.default.svc
      namespace: library-*
  clusterResourceWhitelist:
    - group: ""
      kind: Namespace
  namespaceResourceBlacklist:
    - group: ""
      kind: ResourceQuota
    - group: ""
      kind: LimitRange
```
- **`sourceRepos`** e **`destinations`** restritos ao necessário — o projeto `library` **não** consegue implantar em `kube-system` nem ler repositórios arbitrários.
- **`clusterResourceWhitelist`**: só recursos de cluster permitidos (aqui `Namespace`, para `CreateNamespace=true`). **Vazio = nenhum recurso de escopo de cluster** (sem `ClusterRole` etc.) — o certo para aplicações de produto. **Nunca use o projeto `default`** (ele permite tudo): sempre um projeto por time/produto.
- Pode definir **roles** do projeto e janelas de sync (`syncWindows`: ex.: negar sync automático de produção fora do horário comercial).

## 4. Application

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: library-api-prod
  namespace: argocd
spec:
  project: library
  source:
    repoURL: https://github.com/minha-org/library-gitops.git
    targetRevision: main
    path: apps/library-api/overlays/prod
  destination:
    server: https://kubernetes.default.svc
    namespace: library-prod
  syncPolicy:
    syncOptions:
      - CreateNamespace=true
      - ServerSideApply=true
    retry:
      limit: 5
      backoff:
        duration: 10s
        factor: 2
        maxDuration: 3m
  ignoreDifferences:
    - group: apps
      kind: Deployment
      jsonPointers:
        - /spec/replicas
```
- **`path`** aponta o overlay do ambiente; **`targetRevision`**: `main` (ou uma tag/branch). Para produção, **`main` + revisão por PR** é o padrão.
- **`ignoreDifferences` em `/spec/replicas`**: o **HPA** altera as réplicas em runtime; sem isso o Argo CD marcaria `OutOfSync` o tempo todo e (com `selfHeal`) **brigaria com o HPA**. Remova também `replicas` do Deployment (`kubernetes`).
- **`ServerSideApply=true`** reduz conflitos de campos gerenciados por outros controladores (HPA, mutating webhooks) e evita o limite de tamanho da annotation do *client-side apply*.
- **`retry`** reaplica após falhas transitórias (webhook/CRD ainda não pronto).

### Sync automático: quando sim, quando não

```yaml
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```
| Opção | Efeito | Cuidado |
|---|---|---|
| `automated` | Aplica sozinho qualquer mudança que entra no Git | Em produção, **o merge do PR é o deploy** — é o controle |
| **`prune: true`** | **Apaga** do cluster o que **foi removido do Git** | Remover um manifesto por engano **apaga o recurso (e dados de um PVC!)**. Proteja o que tem estado com a annotation `argocd.argoproj.io/sync-options: Prune=false` |
| **`selfHeal: true`** | **Desfaz** mudanças manuais no cluster (drift) | Ótimo para disciplina GitOps; **atrapalha depuração** (um `kubectl edit` de emergência é revertido). Para investigar, pause o sync (`argocd app set --sync-policy none`) conscientemente |

**Recomendação:** `automated + prune + selfHeal` em **dev e staging**; em **produção**, ou o mesmo **com aprovação obrigatória no PR** (branch protection + reviewers) **ou** `automated` desligado e o **sync manual** após o merge (um botão/`argocd app sync`), conforme a cultura de risco. Use **`syncWindows`** para travar deploys fora do horário. **Não** use `Replace=true`/`--force` como hábito — recria recursos e causa downtime.

**Finalizer** (`resources-finalizer.argocd.argoproj.io`) faz **apagar a Application apagar todos os recursos dela** no cluster. É útil em dev; **em produção, não o adicione** (apagar a Application por engano derrubaria o serviço).

---

## 5. ApplicationSet — um template, vários ambientes

Em vez de uma Application por ambiente copiada à mão, o **ApplicationSet** gera as Applications a partir de uma lista/diretórios/clusters:

```yaml
apiVersion: argoproj.io/v1alpha1
kind: ApplicationSet
metadata:
  name: library-api
  namespace: argocd
spec:
  goTemplate: true
  generators:
    - list:
        elements:
          - env: dev
            auto: "true"
          - env: staging
            auto: "true"
          - env: prod
            auto: "false"
  template:
    metadata:
      name: 'library-api-{{ .env }}'
    spec:
      project: library
      source:
        repoURL: https://github.com/minha-org/library-gitops.git
        targetRevision: main
        path: 'apps/library-api/overlays/{{ .env }}'
      destination:
        server: https://kubernetes.default.svc
        namespace: 'library-{{ .env }}'
      syncPolicy:
        syncOptions:
          - CreateNamespace=true
          - ServerSideApply=true
```
- **Gerador `git directories`** (`apps/*/overlays/*`) cria uma Application **automaticamente** para cada diretório novo — adicionar um serviço = adicionar uma pasta. **Gerador `clusters`** replica para cada cluster registrado (multi-cluster/multi-região).
- Como `automated` é por ambiente e o `syncPolicy.automated` não aceita condicional simples no template, a abordagem comum é **dois ApplicationSets** (um para dev/staging com `automated`, outro para prod sem) ou usar `templatePatch`. Mantenha **prod com política própria**.
- A forma de template depende de `goTemplate` (`{{ .env }}` com Go template; `{{env}}` no modo padrão antigo) — confirme na versão instalada.
- **App-of-apps** (uma Application que aponta para uma pasta de Applications) é o padrão para **bootstrap** do próprio cluster (Argo CD, ingress controller, External Secrets, monitoring).

---

## 6. Migrations (Flyway) com hooks e sync waves

O Argo CD aplica os recursos **em ondas** (sync waves) e executa **hooks** em fases (`PreSync`, `Sync`, `PostSync`). A migration longa do Flyway (`flyway-migrations`, `kubernetes`) é um **PreSync hook**: roda **antes** de os pods novos subirem e, **se falhar, o sync para** — a versão nova nunca chega a subir contra um schema quebrado.

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: library-api-migrate
  annotations:
    argocd.argoproj.io/hook: PreSync
    argocd.argoproj.io/hook-delete-policy: BeforeHookCreation
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/library-api:1.4.2
          envFrom:
            - secretRef:
                name: library-api-secret
```
- **`BeforeHookCreation`**: apaga o Job da execução anterior antes de criar o novo — como o nome do Job é fixo, não colide. (`HookSucceeded` apaga ao terminar; deixe `BeforeHookCreation` para conseguir **ler os logs** da última execução.)
- A **imagem do Job é a mesma tag** do Deployment: o `images:` do Kustomize (`kustomize edit set image`) atualiza **os dois** de uma vez (`kubernetes`, seção Kustomize).
- A migration continua precisando ser **compatível com a versão anterior** (expand → contract): durante o rolling update as duas versões convivem (`flyway-migrations`). **Um rollback do Git não desfaz a migration.**
- **Ordem entre fases:** os hooks `PreSync` rodam **antes de todos os recursos comuns** da Application, e as *sync waves* só ordenam recursos **dentro da mesma fase** — não atravessam fases. Logo, o Secret que o Job usa (`library-api-secret`) **não pode** ser um recurso comum da mesma Application (ainda não existiria quando o `PreSync` roda; o primeiro deploy falharia por secret ausente). Resolva de um destes modos: (a) o `ExternalSecret` fica em **outra Application anterior** (por exemplo a de infraestrutura/bootstrap do namespace, com `sync-wave` menor no app-of-apps); (b) o próprio `ExternalSecret` também é marcado como **hook `PreSync`** com `sync-wave` **menor** que o do Job (dentro da fase `PreSync`, as waves valem). Em deploys seguintes o Secret já existe e o problema some — **teste o primeiro deploy num namespace novo**.

**Sync waves** ordenam recursos comuns (números menores primeiro; padrão `0`):
```yaml
metadata:
  annotations:
    argocd.argoproj.io/sync-wave: "-1"   # ex.: ExternalSecret/ConfigMap antes do Deployment
```
Uma ordem típica: **`-2`** namespace/ExternalSecret → **hook PreSync** (migration) → **`0`** Deployment/Service/HPA → **`1`** Ingress. O Argo CD **espera cada onda ficar *Healthy*** antes de passar à próxima.

---

## 7. Do commit ao cluster: CI atualiza o repositório GitOps

Substitua o job de deploy "`kubectl apply`" do `github-actions-aws` por um job que **só escreve a nova tag no Git**:

```yaml
  promote-dev:
    needs: image
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          repository: minha-org/library-gitops
          token: ${{ secrets.GITOPS_REPO_TOKEN }}
      - name: Set the image tag
        run: |
          cd apps/library-api/overlays/dev
          kustomize edit set image library-api=${{ needs.image.outputs.image }}
      - name: Commit and push
        run: |
          git config user.name "ci-bot"
          git config user.email "ci-bot@example.com"
          git commit -am "deploy(dev): library-api ${{ github.sha }}"
          git push
```
- A tag é o **`github.sha`** (imutável, rastreável — `aws-eks`). O **token** para escrever no repo GitOps é um **GitHub App** ou fine-grained token **restrito àquele repositório** (escrita só no que precisa), guardado em *secrets* — **o CI não tem acesso ao cluster**.
- **Promoção entre ambientes:** **dev** — o CI commita direto (deploy automático). **staging** — job seguinte, depois dos testes de fumaça passarem. **prod** — o CI **abre um pull request** no repo GitOps (`gh pr create` / action de PR) alterando o overlay `prod`; **o merge, com revisão obrigatória, é o gate de produção** (branch protection + reviewers/CODEOWNERS no repositório GitOps). Assim a mesma imagem testada em dev/staging é a que vai para prod.
- **Argo CD Image Updater** automatiza a atualização da tag observando o registry, mas muda o fluxo de auditoria ("quem decidiu esse deploy?" fica menos explícito) e adiciona um componente — **o job de CI acima é mais transparente**; avalie o Image Updater só se a equipe preferir.
- **Esperar o resultado no pipeline** (opcional): com o `argocd` CLI e um token de uma *service account* de baixo privilégio, `argocd app wait library-api-dev --health --timeout 300` faz o job falhar se o deploy não ficar saudável. Alternativa sem dar acesso do CI ao Argo CD: **notificações** (seção 10) avisam o time.
- **Mudança de configuração** (um limite, uma variável de ambiente) é um PR no repo GitOps, **sem build** — o mesmo fluxo.

### Rollback

O rollback correto é **`git revert`** do commit que trocou a tag (ou da mudança de config) → PR → merge → o Argo CD reaplica a versão anterior. O Git continua verdadeiro. O botão **"Rollback" da UI / `argocd app rollback`** só funciona com o **auto-sync desligado**, e deixa o cluster **diferente do Git** — use apenas como emergência e **registre a reversão no Git logo depois**. Lembre: **migrations não revertem** (`flyway-migrations`).

---

## 8. Segredos em GitOps

**Nunca** comite um `Secret` do Kubernetes (base64 **não** é criptografia). Opções (`kubernetes`, `aws-rds-secrets-manager`):
1. **External Secrets Operator** (recomendado na AWS): o `ExternalSecret` — que contém só **referências** ao Secrets Manager/Parameter Store — **vai para o Git**; o operador cria o `Secret` no cluster. O **valor nunca está no Git**; a rotação é propagada.
2. **Sealed Secrets**: o segredo é **cifrado com a chave pública do cluster** e o `SealedSecret` cifrado **pode** ir para o Git; só o controller do cluster decifra.
3. **SOPS + KSOPS/age/KMS**: arquivos cifrados no Git, decifrados na renderização.
O **`argocd-initial-admin-secret`** e as credenciais de repositório do próprio Argo CD também são segredos: gerencie-os pelo mesmo mecanismo ou fora do Git.

---

## 9. Segurança do próprio Argo CD

O Argo CD tem **poder de escrita no cluster** (e, com multi-cluster, em vários) — **comprometê-lo é comprometer tudo**. Trate-o como infraestrutura crítica:
- **SSO (OIDC)** e **desative o `admin` local**. Com Cognito (`aws-cognito`) ou o IdP corporativo, configure `oidc.config` e mapeie **grupos → roles**.
- **RBAC** (`argocd-rbac-cm`, política em CSV) de **menor privilégio**: desenvolvedores `get`/`sync` só nas **suas** aplicações; `override`/`delete` restritos:
```
p, role:library-dev, applications, get,  library/*, allow
p, role:library-dev, applications, sync, library/*-dev, allow
p, role:library-admin, applications, *, library/*, allow
g, library-developers, role:library-dev
g, library-leads, role:library-admin
```
- **AppProject** por time/produto (seção 3); **nunca** o `default`.
- **Ingress com TLS + SSO**; restrinja a origem (WAF/CIDR). **Atualize** o Argo CD regularmente (tem CVEs publicados) e **fixe** a versão.
- **Repositório GitOps protegido:** *branch protection* na `main` (PR obrigatório, reviewers, status checks), `CODEOWNERS` para `overlays/prod`, **commits assinados** se a política exigir — **quem escreve no repo GitOps controla o cluster**.
- Desative recursos que você não usa (`exec` na UI), **NetworkPolicy** no namespace `argocd`, e **audite** os acessos.
- **Cluster alvo:** o Argo CD usa uma *service account* do cluster (in-cluster) ou credencial do cluster remoto (`argocd cluster add`); em EKS use **IAM** em vez de tokens de longa duração (`aws-eks`) — e restrinja o que ele pode criar (AppProject).

---

## 10. Observabilidade, notificações e progressive delivery

- **Saúde:** o Argo CD avalia **Healthy/Progressing/Degraded** a partir dos recursos (Deployment *available*, pods *ready* — as **readiness probes** de `observability`/`kubernetes` é que dizem se a versão nova está saudável). Probes erradas = Argo "Healthy" enquanto o app falha, ou preso em *Progressing*.
- **Métricas Prometheus** do Argo CD (`argocd_app_info`, `argocd_app_sync_total`): alarme em `sync status = OutOfSync` por tempo > X e `health_status = Degraded` (`aws-observability`).
- **Argo CD Notifications:** avise o time no Slack/e-mail quando um sync **falha**, a app fica **Degraded** ou um deploy de **produção** conclui — o canal de feedback do GitOps (principalmente se o CI não espera o resultado).
- **Argo Rollouts** (controlador separado) troca o `Deployment` por um **`Rollout`** com **canary/blue-green** e **análise automática** (consulta métricas do Prometheus — taxa de erro 5xx e latência do `http.server.requests`, `observability`) e **aborta/reverte sozinho** se a nova versão degrada:
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Rollout
spec:
  strategy:
    canary:
      steps:
        - setWeight: 10
        - pause: { duration: 5m }
        - setWeight: 50
        - pause: { duration: 5m }
```
Pesos reais de tráfego exigem um *traffic router* (ALB controller, NGINX, Istio); sem ele o canary é aproximado por proporção de réplicas. **Adote só com necessidade** — o rolling update com `maxUnavailable: 0`, probes e circuit breaker já resolve a maioria dos casos (`kubernetes`).

---

## 11. Validação antes do merge (shift-left)

O repositório GitOps também passa por **CI**, para que um YAML ruim não chegue ao cluster:
```bash
kustomize build apps/library-api/overlays/prod | kubeconform -strict -summary
kustomize build apps/library-api/overlays/prod | trivy config --severity HIGH,CRITICAL -
helm template library chart/library-api -f values-prod.yaml | kubeconform -strict
argocd app diff library-api-prod --local apps/library-api/overlays/prod
```
- **`kubeconform`** valida o YAML contra os schemas do Kubernetes; **Trivy/kube-linter** pegam má configuração (root, sem limits, `latest`); **políticas** (Kyverno/OPA Conftest) impõem regras: "imagem só do nosso ECR", "sem `latest`", "Pod não-root", "toda aplicação tem probes".
- O **PR do repo GitOps mostra o diff dos manifests renderizados** — a revisão lê o efeito real (o `code-reviewer` aplica o checklist: tag fixa, `requests/limits`, probes, secrets fora do Git).

---

## 12. Troubleshooting

```bash
argocd login argocd.example.com --sso
argocd app list
argocd app get library-api-prod
argocd app diff library-api-prod
argocd app sync library-api-prod --dry-run
argocd app history library-api-prod
kubectl -n argocd logs deploy/argocd-repo-server
kubectl -n argocd logs statefulset/argocd-application-controller
```
| Sintoma | Causa provável | Ação |
|---|---|---|
| **`OutOfSync` permanente** sem mudança | Campo alterado por outro controlador (HPA → `replicas`, webhook injetando sidecar, defaults do API server) | `ignoreDifferences`, `ServerSideApply=true`, remover `replicas` do Deployment com HPA |
| **`ComparisonError` / `rpc error`** | Repo inacessível (credencial), path/overlay inexistente, erro de `kustomize build`/`helm template` | Logs do **repo-server**; rode `kustomize build` localmente |
| **`Progressing` preso** | Deployment não fica *ready* (readiness falhando, imagem não puxa, falta secret) | `kubectl describe pod`/`logs` (`kubernetes`, tabela de status de pod) |
| **`Degraded`** | Pod em `CrashLoopBackOff`, Job de hook falhou | Logs do pod/Job; o **PreSync da migration falhou** → corrija e re-sincronize |
| **Sync falha por hook** | Job de migration falhou (SQL, permissão, secret ausente) | Logs do Job; migration compatível; segredo existente |
| **Recurso "sumiu" depois de um sync** | `prune: true` removeu algo apagado do Git | Restaure no Git; proteja com `Prune=false`; revise PRs de remoção |
| **Mudou no cluster e voltou** | `selfHeal: true` desfez a edição manual | Faça a mudança **pelo Git**; para depurar, pause o sync conscientemente |
| **Aplicou mas o pod não reiniciou** | ConfigMap mudou e o Deployment não | `checksum/config` (Helm — `helm-charts`) ou Kustomize `configMapGenerator` (hash no nome) |
| **App órfã não deleta** | Finalizer travado por recurso | Verifique o recurso pendente; remover o finalizer é último recurso |

---

## Regras principais

- **Git é a fonte da verdade; o cluster puxa.** CI constrói e **escreve a tag no Git**; só o Argo CD toca o cluster — **sem credenciais do cluster no CI**.
- **Dois repositórios** (aplicação × GitOps); overlays por ambiente (Kustomize) ou chart (`helm-charts`); tag de imagem **imutável (`github.sha`)**, nunca `latest`.
- **AppProject por time**, nunca o `default`: `sourceRepos`/`destinations` mínimos, sem recursos de cluster além do necessário.
- `automated` + `prune` + `selfHeal` em dev/staging; **produção com PR aprovado como gate** (ou sync manual) e `syncWindows`; **sem finalizer em prod**; `Prune=false` no que guarda dados; `Replace`/`--force` não é hábito.
- `ignoreDifferences` em `/spec/replicas` com HPA; `ServerSideApply=true`.
- **Migration do Flyway = `PreSync` hook** (mesma tag, `BeforeHookCreation`), compatível com a versão anterior; **sync waves** para ordem; rollback do Git **não** reverte o banco.
- **Rollback por `git revert`**; rollback da UI só em emergência e com registro posterior no Git.
- **Segredos nunca no Git**: External Secrets (referências no Git) / Sealed Secrets / SOPS.
- **Proteja o Argo CD**: SSO, `admin` desativado, RBAC mínimo, Ingress TLS, versão fixa e atualizada, **branch protection + CODEOWNERS** no repo GitOps (quem escreve lá controla o cluster).
- Valide o repo GitOps no CI (`kubeconform`, Trivy, políticas); notificações em sync falho/Degraded; Argo Rollouts só com necessidade clara.
- **Sem Lombok** — deliberado.
