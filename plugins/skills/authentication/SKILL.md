---
name: authentication
description: Autenticação stateless com JWT próprio no Spring Boot 4 / Spring Security 7 — User/Permission, JwtTokenProvider, JwtTokenFilter, SecurityConfig em lambda DSL, /auth/signin e /auth/refresh, BCrypt e @PreAuthorize. Use quando adicionar login JWT, proteger endpoints, autorizar por permission ou investigar 401/403; para login gerenciado, veja aws-cognito.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) e [`../code-style/SKILL.md`](../code-style/SKILL.md) para as preferências do projeto, o package layout base e as convenções de code style.

# Authentication (JWT)

API **stateless**: sem sessão, sem cookie. O client faz `POST /auth/signin`, recebe um access token (curto) e um refresh token (longo), e envia `Authorization: Bearer <accessToken>` em cada request. A validação do token acontece em um filter, que popula o `SecurityContext`.

Package layout (de `code-organization`): `security/jwt/` (`JwtTokenProvider`, `JwtTokenFilter`), `data/dto/security/` (`AccountCredentialsDTO`, `TokenDTO`), `config/SecurityConfig`, `model/User` e `model/Permission`, `services/AuthService`, `controllers/AuthController`, e a `InvalidJwtAuthenticationException` de `exception-handling`.

---

## Dependencies

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-security</artifactId>
</dependency>
<dependency>
    <groupId>com.auth0</groupId>
    <artifactId>java-jwt</artifactId>
    <version>${java-jwt.version}</version>
</dependency>
```
`java-jwt` não é gerenciada pelo BOM (veja `maven-config`). Para testar com security, `spring-security-test` (test scope).

## application.yml

```yaml
security:
  jwt:
    token:
      secret-key: ${JWT_SECRET}
      expire-length: 3600000
      refresh-length: 86400000
```
- **`JWT_SECRET` vem do ambiente, sem default no arquivo de produção.** A aplicação deve falhar ao subir se ele não existir — melhor que subir com um segredo conhecido (veja `aws-rds-secrets-manager` / `kubernetes` para entregá-lo ao pod). Para dev local, exporte uma variável ou use um default **somente** no `application.yml` de teste.
- Para HMAC-SHA256 o segredo deve ter pelo menos 32 bytes aleatórios (`openssl rand -base64 48`).
- `expire-length` em ms: access token de 15–60 min; refresh token de horas/dias. Quanto mais longo o access token, maior a janela de um token vazado.

---

## Entities

`User` implementa `UserDetails`; `Permission` implementa `GrantedAuthority`. Sem Lombok, como o resto do pack. As permissions de um user são sempre lidas na autenticação — esse é o caso de `FetchType.EAGER` descrito em `spring-data-jpa`.

```java
@Entity
@Table(name = "users")
public class User implements UserDetails, Serializable {

    private static final long serialVersionUID = 1L;

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_name", unique = true)
    private String userName;

    @Column(name = "full_name")
    private String fullName;

    private String password;

    @Column(name = "account_non_expired")
    private Boolean accountNonExpired;

    @Column(name = "account_non_locked")
    private Boolean accountNonLocked;

    @Column(name = "credentials_non_expired")
    private Boolean credentialsNonExpired;

    private Boolean enabled;

    @ManyToMany(fetch = FetchType.EAGER)
    @JoinTable(name = "user_permission",
        joinColumns = @JoinColumn(name = "id_user"),
        inverseJoinColumns = @JoinColumn(name = "id_permission"))
    private List<Permission> permissions = new ArrayList<>();

    public User() {}

    public List<String> getRoles() {
        return permissions.stream().map(Permission::getDescription).toList();
    }

    @Override
    public Collection<? extends GrantedAuthority> getAuthorities() {
        return permissions;
    }

    @Override
    public String getUsername() {
        return userName;
    }

    @Override
    public boolean isAccountNonExpired() {
        return Boolean.TRUE.equals(accountNonExpired);
    }

    @Override
    public boolean isAccountNonLocked() {
        return Boolean.TRUE.equals(accountNonLocked);
    }

    @Override
    public boolean isCredentialsNonExpired() {
        return Boolean.TRUE.equals(credentialsNonExpired);
    }

    @Override
    public boolean isEnabled() {
        return Boolean.TRUE.equals(enabled);
    }

    // demais getters, setters, equals, hashCode
}
```
```java
@Entity
@Table(name = "permission")
public class Permission implements GrantedAuthority, Serializable {

    private static final long serialVersionUID = 1L;

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String description;

    public Permission() {}

    @Override
    public String getAuthority() {
        return description;
    }

