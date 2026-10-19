---
name: hateoas
description: HATEOAS com Spring HATEOAS no Spring Boot 4 — DTO estendendo RepresentationModel com @Relation, links montados no service com linkTo/methodOn, HAL em JSON, links em XML/YAML, coleções e páginas com PagedResourcesAssembler, Swagger, testes e quando não usar. Use quando a API precisar devolver links (_links) junto com os recursos, ou quando um DTO estender RepresentationModel.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../spring-data-jpa/SKILL.md`](../spring-data-jpa/SKILL.md) e [`../web-config/SKILL.md`](../web-config/SKILL.md) (content negotiation, `@Relation`, mix-in de YAML). Listas paginadas: [`../pagination/SKILL.md`](../pagination/SKILL.md).

# HATEOAS

**HATEOAS** (*Hypermedia as the Engine of Application State*) faz cada resposta trazer **links** para as ações possíveis sobre o recurso — `self`, `findAll`, `update`, `delete`. O client navega pelos links em vez de montar URLs. O formato padrão em JSON é o **HAL** (`_links`, `_embedded`).

## 1. Vale a pena?

| Use quando | Evite quando |
|---|---|
| O curso/projeto adotou o padrão (o pacote assume HATEOAS no CRUD de exemplo) | API interna consumida só pelo próprio front, que já conhece as rotas |
| API pública/navegável, clients genéricos, descoberta de ações | Endpoints de alto volume em que o payload extra pesa |
| As ações disponíveis variam com o estado (ex.: `renew` só quando o empréstimo está ativo) | Equipe sem intenção de os clients **usarem** os links (vira enfeite) |

Decida uma vez por projeto. Misturar endpoints com e sem links confunde os clients.

---

## 2. Dependency

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-hateoas</artifactId>
</dependency>
```
Gerenciada pelo BOM — sem `<version>` (`maven-config`: os starters do Boot 4 são modulares; a library solta não se auto-configura).

---

## 3. DTO

O DTO estende `RepresentationModel<T>` (que traz `add(Link)` e `getLinks()`) e declara a chave da coleção HAL com `@Relation`:

```java
@Relation(collectionRelation = "books")
public class BookDTO extends RepresentationModel<BookDTO> implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;
    private String author;
    private LocalDate launchDate;
    private BigDecimal price;
    private String title;

    public BookDTO() {}

    // getters, setters — same shape as the entity

    @Override
    public boolean equals(Object o) {
        if (o == null || getClass() != o.getClass()) return false;
        if (!super.equals(o)) return false;
        BookDTO bookDTO = (BookDTO) o;
        return Objects.equals(getId(), bookDTO.getId()) && Objects.equals(getAuthor(), bookDTO.getAuthor()) && Objects.equals(getLaunchDate(), bookDTO.getLaunchDate()) && Objects.equals(getPrice(), bookDTO.getPrice()) && Objects.equals(getTitle(), bookDTO.getTitle());
    }

    @Override
    public int hashCode() {
        return Objects.hash(super.hashCode(), getId(), getAuthor(), getLaunchDate(), getPrice(), getTitle());
    }
}
```
- `@Relation(collectionRelation = "books")` define `_embedded.books` nas listas. Sem ele, a chave vira `bookDTOList` — feia e acoplada ao nome da classe.
- `RepresentationModel` já implementa `equals`/`hashCode` sobre os links; chamar `super` mantém a comparação consistente (dois DTOs com os mesmos campos e links diferentes **não** são iguais).
- Sem Lombok, sem `@XmlRootElement` (`web-config`). O mapper (Dozer/MapStruct) ignora `links`: a entity não tem esse campo, e os links são adicionados **depois** do mapeamento.
- **Request bodies:** o mesmo DTO aceita JSON com `_links` sem quebrar, mas os links enviados pelo client são **ignorados** — nunca leia `getLinks()` de uma request.

---

## 4. Links — sempre no service

`spring-data-jpa` fixa a regra: **links nunca são adicionados no controller**. Um método privado no service centraliza todos:

```java
private void addHateoasLinks(BookDTO dto) {
    dto.add(linkTo(methodOn(BookController.class).findById(dto.getId())).withSelfRel().withType("GET"));
    dto.add(linkTo(methodOn(BookController.class).findAll(0, 12, "asc")).withRel("findAll").withType("GET"));
    dto.add(linkTo(methodOn(BookController.class).create(dto)).withRel("create").withType("POST"));
    dto.add(linkTo(methodOn(BookController.class).update(dto)).withRel("update").withType("PUT"));
    dto.add(linkTo(methodOn(BookController.class).delete(dto.getId())).withRel("delete").withType("DELETE"));
}
```
com `import static org.springframework.hateoas.server.mvc.WebMvcLinkBuilder.linkTo;` e `...methodOn;`. Chame-o em todo método que devolve o DTO:

