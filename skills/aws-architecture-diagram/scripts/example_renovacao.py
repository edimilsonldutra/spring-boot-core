"""Exemplo de referência: renovação de empréstimo em ECS Fargate, RDS Multi-AZ, SQS e Cognito.

Rode: python example_renovacao.py <pasta de saída>
Gera <pasta>/renovacao-emprestimo-aws.drawio e, com o draw.io desktop instalado, o .png ao lado.
Todas as coordenadas são absolutas na página.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from drawio_aws import LABEL_RIGHT, Diagram  # noqa: E402

d = Diagram("Renovação de empréstimo - AWS")

# Containers: de fora para dentro, cada um declarado antes dos filhos.
d.group("cloud", "1", "AWS Cloud", 140, 20, 1440, 900, "cloud")
d.group("region", "cloud", "Region sa-east-1 (São Paulo)", 160, 60, 1400, 840, "region")
d.group("vpc", "region", "VPC 10.0.0.0/16", 360, 100, 800, 780, "vpc")
for suf, top, n in (("a", 140, 1), ("b", 520, 2)):
    d.group(f"az{suf}", "vpc", f"Availability Zone sa-east-1{suf}", 380, top, 760, 340, "az")
    d.group(f"pub{suf}", f"az{suf}", f"Subnet pública 10.0.{n}.0/24", 400, top + 40, 200, 280, "public")
    d.group(f"app{suf}", f"az{suf}", f"Subnet privada (app) 10.0.1{n}.0/24", 630, top + 40, 300, 280, "private")
    d.group(f"dat{suf}", f"az{suf}", f"Subnet privada (dados) 10.0.2{n}.0/24", 960, top + 40, 170, 280, "private")
    d.resource(f"nat{suf}", f"pub{suf}", "NAT Gateway", 475, top + 150, "nat_gateway", size=50)

# Ícones
d.resource("users", "1", "Leitores<br>(app e site)", 40, 470, "users")
d.service("cognito", "region", "Amazon Cognito<br>User Pool", 210, 215, "cognito")
# O ALB fica no vão entre as AZs, com o rótulo ao lado, para as setas subirem e descerem livres.
d.resource("alb", "vpc", "Application Load Balancer<br>(nós nas subnets públicas, HTTPS 443)", 590, 470,
           "application_load_balancer", style=LABEL_RIGHT)
d.service("loana", "appa", "loan-service<br>(ECS Fargate)", 840, 240, "fargate")
d.service("notifa", "appa", "notification-service<br>(ECS Fargate)", 670, 320, "fargate")
d.service("loanb", "appb", "loan-service<br>(réplica)", 840, 620, "fargate")
d.service("notifb", "appb", "notification-service<br>(réplica)", 670, 730, "fargate")
d.service("rdsa", "data", "RDS PostgreSQL<br>(primária)", 1010, 240, "rds")
d.service("rdsb", "datb", "RDS PostgreSQL<br>(standby Multi-AZ)", 1010, 620, "rds")
d.service("sqs", "region", "SQS loan-renewed", 1250, 320, "sqs")
d.service("dlq", "region", "SQS loan-renewed-dlq", 1420, 320, "sqs")
d.service("secrets", "region", "Secrets Manager<br>(credenciais do banco)", 1250, 480, "secrets_manager")
d.service("ecr", "region", "Amazon ECR<br>(imagens)", 1250, 620, "ecr")
d.service("cw", "region", "CloudWatch<br>(logs, métricas, alarmes)", 1250, 760, "cloudwatch_2")
d.note("nota", "region",
       "As tasks nas subnets privadas acessam SQS, Secrets Manager, ECR e CloudWatch por VPC endpoints; "
       "o NAT Gateway fica para saídas externas. As réplicas da AZ b usam a mesma RDS primária.",
       1370, 480, 170, 150)

# Fluxos: cada seta com caminho próprio (dobras explícitas onde cruzaria ícone ou título).
d.edge("e1", "users", "cognito", "login (OAuth 2.0 / OIDC)", points=[(70, 230)], exit=(0.5, 0), entry=(0, 0.25))
d.edge("e2", "users", "alb", "HTTPS + access token (JWT)", exit=(1, 0.5), entry=(0, 0.5))
d.edge("e3", "alb", "loana", "HTTP 8080", points=[(620, 270)], exit=(0.5, 0), entry=(0, 0.5), label_pos=0.5)
d.edge("e4", "alb", "loanb", "HTTP 8080", points=[(620, 650)], exit=(0.5, 1), entry=(0, 0.5), label_pos=0.5)
d.edge("e5", "loana", "rdsa", "JDBC 5432", exit=(1, 0.5), entry=(0, 0.5))
d.edge("e6", "rdsa", "rdsb", "replicação síncrona", points=[(1100, 285), (1100, 635)], dashed=True,
       exit=(1, 0.75), entry=(1, 0.25))
d.edge("e7", "loana", "sqs", "publica LoanRenewed (outbox)", points=[(885, 160), (1280, 160)],
       exit=(0.75, 0), entry=(0.5, 0))
d.edge("e8", "sqs", "notifa", "consome (idempotente)", exit=(0, 0.5), entry=(1, 0.5), label_pos=-0.55)
d.edge("e9", "sqs", "dlq", "após 5 tentativas", exit=(1, 0.5), entry=(0, 0.5))
d.edge("e10", "loana", "cognito", "valida JWT (JWKS)", dashed=True, exit=(0, 0.25), entry=(1, 0.667), label_pos=0.6)

out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
d.save(out_dir / "renovacao-emprestimo-aws.drawio", png=True)
