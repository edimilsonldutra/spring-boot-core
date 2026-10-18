---
name: api-gateway
description: API Gateway e BFF com Spring Cloud Gateway — rotas, filtros, circuit breaker, rate limit, CORS, token relay, autenticação na borda sem confiar em headers de identidade externos, e comparação com Ingress/ALB/AWS API Gateway/service mesh. Use quando criar ou revisar a porta de entrada de microsserviços ou um backend for frontend.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../microservices/SKILL.md`](../microservices/SKILL.md), [`../service-communication/SKILL.md`](../service-communication/SKILL.md) e [`../resilience/SKILL.md`](../resilience/SKILL.md). Autenticação: `authentication` ou `aws-cognito`.

# API Gateway e BFF

O **API Gateway** é a **porta de entrada única** dos clientes externos para os microsserviços: recebe a request, **autentica, limita, roteia** e devolve a resposta. Sem ele, o cliente precisaria conhecer cada serviço (endereços, auth, versões) e cada serviço reimplementaria as mesmas preocupações de borda.

## O que o gateway faz — e o que NÃO deve fazer

| ✅ Responsabilidades da **borda** (transversais) | ❌ **Não** coloque no gateway |
|---|---|
| **Roteamento** (`/api/catalog/**` → `catalog`) e versionamento de rota | **Regra de negócio** (vira um monolito disfarçado e gargalo de times) |
| **Terminação TLS** | Orquestração complexa de domínio (isso é `saga-pattern`) |
| **Autenticação** (validar JWT) e autorização **grossa** (rota/escopo) | Acesso a banco de dados |
| **Rate limiting**, quotas, proteção contra abuso | Transformações de dados pesadas e específicas de um serviço |
| **CORS**, headers de segurança, `X-Request-Id`/trace | Estado de sessão de negócio |
| **Circuit breaker/timeout/retry** na borda | |
| **Composição** simples para o front (BFF/API composition) | |
| Logging/métricas/tracing de entrada | |

**O gateway deve ser fino e "burro" quanto ao domínio.** Quando regra de negócio entra no gateway, **todo time precisa mexer nele** e ele vira o gargalo de entrega e de falha de toda a arquitetura (um *single point of failure* e de acoplamento).

## Escolha a ferramenta certa

| Opção | Quando | Observação |
|---|---|---|
| **Spring Cloud Gateway** | Equipe Spring, lógica de borda **em Java** (filters customizados, composição/BFF), roteamento dinâmico | Você opera um serviço a mais (HA, escala, patches) |
| **Ingress (NGINX/ALB Ingress) / Kubernetes Gateway API** | Roteamento simples por host/path, TLS, no cluster (`kubernetes`, `aws-eks`) | **Sem código**, baratíssimo; menos flexível para composição/auth custom |
| **AWS API Gateway** (REST/HTTP API) | Serverless/Lambda (`aws-lambda`), quotas e *usage plans* para parceiros, autorizador JWT do Cognito nativo | Gerenciado, cobra por request; acoplamento à AWS |
| **Service mesh** (Istio/Linkerd) | Tráfego **leste-oeste** (serviço-a-serviço): mTLS, retries, *traffic split* | Não substitui o gateway de **entrada** (norte-sul) — veja `service-communication` |
| **Gateway comercial** (Kong, Apigee…) | Portal de desenvolvedor, monetização, governança de APIs em escala | Custo/licença e outra plataforma a operar |

**Regra prática:** **comece com o Ingress/ALB** (roteamento + TLS); adicione **Spring Cloud Gateway** (ou AWS API Gateway) **quando precisar de lógica de borda** que o ingress não faz — auth centralizada customizada, rate limit por usuário, composição/BFF. Não monte um gateway Spring para fazer só o que o ingress já faz.

---

## 1. Spring Cloud Gateway

> **Versões:** o Spring Cloud Gateway tem **duas variantes** (WebFlux reativa e **Server WebMVC**, com virtual threads — `java-modern-features`) e **os nomes dos starters e o prefixo das properties mudaram nas versões recentes** do Spring Cloud. **Confirme na documentação/Context7 da versão resolvida** (`maven-config`) o artifact e o prefixo exatos antes de copiar — os trechos abaixo mostram a **estrutura**, que é estável.

```xml
<dependency>
    <groupId>org.springframework.cloud</groupId>
    <artifactId>spring-cloud-starter-gateway-server-webflux</artifactId>
</dependency>
```
(BOM `spring-cloud-dependencies` na **linha compatível com o Boot do projeto**, em `<dependencyManagement>`.) O gateway é um **projeto separado** do `scaffold` (um serviço próprio), **não** um módulo dentro de uma API de negócio.

### Rotas, predicates e filters

Uma **rota** = *id* + **predicates** (quando casa) + **filters** (o que fazer) + **uri** (destino).
```yaml
spring:
  cloud:
    gateway:
      routes:
        - id: catalog
          uri: http://library-catalog:8080
          predicates:
            - Path=/api/catalog/**
          filters:
            - StripPrefix=1
            - name: CircuitBreaker
              args:
                name: catalog
                fallbackUri: forward:/fallback/catalog
            - name: RequestRateLimiter
              args:
                redis-rate-limiter.replenishRate: 20
                redis-rate-limiter.burstCapacity: 40
                key-resolver: "#{@userKeyResolver}"
        - id: lending
          uri: http://library-lending:8080
          predicates:
            - Path=/api/lending/**
          filters:
            - StripPrefix=1
```
(Aqui o prefixo `spring.cloud.gateway.routes` é o clássico; **nas versões recentes ele pode ser `spring.cloud.gateway.server.webflux.routes`** — confirme.) O **`uri`** usa o **nome DNS do Service** do Kubernetes (`http://library-catalog:8080` / `.library.svc.cluster.local`) ou o **Service Connect** do ECS (`service-communication`) — **não** IPs, **não** Eureka no Kubernetes.

Em **Java**, a mesma rota com mais controle:
```java
@Bean
RouteLocator routes(RouteLocatorBuilder builder) {
    return builder.routes()
            .route("catalog", r -> r.path("/api/catalog/**")
                    .filters(f -> f.stripPrefix(1)
                            .circuitBreaker(c -> c.setName("catalog").setFallbackUri("forward:/fallback/catalog")))
                    .uri("http://library-catalog:8080"))
            .build();
}
```
Filters úteis: `StripPrefix`, `RewritePath`, `AddRequestHeader`, `RemoveRequestHeader`, `Retry`, `CircuitBreaker`, `RequestRateLimiter`, `TokenRelay`, `SetRequestHeader`; e **filters globais** (`GlobalFilter`) para o que vale em todas as rotas (correlation id, log de acesso).

### Timeouts e retries (sempre)

Defina **timeouts de conexão e resposta** (`spring.cloud.gateway...httpclient.connect-timeout`/`response-timeout`) **menores que o timeout do cliente** — senão o gateway segura conexões de upstreams mortos. **Retry só em GET/idempotentes** e com limite (`Retry` filter com `methods: GET`, `retries: 2`, `backoff`); **nunca** retentar `POST` sem chave de idempotência (`idempotency`, `resilience` — retries amplificam falha). O **circuit breaker** (Resilience4j via Spring Cloud CircuitBreaker) com **fallback** (resposta degradada ou 503 claro) evita que um serviço lento esgote o gateway.

### Rate limiting
`RequestRateLimiter` com **Redis** (algoritmo *token bucket*; `caching` para o Redis/ElastiCache), **chave por usuário/API key/IP** (`KeyResolver`). Em borda pública também considere **AWS WAF**/CDN (`aws-eks`, seção ALB) para abuso volumétrico — o limite por usuário é complemento, não substituto. Devolva **`429 Too Many Requests`** com `Retry-After`.

