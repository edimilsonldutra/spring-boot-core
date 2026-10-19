---
name: code-style
description: Estilo de código Java do pacote — comentários (default nenhum), var, guard clauses, quebras de linha, annotations, equals/hashCode, logger SLF4J, idioms modernos, Jackson 3 e chains do REST Assured, sem Lombok. Use ao gerar ou revisar código Java deste padrão ou quando pedirem para ajustar o estilo de uma classe.
---

# Java Code Style

Baixa cerimônia, explícito, legível. Sem Lombok. Sem mágica. A indentação é de 4 espaços, nunca tabs.

Leia `code-organization` primeiro: o **Step 0** dela coleta as preferências do projeto (comentários, database, posição do Swagger, build tool, mapper, injection). Se esta skill for a primeira aberta na conversa e não existir uma seção `## Project preferences` no `CLAUDE.md` do projeto, execute esse Step 0 agora — no mínimo a pergunta de comentários abaixo.

---

## Comentários no código gerado

**Default: sem comentários** — em Java, XML, YAML, SQL, Dockerfiles e arquivos de ignore. Nomes, métodos pequenos e o texto da skill ao redor carregam a explicação; o que precisar ser explicado vai na resposta do chat ou no `CLAUDE.md` do projeto, não no código.

O desenvolvedor pode optar por ter comentários no Step 0 ("Comments in generated code: yes"). Quando optar, escreva comentários curtos que expliquem o *porquê* (uma constraint, um workaround, uma decisão não óbvia), nunca comentários que repetem o que a linha faz, e nunca código comentado, marcadores `//@formatter:off` ou sobras de TODO.

Os snippets destas skills são escritos sem comentários para poderem ser copiados como estão. Aplique a preferência salva a todo arquivo que você gerar, em toda skill da família, pelo resto da conversa.

---

## Declaração de variáveis

Sempre `var` para variáveis locais quando o tipo é óbvio pelo lado direito. Nunca `var` quando o tipo seria ambíguo sem contexto.

Use `var`:
```java
var user = repository.findByUsername(username);
var token = tokenProvider.createAccessToken(username, user.getRoles());
var sortDirection = "desc".equalsIgnoreCase(direction) ? Sort.Direction.DESC : Sort.Direction.ASC;
var content = given(specification).when().post().then().extract().body().asString();
```

Tipo explícito quando o lado direito não deixa o tipo óbvio, ou quando ajuda no ponto da chamada:
```java
TokenDTO token;
Pageable pageable = PageRequest.of(page, size, sort);
```

Quando uma variável é declarada antes de um branch condicional e atribuída dentro dele, use o tipo explícito:
```java
TokenDTO token;
if (user != null) {
    token = tokenProvider.refreshToken(refreshToken);
} else {
    throw new UsernameNotFoundException("Username " + username + " not found!");
}
return ResponseEntity.ok(token);
```

---

## Instruções if

**Guard clauses de uma linha** — `if` + `throw` ou `if` + `return` sem chaves, na mesma linha:
```java
if (user == null) throw new RequiredObjectIsNullException();
if (book == null) throw new RequiredObjectIsNullException();
```

**Guard de uma linha em controllers** — `if` + `return` na mesma linha, sem chaves:
```java
if (credentialsIsInvalid(credentials)) return ResponseEntity.status(HttpStatus.FORBIDDEN).body("Invalid client request!");
if (parametersAreInvalid(username, refreshToken)) return ResponseEntity.status(HttpStatus.FORBIDDEN).body("Invalid client request!");
```

**if/else multi-linha** — sempre com chaves, corpo na linha seguinte:
```java
if (user != null) {
    token = tokenProvider.refreshToken(refreshToken);
} else {
    throw new UsernameNotFoundException("Username " + username + " not found!");
}
```

