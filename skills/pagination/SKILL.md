---
name: pagination
description: Paginação de listagens no Spring Boot 4 — Pageable a partir de page/size/direction, tamanho máximo, ordenação só por campos permitidos, Page × PagedModel do Spring Data (VIA_DTO) × PagedModel HAL do Spring HATEOAS com PagedResourcesAssembler, busca paginada, contagem cara, keyset e testes. Use quando uma listagem puder crescer, quando um findAll devolver tudo, ou quando o JSON de Page mudar de formato.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md) e [`../spring-data-jpa/SKILL.md`](../spring-data-jpa/SKILL.md). Com links HAL, leia também [`../hateoas/SKILL.md`](../hateoas/SKILL.md). Documentação: `swagger`. Testes: `integration-testing`.

# Paginação

**Toda coleção que pode crescer é paginada.** Um `findAll()` sem limite funciona com 20 linhas e derruba a API com 2 milhões (memória, tempo de resposta, banda). A paginação é decidida no **controller** (parâmetros HTTP), executada pelo **repository** (`LIMIT/OFFSET` no SQL) e montada no **service**.

## 1. Escolha o formato da resposta (uma vez por projeto)

| Formato | Quando | Tipo devolvido pelo service |
|---|---|---|
| **HAL com links** (padrão do pacote) | O projeto usa HATEOAS (`hateoas`) | `org.springframework.hateoas.PagedModel<EntityModel<BookDTO>>` via `PagedResourcesAssembler` |
| **Page estável do Spring Data** | Sem HATEOAS | `org.springframework.data.web.PagedModel<BookDTO>` (ou `Page<BookDTO>` com `VIA_DTO`, abaixo) |
| **Lista + cursor** (keyset) | Feed/rolagem infinita, tabelas enormes, sem "ir para a página 37" | DTO próprio com `items` e `nextCursor` (seção 6) |

> **Dois `PagedModel` diferentes.** `org.springframework.hateoas.PagedModel` (HAL: `_embedded`, `_links`, `page`) e `org.springframework.data.web.PagedModel` (JSON simples: `content`, `page`) têm o **mesmo nome simples**. Importe o certo — o erro de import compila e muda o contrato.

**Nunca serialize `PageImpl` diretamente** sem configurar o modo: o JSON do `PageImpl` expõe detalhes internos (`pageable`, `sort`, `empty`…) que **não são um contrato estável**, e o Spring Data avisa no log. Sem HATEOAS, ligue o modo DTO uma vez:
```java
@Configuration
@EnableSpringDataWebSupport(pageSerializationMode = EnableSpringDataWebSupport.PageSerializationMode.VIA_DTO)
public class PaginationConfig {
}
```
Com isso, um `Page<BookDTO>` devolvido pelo controller vira `{"content": [...], "page": {"size", "number", "totalElements", "totalPages"}}`.

---

## 2. Controller — page, size, direction

O padrão do pacote recebe três parâmetros simples (é o que o `BookControllerDocs` da skill `swagger` documenta) e monta o `Pageable` no controller:

```java
@GetMapping(produces = {
    MediaType.APPLICATION_JSON_VALUE,
    MediaType.APPLICATION_XML_VALUE,
    MediaType.APPLICATION_YAML_VALUE})
@Override
public ResponseEntity<PagedModel<EntityModel<BookDTO>>> findAll(
    @RequestParam(value = "page", defaultValue = "0") Integer page,
    @RequestParam(value = "size", defaultValue = "12") Integer size,
    @RequestParam(value = "direction", defaultValue = "asc") String direction) {

    var pageable = toPageable(page, size, direction);
    return ResponseEntity.ok(service.findAll(pageable));
}

private Pageable toPageable(Integer page, Integer size, String direction) {
    if (page < 0) throw new BadRequestException("Page must not be negative!");
    if (size < 1 || size > MAX_PAGE_SIZE) throw new BadRequestException("Size must be between 1 and " + MAX_PAGE_SIZE + "!");
    var sortDirection = "desc".equalsIgnoreCase(direction) ? Direction.DESC : Direction.ASC;
    return PageRequest.of(page, size, Sort.by(sortDirection, "title"));
}
```
com `private static final int MAX_PAGE_SIZE = 100;` na classe. O `produces` segue os formatos escolhidos em `web-config` (somente JSON quando for o caso).

