---
name: aws-eks
description: Spring Boot no Amazon EKS — ECR (tags imutáveis, scan, lifecycle), cluster com eksctl, IRSA/Pod Identity em vez de access keys, AWS Load Balancer Controller com ALB Ingress, logs e métricas, rede, segurança e custos. Use quando preparar cluster, registry, permissões de pod ou exposição via ALB na AWS.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md) e [`../kubernetes/SKILL.md`](../kubernetes/SKILL.md): os manifests da aplicação são os de lá; esta skill cobre o que é **específico da AWS**. A automação de build/deploy está em `github-actions-aws`.

# AWS EKS

Fluxo: código → **imagem no ECR** → **cluster EKS** roda a imagem → **ALB** expõe → a aplicação acessa **RDS/Secrets Manager/S3/SQS** com permissões IAM *do pod* (nunca chaves).

> Valores como `123456789012`, `us-east-1` e nomes de cluster abaixo são exemplos; use os reais. Resolva versões atuais (Kubernetes, add-ons, controller) na documentação da AWS — elas mudam a cada poucos meses.

---

## 1. ECR — o registry

```bash
aws ecr create-repository \
  --repository-name library-api \
  --image-scanning-configuration scanOnPush=true \
  --image-tag-mutability IMMUTABLE \
  --encryption-configuration encryptionType=KMS
```
- **`IMMUTABLE`**: uma tag (`1.4.2`) nunca é sobrescrita — o que está rodando é rastreável e o rollback é determinístico. Combina com a regra "nunca `latest`" de `kubernetes`.
- **`scanOnPush`**: o ECR escaneia vulnerabilidades a cada push; falhe o pipeline em vulnerabilidade crítica (`aws ecr describe-image-scan-findings`). Para escaneamento contínuo, habilite o Amazon Inspector.
- **Lifecycle policy**: sem ela o repositório acumula imagens para sempre (e você paga o armazenamento):
```json
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep the last 30 images",
      "selection": { "tagStatus": "any", "countType": "imageCountMoreThan", "countNumber": 30 },
      "action": { "type": "expire" }
    }
  ]
}
```
`aws ecr put-lifecycle-policy --repository-name library-api --lifecycle-policy-text file://lifecycle.json`.

Login e push (o CI faz isso — `github-actions-aws`):
```bash
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789012.dkr.ecr.us-east-1.amazonaws.com
docker build -t 123456789012.dkr.ecr.us-east-1.amazonaws.com/library-api:1.4.2 .
docker push 123456789012.dkr.ecr.us-east-1.amazonaws.com/library-api:1.4.2
```
Os nodes do EKS puxam do ECR da mesma conta sem configuração (a role do node já tem `AmazonEC2ContainerRegistryReadOnly`). Para outra conta, adicione uma repository policy.

---

## 2. Cluster EKS (eksctl)

Para aprender e para clusters simples, o `eksctl` descreve tudo em um arquivo versionável. Em organizações maiores o mesmo cluster é declarado em **Terraform/CDK** — a arquitetura abaixo é a mesma.

```yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: library
  region: us-east-1
  version: "1.33"
iam:
  withOIDC: true
vpc:
  nat:
    gateway: HighlyAvailable
managedNodeGroups:
  - name: general
    instanceType: m6i.large
    minSize: 3
    maxSize: 6
    desiredCapacity: 3
    privateNetworking: true
    volumeSize: 50
addons:
  - name: vpc-cni
  - name: coredns
  - name: kube-proxy
  - name: aws-ebs-csi-driver
```
`eksctl create cluster -f cluster.yaml` (leva ~15–20 min). **Escolha a versão do Kubernetes suportada pelo EKS naquele momento**; o `1.33` acima é só exemplo.

- **`privateNetworking: true`**: os nodes ficam em subnets **privadas** (sem IP público); só o ALB está nas públicas.
- **Multi-AZ**: o `HighlyAvailable` NAT e os nodes espalhados em 3 zonas — combine com `topologySpreadConstraints` (veja `kubernetes`).
- **`withOIDC: true`** cria o OIDC provider do cluster, pré-requisito do IRSA (abaixo).
- **Managed node groups** cuidam de patch/atualização do AMI dos nodes. Para escalar nodes automaticamente conforme os pods, use **Karpenter** (ou o Cluster Autoscaler) — o HPA escala pods, não nodes.
- **Fargate** (pods sem node para gerenciar) é uma alternativa para workloads pequenos; custa mais por vCPU e não suporta DaemonSets. **Se você não precisa de Kubernetes**, containers sem cluster para operar (ECS + Fargate) são mais simples: veja `aws-ecs-fargate`; infraestrutura como código em `aws-terraform`; logs/métricas/alarmes em `aws-observability`.
- Mantenha o cluster e os add-ons **atualizados**: o EKS retira versões antigas do suporte padrão e passa a cobrar suporte estendido.

