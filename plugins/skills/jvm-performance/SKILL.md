---
name: jvm-performance
description: Performance de Spring Boot em container — método (medir, achar o gargalo, mudar uma coisa), queries e N+1, HikariCP, memória e GC no pod (MaxRAMPercentage), startup (CDS/AOT), diagnóstico com JFR e dumps, e teste de carga. Use quando a API estiver lenta, o pod levar OOMKilled ou o pool de conexões saturar.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../observability/SKILL.md`](../observability/SKILL.md) e [`../kubernetes/SKILL.md`](../kubernetes/SKILL.md).

# JVM e performance

> **Otimização prematura é a raiz de muito mal.** O método é sempre: **definir o objetivo** (SLO: "p99 < 300 ms a 200 req/s") → **medir** → **achar o gargalo** → **mudar UMA coisa** → **medir de novo**. Sem número antes e depois, você está adivinhando. Nesta ordem de probabilidade, o gargalo costuma ser: (1) queries/índices/N+1, (2) pool de conexões, (3) chamadas externas lentas, (4) memória/GC, (5) CPU da aplicação. O código Java em si raramente é o problema.

---

## 1. Queries primeiro (onde mora 80% dos problemas)

- **N+1** (`spring-data-jpa`): `JOIN FETCH`/`@EntityGraph`/projections; `default_batch_fetch_size` como rede de segurança.
- **Índices** (`flyway-migrations`): em FKs e colunas de `WHERE`/`ORDER BY`. Confirme com `EXPLAIN` (`EXPLAIN ANALYZE` no PostgreSQL) que o índice é usado; um `LIKE '%texto%'` não usa índice B-tree comum.
- **Paginação sempre** em listagens (`Pageable`); nunca `findAll()` sem limite numa tabela que cresce. Para tabelas grandes, paginação por **keyset** (`WHERE id > :last ORDER BY id LIMIT n`) é bem mais rápida que `OFFSET` alto.
- **Leia só o necessário:** projection/DTO em vez de entity completa com colunas grandes (`TEXT`/`BLOB`).
- **`@Transactional(readOnly = true)`** nas leituras.
- **Escritas em lote:** com `IDENTITY` o Hibernate não agrupa inserts (`spring-data-jpa`); para cargas grandes use `JdbcTemplate.batchUpdate` ou `INSERT ... SELECT`.
- Procure queries lentas no próprio database (slow query log do RDS, Performance Insights) — é a fonte mais confiável.

## 2. Pool de conexões (HikariCP)

O Boot usa o HikariCP. O número de conexões **não** deve ser "o maior possível": o database tem poucos cores e muitas conexões ativas só geram contenção. Regra prática (da documentação do Hikari): `conexões ≈ (cores do database × 2) + discos efetivos` — normalmente um pool **pequeno** (5–20 por instância) vence um grande.

```yaml
spring:
  datasource:
    hikari:
      maximum-pool-size: 10
      minimum-idle: 5
      connection-timeout: 3000
      idle-timeout: 600000
      max-lifetime: 1500000
      leak-detection-threshold: 20000