**Condições booleanas que ocupam várias linhas** — `||` e `&&` no final de cada linha, alinhados sob a primeira condição:
```java
private static boolean credentialsIsInvalid(AccountCredentialsDTO credentials) {
    return credentials == null ||
            StringUtils.isBlank(credentials.getPassword()) ||
            StringUtils.isBlank(credentials.getUsername());
}
```

**Pattern matching para `instanceof`** — faça o bind da variável na condição em vez de fazer cast na linha seguinte:
```java
if (body instanceof ProblemDetail problem && problem.getType() == null) {
    problem.setType(URI.create("about:blank"));
}
```

---

## Chamadas de método com vários argumentos

Quando os argumentos não cabem em uma linha, cada argumento na sua própria linha, indentado um nível:
```java
authenticationManager.authenticate(
    new UsernamePasswordAuthenticationToken(
        credentials.getUsername(),
        credentials.getPassword()
    )
);

var token = tokenProvider.createAccessToken(
        credentials.getUsername(),
        user.getRoles()
);
```

---

## Formatação de annotations

**Annotation única, curta** — na mesma linha da declaração:
```java
@Service
public class AuthService { ... }
```

**Annotation com vários argumentos** — cada um na sua própria linha, indentado:
```java
@Operation(
        summary = "Authenticates a user and returns a token",
        description = "Validates user credentials and generates an access token.",
        tags = {"Authentication"},
        responses = {
                @ApiResponse(description = "Success", responseCode = "200", content = @Content),
                @ApiResponse(description = "Bad Request", responseCode = "400", content = @Content)
        }
)
```

**Mapping annotations com vários media types** — vale somente em projetos que escolheram mais que JSON (veja a pergunta da skill `web-config`); cada media type então vai na sua própria linha:
```java
@PostMapping(
        consumes = {
                MediaType.APPLICATION_JSON_VALUE,
                MediaType.APPLICATION_XML_VALUE,
                MediaType.APPLICATION_YAML_VALUE},
        produces = {
                MediaType.APPLICATION_JSON_VALUE,
                MediaType.APPLICATION_XML_VALUE,
                MediaType.APPLICATION_YAML_VALUE}
)
```

Quando há somente `produces` (sem `consumes`), pode ficar em uma linha se couber:
```java
@GetMapping(produces = {
        MediaType.APPLICATION_JSON_VALUE,
        MediaType.APPLICATION_XML_VALUE,
        MediaType.APPLICATION_YAML_VALUE})
```

---

## equals() e hashCode()

Sobre todos os campos, usando getters, em uma única linha quando todos os campos cabem — nunca quebrado em várias linhas:
```java
@Override
public boolean equals(Object o) {
    if (o == null || getClass() != o.getClass()) return false;
    Book book = (Book) o;
    return Objects.equals(getId(), book.getId()) && Objects.equals(getAuthor(), book.getAuthor()) && Objects.equals(getLaunchDate(), book.getLaunchDate()) && Objects.equals(getPrice(), book.getPrice()) && Objects.equals(getTitle(), book.getTitle());
}

@Override
public int hashCode() {
    return Objects.hash(getId(), getAuthor(), getLaunchDate(), getPrice(), getTitle());
}
```

A guard clause `if (o == null || getClass() != o.getClass()) return false;` sempre em uma linha.

---

## Getters e setters

Cada getter e setter nas suas próprias linhas — nunca em uma linha só:
```java
public Long getId() {
    return id;
}

public void setId(Long id) {
    this.id = id;
}
```

---

## Declaração do logger

SLF4J em todo lugar — services, factories, components — declarado `private static final`, construído a partir da classe:
```java
private static final Logger logger = LoggerFactory.getLogger(BookService.class);
```

Os imports são `org.slf4j.Logger` e `org.slf4j.LoggerFactory` (o Spring Boot traz o SLF4J pelo seu logging starter; nenhuma dependency extra). Faça log com placeholders `{}`, nunca com concatenação de strings nem patterns de `String.format` — o SLF4J não interpreta `%s`/`%n`:
```java
logger.info("Email sent to {}", recipient);
```

