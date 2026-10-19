---
name: spring-data-jpa
description: Persistência com Spring Data JPA e Hibernate 7 no padrão do pacote — entities sem Lombok, relationships e fetch, transactions e N+1, repositories com queries custom e modifying, DTOs, mapper Dozer ou MapStruct e testes de repository contra banco real. Use quando criar um CRUD, uma entity ou um repository, ou investigar LazyInitializationException e N+1.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) e [`../code-style/SKILL.md`](../code-style/SKILL.md) para as preferências do projeto (database, mapper, injection), o package layout base e as convenções de code style.

# Spring Data JPA

JPA direto ao ponto, com mapeamentos de coluna explícitos, sem BaseEntity, sem value objects para IDs. Primary keys auto-increment via `IDENTITY`. Schema gerenciado pelo Flyway — nunca pelo Hibernate. Os exemplos usam MySQL; quando o Step 0 escolheu outro database, mantenha os mesmos mapeamentos e troque somente o que é específico do database (driver, URL, SQL nativo, tipos de coluna nas migrations).

---

## application.yml

```yaml
spring:
  jpa:
    hibernate:
      ddl-auto: none
    properties:
      hibernate:
        check_nullability: true
    show-sql: false
    open-in-view: false
```

- `ddl-auto: none` sempre — o Flyway é dono do schema.
- **`check_nullability: true` é obrigatório.** Quando o Bean Validation está no classpath (springdoc e `spring-boot-starter-validation` ambos o trazem), o Hibernate assume que o Bean Validation vai impor o not-null e desliga silenciosamente a sua própria checagem. Uma entity com uma property `@Column(nullable = false)` nula é então enviada ao database — e persistida sempre que a coluna é nullable na migration. Com a flag ligada, o Hibernate falha antes do SQL com um erro `not-null property references a null or transient value`.
- `open-in-view: false` sempre — veja Relationships para saber o que isso significa para lazy loading.
- Não adicione `hibernate.jdbc.batch_size` / `order_inserts` para entities `IDENTITY`: o Hibernate não consegue fazer batch de inserts quando os ids são gerados pelo database, então essas settings não têm efeito.

---

## Entity

- **Sem Lombok** — constructor sem argumentos, getters e setters explícitos. Esta é uma escolha deliberada: nunca sugira nem adicione Lombok a este codebase.
- `implements Serializable` com `serialVersionUID = 1L`.
- `@Id` + `@GeneratedValue(strategy = GenerationType.IDENTITY)`.
- Todas as colunas mapeadas explicitamente via `@Column` (name, nullable, length).
- **Dinheiro é sempre `BigDecimal`** (nunca `Double`/`double`, que não representa centavos com exatidão: `0.1 + 0.2 != 0.3`). A coluna é `decimal` com escala 2 na migration (veja `flyway-migrations`). Cuidado: `BigDecimal.equals` considera a escala (`77.0` ≠ `77.00`); compare valores com `compareTo` e crie literais com `new BigDecimal("77.00")`, nunca `new BigDecimal(77.0)`.
- Datas usam `java.time`: `LocalDate` para uma data sem horário, `LocalDateTime`/`Instant` para um timestamp. Nunca `java.util.Date` com `@Temporal` — o Hibernate 7 o depreca. O tipo da coluna continua sendo o que a migration criou; o Hibernate mapeia `LocalDate` para ele.
- `equals()` e `hashCode()` usando `Objects.equals` / `Objects.hash` via getters, sobre todos os campos.
- Enums reais são mapeados com `@Enumerated(EnumType.STRING)` em um campo cujo tipo Java **é o enum** — nunca `ORDINAL`. Um campo `String` é só um `@Column`; `@Enumerated` em uma `String` é inválido.

```java
@Entity
@Table(name = "books")
public class Book implements Serializable {

    private static final long serialVersionUID = 1L;

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 180)
    private String author;

    @Column(name = "launch_date", nullable = false)
    private LocalDate launchDate;

    @Column(nullable = false)
    private BigDecimal price;

    @Column(nullable = false, length = 250)
    private String title;

    public Book() {}

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public String getAuthor() {
        return author;
    }

    public void setAuthor(String author) {
        this.author = author;
    }

    public LocalDate getLaunchDate() {
        return launchDate;
    }

    public void setLaunchDate(LocalDate launchDate) {
        this.launchDate = launchDate;
    }

    public BigDecimal getPrice() {
        return price;
    }

    public void setPrice(BigDecimal price) {
        this.price = price;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

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
}
```

