---
name: idempotency
description: Idempotência em APIs e consumers Spring Boot — por que requests e mensagens se repetem, Idempotency-Key em POST (chave única, hash do request, replay da resposta, 409/422), transação única, efeitos externos em duas fases, consumers idempotentes, TTL e testes de concorrência. Use quando um POST ou consumer não pode duplicar efeito em retry ou clique duplo.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../spring-data-jpa/SKILL.md`](../spring-data-jpa/SKILL.md), [`../flyway-migrations/SKILL.md`](../flyway-migrations/SKILL.md) e [`../exception-handling/SKILL.md`](../exception-handling/SKILL.md). Esta skill é **fundamento** de `resilience` (retry só é seguro com idempotência), `messaging`, `transactional-outbox` e `saga-pattern`.

# Idempotência

Uma operação é **idempotente** quando **executá-la N vezes tem o mesmo efeito que executá-la 1 vez**. Em sistemas distribuídos, **a mesma operação vai ser repetida** — não é questão de *se*, mas de *quando*:

| Por que repete | Exemplo |
|---|---|
| **Retry** automático (cliente, gateway, SDK, Resilience4j) | O `POST /orders` deu timeout; o client reenvia — **mas o servidor já tinha criado o pedido** |
| **Resultado desconhecido** | A conexão caiu **depois** do commit e **antes** da resposta: o client não sabe se funcionou |
| **Usuário** | Clique duplo no botão "Pagar"; reenvio de formulário; refresh |
| **Entrega at-least-once** | SQS/RabbitMQ/Kafka entregam a mesma mensagem 2× (`messaging`) |
| **Reprocessamento** | Replay de eventos, redrive da DLQ, saga retomada (`saga-pattern`) |
| **Rede/infra** | Balanceador reenviando para outra instância |

Sem idempotência, o resultado é **cobrança duplicada, dois pedidos, e-mail repetido, estoque descontado duas vezes**. **Projete para a repetição**, não torça para ela não ocorrer.

---

## 1. O que já é idempotente (HTTP)

| Método | Idempotente? | Observação |
|---|---|---|
| `GET`, `HEAD`, `OPTIONS` | **Sim** (e seguros: não alteram nada) | |
| `PUT` | **Sim** | "Substitua o recurso `/books/42` por isto" — repetir resulta no mesmo estado |
| `DELETE` | **Sim** (o estado final é o mesmo) | A 2ª chamada pode devolver `404`/`204` — decida e documente (`204` em ambas é mais amigável) |
| **`POST`** | **Não** | Cria/aciona algo **novo** a cada chamada — **é aqui que se precisa de uma chave de idempotência** |
| `PATCH` | Depende | `{"status":"PAID"}` é idempotente; `{"balance":"+10"}` não |

**Desenhe para `PUT`/`PATCH` idempotentes quando possível:** o **cliente gera o id** (UUID) e faz `PUT /orders/{uuid}` — repetir **não duplica**, porque o recurso tem identidade conhecida (a PK única impede o segundo insert; o segundo `PUT` vira *update* idêntico). É a forma **mais simples** de idempotência: **identidade determinada pelo cliente**.

---

## 2. `Idempotency-Key` para `POST`

Quando o servidor gera o id (ou a operação é uma **ação**: "cobrar", "enviar"), o cliente manda um header **`Idempotency-Key: <uuid>`** (convenção de mercado, formalizada em um *draft* do IETF; Stripe, PayPal, Adyen a usam). O servidor **memoriza** a chave e o resultado: a **repetição devolve a mesma resposta, sem reexecutar**.

### Contrato da API

| Situação | Resposta |
|---|---|
| Chave **nova** | Executa; devolve o resultado (`201`) e **guarda** chave + hash do request + resposta |
| **Mesma chave, mesmo corpo**, operação já concluída | **Replay**: devolve o **mesmo status e corpo** guardados (com header `Idempotent-Replayed: true`) — **não** reexecuta |
| **Mesma chave, corpo DIFERENTE** | **`422 Unprocessable Entity`** — a chave foi **reutilizada para outra operação** (bug do cliente). Nunca execute |
| **Mesma chave, requisição ainda em andamento** | **`409 Conflict`** (+ `Retry-After`): o cliente tenta de novo em instantes |
| **Header ausente** onde é obrigatório | **`400 Bad Request`** (operações financeiras/críticas **exigem** a chave) |
| Chave **malformada** | `400` (valide: UUID, ≤ 80 caracteres) |

Documente o header no Swagger (`swagger`: `@Parameter(name = "Idempotency-Key", in = ParameterIn.HEADER, required = true)`). **Escopo da chave:** por **cliente/usuário** (`sub` do JWT — `aws-cognito`), para que dois clientes com a mesma chave não colidam **nem vejam respostas um do outro** (vazamento de dados). **TTL:** a chave vale por um tempo (24 h–7 dias); depois pode ser reutilizada/limpa.

### O cliente

Gera **uma chave por *intenção* do usuário** (ao clicar em "Pagar", **uma vez**) e **reutiliza a mesma chave em todos os retries** daquela intenção. **Nunca** gera uma chave nova a cada tentativa (anula o propósito) **nem** reaproveita a mesma chave para uma operação diferente.

---

## 3. Implementação: tabela com chave única + transação única

**O mecanismo central é uma restrição de unicidade no banco** — ela serializa corridas **sem lock distribuído**. Migration (`flyway-migrations`, MySQL; outros bancos conforme a tabela de equivalência):
```sql
CREATE TABLE IF NOT EXISTS `idempotency_key` (
  `client_id`       varchar(80) NOT NULL,
  `idempotency_key` varchar(80) NOT NULL,
  `request_hash`    char(64)    NOT NULL,
  `response_status` int         NOT NULL,
  `response_body`   json        DEFAULT NULL,
  `created_at`      datetime(6) NOT NULL,
  `expires_at`      datetime(6) NOT NULL,
  PRIMARY KEY (`client_id`, `idempotency_key`),
  KEY `idx_idempotency_expires` (`expires_at`)
);
```
- **PK `(client_id, idempotency_key)`**: a unicidade por cliente. `request_hash` (SHA-256 do corpo) detecta **reuso indevido**. `response_*` guarda o que **replicar**. `expires_at` + índice para a **limpeza**.

### A estratégia: a ação e o registro da chave **na mesma transaction**

Dois blocos: um **coordenador sem transaction** (decide e trata a corrida) e um **store transacional** (executa a ação **e** grava a chave **atomicamente**). Se a ação fizer rollback, a chave **também** some — a repetição **reexecuta** normalmente (nada ficou pela metade).

```java
@Component
public class IdempotentExecutor {

