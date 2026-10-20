---
name: resilience
description: Resiliência em microsserviços Spring Boot — timeouts, retry com backoff e jitter (só idempotente), circuit breaker, bulkhead, rate limiter, fallback honesto, Resilience4j e os recursos nativos do Spring 7, retry storms, o que não é falha (404) e testes de falha com WireMock/Toxiproxy. Use quando proteger chamadas a dependências lentas ou instáveis.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../microservices/SKILL.md`](../microservices/SKILL.md), [`../service-communication/SKILL.md`](../service-communication/SKILL.md) e [`../idempotency/SKILL.md`](../idempotency/SKILL.md) (retry só é seguro com operações idempotentes). Métricas e alertas: `observability`, `aws-observability`.

# Resiliência

Em um sistema distribuído **a falha é normal**, não exceção: a rede perde pacotes, um serviço demora, um pod é reiniciado, o banco satura. **Resiliência** é continuar **útil e previsível** apesar disso — **degradar de forma controlada em vez de cair em cascata**. O perigo central é a **falha em cascata**: um serviço lento faz seus chamadores acumularem threads/conexões, ficarem lentos, e a lentidão se propaga até derrubar tudo.

## Os padrões, em uma tabela

| Padrão | O que faz | Protege contra |
|---|---|---|
| **Timeout** | Desiste de esperar depois de X | Recurso preso para sempre (a base de tudo) |
| **Retry** (backoff + jitter) | Tenta de novo, com espera crescente e aleatória | Falhas **transitórias** (rede, deadlock, deploy em andamento) |
| **Circuit Breaker** | Para de chamar um downstream **doente**, falha rápido, testa a recuperação | Cascata e sobrecarga de um serviço que já está caindo |
| **Bulkhead** | Limita a **concorrência** por dependência (compartimentos) | Uma dependência lenta consumindo **todas** as threads |
| **Rate Limiter** | Limita a **taxa** de chamadas | Sobrecarga/abuso, cotas de terceiros |
| **Fallback** | Resposta alternativa **segura** quando a chamada falha | Experiência quebrada quando há alternativa aceitável |
| **Load shedding** | O serviço **rejeita** o excesso cedo (429/503) | Colapso do próprio serviço sob pico |
| **Idempotência** | Repetir não duplica o efeito | Efeitos duplicados de retry/reentrega (`idempotency`) |

**Ordem de importância:** **timeout** (sempre) → **retry correto** → **circuit breaker + bulkhead** nos downstreams críticos → fallback onde **faz sentido**. Nada disso substitui desenhar **menos acoplamento síncrono** (`microservices`, `messaging`).

---

## 1. Timeout — sem ele nada funciona

**Toda chamada de saída tem timeout** (HTTP, banco, fila, cache, SDK AWS — `service-communication`, `aws-sdk-java`, `jvm-performance`). Sem timeout, um downstream lento segura a thread **indefinidamente**, o pool se esgota e o serviço **para de responder** — mesmo estando "saudável".
- **Conexão** (1–2 s) e **leitura/resposta** (≈ p99 do downstream + margem), separados.
- **Orçamento:** o timeout de cada chamador **maior** que o do downstream; em cadeias, **propague um deadline** (`service-communication`, seção 6).
- Defina também o **timeout da própria request** que você atende (`server.tomcat.connection-timeout`, gateway/ALB idle timeout) coerente com os de saída.
- Em chamadas bloqueantes o **timeout do HTTP client** é o mecanismo real; o `@TimeLimiter` do Resilience4j só vale para chamadas **assíncronas** (`CompletableFuture`) — não "mata" uma thread bloqueada.

## 2. Retry — a ferramenta mais mal usada

Retry **ajuda** em falhas transitórias e **piora** todo o resto. Regras:
1. **Só em operações idempotentes** (GET, PUT, DELETE, ou POST com `Idempotency-Key` — `idempotency`). Retentar um `POST /payments` sem idempotência **cobra duas vezes**.
2. **Só em erros transitórios** (timeout, conexão recusada, `503`, `429`) — **nunca** em `4xx` de negócio (`400`, `404`, `409`, `422`): repetir não muda o resultado.
3. **Limitado** (2–3 tentativas) com **backoff exponencial + jitter** (aleatoriedade): sem jitter, todos os clients retentam **no mesmo instante** e geram picos sincronizados (*thundering herd*).
4. **Em um só lugar da cadeia.** 3 retries em cada uma de 3 camadas = **27** chamadas ao serviço que já está sofrendo — o **retry storm**: seu retry **amplifica** a falha. Decida **uma camada** responsável (normalmente a mais próxima do cliente ou o chamador direto) e as demais **não** retentam.
5. **Respeite `Retry-After`** quando o downstream o envia; combine com **circuit breaker** (parar de retentar quando o serviço está claramente fora).
6. Considere um **orçamento de retry** (no máximo ~10% das chamadas podem ser retries) em sistemas de alto volume.

## 3. Circuit breaker

Três estados: **CLOSED** (chamadas passam; mede falhas) → **OPEN** (a taxa de falha/lentidão passou do limite: **falha imediatamente**, sem chamar o downstream, por um tempo) → **HALF-OPEN** (deixa passar **poucas** chamadas de teste: se funcionam, volta a CLOSED; se não, volta a OPEN).
O benefício: **alivia o downstream** (para de martelá-lo enquanto se recupera) e **libera seus recursos** (falhar rápido, em vez de esperar o timeout cheio em cada chamada).
Conte como falha: **timeouts, `5xx`, conexão**; e **chamadas lentas** (*slow call*: lenta é falha em potencial). **Não** conte erros de negócio (`404`, `400`, `409`) — uma consulta por um recurso inexistente **não** é um downstream doente.

## 4. Bulkhead e rate limiter

- **Bulkhead:** limite de **chamadas concorrentes por dependência** (ex.: no máximo 20 simultâneas ao `catalog`). Se o `catalog` ficar lento, ele ocupa **no máximo 20 threads** — as outras funcionalidades continuam atendendo. Sem isso, **uma** dependência lenta consome **todo** o pool de threads do serviço.
- **Rate limiter:** protege **você** de sobrecarregar um terceiro com cota, e protege seu serviço de clientes abusivos (na borda: `api-gateway`).

---

## 5. Resilience4j (Spring Boot)

> **Versões:** o Resilience4j tem starters para Spring Boot e a integração com o Boot 4 / AOP (`spring-boot-starter-aop` foi renomeado no Boot 4) pode ter artifacts novos. **Confirme na documentação/Context7 da versão resolvida** (`maven-config`) o starter exato e a dependência de AOP/AspectJ necessária para as anotações. A **estrutura** abaixo (anotações e propriedades) é estável.

```xml
<dependency>
    <groupId>io.github.resilience4j</groupId>
    <artifactId>resilience4j-spring-boot3</artifactId>
    <version>${resilience4j.version}</version>
