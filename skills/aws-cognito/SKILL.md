---
name: aws-cognito
description: Amazon Cognito com a API Spring Boot como OAuth2 Resource Server — User Pool, app clients, Authorization Code + PKCE e client credentials, validação do access token (token_use, client_id), cognito:groups e scopes como authorities, operações admin pelo SDK e testes. Use quando trocar o JWT próprio por login gerenciado, MFA ou login social. Não use para JWT emitido pela própria API (authentication).
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../authentication/SKILL.md`](../authentication/SKILL.md) (a alternativa com JWT emitido pela própria API) e [`../aws-sdk-java/SKILL.md`](../aws-sdk-java/SKILL.md).

# Amazon Cognito

**Amazon Cognito** é um provedor de identidade **gerenciado**: cadastro, login, recuperação de senha, **MFA**, login social/corporativo (Google, Apple, SAML, OIDC), tokens JWT — sem você guardar senhas. A API Spring Boot deixa de **emitir** tokens e passa só a **validar** os que o Cognito emite (papel de **OAuth2 Resource Server**).

## Cognito ou JWT próprio (`authentication`)?

| | Cognito (esta skill) | JWT próprio (`authentication`) |
|---|---|---|
| Quem guarda/valida senha | **AWS** | Sua API (BCrypt + tabela `users`) |
| MFA, login social, SAML/OIDC, recuperação de conta | **Pronto** | Você implementa |
| Segurança de senha/credenciais | Responsabilidade da AWS (modelo compartilhado) | **Sua**, inteira |
| Dependência/lock-in | AWS | Nenhum |
| Custo | Por usuário ativo mensal (MAU) | Seu código e infra |
| Quando | Produto com usuários finais, necessidade de MFA/federação, equipe quer **não** ser dona de credenciais | API interna simples, poucos usuários, sem requisitos de IdP |

**Padrão para produto com usuários finais na AWS: Cognito.** Escrever login, reset de senha e MFA à mão é risco que a maioria das equipes não deve assumir.

## Conceitos

- **User Pool**: o diretório de usuários + emissor de tokens. O **issuer** é `https://cognito-idp.<região>.amazonaws.com/<userPoolId>`; as chaves públicas (JWKS) ficam em `<issuer>/.well-known/jwks.json`.
- **App Client**: cada aplicação cliente (SPA, mobile, backend) tem o seu, com **fluxos OAuth** permitidos, *callback URLs* e escopos.
- **Fluxos recomendados:**
  - Apps web/mobile com usuário: **Authorization Code + PKCE** (Hosted UI ou SDK do front). **Nunca** *implicit flow* nem guardar o client secret em SPA/mobile (clientes públicos **sem secret**).
  - Serviço-a-serviço (machine-to-machine): **Client Credentials** com *resource server* e **scopes** customizados (`library/read`, `library/write`).
  - **Não** use o fluxo de senha direto (`USER_PASSWORD_AUTH`) vindo do seu próprio backend como "login proxy" — o front deve falar com o Cognito.
- **Tokens:** *ID token* (identidade do usuário — para o **cliente**), *access token* (autoriza chamadas à **API**), *refresh token* (renova). **A API valida o *access token*, nunca o ID token.**
- **Grupos** (`cognito:groups` no token) = papéis (`admin`, `editor`).

---

## Dependencies e configuração

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-oauth2-resource-server</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>
```
```yaml
spring:
  security:
    oauth2:
      resourceserver:
        jwt:
          issuer-uri: https://cognito-idp.${AWS_REGION}.amazonaws.com/${COGNITO_USER_POOL_ID}

app:
  cognito:
    client-id: ${COGNITO_APP_CLIENT_ID}
