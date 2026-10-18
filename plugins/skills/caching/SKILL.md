---
name: caching
description: Cache no Spring Boot — @Cacheable/@CachePut/@CacheEvict, Caffeine local × Redis/ElastiCache distribuído, TTL e tamanho máximo, desenho de chaves, cachear DTOs (nunca entities), invalidação, stampede, tolerância a falha do cache, hit ratio e testes. Use quando uma leitura medida como cara precisar de cache ou ao revisar um cache existente.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md) e [`../spring-data-jpa/SKILL.md`](../spring-data-jpa/SKILL.md).

# Caching

Cache troca **frescor por velocidade**. É a otimização com mais bugs sutis (dado velho, invalidação esquecida): só cacheie depois de **medir** que a operação é lenta/cara e é lida muito mais do que escrita (`observability`, `jvm-performance`). Muitas vezes o ganho real está em corrigir um N+1 ou criar um índice (`spring-data-jpa`, `flyway-migrations`) — faça isso primeiro.

## Qual cache?

| | Caffeine (local) | Redis (distribuído) |
|---|---|---|
| Onde vive | memória de **cada** pod | servidor externo (ElastiCache) |
| Latência | nanossegundos | ~1 ms (rede) |
| Consistência entre réplicas | **cada pod tem a sua cópia** (pode divergir) | única, compartilhada |
| Sobrevive a restart/deploy | não | sim |
| Custo/ops | zero | um serviço a mais para operar |
| Use para | dados de referência quase estáticos, tolerantes a alguns segundos de atraso | dados que precisam ser coerentes entre réplicas, sessões, rate limit, revogação de tokens |

Com várias réplicas (Kubernetes + HPA), um `@CacheEvict` em um pod **não invalida** o cache local dos outros. Se a coerência importa, use Redis; se o dado tolera TTL curto, Caffeine com TTL de segundos/minutos é simples e rápido.

---

## Spring Cache abstraction

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-cache</artifactId>
</dependency>
```
```java
@Configuration
@EnableCaching
public class CacheConfig {
}
```
```java
@Service
public class BookService {

    @Cacheable(cacheNames = "books", key = "#id")
    @Transactional(readOnly = true)
    public BookDTO findById(Long id) { ... }

    @CachePut(cacheNames = "books", key = "#result.id")
    @Transactional
    public BookDTO update(BookDTO book) { ... }

    @CacheEvict(cacheNames = "books", key = "#id")
    @Transactional
    public void delete(Long id) { ... }
}
```
- `@Cacheable`: se a chave existe, **não executa o método**; senão executa e guarda. `@CachePut` sempre executa e atualiza; `@CacheEvict` remove (`allEntries = true` limpa o cache inteiro — use com parcimônia).
- **Cacheie DTOs, nunca entities JPA**: uma entity em cache arrasta proxies LAZY, estado de sessão e risco de `LazyInitializationException`. O DTO é um valor puro e `Serializable` — como o pack já define.
- **Chave explícita e estável** (`#id`, ou `#a + ':' + #b`). Chave padrão por todos os argumentos serve para parâmetros simples; objetos precisam de `equals/hashCode` corretos.
- **Proxy:** como `@Transactional`, o cache só funciona em chamada **vinda de outra classe**; `this.findById(...)` ignora o cache.
- `null`: por padrão pode ser cacheado; use `unless = "#result == null"` para não cachear ausência (a menos que queira *negative caching* com TTL curto).
- Evite cachear listas paginadas com muitas combinações de parâmetros (explosão de chaves); cacheie o item, ou use um TTL curto.

---

## Caffeine (local)

```xml
<dependency>
    <groupId>com.github.ben-manes.caffeine</groupId>
    <artifactId>caffeine</artifactId>
</dependency>
```
```yaml
spring:
  cache:
    type: caffeine
    cache-names: books
    caffeine:
      spec: maximumSize=1000,expireAfterWrite=5m
```
**Sempre** defina `maximumSize` e `expireAfter*` — cache sem limite é um vazamento de memória que termina em `OOMKilled` (`kubernetes`). Para ligar métricas de hit/miss: `recordStats` no spec (`maximumSize=1000,expireAfterWrite=5m,recordStats`).

## Redis (distribuído, ElastiCache na AWS)

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-data-redis</artifactId>
</dependency>
```
```yaml
spring:
  cache:
    type: redis
    redis:
      time-to-live: 10m
      key-prefix: "library:"
      use-key-prefix: true
  data:
    redis:
      host: ${REDIS_HOST}
      port: 6379
      ssl:
        enabled: true
      timeout: 2s
