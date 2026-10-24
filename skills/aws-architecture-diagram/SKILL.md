---
name: aws-architecture-diagram
description: Diagrama de arquitetura AWS no padrão draw.io (diagrams.net) com os ícones e grupos oficiais — AWS Cloud, conta, região, VPC, Availability Zones, subnets públicas e privadas — gerado por script com coordenadas absolutas, setas com protocolo, exportado em PNG pelo draw.io desktop e conferido visualmente antes da entrega. Traz a biblioteca drawio_aws.py com o catálogo de ícones verificados, regras de layout, checklist visual e um exemplo completo (ECS Fargate, RDS Multi-AZ, SQS, Cognito). Use quando precisar desenhar ou atualizar a visão de infraestrutura AWS de um sistema, para design doc, ADR, threat model, onboarding ou revisão de rede. Não use para fluxo, sequência, estados ou componentes lógicos (Mermaid, design-docs) nem para declarar a infraestrutura (aws-terraform).
---

Antes de aplicar este pattern, leia também [`../design-docs/SKILL.md`](../design-docs/SKILL.md) (seção 9: quando cada diagrama, e o mesmo nome para a mesma fronteira em todos os documentos), [`../aws-terraform/SKILL.md`](../aws-terraform/SKILL.md) (a infraestrutura real, que o diagrama tem que refletir) e [`../repository-understanding/SKILL.md`](../repository-understanding/SKILL.md) (desenhar só o que foi verificado). Conforme o desenho: `aws-ecs-fargate`, `aws-eks`, `aws-lambda`, `aws-rds-secrets-manager`, `aws-sns-sqs`, `aws-cognito`, `threat-modeling`.

# Diagrama de arquitetura AWS (draw.io)