### CORS
Configure **CORS no gateway** (`spring.cloud.gateway...globalcors`) com **origens explícitas** (não `*` com credenciais — `web-config`) e **não repita** nos serviços atrás dele (dupla configuração gera headers duplicados e erros).

---

## 2. Autenticação na borda — e defesa em profundidade

O gateway é o lugar natural para **validar o token** uma vez e rejeitar o tráfego não autenticado **antes** de chegar aos serviços. Com Spring Security no gateway como **OAuth2 Resource Server** (`aws-cognito`: `issuer-uri` do User Pool, validar `token_use=access` e `client_id`):
- Rotas públicas (`/auth/**`, `/actuator/health`) liberadas; **todo o resto exige JWT válido**; `anyRequest().denyAll()` (`authentication`).
- **Autorização grossa** na borda (a rota exige o escopo `library/read`); **autorização fina** (dono do recurso, regra de negócio) **fica no serviço**.

**Defesa em profundidade — o gateway NÃO é a única barreira:**
1. **Os serviços também validam o JWT** (ou autenticam a chamada do gateway). Se o gateway for contornado (outro caminho de rede, um pod malicioso, erro de configuração do Ingress), um serviço que confia "cegamente" no gateway fica aberto. **Zero trust:** a rede interna **não** é confiável (`service-communication`).
2. **Repassar a identidade:** o gateway **repassa o JWT original** (`TokenRelay`/header `Authorization`) e os serviços o validam de novo e leem o `sub`. Evite que o serviço dependa de um header "`X-User-Id`" pré-validado.
3. **Se usar headers de identidade internos** (`X-User-Id`, `X-User-Roles`) por performance: o gateway **precisa remover esses headers da request de entrada** (`RemoveRequestHeader`) **antes** de gravar os seus — senão **qualquer cliente forja** `X-User-Id: admin`. E os serviços só os aceitam de **fonte autenticada** (mTLS/NetworkPolicy). É uma das falhas de segurança mais comuns em gateways.
4. **NetworkPolicy** (`kubernetes`): os serviços só aceitam tráfego **do gateway** e de outros serviços autorizados, nunca da internet.

