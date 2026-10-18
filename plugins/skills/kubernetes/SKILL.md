---
name: kubernetes
description: Deploy de Spring Boot no Kubernetes — Deployment com rolling update sem downtime, probes do Actuator, requests/limits, graceful shutdown, securityContext, Service, Ingress, ConfigMap/Secret, HPA, PDB, Kustomize por ambiente, Flyway em Job e troubleshooting com kubectl. Use quando criar manifests ou investigar CrashLoopBackOff, OOMKilled ou pods not ready.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) e [`../code-style/SKILL.md`](../code-style/SKILL.md) para as preferências do projeto e as convenções. Pré-requisitos: uma imagem no registry (`docker-and-docker-compose`) e as probes do Actuator (`observability`).

# Kubernetes

Manifests YAML **declarativos**, versionados no repositório, em `k8s/` (ou um chart — veja `helm-charts`). Nada de `kubectl run`/`edit` em produção: o estado do cluster vem do Git. Comentários seguem a preferência salva (default: sem).

```
k8s/
├── base/
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml
│   └── kustomization.yaml
└── overlays/
    ├── dev/kustomization.yaml
    └── prod/kustomization.yaml
```

---

## Configuração da aplicação para Kubernetes

```yaml
server:
  shutdown: graceful

spring:
  lifecycle:
    timeout-per-shutdown-phase: 30s
  main:
    banner-mode: off

management:
  endpoint:
    health:
      probes:
        enabled: true
  server:
    port: 9090
```
- `server.shutdown: graceful`: ao receber `SIGTERM` o Spring **para de aceitar** requests novas e **termina** as em andamento (até o timeout) antes de encerrar. Sem isso, cada rolling update derruba requests no meio.
- O container deve receber o `SIGTERM` direto: use `ENTRYPOINT ["java", ...]` na forma **exec** (JSON), como em `docker-and-docker-compose`; a forma shell (`ENTRYPOINT java ...`) coloca um `sh` como PID 1 que engole o sinal.

---

## Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: library-api
  namespace: library
  labels:
    app.kubernetes.io/name: library-api
spec:
  replicas: 3
  revisionHistoryLimit: 5
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  selector:
    matchLabels:
      app.kubernetes.io/name: library-api
  template:
    metadata:
      labels:
        app.kubernetes.io/name: library-api
    spec:
      terminationGracePeriodSeconds: 45
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: app
          image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/library-api:1.0.0
          ports:
            - name: http
              containerPort: 8080
            - name: management
              containerPort: 9090
          envFrom:
            - configMapRef:
                name: library-api-config
            - secretRef:
                name: library-api-secret
          env:
            - name: JAVA_TOOL_OPTIONS
              value: "-XX:MaxRAMPercentage=75"
          resources:
            requests:
              cpu: 250m
              memory: 512Mi
            limits:
              memory: 512Mi
          startupProbe:
            httpGet:
              path: /actuator/health/liveness
              port: management
            periodSeconds: 5
            failureThreshold: 30
          livenessProbe:
            httpGet:
              path: /actuator/health/liveness
              port: management
            periodSeconds: 10
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /actuator/health/readiness
              port: management
            periodSeconds: 5
            failureThreshold: 3
          lifecycle:
            preStop:
              exec:
                command: ["sleep", "10"]
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop: ["ALL"]
          volumeMounts:
            - name: tmp
              mountPath: /tmp
      volumes:
        - name: tmp
          emptyDir: {}
