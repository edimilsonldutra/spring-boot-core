---
name: observability
description: Observabilidade no Spring Boot 4 — Actuator em porta separada, liveness × readiness, métricas Micrometer e Prometheus, métricas e health indicators customizados, tracing OpenTelemetry, logs JSON com trace id e o que monitorar (RED/USE). Use quando adicionar health checks, métricas, tracing ou logs estruturados; é a base das probes do Kubernetes.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) e [`../code-style/SKILL.md`](../code-style/SKILL.md) para as preferências do projeto, o package layout base e as convenções de code style.

# Observability

Os três sinais: **metrics** (números agregados: quantos, quão rápido, quantos erros), **logs** (eventos) e **traces** (o caminho de uma request entre serviços). Sem eles, produção é uma caixa preta. Esta skill dá a base; `kubernetes` consome as probes, `aws-eks` entrega logs/metrics para a AWS.

---

## Dependencies

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-actuator</artifactId>
</dependency>
<dependency>
    <groupId>io.micrometer</groupId>
    <artifactId>micrometer-registry-prometheus</artifactId>
    <scope>runtime</scope>
</dependency>
```
O BOM gerencia as versões. O Boot 4 modularizou a auto-configuration (veja `maven-config`): se um endpoint ou registry não aparecer, confirme no Context7 o starter/módulo exato da versão resolvida em vez de assumir o nome do Boot 3.

## application.yml

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,prometheus
  endpoint:
    health:
      probes:
        enabled: true
      show-details: when-authorized
  health:
    livenessstate:
      enabled: true
    readinessstate:
      enabled: true
  server:
    port: 9090
  metrics:
    tags:
      application: ${spring.application.name}
```
- **Exponha só o necessário.** `include: health,info,prometheus`. Nunca `*` em produção: `env`, `beans`, `heapdump` e `threaddump` vazam segredos e estrutura interna. `heapdump` entrega a memória do processo inteira.
- **`management.server.port: 9090`** serve o Actuator em uma porta separada da API. O `Service`/Ingress só publica a 8080; o Prometheus e o kubelet acessam a 9090 dentro do cluster. Assim não é preciso liberar `/actuator` no `SecurityConfig` público (veja `authentication`).
- `show-details: when-authorized` — os detalhes (database, disco) só aparecem para usuários autenticados; os probes recebem só `UP`/`DOWN`.
- `metrics.tags.application` etiqueta toda métrica com o nome do serviço — essencial para filtrar no Grafana.

---

## Liveness vs readiness (o erro mais comum)

Com `probes.enabled: true` (já é automático dentro do Kubernetes) existem:
- `/actuator/health/liveness` — "o processo está vivo ou travado?" Se falhar, o Kubernetes **reinicia** o pod.
- `/actuator/health/readiness` — "posso receber tráfego agora?" Se falhar, o pod sai do Service, **sem reiniciar**.

**Liveness não pode depender de database nem de serviços externos.** Se o RDS cair e o liveness falhar, o Kubernetes reinicia **todos** os pods em cascata e piora o incidente. Dependências ficam na readiness (e somente as que tornam o pod inútil). O grupo `liveness` padrão do Boot só verifica o estado interno da aplicação — não o adultere.

Para controlar o que entra em cada grupo:
```yaml
management:
  endpoint:
    health:
      group:
        readiness:
          include: readinessState,db
```
Use esses endpoints nas probes do Deployment (veja `kubernetes`).

---

## Metrics customizadas (Micrometer)

Injete o `MeterRegistry` e meça o que importa para o **negócio** e para o SLO:

```java
@Service
public class BookService {

    private final Counter booksCreated;
    private final Timer findAllTimer;

    public BookService(MeterRegistry registry) {
        this.booksCreated = Counter.builder("books.created").description("Books created").register(registry);
        this.findAllTimer = Timer.builder("books.find.all").register(registry);
    }

    public BookDTO create(BookDTO book) {
        var created = doCreate(book);
        booksCreated.increment();
        return created;
    }
}
```
(Uma exceção justificada à field injection: o registry é necessário para construir os meters.) Alternativas sem código: `@Timed`/`@Observed` com `ObservedAspect` habilitado.