Acesso ao cluster:
```bash
aws eks update-kubeconfig --name library --region us-east-1
kubectl get nodes
```
Quem pode usar o `kubectl` é controlado por **EKS access entries** (`aws eks create-access-entry` + `associate-access-policy`), que substituem o antigo ConfigMap `aws-auth`. Dê às pessoas e ao pipeline o **menor** papel que resolve (view/edit por namespace; admin do cluster só para o time de plataforma).

---

## 3. Permissões da aplicação: IRSA / Pod Identity (nunca access keys)

A aplicação acessa S3, SQS, Secrets Manager. **Nunca** coloque `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` em ConfigMap, Secret, imagem ou código — chaves de longa duração vazam e não expiram. O pod recebe **credenciais temporárias** de uma IAM Role; o AWS SDK (e o Spring Cloud AWS, veja `aws-s3-sqs`) as encontra sozinho pela *default credentials provider chain*.

**IRSA** (IAM Roles for Service Accounts):
```bash
eksctl create iamserviceaccount \
  --cluster library --namespace library --name library-api \
  --attach-policy-arn arn:aws:iam::123456789012:policy/library-api-policy \
  --approve
```
Isso cria a role (com trust policy no OIDC do cluster, restrita àquela ServiceAccount) e a ServiceAccount anotada:
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: library-api
  namespace: library
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/library-api-role
```
No Deployment: `spec.template.spec.serviceAccountName: library-api`. Sem isso, o pod usa a role do **node** — permissões demais, compartilhadas por todo pod do node.

**EKS Pod Identity** é o mecanismo mais novo (sem OIDC por cluster; associação feita com `aws eks create-pod-identity-association`, agente `eks-pod-identity-agent`). Para projetos novos, avalie-o; o resultado para a aplicação é o mesmo: credenciais temporárias, nenhuma chave.

**Menor privilégio**: a policy lista só as ações e **ARNs** necessários.
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:PutObject"],
      "Resource": "arn:aws:s3:::library-uploads/*"
    },
    {
      "Effect": "Allow",
      "Action": ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes", "sqs:GetQueueUrl"],
      "Resource": "arn:aws:sqs:us-east-1:123456789012:library-events"
    }
  ]
}
```
Nunca `"Action": "*"` ou `"Resource": "*"`.

---

## 4. Expor com o ALB (AWS Load Balancer Controller)

Instale o **AWS Load Balancer Controller** (Helm, com a IAM role dele via IRSA — siga a documentação atual da AWS). Depois, um `Ingress` com `ingressClassName: alb` cria um Application Load Balancer:

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: library-api
  namespace: library
  annotations:
    alb.ingress.kubernetes.io/scheme: internet-facing
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/listen-ports: '[{"HTTPS":443}]'
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-east-1:123456789012:certificate/xxxx
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS13-1-2-2021-06
    alb.ingress.kubernetes.io/healthcheck-path: /actuator/health/readiness
    alb.ingress.kubernetes.io/healthcheck-port: "9090"
    alb.ingress.kubernetes.io/ssl-redirect: "443"
spec:
  ingressClassName: alb
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
- **`target-type: ip`**: o ALB envia direto ao IP do pod (sem hop pelo NodePort).
- **Health check do ALB** na readiness do Actuator (que está na porta de management, 9090): o ALB só envia tráfego a pods *ready*. Se o Service não expõe a 9090, ajuste `healthcheck-port` para a porta que expõe a readiness, ou exponha só essa porta no Service.
- **TLS** com certificado do **ACM** (gratuito, renovação automática); redirecione HTTP→HTTPS. O DNS (`api.example.com`) é um registro Route 53 apontando para o ALB — automatize com o **ExternalDNS**.
- **WAF** (AWS WAF associado ao ALB) para proteção contra OWASP Top 10 e rate limiting.
- Para um ALB **interno** (APIs privadas entre serviços), `scheme: internal`.
- Ingress de vários serviços no mesmo ALB: `alb.ingress.kubernetes.io/group.name: shared` (economiza o custo de um ALB por aplicação).