Mudar um campo de data de `java.util.Date` para `LocalDate` muda o contrato da API: o valor JSON passa a ser `"2017-11-29"` e as requests só são aceitas em `yyyy-MM-dd`; offset date-times e números epoch são rejeitados com 400. Avise o desenvolvedor ao migrar um projeto existente.

### Campos Boolean / flag
Use `BIT(1)` no MySQL (veja `flyway-migrations`; `BOOLEAN` em outros databases). Mapeie para `Boolean` em Java — o Hibernate cuida da conversão automaticamente.
```java
@Column(nullable = false)
private Boolean enabled;
```

### Campo Enum
```java
@Enumerated(EnumType.STRING)
@Column(name = "status", nullable = false, length = 20)
private Status status;
```

### Relationships
**Use `FetchType.LAZY` por default** em `@ManyToOne`, `@OneToMany` e `@ManyToMany` para evitar carregar grafos que ninguém pediu. Relationships com join table usam `@JoinTable`.
```java
@ManyToOne(fetch = FetchType.LAZY)
@JoinColumn(name = "user_id", nullable = false)
private User user;

@OneToMany(mappedBy = "user", fetch = FetchType.LAZY, cascade = CascadeType.ALL)
private List<Permission> permissions = new ArrayList<>();
```

**LAZY tem um porém com `open-in-view: false`.** O service converte entities em DTOs depois que a chamada ao repository retorna; se o DTO (ou um relatório, ou um `UserDetails` do security) lê uma collection lazy fora de uma transaction, o Hibernate lança `LazyInitializationException`. Escolha uma opção por association:
- `FetchType.EAGER` quando a association é **sempre** parte do uso da entity — por exemplo as permissions de um user, necessárias em toda autenticação, ou os books de uma person quando o DTO sempre os carrega. Então nenhuma proteção contra N+1 é necessária, porque a collection é sempre lida de qualquer jeito.
```java
@ManyToMany(fetch = FetchType.EAGER)
@JoinTable(name = "person_books",
    joinColumns = @JoinColumn(name = "person_id"),
    inverseJoinColumns = @JoinColumn(name = "book_id"))
private List<Book> books;
```
- LAZY mais um fetch explícito (`JOIN FETCH` no `@Query`, ou `@EntityGraph`) quando somente alguns casos de uso precisam da association.
- LAZY mais `@Transactional` no método do service que a lê, quando todo o mapeamento pode acontecer dentro de uma única transaction.

---

## Transactions e N+1

**Transactions.** Métodos de service que escrevem (`create`, `update`, `delete`) ou que fazem mais de uma operação de repository devem ser `@Transactional` (o `org.springframework.transaction.annotation.Transactional` do Spring), para que a operação inteira faça commit ou rollback junto. Métodos somente de leitura usam `@Transactional(readOnly = true)`: o Hibernate pula o dirty checking e o flush, e o driver/replica pode otimizar. A transaction fica na **service layer**, nunca no controller nem no repository.

```java
@Service
public class BookService {

    @Transactional(readOnly = true)
    public BookDTO findById(Long id) { ... }

    @Transactional
    public BookDTO update(BookDTO book) { ... }
}
```
Uma `RuntimeException` (todas as domain exceptions do pack são unchecked) faz rollback; uma checked exception **não**, a menos que você declare `rollbackFor`. Chamar um método `@Transactional` de outro método **da mesma classe** (`this.metodo()`) ignora o proxy e a transaction não é aplicada.

**N+1.** Listar entidades e ler uma association LAZY de cada uma gera 1 query + N queries. Sintomas: dezenas de selects idênticos no log. Soluções, em ordem de preferência: `JOIN FETCH`/`@EntityGraph` no caso de uso que precisa da association; DTO projection (`SELECT new ...BookSummaryDTO(b.id, b.title) FROM Book b`) quando só alguns campos são lidos; `spring.jpa.properties.hibernate.default_batch_fetch_size: 50` como rede de segurança global. Nunca "resolva" trocando tudo para `EAGER`. Para medir, ligue `logging.level.org.hibernate.SQL: DEBUG` **temporariamente** (nunca `show-sql: true` permanente) ou use as metrics de `observability`.

---

## Repository

Estenda `JpaRepository<Entity, Long>`. Queries custom usam `@Query` com JPQL. Deixe o service transformar uma linha ausente em uma domain exception (`findById(id).orElseThrow(...)`) — **não** adicione um `default getById(Long)` ao repository: `getById` já existe no `JpaRepository` (deprecated) e sobrescrevê-lo esconde um método de lazy reference atrás de um eager.

