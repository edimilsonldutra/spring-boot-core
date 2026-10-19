---
name: api-versioning
description: Versionamento de API REST no Spring Boot 4 — quando versionar (e quando uma mudança aditiva basta), versão major no path (/api/book/v1 → v2) com DTOs e controllers por versão, versionamento nativo do Spring Framework 7 (configureApiVersioning, @GetMapping(version), baseline "1.2+", 400 para versão inválida), deprecação com Deprecation/Sunset, client com ApiVersionInserter, Swagger por versão e testes. Use quando precisar quebrar um contrato sem quebrar os clients existentes.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md) e [`../web-config/SKILL.md`](../web-config/SKILL.md) (o `WebConfig` onde a configuração entra). Compatibilidade e contratos: [`../service-communication/SKILL.md`](../service-communication/SKILL.md) (seção 8) e [`../contract-testing/SKILL.md`](../contract-testing/SKILL.md). Política de deprecação: [`../release-management/SKILL.md`](../release-management/SKILL.md). Documentação por versão: [`../swagger-advanced/SKILL.md`](../swagger-advanced/SKILL.md).

# Versionamento de API

**Versionar é caro**: cada versão viva é código, testes, documentação e suporte a mais. A primeira pergunta é se você **precisa** de uma nova versão.

## 1. Precisa mesmo?

| Mudança | Quebra os clients? | O que fazer |
|---|---|---|
| Adicionar campo opcional na resposta, endpoint novo, parâmetro opcional | Não (clients toleram campos desconhecidos — *tolerant reader*) | **Na versão atual**, sem versão nova |
| Remover/renomear campo, mudar tipo ou formato, tornar campo obrigatório, mudar semântica ou status code | **Sim** | **Nova versão major**, convivendo com a antiga |
| Corrigir um bug que clients usam como comportamento | Talvez | Trate como quebra se alguém depende dele (`contract-testing` mostra quem) |

O Jackson 3 já ignora propriedades desconhecidas na entrada (`web-config`), o que ajuda na evolução aditiva. Detecte quebras **antes do merge** comparando o OpenAPI (`oasdiff` — `contract-testing`).

---

## 2. Onde a versão vai

| Estratégia | Exemplo | Prós | Contras |
|---|---|---|---|
| **Path** (padrão do pacote) | `/api/book/v1`, `/api/book/v2` | Visível, fácil de testar no browser/Postman, roteável no gateway, cacheável | URL muda entre versões |
| **Header** | `API-Version: 1.1` | URL estável | Invisível no browser; proxies/caches precisam variar pelo header (`Vary`) |
| **Media type** | `Accept: application/json;v=1.1` | "Purista" REST | Mais difícil de usar e documentar |
| **Query param** | `?version=1.1` | Simples | Mistura versão com filtros; fácil de esquecer |

O pacote usa **a versão major no path** desde o primeiro CRUD (`/api/book/v1` — `code-organization`). Ela é a forma recomendada para **quebras de contrato**. O versionamento nativo do Spring 7 (seção 4) é útil para **variações menores** dentro de uma major ou quando a URL precisa ser estável.

---

## 3. Versão major no path (v1 → v2)

Exemplo: a v2 de Book troca `author` (texto) por `authors` (lista) — uma quebra.

```
controllers/
├── BookController.java          # @RequestMapping("/api/book/v1")
└── BookControllerV2.java        # @RequestMapping("/api/book/v2")
data/dto/
├── BookDTO.java                 # contrato v1 — congelado
└── v2/BookV2DTO.java            # contrato v2
```
```java
@RestController
@RequestMapping("/api/book/v2")
@Tag(name = "Book v2", description = "Endpoints for Managing Books (v2)")
public class BookControllerV2 implements BookControllerV2Docs {

    @Autowired
    private BookService service;

    @GetMapping(value = "/{id}", produces = MediaType.APPLICATION_JSON_VALUE)
    @Override
    public BookV2DTO findById(@PathVariable("id") Long id) {
        return service.findByIdV2(id);
    }
}
```
- **Um service, dois contratos.** A regra de negócio não se duplica: o service trabalha com a entity e converte para o DTO de cada versão (dois métodos de conversão ou dois mappers). Só a **borda** (controller + DTO) é por versão.
- **O DTO da v1 fica congelado.** Mudanças novas vão para a v2; a v1 só recebe correções que não mudem o contrato.
- **Banco compatível com as duas versões** enquanto ambas existirem (`flyway-migrations`: expand → contract). Remover a coluna que a v1 usa só depois de desligar a v1.
- `springdoc.paths-to-match` precisa incluir `/api/**/v2/**` (o default do pacote só expõe `/v1/`) — e um grupo por versão no Swagger (`swagger-advanced`).
- Um gateway pode rotear `/v1` e `/v2` para implantações diferentes durante uma migração grande (`api-gateway`).

---

## 4. Versionamento nativo do Spring Framework 7

O Spring 7 resolve a versão da request (header, path, query ou media type), escolhe o método do controller pela versão e valida versões não suportadas. Configure no `WebConfig` (`web-config`):