---

## 5. Logs, métricas e traces

- **Logs:** a aplicação escreve JSON no stdout (`observability`); um agente (**Fluent Bit** DaemonSet, ou o add-on **Amazon CloudWatch Observability**) envia para o **CloudWatch Logs**. Defina **retenção** no log group (por exemplo 30 dias) — o default é "nunca expirar" e vira custo.
- **Métricas:** Prometheus (self-managed ou **Amazon Managed Service for Prometheus**) raspando `/actuator/prometheus` na 9090 + **Amazon Managed Grafana**; ou Container Insights do CloudWatch.
- **Traces:** OpenTelemetry → **AWS Distro for OpenTelemetry** collector → **X-Ray**.
- Alarmes essenciais: pods em `CrashLoopBackOff`, 5xx do ALB (`HTTPCode_Target_5XX_Count`), latência `TargetResponseTime`, CPU/memória de nodes, conexões do RDS.

---

## 6. Rede e segurança

- **Security groups**: o RDS aceita conexão **somente** do security group dos nodes/pods (veja `aws-rds-secrets-manager`) — nunca `0.0.0.0/0`.
- **NetworkPolicy** (com o VPC CNI com suporte habilitado): comece com *deny all* por namespace e libere só o necessário (ingress do ALB, egress para o RDS e DNS).
- **Endpoint do API server** privado, ou público restrito por CIDR (`--public-access-cidrs`).
- **Secrets** cifrados com KMS (`--secrets-encryption`); credenciais de aplicação em **Secrets Manager** (`aws-rds-secrets-manager`).
- **Pod Security Standards** `restricted` no namespace (label `pod-security.kubernetes.io/enforce: restricted`) — o Deployment de `kubernetes` já atende.
- **VPC endpoints** (S3 gateway; ECR, Secrets Manager, STS interface) evitam tráfego pela NAT e deixam clusters privados funcionarem — e reduzem o custo de NAT.

## 7. Custos (onde o dinheiro vai)

- O **control plane** do EKS tem custo fixo por cluster/hora; NAT gateways, ALBs, volumes EBS e transferência entre AZs costumam pesar mais que a instância.
- Dimensione `requests` com dados reais (`kubectl top`, Container Insights): `requests` inflados = nodes ociosos pagos.
- **Spot** para workloads tolerantes a interrupção (managed node group `spot: true`, várias instance types); on-demand/Savings Plans para o baseline.
- Desligue clusters de dev fora do horário; **tags** de custo (`Project`, `Env`) em tudo; **lifecycle** no ECR e retenção nos logs.
- Um ALB compartilhado por `group.name` em vez de um por serviço.

---

## Operação

```bash
aws eks list-clusters --region us-east-1
aws eks update-kubeconfig --name library --region us-east-1
kubectl -n library get pods,svc,ingress
kubectl -n library get ingress library-api -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
aws eks describe-cluster --name library --query 'cluster.version'
eksctl get iamserviceaccount --cluster library
```
Pod sem credenciais AWS (`Unable to load credentials` / `AccessDenied`): confira `serviceAccountName` no Deployment, a anotação `role-arn` e a trust policy da role (namespace + nome da ServiceAccount exatos).

---

## Regras principais

- ECR: tags **imutáveis**, `scanOnPush`, lifecycle policy; nunca `latest`.
- Nodes em subnets privadas, multi-AZ; só o ALB é público; mantenha cluster e add-ons atualizados.
- **Nunca access keys**: IRSA ou Pod Identity, uma ServiceAccount por aplicação, policy com **menor privilégio** (ações e ARNs explícitos).
- ALB com `target-type: ip`, TLS do ACM, health check na readiness do Actuator, WAF quando público.
- Logs JSON no stdout → CloudWatch **com retenção**; métricas Prometheus; traces OTLP.
- RDS acessível só pelo security group do cluster; NetworkPolicy; secrets cifrados com KMS.
- Tags de custo, `requests` dimensionados por dados reais, ALB compartilhado, Spot onde cabe.
