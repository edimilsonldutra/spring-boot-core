---
name: aws-dynamodb
description: Amazon DynamoDB com o Enhanced Client do SDK v2 — modelagem por padrões de acesso (PK, SK, GSI), repository sem Lombok, query × scan, paginação, escrita condicional e optimistic locking, transações, TTL, streams, capacidade, IAM, IaC e testes com LocalStack. Use quando persistir dados em DynamoDB ou revisar um modelo de tabela.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md) e [`../aws-sdk-java/SKILL.md`](../aws-sdk-java/SKILL.md) (credenciais, clients, timeouts, LocalStack — **não repetidos aqui**).

# Amazon DynamoDB

DynamoDB é um banco **NoSQL chave-valor/documento, serverless**, com latência de milissegundos em qualquer escala, replicação Multi-AZ automática e **sem servidores para operar**. A troca: **sem JOINs, sem consultas ad-hoc, sem SQL** — você modela os dados **a partir das consultas** que a aplicação faz. Se você precisa de relatórios flexíveis, transações multi-tabela complexas ou consultas que mudam toda semana, **fique no relacional** (`aws-rds-secrets-manager`, `spring-data-jpa`). DynamoDB brilha em: carga imprevisível e enorme, acesso por chave, sessão/carrinho/perfil, eventos, catálogos com padrões de acesso conhecidos.

> **Não use "Spring Data DynamoDB" (derjust).** É um projeto comunitário sem manutenção que não acompanha o SDK v2/Boot atual. Use o **DynamoDB Enhanced Client** (SDK v2) ou o `DynamoDbTemplate` do Spring Cloud AWS.

## Dependencies

SDK puro:
```xml
<dependency>
    <groupId>software.amazon.awssdk</groupId>
    <artifactId>dynamodb-enhanced</artifactId>
</dependency>
```
Ou Spring Cloud AWS (configura `DynamoDbClient`/`DynamoDbEnhancedClient` e oferece `DynamoDbTemplate`):
```xml
<dependency>
    <groupId>io.awspring.cloud</groupId>
    <artifactId>spring-cloud-aws-starter-dynamodb</artifactId>
</dependency>
```
Versão pelo BOM correto (`aws-sdk-java`: Spring Cloud AWS na linha compatível com o Boot do projeto).

---

## 1. Modelagem — comece pelos padrões de acesso

**Regra nº 1:** liste **todas as consultas** ("buscar livro por id", "livros de um autor, mais novos primeiro", "últimos 20 pedidos de um cliente") **antes** de desenhar a tabela. Cada padrão de acesso precisa ser atendido por uma **chave** (da tabela ou de um índice).

| Conceito | O que é |
|---|---|
| **Partition key (PK)** | Define **onde** o item mora (hash). Todo acesso eficiente informa a PK. |
| **Sort key (SK)** | Opcional; ordena itens **dentro** da mesma PK e permite *range queries* (`begins_with`, `between`, `>`). |
| **Query** | Lê itens de **uma** PK (com condição na SK). Eficiente e barata. |
| **Scan** | Lê a **tabela inteira**. Caro e lento; **evite** em produção (só em tabelas pequenas, jobs/ETL). |
| **GSI** (Global Secondary Index) | PK/SK **alternativas** para outro padrão de acesso; replicação **eventualmente consistente**, consome capacidade própria. |
| **LSI** | SK alternativa na **mesma** PK; só na criação da tabela; raramente vale. |

**Escolha da PK — o que mais importa:**
- Alta **cardinalidade** e acesso **uniforme**: `bookId` (UUID), `customerId`, `tenantId#orderId`. Evite PK de **baixa cardinalidade ou sequencial/temporal** (`status`, `date`, id autoincremento): gera **hot partition** (uma partição recebe quase todo o tráfego e sofre *throttling* mesmo com capacidade sobrando).
- Um item (incl. atributos) tem **no máximo 400 KB**; uma partição suporta ~3.000 RCU / 1.000 WCU por segundo por chave. Chave "quente" (um único id muito acessado) → distribua (sufixo de *shard*) ou cache (`caching`, DAX).