- **Tamanho máximo obrigatório.** Sem ele, `?size=1000000` é um `findAll()` disfarçado. Rejeite com `400` (como acima) ou limite em silêncio — mas decida e documente. Para um teto global, `spring.data.web.pageable.max-page-size: 100` também vale quando o controller recebe um `Pageable` direto.
- **Ordenação só por campos permitidos.** Nunca repasse um `sort` livre vindo do client para o `Sort.by(...)`: um nome inexistente lança `PropertyReferenceException` (500) e um campo arbitrário permite ordenar por colunas sem índice (consulta lenta sob demanda). Se o client escolhe o campo, valide contra uma lista fixa (`Set.of("title", "author", "launchDate")`).
- **Ordem determinística.** Ordene sempre por um campo **estável**; se ele pode empatar, acrescente o `id` como desempate (`Sort.by(sortDirection, "title").and(Sort.by("id"))`) — sem isso, a mesma linha pode aparecer em duas páginas.
- Mensagens das exceptions seguem o idioma salvo (`exception-handling`).
- **Alternativa:** receber `Pageable pageable` direto no método (com `@PageableDefault(size = 12, sort = "title")`) é mais curto, mas aceita `sort` livre do client — use-o só com `max-page-size` e validação dos campos de ordenação.

---

## 3. Service — Page do repository

O repository já pagina: `JpaRepository.findAll(Pageable)` e qualquer query com um parâmetro `Pageable` retornam `Page<T>`.

**Sem HATEOAS** (com `VIA_DTO`):
```java
@Transactional(readOnly = true)
public Page<BookDTO> findAll(Pageable pageable) {
    logger.info("Finding all books!");
    return repository.findAll(pageable).map(entity -> parseObject(entity, BookDTO.class));
}
```

**Com HATEOAS (HAL)** — o `PagedResourcesAssembler` monta `_embedded`, os links `first/prev/self/next/last` e o bloco `page`:
```java
@Autowired
private PagedResourcesAssembler<BookDTO> assembler;

@Transactional(readOnly = true)
public PagedModel<EntityModel<BookDTO>> findAll(Pageable pageable) {
    logger.info("Finding all books!");
    var books = repository.findAll(pageable).map(entity -> {
        var dto = parseObject(entity, BookDTO.class);
        addHateoasLinks(dto);
        return dto;
    });
    var findAllLink = linkTo(methodOn(BookController.class)
        .findAll(pageable.getPageNumber(), pageable.getPageSize(), String.valueOf(pageable.getSort())))
        .withSelfRel();
    return assembler.toModel(books, findAllLink);
}
```
`addHateoasLinks` e os imports estáticos (`WebMvcLinkBuilder.linkTo/methodOn`) estão em `hateoas`. Links são montados **no service**, nunca no controller (`spring-data-jpa`). A chave da lista dentro de `_embedded` vem do `@Relation(collectionRelation = "books")` do DTO (`web-config`).

---

## 4. Busca paginada

Toda busca que devolve várias linhas também recebe `Pageable`:
```java
@Query("SELECT b FROM Book b WHERE LOWER(b.title) LIKE LOWER(CONCAT('%', :title, '%'))")
Page<Book> findBooksByTitle(@Param("title") String title, Pageable pageable);
```
- Parâmetro **sempre** com `@Param` — nunca concatenado (injeção).
- `LIKE '%x%'` não usa índice B-tree: em tabelas grandes, considere busca por prefixo (`'x%'`), índice full-text do banco ou um motor de busca. Meça (`jvm-performance`).
- O endpoint é `GET /api/book/v1/findBooksByTitle/{title}` (ou `?title=`) com os mesmos `page/size/direction`.

---

## 5. O custo do `count`