</dependency>
```
(`resilience4j.version` em `<properties>` — fora do BOM do Boot; confirme o artifact para o Boot do projeto. Alternativa **agnóstica de implementação**: `spring-cloud-starter-circuitbreaker-resilience4j` com `CircuitBreakerFactory`, do Spring Cloud — usada também pelo Spring Cloud Gateway, `api-gateway`.)

### Configuração por instância (nomeada por dependência)

```yaml
resilience4j:
  circuitbreaker:
    instances:
      catalog:
        slidingWindowType: COUNT_BASED
        slidingWindowSize: 20
        minimumNumberOfCalls: 10
        failureRateThreshold: 50
        slowCallDurationThreshold: 2s
        slowCallRateThreshold: 80
        waitDurationInOpenState: 30s
        permittedNumberOfCallsInHalfOpenState: 3
        automaticTransitionFromOpenToHalfOpenEnabled: true
        ignoreExceptions:
          - br.com.edimilsonldutra.exception.BookNotFoundException
  retry:
    instances:
      catalog:
        maxAttempts: 3
        waitDuration: 200ms
        enableExponentialBackoff: true
        exponentialBackoffMultiplier: 2
        enableRandomizedWait: true
        retryExceptions:
          - org.springframework.web.client.ResourceAccessException
        ignoreExceptions:
          - br.com.edimilsonldutra.exception.BookNotFoundException
  bulkhead:
    instances:
      catalog:
        maxConcurrentCalls: 20
        maxWaitDuration: 0