## 3. BFF (Backend for Frontend) e API Composition

Um **BFF** é um gateway/serviço **dedicado a um tipo de cliente** (web, mobile, parceiros), que **adapta e compõe** as APIs internas para o que **aquela UI** precisa — payloads sob medida, menos viagens (`/home` devolve livros em destaque + empréstimos do usuário numa chamada só).

**API Composition** (como consultar dados de **vários serviços** sem JOIN — `microservices`, seção 3):
```java
@GetMapping("/api/bff/home")
public Mono<HomeResponse> home(@AuthenticationPrincipal Jwt jwt) {
    var featured = catalogClient.featured();
    var loans = lendingClient.loansOf(jwt.getSubject());
    return Mono.zip(featured, loans)
            .map(t -> new HomeResponse(t.getT1(), t.getT2()));
}
```
- **Chamadas em paralelo**, com **timeouts** e **degradação graciosa** (se `lending` falha, devolva o catálogo e um campo `loans: null` com aviso — `resilience`); nunca falhe a tela inteira por um bloco opcional.
- **Um BFF por canal** (web ≠ mobile) quando as necessidades divergem; **evite** um "gateway que serve tudo para todos" (vira o monolito de novo). Um BFF **pertence ao time do front** que o consome, não a um time central de plataforma.
- Composição **só de leitura**/agregação de apresentação. **Transações entre serviços** são **saga** nos serviços, **nunca** no BFF.
- Alternativa: **GraphQL** (um grafo, o cliente escolhe os campos) — avalie quando há muitos clientes com necessidades muito variadas; traz custos próprios (N+1, cache, autorização por campo).

## 4. Operação do gateway