```java
public interface BookRepository extends JpaRepository<Book, Long> {

    @Query("SELECT b FROM Book b WHERE LOWER(b.title) LIKE LOWER(CONCAT('%', :title, '%'))")
    Page<Book> findBooksByTitle(@Param("title") String title, Pageable pageable);
}
```
Coloque em minúsculas **os dois lados** da comparação: o collation default do MySQL é case-insensitive e esconde uma query que só coloca o parâmetro em minúsculas, mas o PostgreSQL e outros são case-sensitive.

### Modifying queries
Um `UPDATE`/`DELETE` em JPQL ignora o persistence context. Marque-o com `@Modifying(clearAutomatically = true)` para que entities obsoletas sejam descartadas, e chame-o dentro de uma transaction (`@Transactional` no método do service — o `org.springframework.transaction.annotation.Transactional` do Spring):
```java
@Modifying(clearAutomatically = true)
@Query("UPDATE Book b SET b.price = :price WHERE b.id = :id")
void updatePrice(@Param("id") Long id, @Param("price") BigDecimal price);
```

- Prefira JPQL a native queries; use `nativeQuery = true` somente quando o JPQL não consegue expressar a query (SQL nativo é específico do database).
- Teste somente métodos `@Query` custom — nunca teste métodos padrão do Spring Data (`findById`, `save`, `delete`).
- Mantenha os repositories focados em acesso a dados; a lógica de negócio pertence ao service.

---

## DTO

Mesma estrutura da entity, sem annotations JPA — `implements Serializable`, getters/setters explícitos, `equals()`/`hashCode()`. Controllers nunca expõem entities. Sem `@XmlRootElement` em DTOs de produção. Quando o projeto usa HATEOAS, o DTO também estende `RepresentationModel<BookDTO>` e carrega `@Relation(collectionRelation = "books")` (skill `hateoas`).

```java
public class BookDTO implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;
    private String author;
    private LocalDate launchDate;
    private BigDecimal price;
    private String title;

    public BookDTO() {}

    // getters, setters, equals, hashCode — same shape as the entity
}
```

---

## Service — conversão entity ↔ DTO

A conversão sempre passa pelo mapper escolhido no Step 0 — nunca no controller, nunca à mão em cinco lugares.

**Dozer (default):** o wrapper `mapper/ObjectMapper` de `code-organization`, importado estaticamente (`import static br.com.padrao.mapper.ObjectMapper.parseObject;`) para que nunca colida com o próprio `ObjectMapper` do Jackson.

```java
@Service
public class BookService {

    private static final Logger logger = LoggerFactory.getLogger(BookService.class);

    @Autowired
    private BookRepository repository;

    @Transactional(readOnly = true)
    public Page<BookDTO> findAll(Pageable pageable) {
        logger.info("Finding all books!");
        return repository.findAll(pageable).map(entity -> parseObject(entity, BookDTO.class));
    }

    @Transactional(readOnly = true)
    public BookDTO findById(Long id) {
        logger.info("Finding one book!");
        var entity = repository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("No records found for this ID!"));
        return parseObject(entity, BookDTO.class);
    }

    @Transactional
    public BookDTO create(BookDTO book) {
        if (book == null) throw new RequiredObjectIsNullException();
        logger.info("Creating one book!");
        var entity = parseObject(book, Book.class);
        return parseObject(repository.save(entity), BookDTO.class);
    }

    @Transactional
    public BookDTO update(BookDTO book) {
        if (book == null) throw new RequiredObjectIsNullException();
        logger.info("Updating one book!");
        var entity = repository.findById(book.getId())
            .orElseThrow(() -> new ResourceNotFoundException("No records found for this ID!"));
        entity.setAuthor(book.getAuthor());
        entity.setLaunchDate(book.getLaunchDate());
        entity.setPrice(book.getPrice());
        entity.setTitle(book.getTitle());
        return parseObject(repository.save(entity), BookDTO.class);
    }

    @Transactional
    public void delete(Long id) {
        logger.info("Deleting one book!");
        var entity = repository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("No records found for this ID!"));
        repository.delete(entity);
    }
}
```

**MapStruct (alternativa):** adicione `mapstruct` e o annotation processor `mapstruct-processor` (veja `maven-config`), declare uma interface por par, e injete-a em vez de chamar `parseObject`:
```java
@Mapper(componentModel = "spring")
public interface BookMapper {

    BookDTO toDto(Book entity);

    Book toEntity(BookDTO dto);
}
```
```java
@Autowired
private BookMapper mapper;
```
O MapStruct gera código simples de getter/setter em tempo de compilação, então funciona com os accessors explícitos que este estilo exige (sem Lombok).