```
- **TTL sempre** (`time-to-live`): é a rede de segurança contra dado velho e contra crescimento sem fim.
- **`key-prefix`** por aplicação/ambiente: um Redis compartilhado não mistura chaves.
- **Serialização:** por default o Spring usa a serialização Java (por isso os DTOs são `Serializable`, com `serialVersionUID` — e uma mudança incompatível de classe invalida entradas no deploy: use TTL curto ou versione o nome do cache `books-v2`). Serialização JSON é legível e tolerante a evolução, mas exige configurar o `RedisCacheConfiguration` com o serializador JSON da versão do Spring Data Redis resolvida (Jackson 3 no Boot 4 — confirme a classe na documentação).
- **Timeout curto e tolerância a falha:** o cache **não pode derrubar a API**. Com Redis fora, a requisição deve ir ao database, não falhar. Registre um `CacheErrorHandler` que loga e ignora erros de leitura/escrita do cache.
- **ElastiCache:** em subnet privada, security group aceitando só o SG do cluster, TLS em trânsito (`ssl.enabled: true`), criptografia em repouso, e (para disponibilidade) **Multi-AZ com failover**; o endpoint vem por variável de ambiente (`aws-rds-secrets-manager` para o auth token no Secrets Manager).
- Redis também serve para **revogar JWT** (guardar `jti` de tokens revogados até expirar — `authentication`) e para **rate limiting**.

---

## Invalidação e consistência

> "Há duas coisas difíceis em ciência da computação: invalidação de cache e nomear coisas."

- Prefira **TTL curto + evict nas escritas** do próprio serviço. Escritas que ocorrem **fora** da aplicação (ETL, outro serviço, SQL manual) não invalidam o cache — o TTL é a única proteção.
- **Cache stampede (thundering herd):** quando uma chave quente expira, centenas de requests recomputam ao mesmo tempo e derrubam o database. Mitigue com `@Cacheable(sync = true)` (apenas uma thread recalcula, as outras esperam), com TTL com *jitter* (variação aleatória) e/ou refresh antecipado (`refreshAfterWrite` no Caffeine).
- **Write-through vs cache-aside:** o `@Cacheable` é *cache-aside* (lê do cache, senão da fonte). A transação do database pode dar **rollback** depois de um `@CachePut`: o cache ficaria com um valor que nunca foi confirmado. Para dados críticos, faça o evict **depois do commit** (`@TransactionalEventListener(phase = AFTER_COMMIT)`) ou deixe a leitura repopular.
- Nunca cacheie dados **por usuário** em chave global (vazamento entre usuários): inclua o identificador do usuário/tenant na chave.
- Nunca cacheie dados sensíveis sem cifrar/TTL curto e sem considerar LGPD.

## Observabilidade do cache

O Micrometer expõe `cache.gets` (hit/miss), `cache.puts`, `cache.evictions`, `cache.size` quando o cache é gerenciado pelo Spring (`observability`). **Hit ratio** = hits / (hits + misses): abaixo de ~50% o cache provavelmente não compensa (chave ruim, TTL curto demais ou dado pouco repetido). Alerte em queda brusca do hit ratio e em aumento de evictions.

## Testes

- Unit test do service **sem** cache (a configuração de cache não é carregada; `testing`).
- Teste o comportamento de cache com `@SpringBootTest` (ou um slice com `@EnableCaching` e `CacheManager` simples) verificando que o 2º `findById` **não** chama o repository (`verify(repository, times(1))`) e que `update`/`delete` invalidam.
- Para Redis real, Testcontainers com `redis:7` (`GenericContainer`); em testes unitários use `spring.cache.type=simple` ou `none`.

---

## Regras principais

- Meça antes de cachear; corrija N+1/índices primeiro.
- Caffeine para dado tolerante a divergência entre pods; Redis para coerência entre réplicas.
- **Sempre** limite de tamanho e TTL; nunca cache sem fronteira.
- Cacheie **DTOs** (valores puros, `Serializable`), nunca entities; inclua o usuário/tenant na chave quando o dado é por usuário.
- O cache não pode derrubar a API: timeouts curtos e `CacheErrorHandler` que ignora falhas.
- Invalidação: TTL curto + evict nas escritas; atenção a rollback, escritas externas e stampede (`sync = true`, jitter).
- ElastiCache privado, com TLS e Multi-AZ; segredo no Secrets Manager.
- Monitore hit ratio e evictions.