O **Mermaid** é o padrão do time para diagramas em documentos (`design-docs` §9): renderiza no GitHub e o diff é revisável. Ele não desenha bem a **visão física da AWS**, com conta, região, VPC, AZs, subnets e os ícones oficiais, que é a linguagem que plataforma, segurança e auditoria esperam. Para essa visão, use o **draw.io**: o arquivo `.drawio` é XML, abre no draw.io desktop, no [app.diagrams.net](https://app.diagrams.net) e na extensão do VS Code, e continua editável por qualquer pessoa.

| Pergunta | Ferramenta |
|---|---|
| Onde cada peça roda na AWS: conta, região, VPC, AZ, subnet, o que é público | **draw.io** (esta skill) |
| Quem chama quem, em que ordem, caminho de erro | Mermaid `sequenceDiagram` |
| Componentes lógicos e fronteiras de confiança de uma feature | Mermaid `flowchart` com `subgraph` |
| Estados de uma entidade, tabelas e relações | Mermaid `stateDiagram-v2`, `erDiagram` |
| Declarar ou mudar a infraestrutura | `aws-terraform` (o diagrama descreve, não cria) |

## 1. Onde fica e o que se versiona

```
docs/architecture/
├── <sistema>-aws.drawio     ← a fonte, editável no draw.io
└── <sistema>-aws.png        ← exportado; é o que o README, o design doc e o PR mostram
```
- O **`.drawio` é a fonte de verdade** depois que existe. O script de geração serve para a **primeira versão** e para mudanças grandes de layout. Se alguém editou o arquivo no draw.io, **não regenere por cima**: edite o `.drawio` (no draw.io ou no XML) e exporte de novo.
- Linke o PNG no documento que o usa (`![Infraestrutura AWS](../architecture/renovacao-aws.png)`) e cite o `.drawio` ao lado, para quem for editar.
- **Sem dados sensíveis:** nada de ID de conta, ARN completo, IP público, hostname interno, nome de bucket com dado pessoal ou segredo. CIDR de VPC e de subnet pode, porque é desenho de rede, não credencial.
- Gravar em `docs/` é escrita de documento: o `architect` grava **com confirmação**, como o design doc.

## 2. Fluxo de trabalho

1. **Levante o que existe, não o que você imagina.** Leia o Terraform (`infra/`), os manifests, as task definitions e o `application.yml`. O que for **inferido** entra no diagrama marcado como tal ("(a confirmar)"). Diagrama que desenha uma subnet que não existe engana a revisão de segurança.
2. **Planeje a grade antes do XML** (seção 4): colunas, onde cada grupo começa e termina, por qual vão cada seta passa.
3. **Escreva um script curto** que importa a biblioteca e declara grupos, ícones e setas com coordenadas **absolutas**:
   ```python
   import sys
   sys.path.insert(0, r"<pasta desta skill>/scripts")   # no plugin: ${CLAUDE_PLUGIN_ROOT}/skills/aws-architecture-diagram/scripts
   from drawio_aws import Diagram, LABEL_RIGHT

   d = Diagram("Renovação de empréstimo - AWS")
   d.group("cloud", "1", "AWS Cloud", 140, 20, 1440, 900, "cloud")
   d.group("region", "cloud", "Region sa-east-1 (São Paulo)", 160, 60, 1400, 840, "region")
   d.service("sqs", "region", "SQS loan-renewed", 1250, 320, "sqs")
   ...
   d.save("docs/architecture/renovacao-aws.drawio", png=True)
   ```
   Rode o script **fora do repositório** (no scratchpad ou em `target/`) enquanto itera, e só grave em `docs/architecture/` a versão conferida. O exemplo completo está em [`scripts/example_renovacao.py`](scripts/example_renovacao.py).
4. **`save()` valida** que todo pai, origem e destino existe e, com o draw.io desktop instalado, **exporta o PNG** ao lado.
5. **Olhe o PNG** (leia a imagem) e passe o checklist da seção 6. Esta etapa não é opcional: XML válido não garante desenho legível. Na primeira versão do exemplo desta skill, o XML estava correto e mesmo assim os rótulos quebravam letra a letra e três setas passavam por cima de ícones.
6. Corrija as coordenadas ou as dobras e exporte de novo até o checklist passar.
7. **Sem draw.io desktop**, entregue o `.drawio` dizendo que **não houve conferência visual** e peça que alguém abra e confira. Nunca diga que o desenho está bom sem ter visto o PNG.

## 3. Biblioteca `scripts/drawio_aws.py`

| Método | Para |
|---|---|
| `Diagram(nome, largura, altura)` | Uma página; o nome vira a aba do draw.io |
| `group(id, pai, rótulo, x, y, w, h, tipo)` | Container. Tipos: `cloud`, `account`, `region`, `vpc`, `az`, `public`, `private`, `asg`, `datacenter`, `generic` |
| `service(id, pai, rótulo, x, y, ícone)` | Ícone de **serviço** (quadrado na cor da categoria), 60×60 |
| `resource(id, pai, rótulo, x, y, ícone)` | Ícone de **recurso** (só o traço): usuários, ALB, NAT, task, bucket, fila |
| `edge(id, origem, destino, rótulo, points=…, exit=…, entry=…, dashed=…, label_pos=…)` | Seta ortogonal. `points` são as dobras (absolutas); `exit`/`entry` escolhem o ponto da borda (0 a 1); `label_pos` vai de -1 (perto da origem) a 1 (perto do destino) |
| `note(id, pai, texto, x, y, w, h)` | Texto explicativo, como "acessa por VPC endpoints" |
| `save(caminho, png=True)` | Grava, valida e exporta |
| `python drawio_aws.py arquivo.drawio` | Valida e exporta um `.drawio` já existente (depois de edição manual) |

Detalhes que a biblioteca já resolve:
- **Coordenadas absolutas.** O draw.io guarda a posição de cada elemento **relativa ao grupo pai**. Calcular isso à mão em cinco níveis de aninhamento é a fonte número um de ícone fora do lugar. A biblioteca converte, e por isso **o pai precisa ser declarado antes dos filhos**.
- **Rótulo sem quebra automática.** O rótulo só quebra onde houver `<br>`. Com a quebra automática do draw.io, o texto cabe nos 60 px do ícone e sai "loan-/service/(ECS/Fargate)".
- **Cor por categoria**, tirada do catálogo (seção 5); você não escolhe cor.
- `LABEL_RIGHT` e `LABEL_LEFT` (passados em `style=`) põem o rótulo ao lado do ícone, quando embaixo ele cruzaria uma seta ou um título.

## 4. Layout

**Grade de colunas** (da esquerda para a direita, o caminho da requisição):
```
| quem usa | borda (Route 53, CloudFront, WAF, Cognito) | VPC: AZs empilhadas | serviços regionais (SQS, SNS, S3, Secrets, ECR, CloudWatch) | notas |
```
- **Aninhamento fixo:** AWS Cloud → (conta) → Region → VPC → Availability Zone → subnet. Serviço regional, sem ENI na VPC (SQS, SNS, S3, DynamoDB, Secrets Manager, ECR, CloudWatch, Cognito), fica **dentro da região e fora da VPC**. Desenhá-lo dentro da VPC está errado e induz a revisão de rede a erro.
- **AZs empilhadas na vertical**, com as mesmas subnets na mesma posição: pública | privada (app) | privada (dados). A AZ b repete a AZ a com rótulo "(réplica)" e **sem repetir as setas**; uma nota diz que as réplicas fazem o mesmo.
- **Load balancer no vão entre as AZs**, com o rótulo ao lado (`LABEL_RIGHT`). Ele é um recurso multi-AZ: desenhá-lo dentro de uma AZ só sugere ponto único de falha. No código, o pai dele é a VPC (`d.resource("alb", "vpc", ...)`), e no texto ele não entra na lista de conteúdo de nenhuma subnet: escrever "pública (ALB, NAT)" contradiz o desenho. O rótulo diz onde estão os nós ("nós nas subnets públicas").
- **Folga de 30 px entre grupos irmãos** e de 40 px no topo de cada grupo (o título ocupa ~20 px). Esses vãos são os **corredores das setas**.
- **Ícone nunca a menos de ~110 px do vizinho na horizontal** (o rótulo de duas linhas tem ~140 px), e o rótulo de baixo precisa de ~40 px livres.
- **Títulos de grupo alinhados à esquerda**, como a biblioteca já faz; seta vertical não passa na faixa do título.

**Setas:**
- **Uma seta, um caminho.** Se duas setas dividiriam o mesmo trecho, desvie uma por um corredor (`points`).
- Seta **com verbo e protocolo**: `HTTPS 443`, `JDBC 5432`, `publica LoanRenewed (outbox)`, `consome (idempotente)`. Seta sem rótulo só para o óbvio (fila → DLQ pode levar "após 5 tentativas").
- **Contínua** para requisição e dado; **tracejada** para controle e assíncrono secundário (validação de JWT, replicação, leitura de segredo).
- Saída e entrada nos lados que **apontam para o destino** (`exit`/`entry`); alinhar o centro de origem e destino na mesma linha elimina dobras.
- Não desenhe a seta de todo task para CloudWatch, ECR e Secrets Manager: uma nota ("as tasks acessam por VPC endpoints") vale mais que seis linhas cruzando o desenho.

**Tamanho:** até **~25 ícones por página**. Passou disso, divida em páginas no mesmo arquivo (visão geral, rede, dados, deploy), cada uma com o seu `Diagram`, ou em arquivos distintos.

## 5. Catálogo de ícones verificados

Todos os nomes abaixo foram exportados pelo draw.io e conferidos. Um nome errado **não dá erro**: vira um quadrado colorido sem desenho (foi o caso de `x_ray` e `opensearch_service`; os certos são `xray` e `elasticsearch_service`). Para usar um ícone fora da lista, inclua-o em `SERVICES`/`RESOURCES`, exporte uma folha de teste e confira o PNG antes de usar.

| Categoria (cor) | `service(...)` |
|---|---|
| Compute e containers (laranja) | `lambda`, `ec2`, `ecs`, `eks`, `fargate`, `ecr`, `batch` |
| Banco de dados (roxo) | `rds`, `aurora`, `dynamodb`, `elasticache`, `keyspaces` |
| Armazenamento (verde) | `s3`, `elastic_file_system`, `backup` |
| Rede e borda (violeta) | `cloudfront`, `route_53`, `api_gateway`, `elastic_load_balancing`, `vpc` |
| Integração (rosa) | `sqs`, `sns`, `eventbridge`, `step_functions`, `mq` |
| Gerenciamento (rosa) | `cloudwatch_2`, `systems_manager`, `cloudformation`, `xray` |
| Segurança (vermelho) | `cognito`, `identity_and_access_management`, `key_management_service`, `secrets_manager`, `waf`, `shield`, `certificate_manager_3` |
| Analytics (violeta) | `kinesis`, `athena`, `elasticsearch_service` (OpenSearch) |

| `resource(...)` | Uso |
|---|---|
| `users`, `user`, `client`, `mobile_client`, `internet` | Quem usa, fora da nuvem |
| `application_load_balancer`, `network_load_balancer`, `nat_gateway`, `internet_gateway`, `endpoints` | Peças de rede dentro da VPC |
| `ecs_service`, `ecs_task`, `lambda_function`, `bucket`, `queue`, `topic` | Recurso específico quando o ícone do serviço é genérico demais |

**Regra de nível:** no mesmo diagrama, use o mesmo nível para o mesmo tipo de peça. Ou todos os workloads como serviço (`fargate`), ou todos como recurso (`ecs_task`).

## 6. Checklist visual (no PNG, antes de entregar)

- [ ] Nenhum rótulo quebrado no meio de palavra nem sobreposto a outro rótulo, ícone ou título de grupo.
- [ ] Nenhuma seta atravessa um ícone; setas só se cruzam onde não há outro caminho, e nunca em cima de um rótulo.
- [ ] Todo ícone está dentro do grupo certo: serviço regional fora da VPC, banco na subnet de dados, nada público fora da subnet pública.
- [ ] Toda seta tem verbo e protocolo, ou é óbvia; tracejado só para controle e assíncrono secundário.
- [ ] Nenhum ícone virou quadrado vazio (nome errado).
- [ ] O diagrama bate com o Terraform/código lido no passo 1; o inferido está marcado.
- [ ] A mesma fronteira tem o mesmo nome aqui, no design doc e no threat model.
- [ ] Sem ID de conta, ARN, IP público, hostname interno ou segredo.

## 7. Exportar pelo draw.io desktop

A biblioteca procura o executável sozinha. À mão:

| Sistema | Comando |
|---|---|
| Windows | `"C:\Program Files\draw.io\draw.io.exe" --export --format png --scale 1.5 --border 20 --output x.png x.drawio` |
| macOS | `/Applications/draw.io.app/Contents/MacOS/draw.io --export --format png --scale 1.5 --border 20 --output x.png x.drawio` |
| Linux / CI sem tela | `xvfb-run --auto-servernum drawio --export --format png --scale 1.5 --border 20 --output x.png x.drawio --no-sandbox` |

- Mensagens de erro de **cache da GPU** no Windows (`Unable to create cache`, `Gpu Cache Creation failed`) aparecem quando o draw.io está aberto e **não impedem** a exportação. Confira se o PNG foi gerado.
- `--format svg` gera vetor (bom para documento impresso); `--embed-diagram` (`-e`) com PNG grava o XML dentro da imagem, que reabre editável no draw.io, útil quando só se quer versionar um arquivo.
- No CI, a exportação pode virar um job que regenera o PNG a cada mudança no `.drawio` e falha se o PNG commitado estiver desatualizado.

## 8. Anti-padrões

- **Entregar sem ver o PNG**: o XML válido esconde rótulo cortado, seta sobre ícone e ícone vazio.
- **Diagrama da arquitetura desejada apresentado como a atual**, ou com peças que não existem no Terraform. Marque "proposto" no título quando for desenho futuro.
- **Serviço regional dentro da VPC**, ou banco em subnet pública "porque coube".
- **Seta de tudo para tudo** (CloudWatch, ECR, IAM): uma nota resolve.
- **Ícones de gerações diferentes** misturados (ícones antigos, de 2017 a 2019, ao lado dos atuais) ou cor trocada à mão.
- **Regenerar por cima** de um `.drawio` editado à mão, perdendo o ajuste de outra pessoa.
- **Um diagrama gigante** com 50 ícones: ninguém lê, e cada mudança quebra o layout.
- **PNG desatualizado** em relação ao `.drawio`: exporte de novo sempre que o fonte mudar.

## Regras principais

- draw.io para a visão física da AWS (conta, região, VPC, AZ, subnet, ícones oficiais); Mermaid para fluxo, sequência, estados e componentes lógicos.
- `docs/architecture/<sistema>-aws.drawio` como fonte e `.png` exportado ao lado; depois de editado à mão, o `.drawio` é a verdade e não se regenera por cima.
- Desenhe o que foi verificado no Terraform e no código; inferido marcado; desenho futuro marcado como "proposto".
- Gere com `scripts/drawio_aws.py`, em coordenadas absolutas, pai declarado antes dos filhos, rótulos quebrados só com `<br>`.
- Aninhamento AWS Cloud → Region → VPC → AZ → subnet; serviços regionais dentro da região e fora da VPC; AZs empilhadas com as mesmas subnets; load balancer entre as AZs.
- Uma seta, um caminho, com verbo e protocolo; tracejado para controle; nota no lugar de setas repetitivas; até ~25 ícones por página.
- Só ícones do catálogo verificado; ícone novo passa por folha de teste antes.
- Exporte o PNG e passe o checklist visual antes de entregar; sem draw.io desktop, declare que não houve conferência visual.
- Sem ID de conta, ARN, IP público, hostname interno ou segredo no diagrama; gravação em `docs/` com confirmação.