    private final IdempotencyStore store;

    public IdempotentExecutor(IdempotencyStore store) {
        this.store = store;
    }

    public StoredResponse run(String clientId, String key, String requestHash, Supplier<StoredResponse> action) {
        var existing = store.find(clientId, key);
        if (existing.isPresent()) return replay(existing.get(), requestHash);
        try {
            return store.executeAndRecord(clientId, key, requestHash, action);
        } catch (DataIntegrityViolationException race) {
            return replay(store.find(clientId, key).orElseThrow(() -> new IdempotencyInProgressException(key)), requestHash);
        }
    }

    private StoredResponse replay(IdempotencyRecord record, String requestHash) {
        if (!record.requestHash().equals(requestHash)) throw new IdempotencyKeyReuseException(record.key());
        return record.toResponse();
    }
}
```
```java
@Component
public class IdempotencyStore {

    private final IdempotencyKeyRepository repository;
    private final Clock clock;

    public IdempotencyStore(IdempotencyKeyRepository repository, Clock clock) {
        this.repository = repository;
        this.clock = clock;
    }

    @Transactional(readOnly = true)
    public Optional<IdempotencyRecord> find(String clientId, String key) {
        return repository.findById(new IdempotencyId(clientId, key)).filter(r -> r.expiresAt().isAfter(Instant.now(clock)));
    }