O `update` acima copia os campos um por um de propósito: ele mantém a entity gerenciada e seu `id`, e é explícito sobre o que um client pode alterar.

Quando o projeto usa HATEOAS, o service também adiciona os links (skill `hateoas`); quando pagina com HAL, ele retorna um `PagedModel` em vez de `Page` (skill `pagination`); sem HATEOAS, retorne `Page<BookDTO>` com a serialização estável descrita em `pagination`. Links nunca são adicionados no controller.

---

## Testes de repository contra um database real

Testes de métodos `@Query` custom usam `@DataJpaTest` no **mesmo tipo de database da produção**, iniciado com Testcontainers — não um H2 embutido. Assim JPQL, o seed data do Flyway e comportamentos específicos do database (collation, tipos) casam com o que roda em produção. Mantenha a substituição embutida desligada com `replace = NONE`.

Os packages do Boot 4 e o starter são novos:
- `org.springframework.boot.data.jpa.test.autoconfigure.DataJpaTest` e `org.springframework.boot.jdbc.test.autoconfigure.AutoConfigureTestDatabase` vêm do `spring-boot-starter-data-jpa-test` (veja `maven-config`);
- a classe de container é `org.testcontainers.mysql.MySQLContainer` (Testcontainers 2) — a antiga `org.testcontainers.containers.MySQLContainer` é deprecated. Para MySQL, crie-a com `.withConfigurationOverride("mysql-default-conf")`: a nova classe não aplica mais essa config de baixa memória implicitamente, e sem ela a ordenação de empates no seed data pode mudar entre execuções.

```java
@DataJpaTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
class BookRepositoryTest {

    static final MySQLContainer mysql = new MySQLContainer("mysql:9.1.0")
        .withConfigurationOverride("mysql-default-conf");

    static {
        mysql.start();
    }

    @DynamicPropertySource
    static void datasource(DynamicPropertyRegistry registry) {
        registry.add("spring.datasource.url", mysql::getJdbcUrl);
        registry.add("spring.datasource.username", mysql::getUsername);
        registry.add("spring.datasource.password", mysql::getPassword);
    }

    @Autowired
    private BookRepository repository;

    @Test
    void findBooksByTitleIgnoresCase() {
        var books = repository.findBooksByTitle("AGILE", PageRequest.of(0, 12, Sort.by("title")));

        assertFalse(books.isEmpty());
    }
}
```
O container é iniciado em um static block, então nenhum artifact extra de JUnit do Testcontainers é necessário. Se o projeto já tem a base class de container compartilhada do setup de integration tests (a skill `integration-testing`), estenda-a em vez de repetir o container aqui, para que a suíte inteira reutilize um container. O Flyway roda contra o container quando o context inicia, então as linhas seedadas estão disponíveis.

---

## Regras principais

- `ddl-auto: none` sempre — o schema é responsabilidade do Flyway. Veja `flyway-migrations`.
- `check_nullability: true` sempre — a checagem de null do próprio Hibernate é desligada silenciosamente caso contrário.
- `show-sql: false` em todos os ambientes; `open-in-view: false` sempre.
- `@GeneratedValue(strategy = GenerationType.IDENTITY)` — auto-increment, PK `Long`.
- Dinheiro em `BigDecimal` (coluna `decimal(…,2)`), nunca `Double`; compare com `compareTo`.
- Datas usam `java.time` (`LocalDate`, `LocalDateTime`, `Instant`) — nunca `java.util.Date` + `@Temporal`.
- Nunca `ORDINAL` para enums — sempre `@Enumerated(EnumType.STRING)` em um campo enum de verdade.
- `LAZY` por default; `EAGER` (ou um fetch explícito) para associations sempre lidas fora de uma transaction.
- `@Transactional` na service layer para escritas; `@Transactional(readOnly = true)` para leituras. Nunca no controller.
- Resolva N+1 com `JOIN FETCH`/`@EntityGraph`/projections, não trocando tudo para `EAGER`.
- Não faça override de `getById` nos repositories; use `findById(...).orElseThrow(...)` no service.
- Busca case-insensitive: `LOWER(column) LIKE LOWER(...)` nos dois lados.
- Conversão entre entity e DTO via o mapper escolhido, somente na service layer.
- **Sem Lombok** — nunca. Esta é uma escolha deliberada.