```
- **`connection-timeout` curto** (3 s): é quanto uma request espera por uma conexão; melhor falhar rápido (e aparecer na métrica) do que empilhar threads.
- **`leak-detection-threshold`** loga o stack trace de quem segurou uma conexão por tempo demais (vazamento ou transação longa) — útil para achar `@Transactional` abrangente demais ou I/O externo dentro de transação. **Nunca chame uma API externa dentro de uma transaction**: ela segura a conexão durante a espera.
- **Conta do cluster:** `réplicas × maximum-pool-size ≤ max_connections do database` (com folga). HPA de 10 réplicas × pool 10 = 100 (`aws-rds-secrets-manager`; considere RDS Proxy).
- Metrics: `hikaricp.connections.active`, `.pending`, `.timeout`, `.acquire`. **`pending > 0` sustentado** = pool saturado (o gargalo está no database ou nas transações longas, não em "falta de conexões").

## 3. Memória e GC da JVM em container

- **`-XX:MaxRAMPercentage=75`** (veja `docker-and-docker-compose`/`kubernetes`): o heap é calculado a partir do **limite do container**; deixe ~25% para metaspace, stacks de thread, buffers diretos e código nativo. `OOMKilled` (exit 137) com heap "folgado" = memória *não-heap* estourou o limite.
- **GC:** o **G1** (default na maioria dos casos) é uma boa escolha geral. Em containers com **menos de 2 CPUs ou ~1,8 GB**, a JVM escolhe o **SerialGC** automaticamente — funciona bem para pods pequenos. **ZGC geracional** (`-XX:+UseZGC`) para heaps grandes e latência de pausa muito baixa (exige CPU e memória folgadas). Não troque de GC sem medir pausas (`jvm.gc.pause`).
- **Não copie dezenas de flags** de blog. O ergonomics da JVM moderna acerta quase tudo; cada flag extra é dívida. Comece só com `MaxRAMPercentage`.
- Tamanho inicial do pod: comece com `512Mi–1Gi` de memória e `requests.cpu` 250–500m; ajuste com os gráficos de `jvm.memory.used`/`jvm.gc.*` e `process.cpu.usage`. Heap que sobe e **nunca desce** entre GCs completos = vazamento (use heap dump).
- `-XX:+ExitOnOutOfMemoryError`: em OOM de heap o processo **morre** e o Kubernetes o reinicia, em vez de ficar zumbi. Para análise post-mortem, `-XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=/dump` com um volume (e cuidado: dump contém dados sensíveis).
- **CPU throttling**: um `limits.cpu` baixo faz o GC/JIT serem estrangulados (latência p99 sobe, startup lento). Veja `kubernetes`.

## 4. Startup

Importante para autoscaling e rollouts rápidos.
- **Lazy initialization** (`spring.main.lazy-initialization=true`) acelera o start, mas **esconde erros de configuração até a primeira request** e piora a latência da primeira chamada — evite em produção com probes; ok em dev/teste.
- **AppCDS / cache AOT** (Class Data Sharing): reduz bastante o tempo de start e a memória. Em JDK recentes, `-XX:+AutoCreateSharedArchive -XX:SharedArchiveFile=/tmp/app.jsa` cria/atualiza o arquivo automaticamente na primeira execução; o Spring Boot também documenta suporte a CDS/AOT cache (JEP 483/514/515) — confirme a receita atual para a versão do projeto.
- **Menos beans, menos autoconfiguration**: exclua o que não usa; `spring-boot-starter-*` demais carrega classes inúteis.
- **Flyway** com muitas migrations aumenta o start — Job separado (`kubernetes`) se for grande.
- **GraalVM native image** reduz drasticamente start e memória (ordem de dezenas de ms), ao custo de build lento, menos dinâmica (reflection/proxies precisam de hints), e pior throughput de pico que a JIT. Só vale para cenários específicos (serverless/scale-to-zero); não é o default do pack.
- Dê folga ao `startupProbe` (`kubernetes`) em vez de tornar a app "rápida demais para ser verdade".

## 5. Concorrência

- **Virtual threads** (`java-modern-features`) elevam a concorrência em APIs I/O-bound, mas o gargalo vira o pool/database. Meça.
- Tomcat: `server.tomcat.threads.max` (default 200) com platform threads; com virtual threads o limite é indireto. Limite requests em voo para proteger dependências frágeis (`Semaphore`/bulkhead).
- **Timeouts em tudo que sai da aplicação** (HTTP client, database, SQS): `RestClient` com connect/read timeout. Chamada externa sem timeout é uma *thread presa para sempre* → esgotamento do pool → cascata.
- `@Async`/executors com fila **limitada** e política de rejeição explícita; fila ilimitada esconde a lentidão até virar `OOM`.

## 6. Diagnóstico

| Sintoma | Ferramenta |
|---|---|
| Qual endpoint é lento | métrica `http.server.requests` por `uri` (p95/p99), tracing (`observability`) |
| Onde o tempo/CPU da JVM vai | **JFR** (Java Flight Recorder): `jcmd <pid> JFR.start duration=60s filename=/tmp/rec.jfr` e abra no JDK Mission Control; baixo overhead, seguro em produção |
| Threads travadas/deadlock | `jcmd <pid> Thread.print` (thread dump) — ou `kubectl exec ... -- jcmd 1 Thread.print`; várias amostras espaçadas |
| Vazamento de memória | heap dump (`jcmd <pid> GC.heap_dump /tmp/h.hprof`) analisado no Eclipse MAT; compare dois dumps |
| Pausas de GC | `jvm.gc.pause`, logs `-Xlog:gc*`; |
| Pool saturado | `hikaricp.connections.pending/active`, thread dump mostrando threads esperando `HikariPool.getConnection` |
| Queries lentas | slow query log / Performance Insights do RDS; `EXPLAIN` |

Em produção, o **JFR e as métricas** são seguros; heap dump congela a JVM por segundos e contém dados — faça com cuidado, fora do horário de pico, e nunca guarde/compartilhe sem proteção. O Actuator `heapdump`/`threaddump` **não** deve estar exposto (`observability`).

## 7. Teste de carga

- Ferramentas: **k6** (scripts JS, ótimo para CI), Gatling, JMeter. Rode contra um ambiente **parecido com produção** (mesmo tamanho de pod/database, dados em volume realista) — um teste em laptop com 100 linhas no banco não prova nada.
- **Aqueça** a JVM antes de medir (JIT): ignore os primeiros ~30–60 s ou rode um warm-up.
- Defina o cenário (rampa até N req/s, mix de endpoints), meça **p50/p95/p99**, taxa de erro e saturação (CPU, pool, GC) — não só a média, que esconde a cauda.
- Procure o **ponto de joelho**: a carga em que a latência dispara. Dimensione `requests`/HPA/pool a partir dele, com margem.
- Automatize um teste de carga "smoke" no pipeline (`github-actions-aws`) com *thresholds* (`p(95)<500`, `http_req_failed<1%`) para pegar regressões.

---

## Regras principais

- Meça antes e depois; mude **uma** coisa por vez; tenha um SLO.
- Queries e índices primeiro (N+1, paginação, projections, `readOnly`); nunca API externa dentro de transaction.
- Pool **pequeno** e consciente; `réplicas × pool ≤ max_connections`; `pending > 0` sustentado é sinal de gargalo no database/transações.
- `MaxRAMPercentage=75` e **só isso** para começar; GC padrão; `ExitOnOutOfMemoryError`; sem CPU `limits` apertado.
- Timeouts em toda chamada de saída; filas e pools de threads **limitados**.
- Lazy initialization só em dev; AppCDS/AOT para acelerar o start; native image só com motivo claro.
- Diagnostique com métricas, JFR e dumps (com cuidado); nunca exponha `heapdump`/`threaddump`.
- Teste de carga em ambiente representativo, com warm-up e olhando p99.