**Single-table vs multi-table.** Single-table design (várias entidades na mesma tabela com `PK`/`SK` genéricos tipo `CUSTOMER#42` / `ORDER#2026-01-15#99`) reduz round trips e custo, mas é **mais difícil de entender e evoluir**. **Para a maioria das equipes Spring, comece com uma tabela por agregado/entidade** e só consolide quando houver necessidade medida. Documente os padrões de acesso e as chaves no repositório (ou ADR — `architect`).

**Exemplo — tabela `books`:**
| Padrão de acesso | Como |
|---|---|
| Livro por id | `GetItem` com PK `id` |
| Livros de um autor | `Query` no GSI `author-index` (PK `author`, SK `title`) |
| Listar todos | **não** (sem Scan); se precisar, outro desenho (índice por categoria + paginação) |

---

## 2. Entity com o Enhanced Client (sem Lombok)

O Enhanced Client mapeia classes com `@DynamoDbBean`: exige **constructor sem argumentos** e **getters/setters** — exatamente o estilo do pack (sem Lombok). As annotations vão nos **getters**.

```java
@DynamoDbBean
public class Book implements Serializable {

    private static final long serialVersionUID = 1L;

    private String id;
    private String author;
    private String title;
    private BigDecimal price;
    private Instant createdAt;
    private Long version;

    public Book() {}

    @DynamoDbPartitionKey
    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    @DynamoDbSecondaryPartitionKey(indexNames = "author-index")
    public String getAuthor() {
        return author;
    }

    public void setAuthor(String author) {
        this.author = author;
    }

    @DynamoDbSecondarySortKey(indexNames = "author-index")
    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public BigDecimal getPrice() {
        return price;
    }

    public void setPrice(BigDecimal price) {
        this.price = price;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    @DynamoDbVersionAttribute
    public Long getVersion() {
        return version;
    }

    public void setVersion(Long version) {
        this.version = version;
    }

    // equals, hashCode
}
```
- Fica em `model/` (como as entities JPA). **Nunca exponha** direto no controller: continue com **DTO + mapper** (`code-organization`).
- **`@DynamoDbVersionAttribute`**: *optimistic locking* — o client incrementa `version` a cada escrita e **falha** (`ConditionalCheckFailedException`) se outro processo alterou o item no meio (lost update). Mapeie para **409 Conflict** (`exception-handling`).
- Tipos: `String`, números, `BigDecimal`, `Boolean`, `Instant` (ISO-8601), `List`, `Map` funcionam. Para dinheiro use **`BigDecimal`**, nunca `double`. Datas: prefira `Instant` (UTC).
- `id` como **UUID string** gerado na aplicação (não há autoincrement).

## 3. Repository

