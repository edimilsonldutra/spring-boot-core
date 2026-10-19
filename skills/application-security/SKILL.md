---
name: application-security
description: Segurança de aplicação (AppSec) em APIs Spring Boot 4, guiada pelo OWASP API Security Top 10 — autorização por objeto e por função (IDOR/BOLA), mass assignment, consumo de recursos e rate limit, injeção, SSRF, desserialização e XML, security headers e CORS, segredos e criptografia, erros e logs, dependências e SBOM, configuração segura e testes de segurança (unit, integração, ZAP, CodeQL, secret scanning). Use ao criar ou revisar qualquer endpoint, antes de expor uma API ou quando pedirem uma revisão de segurança.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md) e [`../authentication/SKILL.md`](../authentication/SKILL.md) (JWT, `SecurityConfig`, BCrypt, `@PreAuthorize`). Desenho de ameaças por feature: [`../threat-modeling/SKILL.md`](../threat-modeling/SKILL.md). Dados pessoais: [`../privacy-lgpd/SKILL.md`](../privacy-lgpd/SKILL.md).

# Segurança de aplicação

A autenticação (`authentication`, `aws-cognito`) responde **quem é** o usuário. Esta skill cobre o resto: **o que ele pode fazer**, o que a API aceita, o que ela devolve, o que ela registra e como ela é configurada. A maioria das falhas reais em APIs não é criptografia quebrada — é **um endpoint que não confere se o recurso pertence a quem pediu**.

Esta skill segue o **OWASP API Security Top 10 (edição 2023)**. Para aplicações com interface web, o **OWASP Top 10** geral complementa — consulte a edição atual em owasp.org.

| # | Risco (OWASP API 2023) | Seção |
|---|---|---|
| API1 | Broken Object Level Authorization (IDOR/BOLA) | 1 |
| API2 | Broken Authentication | 2 |
| API3 | Broken Object Property Level Authorization (mass assignment, exposição de campos) | 3 |
| API4 | Unrestricted Resource Consumption | 4 |
| API5 | Broken Function Level Authorization | 1 |
| API6 | Unrestricted Access to Sensitive Business Flows | 4 |
| API7 | Server Side Request Forgery | 6 |
| API8 | Security Misconfiguration | 7, 8 |
| API9 | Improper Inventory Management | 10 |
| API10 | Unsafe Consumption of APIs | 6 |

Injeção, segredos, logs e dependências atravessam vários itens e têm seções próprias (5, 9, 10, 11).

---

## 1. Autorização: por função e por objeto

**Por função (API5)** — quem pode chamar o endpoint. O `SecurityConfig` termina em `anyRequest().denyAll()` e os métodos usam `@PreAuthorize` (`authentication`). Endpoints administrativos ficam sob uma permissão própria, nunca "escondidos" atrás de uma URL difícil.

**Por objeto (API1, o risco nº 1)** — se **este** recurso pertence a quem pediu. O `@PreAuthorize` não resolve: o usuário tem a permissão `LOAN_READ`, mas não pode ler o empréstimo **de outro**. A checagem fica no **service**, na própria consulta:

```java
@Transactional(readOnly = true)
public LoanDTO findById(Long id) {
    var userId = currentUser.id();
    var entity = repository.findByIdAndUserId(id, userId)
        .orElseThrow(() -> new ResourceNotFoundException("No records found for this ID!"));
    return parseObject(entity, LoanDTO.class);
}
```
- **Filtre pelo dono na query** (`findByIdAndUserId`), não carregue tudo e confira depois — esquecer o "confira depois" em um método é o bug.
- Recurso de outro usuário responde **404**, não 403: o 403 confirma que o id existe (enumeração).
- `currentUser` vem do `SecurityContextHolder` (um componente pequeno que lê o `Authentication`), **nunca** de um parâmetro, header (`X-User-Id`) ou campo do body enviado pelo client.
- Vale para **toda** operação que recebe um id: GET, PUT, DELETE, download de arquivo (`file-upload-download`), exportação (`file-import-export`), sub-recursos (`/loans/{id}/items`).
- Ids sequenciais facilitam a enumeração, mas **trocar por UUID não substitui a checagem** — só dificulta adivinhar.
- Listagens também filtram pelo dono (`findAllByUserId(userId, pageable)`).

---

## 2. Autenticação (API2)