    @Transactional
    public StoredResponse executeAndRecord(String clientId, String key, String requestHash, Supplier<StoredResponse> action) {
        var response = action.get();
        repository.saveAndFlush(IdempotencyRecord.of(clientId, key, requestHash, response, Instant.now(clock).plus(Duration.ofHours(24))));
        return response;
    }
}
```
```java
public record StoredResponse(int status, String body) {}
```
**Como a corrida é resolvida** (duas requests idênticas simultâneas): ambas veem "sem chave", ambas executam `executeAndRecord`; o `saveAndFlush` da segunda **bloqueia no índice único** até a primeira **confirmar** (ou desfazer); se a primeira confirmou, a segunda recebe `DataIntegrityViolationException` → **sua transaction faz rollback** (desfazendo **também a ação dela** — nada duplicou) → o coordenador **relê a chave da vencedora** (já confirmada) e faz o **replay**. Se a primeira desfez, a segunda **segue e conclui**. **Sem lock distribuído, sem `IN_PROGRESS` obrigatório.** O `IdempotencyStore` é um **bean separado** para o proxy do `@Transactional` valer (chamada interna `this.` ignoraria — `spring-data-jpa`).

`IdempotencyKeyReuseException` → `422`; `IdempotencyInProgressException` → `409` com `Retry-After` (mapeadas no `@ControllerAdvice` — `exception-handling`).

### O controller

```java
@PostMapping
public ResponseEntity<String> create(
        @RequestHeader("Idempotency-Key") String key,
        @Valid @RequestBody CreateOrderRequest request,
        @AuthenticationPrincipal Jwt jwt) {
    IdempotencyKeys.validate(key);
    var hash = RequestHasher.sha256(jsonMapper.writeValueAsString(request));
    var stored = executor.run(jwt.getSubject(), key, hash, () -> {
        var order = service.create(request);
        return new StoredResponse(HttpStatus.CREATED.value(), jsonMapper.writeValueAsString(order));
    });
    return ResponseEntity.status(stored.status())
            .contentType(MediaType.APPLICATION_JSON)
            .body(stored.body());
}
```
- **Hash do corpo canonizado** (serialização estável do **DTO**, não os bytes brutos com espaços/ordem de campos diferentes) → `HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(...))` num `RequestHasher`.
- A ação (`service.create`) é o **caso de uso normal** — **sem saber** de idempotência; o executor a envolve. Pode virar uma **annotation `@Idempotent` + interceptor/AOP** para não repetir o código por endpoint (cuidado com a transação: o advice precisa ficar **fora** do `@Transactional` da ação).
- `Idempotent-Replayed: true` no replay (header opcional, útil ao cliente/diagnóstico).
- **Autorização continua valendo** no replay (o `clientId` é o `sub` autenticado).

### Quando a ação tem efeitos **fora do banco** (duas fases)

A estratégia acima só é **atômica** se **todos os efeitos estão no banco** (mesma transaction). Se a ação também **chama um sistema externo** (gateway de pagamento, e-mail, outra API) — que **não faz rollback** —, um crash **depois** do efeito externo e **antes** do commit **perde a chave** e a repetição **reexecuta o efeito externo**. Soluções:
1. **Propague a idempotência para o sistema externo**: passe a **mesma chave** (derivada: `orderId`/`eventId`) ao provedor de pagamento (Stripe/Adyen aceitam `Idempotency-Key`). É a **defesa mais forte** — **a idempotência tem que ir até o final da cadeia**.
2. **Duas fases:** (a) grave a chave como **`IN_PROGRESS`** e **faça commit**; (b) execute o efeito externo; (c) atualize para `COMPLETED` com a resposta. A repetição vendo `IN_PROGRESS` devolve `409` (ou espera); chaves `IN_PROGRESS` **antigas** (crash no meio) exigem **reconciliação** (consultar o provedor externo pelo estado antes de decidir). Mais complexo — use quando o efeito externo é **crítico e não idempotente** por si.
3. **Outbox** para efeitos de mensagem/e-mail (`transactional-outbox`): grave a **intenção** na transaction; o relay executa **com idempotência** do outro lado.

---

## 4. Consumers de mensagens idempotentes

Brokers entregam **at-least-once** (`messaging`): **todo consumer precisa ser idempotente**. Três técnicas, da mais simples:

1. **Operação naturalmente idempotente** — a mais barata e robusta:
   - **Upsert** (`INSERT ... ON DUPLICATE KEY UPDATE` / `ON CONFLICT`), `UPDATE ... SET status = 'PAID'` (e não `balance = balance + x`).
   - **Escrita condicional** (`attribute_not_exists(id)` no DynamoDB — `aws-dynamodb`; `WHERE version < :v` na projeção — `cqrs-event-sourcing`).
   - **Operações de conjunto** (adicionar ao set).
2. **Tabela de mensagens processadas** (chave única `message_id`/`eventId` **na mesma transaction** do efeito): `INSERT` duplicado → ignora. O código completo está em `transactional-outbox` (seção 5). **Mesmo princípio** do `IdempotencyStore` desta skill.
3. **Chave de idempotência para o efeito externo** (o `eventId` repassado ao provedor de pagamento) — 3 do bloco acima.

**A chave de idempotência da mensagem é o `eventId`** (UUID do envelope — `messaging`), **gerado pelo produtor uma vez** e **mantido nos reenvios** (o outbox reutiliza o mesmo `id`). **Não** use o `messageId` do broker como chave: uma republicação pelo produtor gera um id novo no broker, e o consumer **processaria de novo**.

**Desordem** (não só duplicata): além da dedup, verifique a **versão** do agregado/evento e **ignore o mais antigo** (`cqrs-event-sourcing`, `saga-pattern`).

---

## 5. Operação: TTL, limpeza e custo

- **Limpe** as chaves expiradas por job (`DELETE FROM idempotency_key WHERE expires_at < :now LIMIT 1000` em lotes — `flyway-migrations`: operações em lotes) — a tabela cresce **uma linha por requisição de `POST`**.
- **TTL ≥ janela de retry do cliente** (mínimo 24 h; operações financeiras dias). Chave expirada = a operação pode ser reexecutada — documente.
- **Tamanho da resposta guardada:** limite (ex.: ≤ 64 KB); respostas grandes guardam só uma **referência** (id do recurso criado) e o replay **recarrega** o recurso.
- **Armazenamento alternativo:** **Redis** (`SET key value NX EX 86400`) é leve e rápido para operações **sem atomicidade com o banco** (o resultado e o efeito não estão na mesma transaction → janela de inconsistência; use quando o efeito **também** é idempotente por natureza). **DynamoDB** com escrita condicional + TTL nativo (`aws-dynamodb`) quando a API já é serverless. O banco **relacional na mesma transaction** é o **mais seguro** para efeitos relacionais.
- **No Lambda**, o **Powertools Idempotency** (DynamoDB) implementa isto pronto (`aws-lambda`).
- **Métricas:** taxa de **replays** (muitos = clientes com timeout curto ou rede ruim), `409`/`422` (bugs de cliente) — `observability`.
- **Segurança:** a chave **não é segredo**, mas o **escopo por cliente** é obrigatório; o **corpo guardado** pode ter dado pessoal — mesmo tratamento de retenção/LGPD que o dado original (`aws-observability`: nunca logar o corpo).

## 6. Interação com retry e resiliência

`resilience`: **retry só em operações idempotentes**. A regra prática:
- `GET/PUT/DELETE` → retry livre (com limite/backoff).
- **`POST` → retry só se o request leva `Idempotency-Key`** (o **mesmo** em todas as tentativas — `RestClient` com `defaultHeader` por requisição, **gerado antes** do loop de retry, **não dentro**).
- Gateway (`api-gateway`) e SDKs (`aws-sdk-java`) que re-tentam sozinhos: confirme se a operação é segura de repetir. SQS/SNS `publish` re-tentado pelo SDK pode **duplicar** — consumers idempotentes.

## 7. Testes

O comportamento é de **concorrência e falha**: teste com **banco real em container** (`integration-testing`), não com mocks:
- **Mesma chave 2×, mesmo corpo** → **um** efeito (uma linha em `orders`), **mesmo status e corpo** na 2ª, header `Idempotent-Replayed`.
- **Mesma chave, corpo diferente** → `422`, **nenhum** efeito novo.
- **N requests concorrentes** com a mesma chave (`ExecutorService` + `CountDownLatch` para largada simultânea) → **exatamente um** pedido criado; as demais recebem **o mesmo resultado** (replay) ou `409`; **nenhuma** cria duplicata.
- **Falha na ação** (exceção) → a chave **não** é gravada (rollback); a repetição **executa** de verdade.
- **Chave ausente** → `400`; **malformada** → `400`; **expirada** → tratada como nova.
- **Escopo por cliente:** o cliente B com a **mesma chave** do cliente A **não** vê a resposta de A e executa a sua operação.
- **Consumer:** a **mesma mensagem 2×** (e fora de ordem) → **um** efeito (`messaging`, `transactional-outbox`).
- **Limpeza:** o job remove só as chaves expiradas.
- Use **Awaitility**/latches, **nunca `Thread.sleep`**.

## 8. Anti-patterns

- **`POST` crítico sem idempotência** + retry automático (cobrança duplicada).
- **Verificar a chave "se existe então retorna" sem a restrição única** (corrida: dois processam).
- **Gravar a chave em uma transaction e a ação em outra** (janelas de inconsistência) — para efeitos no banco, use **uma só**.
- **Não comparar o hash do request** (a mesma chave aceita para operações diferentes).
- **Escopo global da chave** (vazamento de respostas entre clientes).
- **Cliente gerando chave nova a cada retry**, ou reaproveitando para outra operação.
- **Idempotência só até a borda** (a API é idempotente, mas chama o provedor de pagamento sem chave).
- **Usar o `messageId` do broker** como chave de dedup de eventos (use o `eventId` do produtor).
- **Sem TTL/limpeza** (tabela infinita) ou TTL menor que a janela de retry.
- **Confiar em "exactly-once"** do broker fim a fim.

---

## Regras principais

- **A repetição vai acontecer** (retry, timeout com resultado desconhecido, clique duplo, at-least-once): projete **toda** operação que altera estado para **tolerar repetição**.
- Prefira a **idempotência natural**: `PUT` com **id gerado pelo cliente**, upsert, escrita condicional, `status = X` em vez de incremento.
- **`POST` crítico → `Idempotency-Key`** (por cliente/`sub`, TTL ≥ janela de retry): chave nova executa e guarda; **mesma chave+corpo → replay** da resposta; **corpo diferente → `422`**; **em andamento → `409`**; ausente em operação crítica → `400`.
- **Unicidade no banco** (PK `(client_id, key)`) resolve a corrida **sem lock distribuído**; **ação + registro da chave na mesma transaction** (store como bean separado para o proxy); rollback da ação desfaz a chave.
- **Efeitos fora do banco**: propague a **mesma chave ao sistema externo**, ou duas fases com reconciliação, ou outbox — **a idempotência vai até o fim da cadeia**.
- **Consumers**: operação naturalmente idempotente, ou **tabela de processados com `eventId`** (do produtor, estável nos reenvios) na **mesma transaction**; tolere **desordem** com versão.
- **Retry só com idempotência** (`POST` apenas com a mesma `Idempotency-Key` em todas as tentativas, gerada **antes** do retry).
- **Limpe** as chaves expiradas em lotes; limite o tamanho da resposta guardada; mesmo tratamento de LGPD do dado original; documente o header no Swagger.
- **Teste com banco real e concorrência**: duplicata, corpo diferente, N simultâneas, falha da ação, escopo por cliente, expiração, consumer 2×.
- **Sem Lombok** — deliberado.