```java
@Repository
public class BookRepository {

    private final DynamoDbTable<Book> table;

    public BookRepository(DynamoDbEnhancedClient enhancedClient, @Value("${app.dynamodb.books-table}") String tableName) {
        this.table = enhancedClient.table(tableName, TableSchema.fromBean(Book.class));
    }

    public Optional<Book> findById(String id) {
        return Optional.ofNullable(table.getItem(Key.builder().partitionValue(id).build()));
    }

    public Book save(Book book) {
        table.putItem(book);
        return book;
    }

    public void createIfAbsent(Book book) {
        table.putItem(PutItemEnhancedRequest.builder(Book.class)
                .item(book)
                .conditionExpression(Expression.builder().expression("attribute_not_exists(id)").build())
                .build());
    }

    public Page<Book> findByAuthor(String author, Map<String, AttributeValue> startKey, int limit) {
        var request = QueryEnhancedRequest.builder()
                .queryConditional(QueryConditional.keyEqualTo(Key.builder().partitionValue(author).build()))
                .exclusiveStartKey(startKey)
                .limit(limit)
                .build();
        return table.index("author-index").query(request).iterator().next();
    }

    public void delete(String id) {
        table.deleteItem(Key.builder().partitionValue(id).build());
    }
}
```
(Constructor injection aqui porque o campo `table` é montado no construtor — exceção justificada à preferência de field injection, como em `observability`.)
- O **nome da tabela vem de configuração** (`app.dynamodb.books-table`), diferente por ambiente (`books-dev`, `books-prod`).
- `getItem` devolve `null` quando não existe → `Optional`; o **service** lança `ResourceNotFoundException` (`exception-handling`).
- **`createIfAbsent`**: escrita **condicional** — `attribute_not_exists(id)` impede sobrescrever; lança `ConditionalCheckFailedException` (→ 409). É também o jeito de fazer **idempotência** (`messaging`): grave o `eventId` com condição de ausência.
- **Paginação:** `Query`/`Scan` devolvem **no máximo 1 MB** por chamada. Use `limit` + `lastEvaluatedKey()` da página como **token de paginação** para o client (codifique em Base64); `exclusiveStartKey` na próxima chamada. **Nunca** assuma que a primeira página é tudo. Itere `query(...).items()` só quando quer realmente todos os resultados.
- **`Query` no GSI** é eventualmente consistente: logo após um `putItem` o item pode demorar milissegundos para aparecer no índice. Leitura **fortemente consistente** (`consistentRead(true)`) só existe na tabela base, não no GSI, e custa 2× RCU.

## 4. Atualização parcial, transações e batch

- **`updateItem`** (read-modify-write com o Enhanced Client) respeita o `version`. Para contadores atômicos use **`UpdateExpression`** via client de baixo nível (`SET views = views + :inc`) em vez de ler e gravar.
- **Transações:** `enhancedClient.transactWriteItems(...)` aplica até **100 itens** (de várias tabelas) de forma **atômica** (tudo ou nada), com condições. Custa o dobro da capacidade. Use para invariantes entre itens (transferência, reserva de estoque + pedido) — não como regra geral.
- **Batch** (`batchWriteItem`/`batchGetItem`, até 25/100 itens) reduz round trips, mas **não é atômico** e itens podem voltar em `unprocessedItems` — você precisa **re-tentar com backoff** o que sobrou. Sempre verifique `unprocessedItems`.

## 5. TTL, Streams e backup

- **TTL:** atributo numérico (epoch em segundos) que o DynamoDB usa para **apagar** itens expirados **gratuitamente**; a remoção pode atrasar até ~48h, então **filtre** itens expirados na leitura se a precisão importar. Bom para sessões/tokens/cache.
- **DynamoDB Streams:** fluxo ordenado (por chave) das mudanças da tabela, consumível por **Lambda** (`aws-lambda`) ou Kinesis. Base do **outbox no DynamoDB** (grave o evento na **mesma transação** `transactWriteItems` e deixe o stream publicar) e de CDC — análogo ao `transactional-outbox` relacional.
- **PITR** (point-in-time recovery) e **backups on-demand** ligados em produção; **deletion protection** na tabela; **Global Tables** para multi-região.

## 6. Capacidade e custo

| Modo | Como cobra | Use quando |
|---|---|---|
| **On-demand** | por request | Carga imprevisível, começo de projeto, picos; **default razoável** |
| **Provisioned** (+ auto scaling) | capacidade reservada (RCU/WCU) | Carga estável e previsível → mais barato |

Custo por item: leitura **eventual** de até 4 KB = 0,5 RCU; **forte** = 1; **escrita** de até 1 KB = 1 WCU; **transação** = 2×. Itens grandes e `Scan` custam caro. **GSI** repete cada escrita (cada índice multiplica o custo de escrita) — crie só os necessários. Alarme em `ThrottledRequests`/`ConsumedReadCapacityUnits` (`aws-observability`).