```

Por que cada escolha:
- **`maxUnavailable: 0` + `maxSurge: 1`:** o novo pod precisa ficar *ready* antes de um antigo ser removido — zero downtime. Combine com `flyway-migrations` (expand → contract), porque as duas versões convivem.
- **Imagem com tag imutável** (`1.0.0` ou o SHA do commit) — **nunca `latest`**: com `latest` você não sabe o que está rodando e o rollback não é determinístico.
- **Probes** (veja `observability`): a **startup** dá até 30×5 s para a JVM + Flyway subirem *antes* de a liveness começar a contar — sem ela, uma aplicação lenta para iniciar é morta em loop (`CrashLoopBackOff`). **Liveness** só verifica o processo; **readiness** decide o tráfego. Liveness nunca depende de database.
- **`preStop: sleep 10` + `terminationGracePeriodSeconds: 45`:** o Kubernetes tira o pod do Service e manda o `SIGTERM` em paralelo; o `sleep` dá tempo de o load balancer parar de enviar tráfego antes do shutdown começar. A soma `preStop (10) + timeout-per-shutdown-phase (30)` deve caber no `terminationGracePeriodSeconds` (45).
- **Memória: `requests == limits`** e o `MaxRAMPercentage=75`: a JVM calcula o heap a partir do limite do container; estourar o limite é `OOMKilled` (exit 137). Dimensione olhando as metrics reais (`jvm.memory.*`), não adivinhando — veja `jvm-performance`.
- **CPU: defina `requests`, evite `limits` de CPU** na maioria dos casos: o limite causa *throttling* (a JVM e o GC ficam lentos, a latência p99 explode, principalmente no startup). Se a plataforma exigir limit, seja generoso.
- **`readOnlyRootFilesystem` + `emptyDir` em `/tmp`:** a JVM e o Tomcat escrevem em `/tmp`; o resto do filesystem fica imutável — uma invasão não consegue gravar binários.
- **`runAsNonRoot`**, `drop: ALL` e `seccompProfile: RuntimeDefault`: o baseline de segurança *Pod Security Standards "restricted"*.

---

## Service e Ingress

```yaml
apiVersion: v1
kind: Service
metadata:
  name: library-api
  namespace: library
spec:
  selector:
    app.kubernetes.io/name: library-api
  ports:
    - name: http
      port: 80
      targetPort: http
```
Tipo `ClusterIP` (default): só acessível dentro do cluster. Para fora, use um **Ingress**:
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: library-api
  namespace: library
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.example.com
      secretName: library-api-tls
  rules:
    - host: api.example.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: library-api
                port:
                  name: http
```
Na AWS o `ingressClassName` é `alb` e as annotations são outras — veja `aws-eks`. A porta de management (9090) **não** entra no Service/Ingress: só o kubelet e o Prometheus chegam nela.

---

## ConfigMap e Secret

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: library-api-config
  namespace: library
data:
  SPRING_PROFILES_ACTIVE: prod
  SPRING_DATASOURCE_URL: jdbc:mysql://mysql.library.svc:3306/library_api
  CORS_ORIGINPATTERNS: https://app.example.com
```
- O Spring faz *relaxed binding* de variável de ambiente: `SPRING_DATASOURCE_URL` → `spring.datasource.url`; `CORS_ORIGINPATTERNS` → `cors.originPatterns`. O `application.yml` é o mesmo em todo ambiente.
- Dados **não sensíveis** no ConfigMap; **sensíveis** no Secret (`SPRING_DATASOURCE_PASSWORD`, `JWT_SECRET`).

**Secret nunca vai para o Git em texto/base64** — base64 não é criptografia. Opções, da melhor para a mais simples: **External Secrets Operator** sincronizando do AWS Secrets Manager (veja `aws-rds-secrets-manager`), **Sealed Secrets** (versiona o secret cifrado), ou `kubectl create secret` aplicado fora do Git por quem tem permissão:
```bash
kubectl -n library create secret generic library-api-secret \
  --from-literal=SPRING_DATASOURCE_PASSWORD='...' \
  --from-literal=JWT_SECRET="$(openssl rand -base64 48)"
```
Habilite a criptografia de secrets em repouso no cluster (KMS) e aplique RBAC mínimo para quem lê `secrets`.

---

## Escala e disponibilidade

**HPA** (`autoscaling/v2`) escala pelo uso de CPU em relação ao `request`:
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: library-api
  namespace: library
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: library-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```
Requer o `metrics-server` e `resources.requests.cpu` definido. Com HPA, **remova `replicas`** do Deployment (ou o `kubectl apply` brigará com o HPA). Cuidado: cada réplica abre seu próprio pool de conexões — `maxReplicas × maximumPoolSize` não pode passar o limite de conexões do database (veja `jvm-performance`).