Os detalhes estão em `authentication` (JWT próprio) e `aws-cognito` (login gerenciado). Os pontos que mais falham:
- **Força bruta no login:** limite tentativas por usuário e por IP (seção 4) e responda com a **mesma mensagem e o mesmo tempo** para usuário inexistente e senha errada (sem enumeração).
- Token com expiração curta, assinatura **verificada** (`verify`, nunca só `decode`), algoritmo fixo no servidor; refresh token com rotação.
- Recuperação de senha: token aleatório (`SecureRandom`), de uso único, com expiração curta, guardado como **hash**; a resposta é a mesma exista ou não o e-mail.
- Troca de senha e de e-mail exigem a senha atual.
- Senhas: `DelegatingPasswordEncoder` com BCrypt (ou Argon2); nunca MD5/SHA-1/SHA-256 puros.

---

## 3. Propriedades: o que entra e o que sai (API3)

**Mass assignment** — o client envia um campo que não deveria poder alterar (`id`, `role`, `enabled`, `ownerId`, `price` num pedido):
- Entities **nunca** são o `@RequestBody` (já é regra do pacote — `code-organization`). Para operações sensíveis, use um DTO de request **só com os campos editáveis** (`data/dto/request/`), em vez do DTO completo.
- O `update` copia campo a campo (`spring-data-jpa`) — nunca "copie tudo do DTO para a entity".
- `id` e campos calculados: `@JsonProperty(access = JsonProperty.Access.READ_ONLY)` no DTO de resposta.

**Exposição de dados** — a resposta devolve mais do que a tela precisa:
- DTO de resposta só com o necessário; nada de hash de senha, token, flags internas, dados de outros usuários.
- Campos sensíveis condicionados à permissão de quem lê (mascarar CPF, e-mail) — `privacy-lgpd`.
- Não confie no front para esconder campos: se está no JSON, está exposto.

---

## 4. Consumo de recursos e fluxos sensíveis (API4, API6)

Uma API sem limites é derrubada por um único client (por erro ou de propósito):
- **Paginação obrigatória com tamanho máximo** (`pagination`); limites de upload (`file-upload-download`), de linhas na importação (`file-import-export`), de tamanho de body e de itens em listas recebidas (`@Size(max = 100)` — `bean-validation`).
- **Timeouts** em toda chamada de saída (`resilience`) e no banco (`spring.jpa.properties.jakarta.persistence.query.timeout`, `spring.transaction.default-timeout`).
- **Rate limit** por usuário/IP: na borda (gateway, Ingress, WAF — `api-gateway`) para o grosso; na aplicação (Bucket4j ou o `RateLimiter` do Resilience4j) para regras de negócio específicas. Responda **429** com `Retry-After`.
- **Fluxos de negócio sensíveis** (cadastro, login, recuperação de senha, compra, envio de e-mail/SMS, cupom): limites próprios, mais apertados, e detecção de automação — eles são abusados mesmo sem bug técnico.
- Expressões regulares de validação simples (sem backtracking catastrófico — ReDoS).

---

## 5. Injeção

- **SQL/JPQL:** sempre parâmetros (`:title` com `@Param`), nunca concatenação — inclusive em `nativeQuery`. Nomes de coluna e ordenação vindos do client: **lista permitida** (`pagination`), porque não podem ser parâmetros.
- **`LIKE`:** escape `%` e `_` do texto do usuário quando o curinga não é desejado.
- **Comandos do sistema:** evite `Runtime.exec`/`ProcessBuilder` com entrada do usuário; se inevitável, lista de argumentos (nunca uma string passada a `sh -c`) e valores de uma lista permitida.
- **Logs:** texto do usuário com quebra de linha forja linhas de log — logs em JSON (`observability`) escapam isso; com logs em texto, remova `\r\n`.
- **Templates e e-mail:** Thymeleaf `th:text` (escapa), nunca `th:utext` com dado do usuário (`email`); headers de e-mail nunca concatenados.
- **Planilhas:** CSV/formula injection na exportação (`file-import-export`).
- **Expressões dinâmicas** (SpEL, OGNL, templates Jasper): nunca avalie expressão vinda do usuário (`pdf-reports`).

---

## 6. Requisições para fora: SSRF e APIs de terceiros (API7, API10)

**SSRF** — a API busca uma URL informada pelo usuário (webhook, "importar de uma URL", avatar por link) e o atacante aponta para dentro da rede: `http://169.254.169.254/` (metadados da nuvem com credenciais), `http://localhost:9090/actuator`, serviços internos.
- Evite aceitar URLs livres. Se o caso de uso exige: **lista permitida de hosts/esquemas** (só `https`), resolva o DNS e **rejeite IPs privados, loopback, link-local e de metadados** (e repita a checagem a cada redirect — ou desligue redirects).
- Na AWS, exija **IMDSv2** nas instâncias/nós (o token de sessão bloqueia o SSRF simples) e dê aos pods credenciais por IRSA, não pelo perfil do nó (`aws-eks`).
- Faça a chamada de um componente isolado, com timeout e limite de tamanho da resposta.