---

## Idioms modernos de Java

Features do Java 17+ que o codebase usa onde encaixam. Nenhuma é obrigatória para uma feature funcionar.

- **Records** para payloads imutáveis, somente de serialização, sem framework que precise de setters, como o error body: `public record ExceptionResponse(Date timestamp, String message, String details) {}`. Entities e DTOs que Dozer, Hibernate ou Jackson precisam popular continuam classes com um constructor sem argumentos.
- **`instanceof` pattern matching** (veja acima) em vez de um cast na linha seguinte.
- **`Stream.toList()`** em vez de `collect(Collectors.toList())` quando o resultado só é lido.
- **Text blocks** para fixtures multi-linha em testes (conteúdo CSV, bodies JSON).
- **Records privados dentro de uma classe de teste** para fixtures pequenas de teste.

---

## Jackson 3 em testes e helpers

O Spring Boot 4 usa Jackson 3: os packages são `tools.jackson.core`, `tools.jackson.databind` e `tools.jackson.dataformat.*`. O package das annotations **não** mudou — `@JsonProperty`, `@JsonIgnore` e `@JsonInclude` ainda são importadas de `com.fasterxml.jackson.annotation`.

- Mappers são imutáveis: construa-os, não os mute.
```java
var objectMapper = JsonMapper.builder()
        .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
        .build();
```
- `JacksonException` é unchecked, então métodos de teste e helpers não declaram mais `throws JsonProcessingException`.
- O Jackson 3 ignora properties desconhecidas por default; habilite `DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES` explicitamente onde rejeitá-las for o comportamento pretendido.

---

## Formatação de chain do REST Assured

Cada método na sua própria linha, indentado para mostrar o agrupamento lógico: setup → body → when → then → extract:

```java
tokenDto = given()
        .basePath("/auth/signin")
        .port(TestConfigs.SERVER_PORT)
        .contentType(MediaType.APPLICATION_JSON_VALUE)
        .body(credentials)
        .when()
        .post()
        .then()
        .statusCode(200)
        .extract()
        .body()
        .as(TokenDTO.class);
```

---

## Atribuição de variável após o REST Assured

Sempre atribua a uma variável tipada primeiro, depois ao campo static compartilhado:
```java
BookDTO createdBook = objectMapper.readValue(content, BookDTO.class);
book = createdBook;
```

Não:
```java
book = objectMapper.readValue(content, BookDTO.class);
```
(perde a referência intermediária).

---

## Quebra de linha em chamada de constructor

Quando uma chamada de constructor com dois ou mais argumentos é atribuída a uma variável, quebre depois do `=`:
```java
AccountCredentialsDTO credentials =
    new AccountCredentialsDTO("leandro", "admin123");
```

---

## Linhas vazias

- Uma linha em branco entre os campos e o primeiro constructor.
- Uma linha em branco entre métodos.
- Nenhuma linha em branco entre `@Override` e a assinatura do método.
- Nenhuma linha em branco entre a(s) annotation(s) da classe e `public class`.
- Uma linha em branco após a chave de abertura de um método que tenha mais de duas instruções.

---

## Regras principais

- **Sem comentários no código gerado**, a menos que o desenvolvedor tenha optado por eles no Step 0.
- `var` para locais quando o tipo é óbvio — tipo explícito quando declarada antes de um branch.
- Guard clauses de uma linha (`if (x == null) throw ...`) — sem chaves, sem nova linha.
- `if/else` multi-linha sempre usa chaves.
- Returns booleanos com várias condições: `||` / `&&` no final da linha, próxima condição indentada.
- O return de `equals()` em uma única linha, independentemente do comprimento.
- Logger: SLF4J, `private static final`, placeholders `{}`.
- Chains do REST Assured: um método por linha, chain completa.
- Variável intermediária antes de atribuir ao campo static em testes.
- Indentação de 4 espaços.
- **Sem Lombok** — nunca. Esta é uma escolha deliberada.
