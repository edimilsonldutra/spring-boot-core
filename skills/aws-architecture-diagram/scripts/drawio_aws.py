"""Gera diagramas de arquitetura AWS no formato do draw.io (diagrams.net).

Uso: escreva um script curto que importa este módulo, declara grupos, ícones e
setas com coordenadas ABSOLUTAS na página e chama save(). O módulo converte as
coordenadas para relativas ao grupo pai (o que o draw.io exige em containers
aninhados), valida as referências e, se o draw.io desktop estiver instalado,
exporta o PNG para conferência visual.

    import sys; sys.path.insert(0, "<pasta desta skill>/scripts")
    from drawio_aws import Diagram

    d = Diagram("Renovação de empréstimo - AWS")
    d.group("cloud", "1", "AWS Cloud", 140, 20, 1440, 900, "cloud")
    d.service("sqs", "cloud", "SQS loan-renewed", 1250, 320, "sqs")
    d.edge("e1", "loan", "sqs", "publica LoanRenewed", points=[(885, 160), (1280, 160)])
    d.save("docs/architecture/renovacao-aws.drawio", png=True)
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import quoteattr

# Cores por categoria da paleta oficial da AWS (ícones de 2023 em diante).
COLORS = {
    "compute": "#ED7100",      # EC2, Lambda, ECS, EKS, Fargate, ECR, Batch
    "database": "#C925D1",     # RDS, Aurora, DynamoDB, ElastiCache, Keyspaces
    "storage": "#7AA116",      # S3, EFS, EBS, Backup
    "network": "#8C4FFF",      # VPC, ELB, CloudFront, Route 53, API Gateway
    "integration": "#E7157B",  # SQS, SNS, EventBridge, Step Functions, MQ
    "management": "#E7157B",   # CloudWatch, Systems Manager, CloudFormation
    "security": "#DD344C",     # Cognito, IAM, KMS, Secrets Manager, WAF
    "analytics": "#8C4FFF",    # Kinesis, Athena, OpenSearch
    "neutral": "#232F3E",      # usuários, clientes, internet
}

# Serviço (resIcon de mxgraph.aws4.resourceIcon) -> categoria. Só ícones verificados
# exportando pelo draw.io; um nome errado vira um quadrado colorido sem desenho.
SERVICES = {
    "lambda": "compute", "ec2": "compute", "ecs": "compute", "eks": "compute",
    "fargate": "compute", "ecr": "compute", "batch": "compute",
    "rds": "database", "aurora": "database", "dynamodb": "database",
    "elasticache": "database", "keyspaces": "database",
    "s3": "storage", "elastic_file_system": "storage", "backup": "storage",
    "cloudfront": "network", "route_53": "network", "api_gateway": "network",
    "elastic_load_balancing": "network", "vpc": "network",
    "sqs": "integration", "sns": "integration", "eventbridge": "integration",
    "step_functions": "integration", "mq": "integration",
    "cloudwatch_2": "management", "systems_manager": "management",
    "cloudformation": "management", "xray": "management",
    "cognito": "security", "identity_and_access_management": "security",
    "key_management_service": "security", "secrets_manager": "security",
    "waf": "security", "shield": "security", "certificate_manager_3": "security",
    "kinesis": "analytics", "athena": "analytics",
    "elasticsearch_service": "analytics",  # ícone do Amazon OpenSearch Service
}

# Recursos (shape direto de mxgraph.aws4, sem o quadrado de fundo).
RESOURCES = {
    "users": "neutral", "user": "neutral", "client": "neutral", "mobile_client": "neutral",
    "internet": "neutral",
    "application_load_balancer": "network", "network_load_balancer": "network",
    "nat_gateway": "network", "internet_gateway": "network", "endpoints": "network",
    "ecs_service": "compute", "ecs_task": "compute", "lambda_function": "compute",
    "bucket": "storage", "queue": "integration", "topic": "integration",
}

_GROUP_BASE = (
    "points=[[0,0],[0.25,0],[0.5,0],[0.75,0],[1,0],[1,0.25],[1,0.5],[1,0.75],[1,1],[0.75,1],[0.5,1],[0.25,1],"
    "[0,1],[0,0.75],[0,0.5],[0,0.25]];outlineConnect=0;gradientColor=none;html=1;whiteSpace=wrap;fontSize=12;"
    "fontStyle=0;container=1;pointerEvents=0;collapsible=0;recursiveResize=0;shape=mxgraph.aws4.group;"
    "verticalAlign=top;align=left;spacingLeft=30;"
)
GROUPS = {
    "cloud": _GROUP_BASE + "dashed=0;grIcon=mxgraph.aws4.group_aws_cloud_alt;strokeColor=#232F3E;fillColor=none;fontColor=#232F3E;",
    "account": _GROUP_BASE + "dashed=0;grIcon=mxgraph.aws4.group_account;strokeColor=#CD2264;fillColor=none;fontColor=#CD2264;",
    "region": _GROUP_BASE + "dashed=1;grIcon=mxgraph.aws4.group_region;strokeColor=#00A4A6;fillColor=none;fontColor=#147EBA;",
    "vpc": _GROUP_BASE + "dashed=0;grIcon=mxgraph.aws4.group_vpc2;strokeColor=#8C4FFF;fillColor=none;fontColor=#AAB7B8;",
    "public": _GROUP_BASE + "dashed=0;grIcon=mxgraph.aws4.group_security_group;grStroke=0;strokeColor=#7AA116;fillColor=#F2F6E8;fontColor=#248814;",
    "private": _GROUP_BASE + "dashed=0;grIcon=mxgraph.aws4.group_security_group;grStroke=0;strokeColor=#00A4A6;fillColor=#E6F6F7;fontColor=#147EBA;",
    "asg": _GROUP_BASE + "dashed=1;grIcon=mxgraph.aws4.group_auto_scaling_group;strokeColor=#ED7100;fillColor=none;fontColor=#ED7100;",
    "datacenter": _GROUP_BASE + "dashed=0;grIcon=mxgraph.aws4.group_corporate_data_center;strokeColor=#7D8998;fillColor=none;fontColor=#5A6C86;",
    "az": "fillColor=none;strokeColor=#147EBA;dashed=1;verticalAlign=top;align=left;spacingLeft=10;fontStyle=0;"
          "fontColor=#147EBA;html=1;container=1;collapsible=0;recursiveResize=0;",
    "generic": "fillColor=none;strokeColor=#5A6C86;dashed=1;verticalAlign=top;align=left;spacingLeft=10;fontStyle=0;"
               "fontColor=#5A6C86;html=1;container=1;collapsible=0;recursiveResize=0;",
}

# Sem whiteSpace=wrap: o rótulo só quebra onde houver <br>, nunca na largura do ícone.
_ICON = ("sketch=0;outlineConnect=0;fontColor=#232F3E;gradientColor=none;dashed=0;verticalLabelPosition=bottom;"
         "verticalAlign=top;align=center;html=1;fontSize=12;fontStyle=0;aspect=fixed;")
LABEL_RIGHT = "verticalLabelPosition=middle;labelPosition=right;align=left;spacingLeft=6;"
LABEL_LEFT = "verticalLabelPosition=middle;labelPosition=left;align=right;spacingRight=6;"


class Diagram:
    def __init__(self, name: str, page_width: int = 1650, page_height: int = 950):
        self.name = name
        self.page = (page_width, page_height)
        self.cells: list[str] = []
        self.origin = {"1": (0, 0)}
        self.ids = {"0", "1"}

    def _vertex(self, id, parent, label, style, x, y, w, h, container=False):
        if id in self.ids:
            raise ValueError(f"id repetido: {id}")
        if parent not in self.origin:
            raise ValueError(f"{id}: o pai '{parent}' não é um grupo declarado antes")
        px, py = self.origin[parent]
        self.cells.append(
            f'<mxCell id="{id}" value={quoteattr(label)} style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{x - px}" y="{y - py}" width="{w}" height="{h}" as="geometry"/></mxCell>')
        self.ids.add(id)
        if container:
            self.origin[id] = (x, y)

    def group(self, id, parent, label, x, y, w, h, kind):
        """Grupo AWS: cloud, account, region, vpc, az, public, private, asg, datacenter, generic."""
        self._vertex(id, parent, label, GROUPS[kind], x, y, w, h, container=True)

    def service(self, id, parent, label, x, y, icon, size=60, style=""):
        """Ícone de serviço (quadrado colorido da categoria), ex.: icon="sqs"."""
        color = COLORS[SERVICES[icon]]
        full = _ICON + f"strokeColor=#ffffff;fillColor={color};shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.{icon};" + style
        self._vertex(id, parent, label, full, x, y, size, size)

    def resource(self, id, parent, label, x, y, icon, size=60, style=""):
        """Ícone de recurso (só o desenho, sem fundo), ex.: icon="nat_gateway"."""
        color = COLORS[RESOURCES[icon]]
        full = _ICON + f"strokeColor=none;pointerEvents=1;fillColor={color};shape=mxgraph.aws4.{icon};" + style
        self._vertex(id, parent, label, full, x, y, size, size)

    def note(self, id, parent, text, x, y, w, h):
        style = "text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;fontSize=11;fontColor=#545B64;"
        self._vertex(id, parent, text, style, x, y, w, h)

    def edge(self, id, src, dst, label="", points=(), dashed=False, exit=None, entry=None, label_pos=0.0, both=False):
        """Seta ortogonal. points: dobras em coordenadas absolutas. exit/entry: (x, y) de 0 a 1 na borda.
        label_pos: -1 (perto da origem) a 1 (perto do destino)."""
        style = ("edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;"
                 "endFill=1;strokeColor=#545B64;fontSize=11;labelBackgroundColor=#FFFFFF;")
        if dashed:
            style += "dashed=1;"
        if both:
            style += "startArrow=block;startFill=1;"
        if exit:
            style += f"exitX={exit[0]};exitY={exit[1]};exitDx=0;exitDy=0;"
        if entry:
            style += f"entryX={entry[0]};entryY={entry[1]};entryDx=0;entryDy=0;"
        pts = "".join(f'<mxPoint x="{x}" y="{y}"/>' for x, y in points)
        geom = (f'<mxGeometry x="{label_pos}" relative="1" as="geometry">'
                + (f'<Array as="points">{pts}</Array>' if pts else "") + '<mxPoint as="offset"/></mxGeometry>')
        self.cells.append(f'<mxCell id="{id}" value={quoteattr(label)} style="{style}" edge="1" parent="1" '
                          f'source="{src}" target="{dst}">{geom}</mxCell>')
        self.ids.add(id)

    def xml(self) -> str:
        w, h = self.page
        return ('<mxfile host="app.diagrams.net" type="device">\n'
                f'  <diagram id="d1" name={quoteattr(self.name)}>\n'
                f'    <mxGraphModel dx="{w}" dy="{h}" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" '
                f'arrows="1" fold="1" page="1" pageScale="1" pageWidth="{w}" pageHeight="{h}" math="0" shadow="0">\n'
                '      <root>\n        <mxCell id="0"/>\n        <mxCell id="1" parent="0"/>\n        '
                + "\n        ".join(self.cells)
                + '\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n')

    def save(self, path, png=False, scale=1.5):
        """Grava o .drawio, valida as referências e, com png=True, exporta <path>.png pelo draw.io desktop."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.xml(), encoding="utf-8")
        problems = validate(path)
        if problems:
            raise SystemExit("referências quebradas: " + ", ".join(problems))
        print(f"{path}: {len(self.cells)} elementos, referências OK")
        if png:
            out = export_png(path, scale=scale)
            print(f"{out}: exportado" if out else "draw.io desktop não encontrado: PNG não exportado (sem conferência visual)")
        return path