**Consumo inseguro de APIs** — dados vindos de um parceiro ou de outro serviço são **entrada não confiável**: valide schema e tamanho, trate erros e timeouts (`service-communication`, `resilience`), use TLS verificado, e não siga redirects para hosts desconhecidos.

---

## 7. Desserialização e XML

- **Nunca serialização Java nativa** (`ObjectInputStream`) com dados externos — nem em cache, fila ou cookie. Use JSON.
- Jackson: não ligue *default typing* polimórfico global; se precisar de `@JsonTypeInfo`, use `JsonTypeInfo.Id.NAME` com subtipos declarados (`@JsonSubTypes`), nunca `Id.CLASS` com entrada externa.
- Mensageria: `trusted.packages` restrito no Kafka (`kafka`), nunca `*`.
- XML: os parsers do pacote (Jackson XML, POI) já vêm sem resolução de entidades externas. Em um parser próprio (`DocumentBuilderFactory`, `SAXParserFactory`, `XMLInputFactory`), **desligue DTDs** (`http://apache.org/xml/features/disallow-doctype-decl` = `true`) — é o que impede XXE e "billion laughs".

---

## 8. Configuração segura (API8)

### Security headers
O Spring Security já envia por padrão `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cache-Control: no-store…` e `Strict-Transport-Security` em respostas HTTPS. Para uma API JSON, acrescente uma CSP restritiva e a política de referrer na mesma `SecurityFilterChain` de `authentication`:
```java
.headers(headers -> headers
    .contentSecurityPolicy(csp -> csp.policyDirectives("default-src 'none'; frame-ancestors 'none'"))
    .referrerPolicy(referrer -> referrer.policy(ReferrerPolicyHeaderWriter.ReferrerPolicy.NO_REFERRER))
    .httpStrictTransportSecurity(hsts -> hsts.includeSubDomains(true).maxAgeInSeconds(31536000)))
```
- `default-src 'none'` serve para respostas JSON; o **Swagger UI** precisa de scripts e estilos — aplique uma CSP mais permissiva só a `/swagger-ui/**` (uma segunda `SecurityFilterChain` com `securityMatcher`) ou desligue a UI em produção (`swagger-advanced`).
- HSTS só faz efeito sob HTTPS; atrás de um proxy que termina o TLS, configure `server.forward-headers-strategy: framework` para o Spring saber que a request original era HTTPS.

### Checklist de configuração
- **CORS:** origins explícitas no `application.yml`, nunca `*` com credenciais (`web-config`).
- **CSRF:** desligado **só** porque a API é stateless com token em header; se usar cookie de autenticação, religue (`authentication`).
- **Actuator:** porta separada, só `health,info,prometheus` expostos (`observability`).
- **Swagger UI:** desligado ou protegido em produção (`swagger`).
- **Erros:** sem stack trace nem mensagem interna no body (`exception-handling`); `server.error.include-stacktrace: never` e `server.error.include-message: never` no profile de produção.
- **TLS** em toda conexão (cliente → API, API → banco com certificado verificado — `aws-rds-secrets-manager`), versões antigas de TLS desligadas no balanceador.
- **Profiles:** nada de `devtools`, H2 console, endpoints de debug ou usuários de seed de teste em produção.
- **Container:** usuário não root, imagem mínima, sistema de arquivos somente leitura quando possível (`docker-and-docker-compose`, `kubernetes`).

---

## 9. Segredos e criptografia

- Segredos **só** por variável de ambiente ou gerenciador (Secrets Manager, Parameter Store, Vault, Key Vault) — nunca no Git, nunca no `application.yml` de produção, nunca em log, nunca na imagem. A aplicação **falha ao subir** se um segredo obrigatório faltar (sem default inseguro — `authentication`).
- Vazou? **Rotacione** — apagar do Git não basta (está no histórico).
- Tokens e identificadores aleatórios com `SecureRandom` (ou `UUID.randomUUID()`), nunca `Random`/`Math.random()`.
- Não invente criptografia. Para dados sensíveis em repouso, prefira a criptografia do banco/disco/KMS; quando precisar no nível do campo, AES-GCM com chave no KMS e IV único por valor.
- Hash de senha: BCrypt/Argon2 (seção 2). Hash para integridade/identificação: SHA-256 — nunca MD5/SHA-1.
- Compare segredos (tokens, assinaturas de webhook) em tempo constante: `MessageDigest.isEqual(a, b)`.