```java
@Override
public void configureApiVersioning(ApiVersionConfigurer configurer) {
    configurer.useRequestHeader("API-Version")
        .addSupportedVersions("1.0", "1.1", "1.2")
        .setDefaultVersion("1.0")
        .setVersionRequired(false);
}
```
Outros resolvedores do mesmo configurer: `useQueryParam("version")`, `useMediaTypeParameter(MediaType.APPLICATION_JSON, "v")` e `usePathSegment(index)` (a versão em um segmento do path). Escolha **um** e mantenha.

Mapeamento por versão no controller:
```java
@GetMapping(value = "/{id}", version = "1.0")
public BookDTO findById(@PathVariable("id") Long id) { ... }

@GetMapping(value = "/{id}", version = "1.2+")
public BookV12DTO findByIdWithRating(@PathVariable("id") Long id) { ... }
```
- **`"1.0"`** casa só com a 1.0; **`"1.2+"`** (baseline) casa com a 1.2 e as versões suportadas acima dela; **sem `version`** casa com qualquer versão, mas perde para um método com versão mais específica.
- Entre os métodos que casam, vence a **maior versão menor ou igual** à pedida.
- Versão inválida ou não suportada → **400** (`InvalidApiVersionException`); versão ausente com `setVersionRequired(true)` → **400** (`MissingApiVersionException`); versão sem método correspondente → **400** (`NotAcceptableApiVersionException`). Esses erros chegam ao handler como `ProblemDetail` (`exception-handling`).
- O parser padrão é semântico (`major.minor.patch`; minor/patch ausentes valem 0).
- O Spring Boot 4 também expõe essa configuração por propriedades (`spring.mvc.apiversion.*`, como `use.header`, `supported`, `default`). Confira os nomes exatos na documentação da versão do Boot resolvida em `maven-config` antes de usá-las; a configuração Java acima é a forma garantida.

### Deprecação na própria resposta
```java
var deprecation = new StandardApiVersionDeprecationHandler();
deprecation.configureVersion("1.0")
    .setDeprecationDate(ZonedDateTime.parse("2026-01-01T00:00:00Z"))
    .setSunsetDate(ZonedDateTime.parse("2026-07-01T00:00:00Z"))
    .setSunsetLink(URI.create("https://example.com/docs/migration-v1-v2"));
configurer.setDeprecationHandler(deprecation);
```
Requests na 1.0 passam a receber os headers `Deprecation`, `Sunset` e `Link` (RFC 9745 e RFC 8594). Para o versionamento por path da seção 3, adicione os mesmos headers com um filtro ou interceptor nos controllers da versão antiga.

### Client
`RestClient`, `WebClient` e os HTTP Service clients enviam a versão com um `ApiVersionInserter`:
```java
var client = RestClient.builder()
    .baseUrl("http://catalog")
    .apiVersionInserter(ApiVersionInserter.useHeader("API-Version"))
    .build();

var book = client.get().uri("/api/book/{id}", id).apiVersion("1.2").retrieve().body(BookV12DTO.class);
```
Os demais conectores de `service-communication` (timeouts, tradução de erros) continuam valendo.

---

## 5. Ciclo de vida de uma versão

1. **Lançar a v2** convivendo com a v1 (mesmo banco compatível).
2. **Anunciar a deprecação da v1** com data (`Deprecation`), guia de migração e prazo de desligamento (`Sunset`). Janela típica: 6–12 meses para API pública, menos para interna (`release-management`).
3. **Medir quem ainda usa a v1** (métrica por versão e por client — `observability`; contratos — `contract-testing`). Avise diretamente quem ainda chama.
4. **Desligar** na data: a rota passa a responder `410 Gone` por um tempo, com link para a migração, antes de sumir.
5. **Limpar**: remover controllers, DTOs, testes e a parte "expand" do banco (contract).

Nunca mantenha mais de **duas** versões major vivas sem um motivo forte.

---

## 6. Testes

- Cada versão viva tem seus **testes de integração** (`integration-testing`) — o teste da v1 é a garantia de que a v2 não a quebrou.
- Com o versionamento nativo: request sem versão (default), com versão suportada, com baseline (`1.3` caindo no método `1.2+`), versão desconhecida (**400**) e headers de deprecação na versão antiga. No MockMvc, `MockMvcRequestBuilders.get(...).header("API-Version", "1.2")` (ou o suporte de versão do próprio MockMvc).
- `oasdiff` no CI comparando o OpenAPI da `main` com o do PR: quebra na v1 bloqueia o merge (`contract-testing`).

---

## Regras principais

- Mudança aditiva **não** cria versão; quebra de contrato cria uma **nova versão major** que convive com a anterior.
- Padrão do pacote: versão major no path (`/api/<recurso>/v1`, `/v2`), controller e DTO por versão, **um** service com a regra de negócio.
- O DTO de uma versão publicada fica congelado.
- Versionamento nativo do Spring 7 (`configureApiVersioning`, `@GetMapping(version = ...)`) para variações menores ou URL estável — um único resolvedor; versões inválidas respondem 400.
- Deprecação com data, `Deprecation`/`Sunset`/`Link` na resposta, guia de migração e medição de uso antes de desligar.
- Banco compatível com todas as versões vivas (expand → contract).
- Swagger com um grupo por versão; `paths-to-match` inclui todas as versões expostas.
- Detecte quebras de contrato no CI (`oasdiff`, contract tests).
- **Sem Lombok** — deliberado.