- **Alta disponibilidade:** o gateway é **crítico** — **mínimo 2–3 réplicas** em zonas distintas, **HPA**, **PDB**, probes e graceful shutdown (`kubernetes`, `observability`); **stateless** (sem sessão em memória; rate limit no Redis). Uma queda dele derruba **todo** o acesso.
- **Observabilidade:** o gateway é o **melhor ponto para o `traceId`**: gere/propague `X-Request-Id` e o contexto de trace (`observability`, `aws-observability`); métricas **por rota** (taxa, erros, latência p99 — `http.server.requests`/`spring.cloud.gateway.requests`), alarmes em 5xx e em **circuit breakers abertos**. **Access log** estruturado (sem tokens, sem PII).
- **Segurança operacional:** TLS, headers (`Strict-Transport-Security`, etc.), limite de **tamanho de body e de headers**, remoção de headers sensíveis nas respostas (`Server`, stack traces — `exception-handling`), **WAF** à frente. Atualize o gateway com frequência (é a superfície exposta).
- **Configuração de rotas como código** (no Git, revisada — `argocd`/`kubernetes`); rotas **dinâmicas** (de um serviço de configuração) só com muito critério.
- **Latência:** cada hop acrescenta tempo; mantenha os filters **baratos** e **não bloqueantes** (na variante WebFlux, **nunca** chame código bloqueante no event loop — use a variante **Server WebMVC** com virtual threads se a lógica for bloqueante).
- **Versionamento:** `/v1`, `/v2` no path roteado para versões do serviço (`microservices`); o gateway ajuda a **depreciar** uma versão (header `Deprecation`/`Sunset`).

## 5. Testes

- **Unit/slice:** os `GlobalFilter` e `KeyResolver` como classes simples; as rotas com **`WebTestClient`** apontando para **WireMock** (`@AutoConfigureWireMock`/Testcontainers `wiremock`) simulando o serviço upstream: *rota correta*, `StripPrefix` aplicado, header de identidade **removido da entrada e reescrito**, 401 sem token, 429 ao exceder o limite, **fallback** quando o upstream devolve 500/atrasa.
- **Falhas:** upstream **lento** (delay do WireMock) → timeout e circuit breaker abrem; upstream **fora** → 503 com fallback (`resilience`).
- **Segurança:** teste explicitamente que um cliente **não consegue forjar** os headers de identidade (envie `X-User-Id` na request de entrada e verifique que o serviço recebe o valor do **token**, não o forjado).
- **Contrato:** o gateway é um **consumidor** das APIs internas — contract tests (`contract-testing`) protegem as rotas/compositions de quebra.

---

## Regras principais

- O gateway cuida de **preocupações transversais da borda** (roteamento, TLS, auth grossa, rate limit, CORS, trace); **nunca regra de negócio, banco ou orquestração de domínio**.
- **Ingress/ALB primeiro**; Spring Cloud Gateway/AWS API Gateway **quando precisar de lógica de borda**; mesh é leste-oeste, não substitui o gateway de entrada.
- **Confirme na versão** o artifact e o prefixo de properties do Spring Cloud Gateway (mudaram); `uri` por **DNS do Service/Service Connect**, nunca IP.
- **Timeouts sempre** (menores que os do cliente); **retry só idempotente e limitado** (nunca `POST` sem chave de idempotência); **circuit breaker + fallback**; rate limit por usuário (Redis) + WAF; `429` com `Retry-After`.
- **Defesa em profundidade:** os serviços **também validam o JWT**; **remova headers de identidade vindos de fora** antes de gravar os seus; **NetworkPolicy** só do gateway para os serviços; zero trust na rede interna.
- **BFF por canal**, de propriedade do time do front, só leitura/composição **em paralelo com degradação graciosa**; **sem transação entre serviços no BFF**.
- Gateway **crítico**: ≥ 2–3 réplicas, HPA, PDB, stateless; `traceId` na entrada; métricas por rota; alarmes em 5xx e circuit breakers abertos; sem blocking no event loop.
- CORS **só no gateway**, origens explícitas; rotas como código no Git.
- Teste rotas com WireMock, falhas upstream, segurança (**headers forjados**) e contratos.
- **Sem Lombok** — deliberado.