---

## 10. Inventário, dependências e supply chain (API9)

- **Inventário de APIs:** toda versão exposta é conhecida e documentada (`swagger-advanced`, `api-versioning`); versões antigas têm data de desligamento; nenhum endpoint "esquecido" (debug, versão beta) em produção.
- **Dependências:** o BOM do Boot em dia (patch releases trazem correções de segurança), scanner no CI (`dependency-check`, Dependabot alerts — `maven-config`, `github-actions`) e política: vulnerabilidade **crítica explorável** bloqueia o merge; as demais têm prazo.
- **SBOM:** gere um SBOM CycloneDX no build (`cyclonedx-maven-plugin`, versão por property) e publique com a imagem — saber em minutos se uma CVE nova afeta seus serviços.
- **Imagem:** scan (Trivy) antes do push, base mínima atualizada.
- **Pipeline:** actions fixadas por SHA, permissões mínimas, OIDC em vez de chaves (`github-actions`, `github-actions-aws`, `github-actions-cloud`).

---

## 11. Logs e monitoramento de segurança

- **Registre eventos de segurança**: login (sucesso e falha), refresh, logout, troca de senha, acesso negado (403/404 de autorização), alteração de permissão, exportação em massa. Com o usuário (id, não e-mail), o IP e o trace id.
- **Nunca registre**: senha, token, `Authorization`, segredo, número de cartão, corpo de request com dado pessoal (`privacy-lgpd`).
- **Alertas** para padrões de ataque: pico de 401/403/429, muitas falhas de login para uma conta ou de um IP, acesso a muitos ids diferentes em pouco tempo (enumeração) — `observability`, `aws-observability`.
- Logs com retenção definida e acesso restrito.

---

## 12. Testes de segurança

| Camada | O que testar | Como |
|---|---|---|
| Unit (service) | Checagem de dono: recurso de outro usuário → `ResourceNotFoundException` | `testing`, com o `currentUser` mockado |
| Slice (`@WebMvcTest`) | Cada endpoint sem autenticação → 403; sem a permissão → 403 | `@WithMockUser(authorities = ...)` |
| Integração | Token real; **IDOR** (usuário A lendo/alterando o recurso de B); mass assignment (`role` no body ignorado); limites (size, upload, 429); headers de segurança presentes | `integration-testing` |
| Pipeline | **SAST** (CodeQL), **secret scanning** com push protection, scan de dependências e imagem | `github-actions` |
| DAST | Varredura da aplicação rodando (OWASP ZAP baseline contra o docker compose do CI) | Job no CI; achados triados, não ignorados em bloco |

Para cada endpoint novo, o `qa` cobre pelo menos: sem token, permissão insuficiente, **recurso de outro usuário**, campo proibido no body e entrada acima do limite.

---

## Regras principais

- **Autorização por objeto em toda operação com id**, na própria query (`findByIdAndUserId`); recurso de outro usuário → 404. O usuário atual vem do `SecurityContext`, nunca do client.
- Autorização por função com `@PreAuthorize` e `anyRequest().denyAll()` no fim.
- DTOs de request só com os campos editáveis; `id` read-only; respostas só com o necessário.
- Limites em tudo: paginação, upload, importação, tamanho de listas, timeouts; rate limit (429) — mais apertado em login, cadastro e fluxos de negócio sensíveis.
- Sem concatenação em SQL/JPQL, comandos, logs, templates, headers; listas permitidas para o que não pode ser parâmetro.
- URLs informadas pelo usuário: lista permitida e bloqueio de IPs internos/metadados (SSRF); dados de terceiros são entrada não confiável.
- Sem serialização Java nativa nem default typing polimórfico; parsers XML sem DTD.
- Security headers (CSP restritiva, HSTS, referrer), CORS explícito, Actuator isolado, Swagger UI protegido, erros sem detalhe interno em produção.
- Segredos fora do Git e da imagem, falha ao subir sem eles, rotação quando vazar; `SecureRandom`; comparação em tempo constante.
- Dependências escaneadas, SBOM gerado, imagem escaneada, pipeline com OIDC e permissões mínimas.
- Eventos de segurança registrados sem dados sensíveis, com alertas para padrões de ataque.
- Testes de IDOR, permissão, mass assignment e limites em todo endpoint novo; SAST, secret scanning e DAST no pipeline.
- **Sem Lombok** — deliberado.