def validate(path) -> list[str]:
    cells = ET.parse(path).getroot().findall(".//mxCell")
    ids = {c.get("id") for c in cells}
    return [f"{c.get('id')}.{k}={c.get(k)}" for c in cells
            for k in ("parent", "source", "target") if c.get(k) and c.get(k) not in ids]


def drawio_executable() -> str | None:
    found = shutil.which("drawio") or shutil.which("draw.io")
    if found:
        return found
    candidates = {
        "Windows": [os.path.expandvars(r"%ProgramFiles%\draw.io\draw.io.exe"),
                    os.path.expandvars(r"%LOCALAPPDATA%\Programs\draw.io\draw.io.exe")],
        "Darwin": ["/Applications/draw.io.app/Contents/MacOS/draw.io"],
        "Linux": ["/opt/drawio/drawio", "/usr/bin/drawio", "/snap/bin/drawio"],
    }.get(platform.system(), [])
    return next((c for c in candidates if os.path.exists(c)), None)


def export_png(path, scale=1.5, border=20) -> Path | None:
    exe = drawio_executable()
    if not exe:
        return None
    path = Path(path)
    out = path.with_suffix(".png")
    cmd = [exe, "--export", "--format", "png", "--scale", str(scale), "--border", str(border), "--output", str(out), str(path)]
    if platform.system() == "Linux" and not os.environ.get("DISPLAY") and shutil.which("xvfb-run"):
        cmd = ["xvfb-run", "--auto-servernum", *cmd, "--no-sandbox"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120, check=False)
    return out if out.exists() else None


if __name__ == "__main__":
    for arg in sys.argv[1:]:
        problems = validate(arg)
        print(f"{arg}: {'OK' if not problems else 'quebrado: ' + ', '.join(problems)}")
        out = export_png(arg)
        print(f"  png: {out or 'draw.io desktop não encontrado'}")