```
- **`minimumNumberOfCalls`**: o breaker só avalia depois de N chamadas — evita abrir por 1 falha em 2 chamadas.
- **`ignoreExceptions`**: erros de **negócio** (`BookNotFoundException`) **não** contam como falha e **não** abrem o breaker nem são retentados (a regra do `service-communication`: `404` ≠ falha técnica).
- **`retryExceptions`**: **só** as exceptions transitórias (`ResourceAccessException`: timeout/conexão; e os `5xx` mapeados para a sua `...UnavailableException`).
- **`maxWaitDuration: 0`** no bulkhead = **rejeita na hora** quando cheio (falha rápida, sem fila escondida). Fila ilimitada esconde a lentidão até virar OOM (`jvm-performance`).
- **Uma instância nomeada por dependência** (`catalog`, `payment`) com limites ajustados a cada uma — **não** um breaker global.
- Valores acima são **ponto de partida**: calibre com os SLOs e métricas reais.

### Aplicar no adapter (o lugar certo — `service-communication`)

```java
@Component
public class CatalogGateway implements BookCatalog {

    private static final Logger logger = LoggerFactory.getLogger(CatalogGateway.class);

    private final CatalogClient client;

    public CatalogGateway(CatalogClient client) {
        this.client = client;
    }

    @Override
    @Bulkhead(name = "catalog")
    @CircuitBreaker(name = "catalog", fallbackMethod = "availabilityFallback")
    @Retry(name = "catalog")
    public boolean isAvailable(BookId id) {
        try {
            return client.findById(id.value()).available();
        } catch (HttpClientErrorException.NotFound e) {
            throw new BookNotFoundException(id);
        } catch (HttpServerErrorException | ResourceAccessException e) {
            throw new CatalogUnavailableException("Catalog service unavailable", e);
        }
    }