## 7. Infraestrutura (a tabela NÃO nasce no startup)

Crie tabelas e índices por **IaC** (Terraform — `aws-terraform`), nunca pelo código da aplicação em produção (a aplicação não deve ter permissão de `CreateTable`). **Flyway não se aplica ao DynamoDB**: mudanças de dados/atributos são **scripts/jobs** versionados; atributos novos são **opcionais** (schemaless) — o código novo trata `null` e o antigo ignora o que não conhece (compatibilidade expand → contract, igual a `flyway-migrations`).
```hcl
resource "aws_dynamodb_table" "books" {
  name         = "books-${var.env}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "id"

  attribute {
    name = "id"
    type = "S"
  }
  attribute {
    name = "author"
    type = "S"
  }
  attribute {
    name = "title"
    type = "S"
  }

  global_secondary_index {
    name            = "author-index"
    hash_key        = "author"
    range_key       = "title"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }
  deletion_protection_enabled = true
}
```
(`projection_type = "ALL"` copia todos os atributos para o índice — conveniente, mas caro em escrita/armazenamento; prefira `INCLUDE` com os campos que a query precisa.)

## 8. IAM de menor privilégio

```json
{
  "Effect": "Allow",
  "Action": ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:UpdateItem", "dynamodb:DeleteItem", "dynamodb:Query"],
  "Resource": [
    "arn:aws:dynamodb:us-east-1:123456789012:table/books-prod",
    "arn:aws:dynamodb:us-east-1:123456789012:table/books-prod/index/*"
  ]
}
```
Sem `dynamodb:Scan`, `CreateTable`, `DeleteTable` para a aplicação. Via IRSA/task role (`aws-eks`, `aws-ecs-fargate`) — **nunca access keys**. Condição `dynamodb:LeadingKeys` permite **isolar linhas por tenant/usuário** na própria policy (multi-tenant).

## 9. Testes

LocalStack com `.withServices("dynamodb")` (`aws-s3-sqs`/`aws-sdk-java`) ou a imagem `amazon/dynamodb-local`. Crie a tabela **no teste** (`table.createTable(...)` com o GSI). Cubra: salvar e buscar, **`createIfAbsent` duplicado → exceção**, **conflito de versão** (duas atualizações do mesmo item → a segunda falha), **query no GSI com paginação**, e o mapeamento da exceção para 409/404 no `@WebMvcTest` (`testing`). Awaitility (nunca `Thread.sleep`) para o GSI eventual.

---

## Regras principais

- **Padrões de acesso primeiro**; cada consulta é atendida por chave ou índice. **Sem `Scan`** em produção.
- PK de **alta cardinalidade e acesso uniforme** (sem status/data/id sequencial como PK) — evita hot partition.
- Uma tabela por agregado por padrão; single-table só com necessidade medida e documentada.
- Enhanced Client com `@DynamoDbBean` (no-arg + getters/setters, **sem Lombok**), annotations nos getters; entity **nunca exposta** (DTO + mapper); `BigDecimal` para dinheiro, `Instant` para datas.
- `@DynamoDbVersionAttribute` (optimistic locking) e **escrita condicional** para idempotência/não sobrescrever; `ConditionalCheckFailed` → 409.
- **Paginação por `lastEvaluatedKey`**; batch exige tratar `unprocessedItems`; transação só para invariantes entre itens.
- GSI só os necessários (multiplicam o custo de escrita) e são eventualmente consistentes.
- On-demand por padrão; PITR e deletion protection em produção; tabelas **por IaC**, nome por configuração; sem `CreateTable`/`Scan` na policy da aplicação.
- IAM por ARN (tabela e `/index/*`), via IRSA/task role — nunca access keys.
- Testes com LocalStack/DynamoDB Local, incluindo conflito de versão, duplicata e paginação.
- Preferir relacional quando precisa de consultas flexíveis/JOINs.
- **Sem Lombok** — deliberado.