**PodDisruptionBudget** garante que manutenção do cluster (drain de node) nunca derrube todas as réplicas:
```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: library-api
  namespace: library
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app.kubernetes.io/name: library-api
```
Para alta disponibilidade, espalhe as réplicas entre zonas: `topologySpreadConstraints` com `topologyKey: topology.kubernetes.io/zone` e `whenUnsatisfiable: ScheduleAnyway`.

---

## Migrations do Flyway

Com várias réplicas subindo juntas, o Flyway serializa por lock (seguro), mas uma migration longa deixa o pod *not ready* e pode estourar o `startupProbe`. Para migrations pesadas, rode-as em um **Job** antes do deploy (e `spring.flyway.enabled=false` no Deployment):
```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: library-api-migrate-1-0-0
  namespace: library
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: migrate
          image: 123456789012.dkr.ecr.us-east-1.amazonaws.com/library-api:1.0.0
          envFrom:
            - secretRef:
                name: library-api-secret
```
(com uma imagem/entrypoint que só executa o Flyway e sai, ou o Flyway CLI). Para migrations rápidas o Flyway no startup é suficiente.

---

## Kustomize (um conjunto de manifests, vários ambientes)

`base/kustomization.yaml` lista os recursos; cada overlay muda só o que difere:
```yaml
resources:
  - ../../base
namespace: library-prod
images:
  - name: 123456789012.dkr.ecr.us-east-1.amazonaws.com/library-api
    newTag: 1.0.0
replicas:
  - name: library-api
    count: 5
patches:
  - path: resources-patch.yaml
```
`kubectl apply -k k8s/overlays/prod`. O CI atualiza só o `newTag` (`kustomize edit set image`) a cada release. Para parametrização mais rica, ou distribuir o app como pacote, veja `helm-charts`. Para entregar **por GitOps** (o cluster **puxa** do Git em vez de o CI rodar `kubectl apply`), veja `argocd`.

---

## Operação e troubleshooting

```bash
kubectl apply -k k8s/overlays/prod
kubectl -n library rollout status deployment/library-api --timeout=300s
kubectl -n library rollout undo deployment/library-api
kubectl -n library get pods -l app.kubernetes.io/name=library-api
kubectl -n library logs deploy/library-api --tail=200 -f
kubectl -n library describe pod <pod>
kubectl -n library top pod
kubectl -n library port-forward deploy/library-api 8080:8080
kubectl -n library get events --sort-by=.lastTimestamp
```
Diagnóstico pelo status do pod:

| Status | Causa provável | Onde olhar |
|---|---|---|
| `ImagePullBackOff` | tag errada, registry privado sem credencial/permissão | `describe pod` → Events |
| `CrashLoopBackOff` | a aplicação cai ao subir (config/secret ausente, Flyway falhou) ou a liveness mata uma app lenta | `logs --previous` e o `startupProbe` |
| `OOMKilled` (exit 137) | limite de memória baixo para o heap | `describe pod` → Last State; `jvm-performance` |
| `Running` mas `0/1 Ready` | readiness falhando (database fora, porta/path errados) | `describe pod` → Readiness probe failed |
| `Pending` | sem capacidade/node, `requests` altos demais, PVC não ligado | `describe pod` → Events |
| `Evicted` | node sem memória/disco | `kubectl describe node` |

---

## Regras principais

- Tudo declarativo e no Git; tag de imagem **imutável**, nunca `latest`.
- `startupProbe` + `liveness` (só processo) + `readiness` (tráfego); Actuator em porta separada; liveness nunca depende de database.
- `server.shutdown: graceful`, `preStop sleep`, e `terminationGracePeriodSeconds` > soma dos dois; `ENTRYPOINT` em forma exec.
- Rolling update com `maxUnavailable: 0`; migrations compatíveis com as duas versões (expand → contract).
- Memória `requests == limits` com `MaxRAMPercentage`; CPU com `requests`, evitando `limits`.
- Pod seguro: não-root, `readOnlyRootFilesystem`, `drop ALL`, `RuntimeDefault`; `emptyDir` em `/tmp`.
- Config por variável de ambiente (relaxed binding); secrets **fora do Git** (External Secrets/Sealed Secrets).
- HPA + PDB + `topologySpreadConstraints` para escala e disponibilidade; some `maxReplicas × pool` ≤ conexões do database.
- Um overlay por ambiente (Kustomize) ou um chart (`helm-charts`).