    // getters, setters, equals, hashCode
}
```
O repository: `Optional<User> findByUserName(String userName);` e um `UserService implements UserDetailsService` cujo `loadUserByUsername` faz `repository.findByUserName(username).orElseThrow(() -> new UsernameNotFoundException("Username " + username + " not found!"))`.

**Seed de senha.** O `DelegatingPasswordEncoder` espera o prefixo do algoritmo: grave `{bcrypt}$2a$10$...` na migration (hash gerado fora do SQL, nunca texto puro — veja `flyway-migrations`). Sem o prefixo, o login falha com `There is no PasswordEncoder mapped for the id "null"`.

---

## JwtTokenProvider

```java
@Component
public class JwtTokenProvider {

    private static final Logger logger = LoggerFactory.getLogger(JwtTokenProvider.class);

    @Value("${security.jwt.token.secret-key}")
    private String secretKey;

    @Value("${security.jwt.token.expire-length}")
    private long accessValidity;

    @Value("${security.jwt.token.refresh-length}")
    private long refreshValidity;

    @Autowired
    private UserDetailsService userDetailsService;

    private Algorithm algorithm;

    @PostConstruct
    void init() {
        algorithm = Algorithm.HMAC256(secretKey.getBytes(StandardCharsets.UTF_8));
    }

    public TokenDTO createTokens(String username, List<String> roles) {
        var now = Instant.now();
        var accessExpiration = now.plusMillis(accessValidity);
        var accessToken = JWT.create()
                .withSubject(username)
                .withClaim("roles", roles)
                .withIssuedAt(now)
                .withExpiresAt(accessExpiration)
                .sign(algorithm);
        var refreshToken = JWT.create()
                .withSubject(username)
                .withClaim("roles", roles)
                .withIssuedAt(now)
                .withExpiresAt(now.plusMillis(refreshValidity))
                .sign(algorithm);
        return new TokenDTO(username, true, Date.from(now), Date.from(accessExpiration), accessToken, refreshToken);
    }

    public Authentication getAuthentication(String token) {
        var decoded = JWT.require(algorithm).build().verify(token);
        var userDetails = userDetailsService.loadUserByUsername(decoded.getSubject());
        return new UsernamePasswordAuthenticationToken(userDetails, "", userDetails.getAuthorities());
    }

    public String resolveToken(HttpServletRequest request) {
        var header = request.getHeader("Authorization");
        if (header != null && header.startsWith("Bearer ")) return header.substring(7);
        return null;
    }

    public boolean validateToken(String token) {
        try {
            JWT.require(algorithm).build().verify(token);
            return true;
        } catch (JWTVerificationException e) {
            logger.debug("Invalid JWT: {}", e.getMessage());
            return false;
        }
    }
}
```
- O `verify` checa **assinatura e expiração**. Nunca use `JWT.decode(token)` para autorizar — ele só lê, não valida.
- Nunca logue o token nem o segredo. O log de debug acima registra só o motivo.
- O JWT **não é criptografado**, só assinado: não coloque nada sensível nos claims.
- O refresh endpoint deve validar o refresh token e confirmar que o usuário ainda existe/está ativo antes de emitir um novo par. Para revogação real (logout, troca de senha), é preciso estado no servidor (lista de tokens/`jti` revogados em Redis — veja `caching`); JWT puro não se revoga antes de expirar, por isso o access token é curto.

---

## JwtTokenFilter

`OncePerRequestFilter`. Para token ausente ou ruim, **não lança exception**: segue a chain sem autenticar, e o Spring Security responde 403 nos paths protegidos (veja `exception-handling`, "Errors that never reach the handler").

```java
public class JwtTokenFilter extends OncePerRequestFilter {

    private final JwtTokenProvider tokenProvider;

