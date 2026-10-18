---
name: helm-charts
description: Helm para Spring Boot — estrutura do chart, values por ambiente, templates com helpers, checksum de ConfigMap, secrets fora do chart, lint/template/diff no CI, upgrade --atomic, rollback e Helm × Kustomize. Use quando empacotar a aplicação como chart ou depurar um release Helm.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) e [`../code-style/SKILL.md`](../code-style/SKILL.md), e a skill [`../kubernetes/SKILL.md`](../kubernetes/SKILL.md): o chart é a **mesma** configuração do Deployment/Service/probes de lá, só parametrizada.

# Helm charts

**Helm ou Kustomize?** Kustomize (em `kubernetes`) basta quando você tem *uma* aplicação e poucos ambientes: patches simples, sem linguagem de template. Escolha Helm quando precisa de **muita parametrização**, de **versionar e distribuir** a aplicação como pacote (chart em registry OCI), de **rollback com histórico de releases**, ou quando consome charts de terceiros (ingress-nginx, External Secrets, Prometheus). Não misture os dois para a mesma aplicação.

## Estrutura

```
chart/library-api/
├── Chart.yaml
├── values.yaml
├── values-dev.yaml
├── values-prod.yaml
└── templates/
    ├── _helpers.tpl
    ├── deployment.yaml
    ├── service.yaml
    ├── ingress.yaml
    ├── configmap.yaml
    ├── hpa.yaml
    ├── pdb.yaml
    └── NOTES.txt
```

**Chart.yaml**
```yaml
apiVersion: v2
name: library-api
description: Library REST API
type: application
version: 0.1.0
appVersion: "1.0.0"
```
`version` é a versão do **chart** (muda quando os templates mudam); `appVersion` é a versão da **aplicação** (a tag da imagem). O CI incrementa ambas conscientemente.

## values.yaml (defaults seguros, tudo parametrizável)

```yaml
replicaCount: 3

image:
  repository: 123456789012.dkr.ecr.us-east-1.amazonaws.com/library-api
  tag: ""
  pullPolicy: IfNotPresent

service:
  port: 80

ingress:
  enabled: false
  className: nginx
  host: api.example.com

resources:
  requests:
    cpu: 250m
    memory: 512Mi
  limits:
    memory: 512Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

config:
  SPRING_PROFILES_ACTIVE: prod

existingSecret: library-api-secret
```
`image.tag` vazio significa "use o `appVersion`" (veja o template). **Não há senha, token nem chave em nenhum `values*.yaml`** — eles ficam no Git. O Secret é referenciado por nome (`existingSecret`) e criado fora do chart (External Secrets/Sealed Secrets — veja `kubernetes` e `aws-rds-secrets-manager`).

`values-prod.yaml` sobrescreve só o que difere: `replicaCount`, `resources`, `ingress.enabled: true`, `config.*`.

## templates/_helpers.tpl

```yaml
{{- define "library-api.fullname" -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "library-api.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "library-api.selectorLabels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}
```
Os `selectorLabels` do Deployment **não podem mudar** depois da primeira instalação (o selector é imutável) — por isso são só `name` e `instance`, sem versão.

## templates/deployment.yaml (trecho)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "library-api.fullname" . }}
  labels:
    {{- include "library-api.labels" . | nindent 4 }}
spec:
  {{- if not .Values.autoscaling.enabled }}
  replicas: {{ .Values.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "library-api.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
      labels:
        {{- include "library-api.selectorLabels" . | nindent 8 }}
    spec:
      containers:
        - name: app
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          imagePullPolicy: {{ .Values.image.pullPolicy }}
          envFrom:
            - configMapRef:
                name: {{ include "library-api.fullname" . }}
            - secretRef:
                name: {{ .Values.existingSecret }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
```
O restante (probes, `securityContext`, `lifecycle`, volumes) é copiado do Deployment de `kubernetes`, sem mudança. Pontos específicos do Helm:
- **`checksum/config`**: o Kubernetes **não** reinicia pods quando um ConfigMap muda. A annotation com o hash do ConfigMap muda junto, o que altera o *pod template* e dispara o rolling update.
- **`replicas` omitido quando o HPA está ligado**, para o Helm não brigar com o autoscaler a cada upgrade.
- `nindent`/`toYaml` mantêm a indentação do YAML; erro de indentação é a causa nº 1 de template quebrado.

## Fluxo de trabalho

```bash
helm lint chart/library-api -f chart/library-api/values-prod.yaml
helm template library chart/library-api -f chart/library-api/values-prod.yaml
helm upgrade --install library chart/library-api \
  --namespace library --create-namespace \
  -f chart/library-api/values-prod.yaml \
  --set image.tag=1.4.2 \
  --atomic --wait --timeout 5m
helm history library -n library
helm rollback library 3 -n library
```
- **`helm lint` e `helm template` no CI** a cada pull request: pegam erro de template sem tocar o cluster. Valide o YAML renderizado com `kubeconform`/`kubectl apply --dry-run=server`.
- **`--atomic --wait`**: o upgrade espera os pods ficarem *ready* e, se falhar (probe, timeout), faz **rollback automático** para a release anterior.
- **`helm diff upgrade`** (plugin `helm-diff`) mostra o que mudaria antes de aplicar — use no pipeline de produção.
- `--set image.tag=<git sha ou versão>` vem do CI; nunca fixe a tag no `values.yaml`.
- Um rollback do Helm reverte os manifests, **não o database**: migrations do Flyway já aplicadas continuam (por isso expand → contract, veja `flyway-migrations`).

## Distribuição

Empacote e publique o chart em um registry OCI (o ECR aceita charts):
```bash
helm package chart/library-api
helm push library-api-0.1.0.tgz oci://123456789012.dkr.ecr.us-east-1.amazonaws.com/charts
```
(`aws ecr get-login-password | helm registry login ...` antes — veja `aws-eks`/`github-actions-aws`.)

## Regras principais

- Helm para muita parametrização/distribuição; Kustomize para o caso simples — não os dois.
- `version` (chart) ≠ `appVersion` (app); a tag da imagem vem de `--set image.tag`, nunca de `latest`.
- **Nenhum segredo nos `values*.yaml`**; Secret referenciado por nome e criado fora do chart.
- `selectorLabels` estáveis (imutáveis); `checksum/config` para reiniciar quando o ConfigMap muda.
- `helm lint` + `helm template` + validação do YAML em todo PR; `upgrade --atomic --wait` em deploy; `helm diff` antes de produção.
- Rollback reverte manifests, não migrations.
- Com GitOps, o Argo CD renderiza o chart/overlay a partir do Git em vez de o CI rodar `helm upgrade` (`argocd`).