    private boolean availabilityFallback(BookId id, Throwable cause) {
        logger.warn("Catalog unavailable for {}, rejecting the loan: {}", id, cause.toString());
        throw new CatalogUnavailableException("Catalog service unavailable", cause);
    }
}
```
- **Ordem dos aspectos** do Resilience4j (de fora para dentro): `Retry` → `CircuitBreaker` → `RateLimiter` → `TimeLimiter` → `Bulkhead` → chamada. Cada tentativa do retry passa pelo breaker; **quando o breaker está OPEN**, o `CallNotPermittedException` interrompe o retry (não adianta retentar).
- **As anotações só funcionam em chamada vinda de outro bean** (proxy AOP): `this.isAvailable()` ignora-as — mesma regra de `@Transactional`.
- **Fallback honesto:** o fallback **não finge sucesso** quando a decisão depende do dado. Aqui, decidir um empréstimo **sem saber** se o livro existe seria um erro; o fallback **falha rápido com `503` claro**. Fallbacks válidos para **leituras degradáveis**: devolver **dado em cache marcado como antigo**, uma lista vazia **com aviso**, o campo opcional ausente (`api-gateway`, composição com degradação). **Nunca** invente dados de negócio (preço, saldo, estoque) ou "aprove por padrão" uma validação de segurança/financeira.
- A **exception de domínio** vira `503` no `@ControllerAdvice` (`exception-handling`); o breaker aberto (`CallNotPermittedException`) também deve ser mapeado para `503` com `Retry-After`.

### Métricas e alertas

O Resilience4j publica métricas no **Micrometer** (`resilience4j.circuitbreaker.state`, `.calls`, `.failure.rate`, `resilience4j.bulkhead.available.concurrent.calls`, `resilience4j.retry.calls`) — vão ao Prometheus/CloudWatch (`observability`, `aws-observability`). **Alerte** em: **breaker abriu** (`state = OPEN`), taxa de falha alta, bulkhead **cheio** (rejeições), muitas tentativas de retry. **Importante:** **não amarre** o health de **liveness** ao breaker/dependências (`observability`) — se o `catalog` cair, reiniciar **todos** os pods piora; o breaker pode alimentar o **readiness** só se o pod for inútil sem a dependência.

## 6. Recursos nativos do Spring Framework 7

O **Spring Framework 7** trouxe **retry e limite de concorrência no núcleo**, sem Resilience4j: `@Retryable` e `@ConcurrencyLimit`, habilitados com `@EnableResilientMethods`.
```java
@Configuration
@EnableResilientMethods
public class ResilienceConfig {
}
```
```java
@Retryable(includes = ResourceAccessException.class, maxRetries = 3, delay = 200, multiplier = 2.0, jitter = 50)
@ConcurrencyLimit(20)
public BookResponse fetch(Long id) { ... }
```
(Há também o `RetryTemplate` programático em `org.springframework.core.retry`. **Confirme os nomes e atributos exatos na versão resolvida** — a API é nova.) **Escolha:** para **retry + limite de concorrência simples**, o nativo basta e **evita uma dependência**; para **circuit breaker**, rate limiter, métricas ricas e configuração por instância, **use Resilience4j** (o Spring 7 **não** tem circuit breaker). Não aplique os dois ao mesmo método (retries duplicados).

---

## 7. Falha em cascata — como projetar contra ela

- **Falhe rápido**: timeout curto + breaker. Esperar 30 s para dizer "não" é pior que dizer "não" em 100 ms.
- **Isole** dependências (bulkhead, pools separados); a dependência **opcional** não pode derrubar o caminho **crítico** (composição com degradação — `api-gateway`).
- **Reduza o acoplamento síncrono**: o que pode ser **assíncrono** (evento + fila com retry e DLQ — `messaging`) **deve** ser; a fila é o *buffer* que absorve a falha do consumidor.
- **Load shedding** no servidor: limite o que você aceita (`server.tomcat.threads.max`/`accept-count`, rate limit, `@ConcurrencyLimit`) e **rejeite o excesso cedo** (`503`/`429`) em vez de aceitar tudo e colapsar; prefira **descartar** requests de baixa prioridade.
- **Escala com cuidado:** autoscaling **não corrige** dependência lenta (mais pods = mais pressão sobre o downstream/banco); respeite `réplicas × pool ≤ conexões do banco` (`jvm-performance`, `aws-rds-secrets-manager`).
- **Infra:** *readiness* correta (tira o pod doente do tráfego), `PodDisruptionBudget`, rolling update com `maxUnavailable: 0`, graceful shutdown (`kubernetes`), múltiplas AZs (`aws-eks`).
- **Dados:** pool com `connection-timeout` curto (`jvm-performance`); **nunca** chamada externa dentro de transaction.
- **Mensageria:** retry **com limite + DLQ**; erro permanente não retenta (`messaging`).
- **Idempotência em tudo** que pode repetir (`idempotency`).

## 8. Testar a falha (o que não é testado, não funciona)

Resiliência que nunca viu falha é **crença**, não garantia. Teste:
- **Unit/integração com WireMock** (fault injection): atraso (`withFixedDelay`) → timeout dispara e o retry ocorre **no máximo N vezes**; `503` repetido → o **breaker abre** após `minimumNumberOfCalls` e as chamadas seguintes **falham rápido sem chegar ao WireMock**; depois de `waitDurationInOpenState`, **half-open** e **recuperação**; `Fault.CONNECTION_RESET_BY_PEER`; resposta intermitente (cenários com estado). Use **janelas pequenas** no profile de teste (`waitDurationInOpenState: 1s`).
- **`404` não abre o breaker** e **não é retentado** (o erro de negócio ignorado) — teste explicitamente.
- **Retry só idempotente:** `POST` sem chave **não** é retentado.
- **Bulkhead:** N+1 chamadas concorrentes → a (N+1)ª é rejeitada rapidamente.
- **Falha de rede real:** **Toxiproxy** com Testcontainers (latência, corte de conexão, *timeout*, banda limitada) entre seu serviço e o downstream/banco — prova o comportamento com **rede de verdade**.
- **Chaos engineering** (em staging, depois com cuidado em produção): matar pods, injetar latência/falhas — **AWS Fault Injection Service (FIS)**, **Chaos Mesh**/Litmus no Kubernetes — com hipótese ("se o `catalog` cair, `lending` devolve 503 em < 200 ms e o resto funciona"), escopo pequeno e **abort condition** (alarme). **Game days** treinam o time e a documentação.
- **Teste de carga** com o downstream degradado (`jvm-performance`): confirme que **não há cascata** (latência e pool do chamador estáveis).

## 9. Anti-patterns

- **Sem timeout** (ou o default infinito).
- **Retry em tudo**, em todas as camadas, sem backoff/jitter, ou em operação não idempotente.
- **Fallback que mente** (devolver dado inventado para uma decisão de negócio) ou que **engole** o erro silenciosamente.
- **Breaker contando erros de negócio (`404`, `400`)** como falha — abre sem motivo.
- **Um breaker global** em vez de por dependência; limites copiados sem calibrar.
- **Liveness probe dependente do downstream** (reinício em cascata).
- **Fila ilimitada** (thread pool/bulkhead com espera infinita) escondendo a lentidão.
- **Chamada de rede dentro de `@Transactional`**.
- **Resilience4j + `@Retryable` no mesmo método**; anotação em chamada `this.` (sem efeito).
- **Nunca testar a falha** — "já tem circuit breaker" não é prova.

---

## Regras principais

- **Timeout em toda chamada de saída** (conexão e leitura), com orçamento coerente entre os hops; é a base — sem ele os demais padrões não bastam.
- **Retry só em operação idempotente, só em erro transitório, limitado (2–3), com backoff exponencial + jitter e em um só lugar da cadeia** (retry storm); nunca em `4xx` de negócio; respeite `Retry-After`.
- **Circuit breaker + bulkhead por dependência crítica**, nomeados e calibrados; `minimumNumberOfCalls`; **`ignoreExceptions` para erros de negócio**; bulkhead sem fila escondida.
- **Fallback honesto:** degrade com dado seguro marcado, ou falhe rápido com `503`; **nunca invente dado de negócio** nem "aprove por padrão".
- Aplique no **adapter/ACL** (`service-communication`); proxy AOP (não funciona em `this.`); breaker aberto → `503` com `Retry-After`.
- Resilience4j para breaker/rate limiter/métricas; `@Retryable`/`@ConcurrencyLimit` do Spring 7 para o simples (**confirme** a API nova); nunca os dois no mesmo método. Confirme starters/AOP do Boot 4.
- Métricas e **alertas** (breaker aberto, bulkhead cheio, retries); **liveness nunca depende de downstream**.
- Reduza o acoplamento síncrono (fila + DLQ), **load shedding**, escala consciente (`réplicas × pool`), infra (probes, PDB, multi-AZ).
- **Teste a falha:** WireMock (delay/5xx/reset), breaker abre e recupera, `404` não abre, Toxiproxy, chaos (FIS/Chaos Mesh) com hipótese e abort condition.
- **Sem Lombok** — deliberado.