    public JwtTokenFilter(JwtTokenProvider tokenProvider) {
        this.tokenProvider = tokenProvider;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        var token = tokenProvider.resolveToken(request);
        if (token != null && tokenProvider.validateToken(token)) {
            SecurityContextHolder.getContext().setAuthentication(tokenProvider.getAuthentication(token));
        }
        chain.doFilter(request, response);
    }
}
```
**Armadilha do filter registrado duas vezes.** O filter **não** leva `@Component`: o Spring Boot registraria automaticamente todo bean `Filter` na chain do servlet **além** da security chain, e ele rodaria duas vezes por request. Como não é bean, a injection é por constructor (a exceção justificada à preferência de field injection) e a instância é criada no `SecurityConfig`.

---

## SecurityConfig

Spring Security 7: configuração **somente em lambda DSL** (`and()` e a configuração por `WebSecurityConfigurerAdapter` não existem mais).

```java
@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    @Autowired
    private JwtTokenProvider tokenProvider;

    @Bean
    PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }

    @Bean
    AuthenticationManager authenticationManager(AuthenticationConfiguration configuration) throws Exception {
        return configuration.getAuthenticationManager();
    }

    @Bean
    SecurityFilterChain securityFilterChain(HttpSecurity http) throws Exception {
        var jwtFilter = new JwtTokenFilter(tokenProvider);
        return http
                .httpBasic(basic -> basic.disable())
                .formLogin(form -> form.disable())
                .csrf(csrf -> csrf.disable())
                .cors(cors -> {})
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .addFilterBefore(jwtFilter, UsernamePasswordAuthenticationFilter.class)
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(
                                "/auth/signin",
                                "/auth/refresh/**",
                                "/swagger-ui/**",
                                "/v3/api-docs/**",
                                "/actuator/health/**").permitAll()
                        .requestMatchers("/api/**").authenticated()
                        .anyRequest().denyAll())
                .build();
    }
}
```
- **CSRF desabilitado é correto aqui** porque a API é stateless, não usa cookie de sessão e o token vai em header. Se você algum dia autenticar por cookie, **religue** o CSRF.
- `.cors(cors -> {})` é obrigatório com `WebConfig` (veja `web-config`) — sem ele o preflight é rejeitado antes do MVC.
- `anyRequest().denyAll()` no fim: o que não foi liberado explicitamente é negado. Libere `/actuator/health/**` só se o Kubernetes/ALB precisar chamar as probes sem token (veja `observability`); nunca libere `/actuator/**` inteiro.
- `/auth/createUser` aberto permite que qualquer um se cadastre; só o inclua em `permitAll()` se isso for o requisito.

## Autorização por role

`@EnableMethodSecurity` habilita `@PreAuthorize` nos services/controllers:
```java
@PreAuthorize("hasAuthority('ADMIN')")
@DeleteMapping("/{id}")
public ResponseEntity<?> delete(@PathVariable("id") Long id) { ... }
```
Como `Permission#getAuthority` devolve a `description` crua, use `hasAuthority('ADMIN')`. `hasRole('ADMIN')` espera o prefixo `ROLE_`.

---

## AuthService e AuthController

```java
@Service
public class AuthService {

    @Autowired
    private AuthenticationManager authenticationManager;

    @Autowired
    private JwtTokenProvider tokenProvider;

    @Autowired
    private UserRepository repository;

    public TokenDTO signIn(AccountCredentialsDTO credentials) {
        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(
                        credentials.getUsername(),
                        credentials.getPassword()));
        var user = repository.findByUserName(credentials.getUsername())
                .orElseThrow(() -> new UsernameNotFoundException("Username " + credentials.getUsername() + " not found!"));
        return tokenProvider.createTokens(credentials.getUsername(), user.getRoles());
    }
}
```
```java
@RestController
@RequestMapping("/auth")
@Tag(name = "Authentication", description = "Endpoints for authentication")
public class AuthController {

    @Autowired
    private AuthService service;

    @PostMapping("/signin")
    public ResponseEntity<?> signIn(@RequestBody AccountCredentialsDTO credentials) {
        if (credentialsIsInvalid(credentials)) return ResponseEntity.status(HttpStatus.FORBIDDEN).body("Invalid client request!");
        return ResponseEntity.ok(service.signIn(credentials));
    }

    private static boolean credentialsIsInvalid(AccountCredentialsDTO credentials) {
        return credentials == null ||
                StringUtils.isBlank(credentials.getPassword()) ||
                StringUtils.isBlank(credentials.getUsername());
    }
}
```
Credenciais erradas fazem o `AuthenticationManager` lançar `BadCredentialsException` dentro do controller — adicione um `@ExceptionHandler(AuthenticationException.class)` no `CustomEntityResponseHandler` (veja `exception-handling`) respondendo 401/403 com uma mensagem **genérica** ("Invalid username or password") que não revele se foi o usuário ou a senha que errou.

---

## 403 ou 401?

Com este filter, token ausente/inválido em path protegido resulta em **403 de body vazio** (o default do Spring Security aqui). Se a API precisa de 401 + `WWW-Authenticate`, registre um `AuthenticationEntryPoint` em `.exceptionHandling(e -> e.authenticationEntryPoint(...))` e documente 401 no Swagger (veja `swagger`). Escolha uma e seja consistente.

---

## Regras principais

- Stateless: `SessionCreationPolicy.STATELESS`, sem cookie; CSRF desabilitado **só** porque o token vai em header.
- `JWT_SECRET` do ambiente, sem default em produção, ≥ 32 bytes aleatórios; nunca em Git, nunca em log.
- Valide com `JWT.require(algorithm).build().verify(...)` — nunca `decode` para autorizar. Nada sensível nos claims.
- Access token curto (15–60 min); refresh token separado; revogação exige estado no servidor.
- `JwtTokenFilter` **sem** `@Component` (evita rodar duas vezes); token ruim → segue a chain sem autenticar, nunca lança.
- Spring Security 7: somente lambda DSL; `anyRequest().denyAll()` no final; libere apenas o necessário.
- Senhas com `DelegatingPasswordEncoder` (`{bcrypt}`); nunca texto puro, nem em seed.
- `@EnableMethodSecurity` + `@PreAuthorize("hasAuthority('...')")` para autorização por permission. A permission não basta para recursos de um usuário: a **autorização por objeto** (IDOR) e o resto da segurança da API estão em `application-security`.
- Mensagem de login falho genérica; não revele se o usuário existe.
- **Sem Lombok** — deliberado.