```java
@Transactional(readOnly = true)
public BookDTO findById(Long id) {
    logger.info("Finding one book!");
    var entity = repository.findById(id)
        .orElseThrow(() -> new ResourceNotFoundException("No records found for this ID!"));
    var dto = parseObject(entity, BookDTO.class);
    addHateoasLinks(dto);
    return dto;
}
```
- **`methodOn` cria um proxy do controller** e registra a chamada para descobrir a URL — o método **não executa**. Funciona com o controller que implementa `*ControllerDocs`. Passe valores reais para os parâmetros que entram na URL (`id`, `page`); os que vão no body (`dto`) não afetam o link.
- **URL absoluta** derivada da request atual (host, porta, `X-Forwarded-*` quando atrás de proxy/Ingress — configure `server.forward-headers-strategy: framework` para que os links não saiam com o host interno do pod).
- **Links condicionais** são a parte mais útil do HATEOAS: adicione `renew` só quando o empréstimo pode ser renovado; não adicione `delete` quando o usuário não tem permissão. O client descobre o que pode fazer pelo que **está** na resposta.
- `withType("GET")` é informativo (HAL não exige); mantenha-o consistente em todos os links.

---

## 5. Formato na resposta

**JSON (HAL)** — o Spring HATEOAS usa HAL como representação JSON padrão (`spring.hateoas.use-hal-as-default-json-media-type: true` é o default), também quando o client pede `application/json`:
```json
{
  "_links": {
    "self":   { "href": "http://localhost:8080/api/book/v1/1", "type": "GET" },
    "delete": { "href": "http://localhost:8080/api/book/v1/1", "type": "DELETE" }
  },
  "author": "Robert C. Martin",
  "id": 1,
  "title": "Clean Code"
}
```
O Jackson 3 escreve as properties em ordem alfabética, então `_links` vem primeiro (`web-config`: wire format).

**XML e YAML** (se o projeto os escolheu em `web-config`) escrevem `links` como lista (`rel`, `href`, `type`), não `_links`. O YAML precisa do mix-in em `EntityModel` descrito em `web-config` para não repetir um `links: []` vazio.

**Listas e páginas** — use `PagedResourcesAssembler`/`PagedModel` (`pagination`) ou, para uma lista sem paginação, `CollectionModel.of(dtos, selfLink)`. Cada item mantém seus próprios links.

---

## 6. Swagger e segurança

- O springdoc 3 documenta `RepresentationModel`/`PagedModel` com o `spring-boot-starter-hateoas` presente (`swagger`). Declare a resposta de lista como o tipo real (`PagedModel<EntityModel<BookDTO>>`).
- Links **não substituem autorização**: um client pode chamar a URL de `delete` mesmo sem o link. A checagem continua no endpoint (`authentication`, IDOR). O link ausente é só uma dica de UX.

---

## 7. Testes

- **Unit test do service:** verifique os links pelo `rel` e pelo `href` (não pela ordem):
```java
var result = service.findById(1L);

assertThat(result.getLink("self")).isPresent();
assertThat(result.getRequiredLink("self").getHref()).endsWith("/api/book/v1/1");
assertThat(result.getRequiredLink("delete").getType()).isEqualTo("DELETE");
```
`linkTo` precisa de uma request no contexto; em unit test puro, registre uma: `RequestContextHolder.setRequestAttributes(new ServletRequestAttributes(new MockHttpServletRequest()))` no `@BeforeEach` (e limpe no `@AfterEach`). Os hrefs então começam em `http://localhost`.
- **Integração** (`integration-testing`): `body("_links.self.href", endsWith("/api/book/v1/" + id))` e, em listas, `body("_embedded.books[0]._links.self.href", notNullValue())`.
- **Links condicionais:** um teste por estado (com e sem o link).

---

## Regras principais

- Decida uma vez por projeto se a API usa HATEOAS; não misture endpoints com e sem links.
- `spring-boot-starter-hateoas` (sem versão); DTO `extends RepresentationModel<T>` com `@Relation(collectionRelation = "...")`.
- `equals`/`hashCode` do DTO chamam `super` (os links fazem parte da representação).
- Links adicionados **no service**, em um método privado (`addHateoasLinks`), nunca no controller; `linkTo(methodOn(...))`, nunca URL montada à mão.
- Atrás de proxy/Ingress: `server.forward-headers-strategy: framework` para links com o host público.
- Links condicionais refletem o estado e a permissão — mas a autorização continua no endpoint.
- Listas: `PagedResourcesAssembler`/`PagedModel` (`pagination`) ou `CollectionModel`.
- Teste links por `rel` e `href`; em unit test, registre uma request no `RequestContextHolder`.
- **Sem Lombok** — deliberado.