Regras de ouro:
- **Cardinalidade baixa nas tags.** Tag = valor de um conjunto pequeno e fixo (`status`, `method`, `result`). **Nunca** `userId`, `email`, `orderId`, URL com parâmetro: cada valor novo cria uma série e derruba o Prometheus.
- Nomes em `lower.dot.case`; o Micrometer converte para `snake_case` no Prometheus.
- O Boot já entrega, sem código: `http.server.requests` (latência/erros por rota), JVM (heap, GC, threads), `hikaricp.connections.*`, `jdbc`, logback. Comece por elas.

**O que monitorar** — método RED por endpoint (**R**ate, **E**rrors, **D**uration p95/p99) e USE por recurso (**U**tilization, **S**aturation, **E**rrors: CPU, heap, pool de conexões). Alertas úteis: taxa de 5xx, latência p99, `hikaricp.connections.pending > 0`, heap perto do limite, pod restarts.

## Health indicator customizado

Para uma dependência que torna o pod inútil (e que você incluiu na readiness):
```java
@Component
public class PaymentGatewayHealthIndicator implements HealthIndicator {

    @Autowired
    private PaymentGatewayClient client;

    @Override
    public Health health() {
        return client.ping() ? Health.up().build() : Health.down().withDetail("gateway", "unreachable").build();
    }
}
```
Mantenha o check **barato e com timeout curto** — as probes rodam a cada poucos segundos.

---

## Logs estruturados e correlação

Em container, o log vai para **stdout**, e é a plataforma (CloudWatch, Loki) que coleta. Nada de arquivo de log no container. Em produção use JSON, que o agregador consegue indexar:

```yaml
logging:
  structured:
    format:
      console: ecs
```
(`ecs`, `logstash` ou `gelf`.) Em dev local mantenha o formato texto padrão.

- **Níveis:** `ERROR` = precisa de atenção humana; `WARN` = anormal mas tratado; `INFO` = marcos de negócio; `DEBUG` = diagnóstico (desligado em produção).
- **Nunca logue** senha, token, CPF/cartão, corpo completo de request com dado pessoal. Isso é incidente de LGPD.
- Logue com placeholders `{}` (veja `code-style`), e passe a exception como **último argumento** para sair o stack trace: `logger.error("Failed to create {}", id, ex)`.
- **Trace id no log:** com tracing ligado, o Boot coloca `traceId`/`spanId` no MDC e nos logs estruturados — é o que permite achar todos os logs de uma request (e correlacionar com o erro devolvido ao client em `exception-handling`).

## Tracing distribuído

Para seguir uma request por vários serviços, o Boot usa Micrometer Tracing com OpenTelemetry (o Boot 4 traz um starter OpenTelemetry próprio — confirme o nome no Context7). Configuração mínima:
```yaml
management:
  tracing:
    sampling:
      probability: 0.1
```
- Em produção amostre (`0.05`–`0.2`); `1.0` só em dev, ou o custo de armazenamento explode.
- Exporte por OTLP para um collector (AWS Distro for OpenTelemetry / X-Ray, Tempo, Jaeger): `management.otlp.tracing.endpoint`. O collector roda como DaemonSet/sidecar — ver `aws-eks`.
- Propagação automática nos `RestClient`/`WebClient`/`RestTemplate` criados a partir dos **builders do Spring** (injete o `RestClient.Builder`; não use `new`).

---

## Testando

Teste que o health responde e que a métrica existe, sem inventar mock: um `@SpringBootTest` com `@AutoConfigureObservability`/porta aleatória chamando `/actuator/health/readiness` e `/actuator/prometheus` (veja `integration-testing`). Para a readiness com database, o Testcontainers já sobe o database real.

---

## Regras principais

- Exponha só `health,info,prometheus`; **nunca** `*` em produção. Actuator em porta separada (`management.server.port`).
- **Liveness nunca depende de database/serviço externo**; dependências ficam na readiness.
- Tags de métricas com cardinalidade baixa — nunca ids de usuário/pedido.
- Etiquete tudo com `application` e meça RED/USE; alerte em 5xx, p99, pool pendente e restarts.
- Logs em stdout, JSON estruturado em produção, com `traceId`; nunca dado sensível; exception como último argumento.
- Tracing com amostragem em produção, exportado por OTLP; use os builders do Spring para propagar o contexto.
- Confirme starters/pacotes do Boot 4 na versão resolvida.
- **Sem Lombok** — deliberado.