Um `Page` executa **duas** queries: a página e um `SELECT count(*)` para `totalElements`/`totalPages`. Em tabelas grandes ou com joins, o `count` pode custar mais que a página.
- Query custom com join/fetch: declare um `countQuery` simples (`@Query(value = "...", countQuery = "SELECT count(b) FROM Book b WHERE ...")`).
- Quando o client não precisa do total (rolagem "carregar mais"), retorne `Slice<T>` em vez de `Page<T>`: o Spring Data busca `size + 1` linhas para saber se há próxima, sem `count`.
- **Nunca** `JOIN FETCH` de coleção com paginação: o Hibernate pagina **em memória** (aviso `HHH90003004`/`firstResult/maxResults specified with collection fetch`) — busque os ids paginados e depois os detalhes, ou use `@EntityGraph`/`@BatchSize` (`spring-data-jpa`).

---

## 6. Offset × keyset (cursor)

`OFFSET 100000` obriga o banco a ler e descartar 100 mil linhas: páginas profundas ficam lentas, e inserções durante a navegação deslocam linhas entre páginas.

| | Offset (`page`/`size`) | Keyset (cursor) |
|---|---|---|
| "Ir para a página N" | ✅ | ❌ |
| Desempenho em páginas profundas | Piora linearmente | Constante (usa índice) |
| Estável com inserções concorrentes | ❌ | ✅ |
| Quando usar | Telas administrativas, tabelas pequenas/médias | Feeds, exportações, sincronização, APIs públicas com muito volume |

Keyset: `WHERE (title, id) > (:lastTitle, :lastId) ORDER BY title, id LIMIT :size`, com índice composto `(title, id)`. O Spring Data oferece `ScrollPosition`/`Window<T>` (`repository.findFirst10ByOrderByTitleAscIdAsc(ScrollPosition.keyset())`); devolva ao client um cursor **opaco** (Base64 do último valor), nunca a query.

---

## 7. Documentação e testes

- **Swagger:** documente `page`, `size` (com o máximo) e `direction` com `@Parameter`; a resposta paginada como o tipo real. Veja `swagger` e `swagger-advanced` (exemplos de resposta).
- **Testes de integração** (`integration-testing`): crie mais linhas que uma página e verifique **o conteúdo e os metadados**:
```java
api().queryParam("page", 0).queryParam("size", 2).queryParam("direction", "asc")
    .when().get("/api/book/v1")
    .then().statusCode(200)
    .body("_embedded.books", hasSize(2))
    .body("page.size", equalTo(2))
    .body("page.totalElements", greaterThanOrEqualTo(3))
    .body("_links.next.href", notNullValue());
```
Sem HATEOAS, as chaves são `content` e `page`. Teste também `size` acima do máximo (`400`), `page` negativa (`400`), a última página (sem `next`) e a ordem com empates. Para deserializar a resposta HAL em objetos, use os wrappers só de teste (`WrapperBookDTO`, `PagedModelBook…` — `code-organization`, naming) com `@JsonProperty("books")` casando com o `@Relation`.

---

## Regras principais

- Toda coleção que pode crescer é paginada; nenhum endpoint devolve uma tabela inteira.
- `size` tem **máximo** (ex.: 100) e `page` não aceita negativo — `400` para valores fora da faixa.
- Ordenação só por campos de uma lista permitida, com desempate estável (`id`); nunca `sort` livre do client direto no `Sort.by`.
- Sem HATEOAS: `@EnableSpringDataWebSupport(pageSerializationMode = VIA_DTO)` ou `org.springframework.data.web.PagedModel` — nunca `PageImpl` serializado cru.
- Com HATEOAS: `PagedResourcesAssembler` no service, `PagedModel<EntityModel<BookDTO>>` do pacote `org.springframework.hateoas`, `@Relation(collectionRelation)` no DTO.
- Cuidado com os dois `PagedModel` de mesmo nome — confira o import.
- `countQuery` simples para queries com join; `Slice` quando o total não é necessário; keyset para páginas profundas ou feeds.
- Nunca `JOIN FETCH` de coleção com paginação (paginação em memória).
- Teste conteúdo, metadados, limites (`size` máximo, `page` negativa) e ordem com empates.
- **Sem Lombok** — deliberado.
