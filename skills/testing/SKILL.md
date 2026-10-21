---
name: testing
description: Unit tests e slice tests no Spring Boot 4 — service com JUnit 5, Mockito e AssertJ (sem Spring), controller com @WebMvcTest, MockMvc e @MockitoBean, @ParameterizedTest, ArgumentCaptor, naming Given-When-Then e o que testar ou não. Use quando escrever testes de service ou de controller. Não use para testes contra banco real ou a aplicação rodando (integration-testing) nem para cobertura (test-coverage).
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) e [`../code-style/SKILL.md`](../code-style/SKILL.md) para as preferências do projeto, o package layout base e as convenções de code style.

# Testing

Pirâmide: **muitos unit tests** (milissegundos, sem Spring, sem database) → **alguns slice tests** (só a web layer) → **poucos integration tests** com database real em container (`integration-testing`, e os `@DataJpaTest` de `spring-data-jpa`). Cada nível prova uma coisa diferente; não duplique.

---

## Dependencies

Já vêm com `spring-boot-starter-test` (JUnit 5, Mockito, AssertJ, Hamcrest, JSONassert, JsonPath). O argLine do surefire com o agent do Mockito está em `maven-config` — sem ele o JDK 21+ avisa em todo teste.

Para slice tests da web layer, o Boot 4 tem um módulo de teste próprio:
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-webmvc-test</artifactId>
    <scope>test</scope>
</dependency>
```
No Boot 4 as annotations de slice mudaram de package junto com os starters (`@WebMvcTest` em `org.springframework.boot.webmvc.test.autoconfigure`, como `@DataJpaTest` em `org.springframework.boot.data.jpa.test.autoconfigure`). Confirme o import exato na versão que o projeto resolveu (Context7, veja `maven-config`) em vez de copiar de um projeto Boot 3.

---

## Unit test de service (o teste mais comum)

`@ExtendWith(MockitoExtension.class)`, sem `@SpringBootTest`. `@Mock` para as dependencies externas (repository), `@InjectMocks` para a classe sob teste — funciona com injection por field ou por constructor. O mapper (Dozer) é uma classe estática simples: use o real, não faça mock.

```java
@ExtendWith(MockitoExtension.class)
class BookServiceTest {

    @Mock
    private BookRepository repository;

    @InjectMocks
    private BookService service;

    @Test
    void findByIdReturnsTheBookWhenItExists() {
        var book = new Book();
        book.setId(1L);
        book.setTitle("Clean Code");
        when(repository.findById(1L)).thenReturn(Optional.of(book));

        var result = service.findById(1L);

        assertThat(result.getId()).isEqualTo(1L);
        assertThat(result.getTitle()).isEqualTo("Clean Code");
    }

    @Test
    void findByIdThrowsWhenTheBookDoesNotExist() {
        when(repository.findById(99L)).thenReturn(Optional.empty());

        assertThatThrownBy(() -> service.findById(99L))
                .isInstanceOf(ResourceNotFoundException.class)
                .hasMessage("No records found for this ID!");
    }

    @Test
    void createThrowsWhenTheBookIsNull() {
        assertThrows(RequiredObjectIsNullException.class, () -> service.create(null));
        verifyNoInteractions(repository);
    }
}
```
- Nome do método diz **o comportamento** (`findByIdThrowsWhenTheBookDoesNotExist`), não a implementação (`testFindById2`).
- Estrutura **Given / When / Then** separada por linha em branco, sem comentários (preferência do pack).
- Assert o resultado e os efeitos relevantes; `verify(...)` só para efeitos colaterais que importam (`verify(repository).delete(entity)`), não para cada chamada — testes presos à implementação quebram a cada refactor.
- `assertThat` (AssertJ) lê melhor que `assertEquals`; o pack já usa os dois — seja consistente dentro de uma classe.

### ArgumentCaptor
Para verificar **o que** foi salvo:
```java
var captor = ArgumentCaptor.forClass(Book.class);
when(repository.save(captor.capture())).thenAnswer(invocation -> invocation.getArgument(0));

service.create(dto);