```
- Com `issuer-uri`, o Spring descobre o JWKS pelo `/.well-known/openid-configuration` e **valida assinatura, expiração e issuer** automaticamente (e cacheia as chaves). `AWS_REGION`, `COGNITO_USER_POOL_ID` e `COGNITO_APP_CLIENT_ID` vêm do **ambiente** (`kubernetes`/`aws-ecs-fargate`) — não são segredo, mas variam por ambiente. **Sem client secret** na API (ela só valida).
- A aplicação precisa alcançar o endpoint do Cognito (JWKS) na **inicialização/primeiro uso**: subnets privadas precisam de NAT ou VPC endpoint. (O `JwtDecoder` por `issuer-uri` consulta o provedor **na criação do bean** — se o Cognito estiver inacessível na subida, a app falha; para subir mesmo assim, configure `jwk-set-uri` direto — a validação do *issuer* continua por validator.)

## SecurityFilterChain

```java
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        return http
                .csrf(csrf -> csrf.disable())
                .cors(cors -> {})
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/actuator/health/**", "/swagger-ui/**", "/v3/api-docs/**").permitAll()
                        .requestMatchers(HttpMethod.DELETE, "/api/**").hasAuthority("ROLE_admin")
                        .requestMatchers("/api/**").authenticated()
                        .anyRequest().denyAll())
                .oauth2ResourceServer(oauth2 -> oauth2
                        .jwt(jwt -> jwt.jwtAuthenticationConverter(jwtAuthenticationConverter())))
                .build();
    }

    private JwtAuthenticationConverter jwtAuthenticationConverter() {
        var groups = new JwtGrantedAuthoritiesConverter();
        groups.setAuthoritiesClaimName("cognito:groups");
        groups.setAuthorityPrefix("ROLE_");

        var scopes = new JwtGrantedAuthoritiesConverter();

        var converter = new JwtAuthenticationConverter();
        converter.setJwtGrantedAuthoritiesConverter(jwt -> {
            var authorities = new ArrayList<GrantedAuthority>(scopes.convert(jwt));
            authorities.addAll(groups.convert(jwt));
            return authorities;
        });
        return converter;
    }
}
```
- **Mesma estrutura de `authentication`** (stateless, CSRF off porque o token vai em header, `.cors(...)`, `anyRequest().denyAll()`), mas **sem** `JwtTokenFilter`, `JwtTokenProvider`, `AuthController`/`/auth/signin` e **sem** tabela de senhas: o login acontece no Cognito. (`/swagger-ui` — veja `swagger`; em produção avalie desabilitar.)
- **Authorities:** o Spring converte o claim **`scope`** em `SCOPE_<scope>` por padrão; os **grupos** (`cognito:groups`) precisam de mapeamento explícito (acima, `ROLE_admin`, `ROLE_editor`). Use `hasAuthority("ROLE_admin")` ou `@PreAuthorize("hasAuthority('ROLE_admin')")`/`hasRole('admin')` (com o prefixo `ROLE_`).
- **Scopes de resource server** (M2M): `hasAuthority("SCOPE_library/write")`.

### Validar `token_use` e `client_id` (importante)

O Cognito **access token não tem claim `aud`** (usa `client_id`), então a validação padrão de *audience* não serve, e **um ID token de outro app client do mesmo User Pool também seria aceito** pela validação de assinatura/issuer. Valide **o tipo do token** e **o client**:
```java
@Bean
JwtDecoder jwtDecoder(@Value("${spring.security.oauth2.resourceserver.jwt.issuer-uri}") String issuer,
                      @Value("${app.cognito.client-id}") String clientId) {
    var decoder = NimbusJwtDecoder.withIssuerLocation(issuer).build();

    OAuth2TokenValidator<Jwt> tokenUseAndClient = jwt -> {
        var accessToken = "access".equals(jwt.getClaimAsString("token_use"));
        var expectedClient = clientId.equals(jwt.getClaimAsString("client_id"));
        return accessToken && expectedClient
                ? OAuth2TokenValidatorResult.success()
                : OAuth2TokenValidatorResult.failure(new OAuth2Error("invalid_token", "Wrong token_use or client_id", null));
    };

    decoder.setJwtValidator(new DelegatingOAuth2TokenValidator<>(
            JwtValidators.createDefaultWithIssuer(issuer), tokenUseAndClient));
    return decoder;
}
```
Declarar o bean `JwtDecoder` **substitui** o auto-configurado por `issuer-uri`; por isso o validator inclui `createDefaultWithIssuer` (assinatura, `exp`, `nbf`, issuer) **mais** o seu. Se a API aceita tokens de **vários** app clients, valide `client_id ∈ lista`.

### Obtendo o usuário no controller

```java
@GetMapping("/me")
public Map<String, Object> me(@AuthenticationPrincipal Jwt jwt) {
    return Map.of("sub", jwt.getSubject(), "username", jwt.getClaimAsString("username"));
}
```
Use **`sub`** (UUID imutável do usuário) como **chave do usuário** nos seus dados — nunca e-mail ou username (podem mudar). **Autorização por recurso** (IDOR): confirme que o recurso pertence ao `sub` do token (`code-reviewer` 🔴 se faltar); papel não substitui checagem de dono.

---

## Operações administrativas (SDK, não o fluxo do usuário)

Criar/desativar usuário, adicionar a grupo, resetar senha por back-office usa o **`CognitoIdentityProviderClient`** (SDK puro — `aws-sdk-java`; sem starter do Spring Cloud AWS), **isolado atrás de uma interface do domínio** (`UserDirectory`):
```java
adminCreateUser: AdminCreateUserRequest.builder().userPoolId(poolId).username(email).userAttributes(...).build()
adminAddUserToGroup: AdminAddUserToGroupRequest.builder().userPoolId(poolId).username(username).groupName("editor").build()
```
IAM **mínimo** na task role/IRSA (`aws-eks`, `aws-ecs-fargate`): `cognito-idp:AdminCreateUser`, `AdminAddUserToGroup`, `AdminDisableUser`… **no ARN do User Pool** — nunca `cognito-idp:*` em `*`. **Não** exponha essas operações sem autorização forte (`ROLE_admin`).

## Recursos do Cognito que valem conhecer

- **MFA** (TOTP/SMS) e **política de senha** no User Pool; **proteção avançada** (*adaptive authentication*, credenciais comprometidas) em planos pagos.
- **Federação** (Google/Apple/Facebook/SAML/OIDC) pelo Hosted UI: a API continua só validando o JWT do Cognito.
- **Triggers Lambda** (`aws-lambda`): *Pre sign-up*, *Post confirmation* (criar o registro do usuário no seu banco), **Pre token generation** (adicionar claims customizados, como `tenant_id`) — mantenha-os **rápidos e idempotentes** (um erro bloqueia o login).
- **Tokens:** *access token* curto (5 min–1 h), *refresh token* mais longo; **revogação** (`RevokeToken`) invalida o refresh. O access token já emitido vale até expirar (`authentication`: JWT não se revoga antes do `exp`) — mantenha-o curto.
- **Alternativa de borda:** o **API Gateway** (HTTP API) tem *JWT authorizer* nativo para o Cognito (valida antes de chegar na API); **valide também na aplicação** (defesa em profundidade, e o ALB/ECS pode ser acessado de outro caminho).
- **Pools por ambiente** (dev/staging/prod separados), criados por IaC (`aws-terraform`); nunca compartilhe o pool de produção com dev.

## Segurança — checklist

- Valide **access token** (`token_use=access`) e `client_id`; nunca aceite ID token na API.
- Clientes públicos **sem secret**; *Authorization Code + PKCE*; sem *implicit flow*.
- `sub` como identificador; autorização por **dono do recurso**, além de papel.
- Não logue tokens; não os coloque em URL; o front guarda tokens com cuidado (preferir memória/cookie `HttpOnly` via BFF a `localStorage`).
- TLS em todo lugar; CORS restrito às origens do front (`web-config`).
- IAM mínimo para as operações admin; pools separados por ambiente.

## Testes

- **Unit/slice** (`testing`): use o `SecurityMockMvcRequestPostProcessors.jwt()` do `spring-security-test` para simular o JWT e suas authorities **sem** chamar o Cognito:
```java
mockMvc.perform(delete("/api/book/v1/{id}", 1L)
                .with(jwt().authorities(new SimpleGrantedAuthority("ROLE_admin"))))
        .andExpect(status().isNoContent());

mockMvc.perform(delete("/api/book/v1/{id}", 1L)
                .with(jwt().authorities(new SimpleGrantedAuthority("ROLE_editor"))))
        .andExpect(status().isForbidden());

mockMvc.perform(get("/api/book/v1/{id}", 1L))
        .andExpect(status().isUnauthorized());
```
(Sem token, o Resource Server responde **401** com `WWW-Authenticate: Bearer` — diferente do 403 vazio do `authentication`; documente no Swagger — `swagger`.) Teste o **mapeamento de `cognito:groups`** e o **validator** (`token_use`, `client_id`) com JWTs montados no teste.
- **Integration real** contra um User Pool de **desenvolvimento** (jobs separados): LocalStack Cognito tem cobertura limitada; prove o fluxo real na conta de dev.

---

## Regras principais

- Produto com usuários finais → **Cognito** (não implemente login/reset/MFA à mão); API simples interna → `authentication`.
- A API é **Resource Server**: `issuer-uri`, valida **access token** (`token_use=access`) e **`client_id`**; **nunca ID token**.
- Fluxos: **Authorization Code + PKCE** (usuário) e **client credentials** com scopes (M2M); sem implicit, sem secret em cliente público.
- Stateless, CSRF off (token em header), `.cors`, `anyRequest().denyAll()`; sem `/auth/signin` nem senha na sua base.
- Mapeie `cognito:groups` → `ROLE_*` e `scope` → `SCOPE_*`; **autorize pelo dono do recurso (`sub`)**, não só pelo papel.
- `sub` é a chave do usuário (nunca e-mail/username).
- Operações admin pelo SDK atrás de interface, IAM mínimo no ARN do pool; pools separados por ambiente, por IaC.
- Access token curto; não logar tokens; 401 documentado no Swagger.
- Testes com `jwt()` do `spring-security-test`; fluxo real em conta de dev.
- **Sem Lombok** — deliberado.