assertThat(captor.getValue().getTitle()).isEqualTo(dto.getTitle());
```

### Strict stubs
O `MockitoExtension` falha o teste se um `when(...)` não for usado (`UnnecessaryStubbingException`). Isso é útil: apague o stub sobrando em vez de usar `lenient()`.

---

## @ParameterizedTest

Uma regra, vários valores — em vez de copiar o teste:
```java
@ParameterizedTest
@ValueSource(strings = {"", " ", "   "})
void isBlankTitleReturnsTrueForBlankValues(String title) {
    assertTrue(TitleRules.isBlank(title));
}
```
Para pares entrada/saída: `@CsvSource({"10.0, 11.0", "0, 0"})`. Para dados complexos: `@MethodSource`.

---

## Slice test de controller (@WebMvcTest)

Sobe **somente** a web layer (controllers, handler de exceptions, conversão JSON, validation). O service vira um mock. Prova: rota, status HTTP, JSON, validation, formato de erro.

```java
@WebMvcTest(BookController.class)
class BookControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private BookService service;

    @Test
    void findByIdReturns200WithTheBook() throws Exception {
        var dto = new BookDTO();
        dto.setId(1L);
        dto.setTitle("Clean Code");
        when(service.findById(1L)).thenReturn(dto);

        mockMvc.perform(get("/api/book/v1/{id}", 1L).accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.title").value("Clean Code"));
    }

    @Test
    void findByIdReturns404WhenTheServiceThrows() throws Exception {
        when(service.findById(99L)).thenThrow(new ResourceNotFoundException("No records found for this ID!"));

        mockMvc.perform(get("/api/book/v1/{id}", 99L).accept(MediaType.APPLICATION_JSON))
                .andExpect(status().isNotFound())
                .andExpect(jsonPath("$.message").value("No records found for this ID!"));
    }

    @Test
    void createReturns400WithFieldErrorsWhenTheBodyIsInvalid() throws Exception {
        mockMvc.perform(post("/api/book/v1")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content("{\"title\":\"\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.errors.title").exists());
    }
}
```
- **`@MockitoBean`** (`org.springframework.test.context.bean.override.mockito.MockitoBean`) substitui o antigo `@MockBean`, que foi removido no Boot 4.
- O `@ControllerAdvice` do projeto é carregado pelo slice — por isso o 404 e o 400 acima funcionam.
- Com Spring Security no projeto, o slice aplica a security: use `@WithMockUser` (ou `SecurityMockMvcRequestPostProcessors.jwt()` se usar resource server) e inclua o `SecurityConfig` com `@Import`.
- `MockMvc` valida o contrato HTTP sem rede e sem porta; REST Assured (`integration-testing`) fica para os testes contra a aplicação rodando.

---

## O que testar e o que não testar

**Teste:** regras de negócio do service (ramos, validações, exceptions), conversões e cálculos, o contrato da web layer (status, JSON, erros), queries `@Query` customizadas (em `spring-data-jpa`).
**Não teste:** getters/setters/`equals`/`hashCode` triviais, métodos padrão do Spring Data (`save`, `findById`), o framework, nem código sem lógica que só delega. Um teste que apenas repete a implementação não protege nada.

Regras de qualidade:
- **Determinístico:** nada de `LocalDate.now()`, `Random` ou ordem de `HashMap` no resultado esperado — injete um `Clock` ou fixe os valores.
- **Independente:** cada teste monta o próprio estado; sem ordem entre testes de unit/slice (os integration tests do pack podem ter ordem — veja `integration-testing`).
- **Rápido:** unit test que demora mais de 100 ms provavelmente não é unit test.
- **Um motivo para falhar** por teste.
- Dados de teste repetitivos ganham um helper estático (`BookMocks.validBook()`), em `src/test`.

---

## Cobertura (JaCoCo)

Cobertura mostra o que **não** foi testado; não prova qualidade — um teste sem `assert` dá 100% de cobertura e zero proteção. O padrão do pacote é **90% de linha e de branch** (`check` do JaCoCo); prefira **branch** a linha nas camadas de regra de negócio e, em **legado**, use **cobertura do código novo + catraca** até chegar lá. Nunca persiga 100% escrevendo testes vazios. A configuração do JaCoCo (Maven e Gradle, `@{argLine}` com o agent do Mockito, exclusões, gate no CI) e o **mutation testing com PIT** estão em `test-coverage`.

## Onde continuar

- **Padrões de teste** (test doubles, Test Data Builder, `@Nested`, property-based, test smells, testes flaky, TDD/BDD): `test-patterns`.
- **Testes de integração com banco real em container** (Testcontainers, REST Assured, isolamento de dados, cache de contexto): `integration-testing`.
- **Cobertura e qualidade da suíte** (JaCoCo, diff coverage, PIT): `test-coverage`.
- **Contratos entre serviços**: `contract-testing`. **AWS local**: `localstack`.

---

## Regras principais

- Unit test de service: `@ExtendWith(MockitoExtension.class)`, sem Spring; slice de controller: `@WebMvcTest` + `MockMvc` + `@MockitoBean`.
- `@MockBean` não existe mais no Boot 4 — use `@MockitoBean`.
- Nome do método descreve o comportamento; estrutura Given/When/Then; sem comentários.
- `verify` só para efeitos colaterais relevantes; assert o resultado.
- Sem `lenient()` para esconder stub sobrando.
- Determinístico, independente e rápido; injete `Clock` em vez de `now()`.
- Não teste getters, o framework nem métodos padrão do Spring Data.
- Confirme os imports de teste do Boot 4 na versão resolvida.
- **Sem Lombok** — deliberado.
