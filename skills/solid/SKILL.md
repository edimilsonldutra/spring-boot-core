---
name: solid
description: Princípios SOLID aplicados a Spring Boot no padrão do pacote — responsabilidade única em services e controllers, aberto/fechado com estratégias como beans, substituição de Liskov em hierarquias e exceptions, segregação de interfaces (ports, ControllerDocs, repositories) e inversão de dependência com injeção do Spring — mais coesão, acoplamento, DRY, KISS, YAGNI, Lei de Demeter, composição sobre herança, sinais de violação e quando NÃO aplicar. Use ao desenhar classes novas, revisar design de código ou quando uma classe ficar difícil de testar ou de mudar.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) (layout flat-by-layer e preferência de injeção) e [`../code-style/SKILL.md`](../code-style/SKILL.md). Mudar o design de código existente com segurança: [`../refactoring/SKILL.md`](../refactoring/SKILL.md). Soluções recorrentes: [`../design-patterns/SKILL.md`](../design-patterns/SKILL.md). Domínio rico: [`../ddd-hexagonal/SKILL.md`](../ddd-hexagonal/SKILL.md).

# SOLID

SOLID são cinco princípios para código **fácil de mudar e de testar**. São **heurísticas**, não leis: servem para diagnosticar por que uma classe dói, não para justificar camadas de abstração antecipadas. A pergunta que guia todos eles: **quando o requisito X mudar, quantos arquivos eu toco e quantos testes quebram?**

| Princípio | Em uma frase | Sintoma de violação |
|---|---|---|
| **S** — Single Responsibility | Uma classe tem **um motivo para mudar** | `BookService` com 15 dependências, que muda por causa de e-mail, PDF e regra de preço |
| **O** — Open/Closed | Adicionar comportamento **sem editar** o que funciona | Todo formato novo de exportação exige mexer no mesmo `if/else` |
| **L** — Liskov Substitution | Uma implementação pode **substituir** a abstração sem surpresa | Subclasse que lança `UnsupportedOperationException` ou ignora parte do contrato |
| **I** — Interface Segregation | Clientes não dependem de métodos que **não usam** | Interface com 20 métodos que cada implementação preenche pela metade |
| **D** — Dependency Inversion | Regra de negócio depende de **abstrações**, não de detalhes | Service que instancia `new SmtpClient(...)` ou `new RestTemplate()` por dentro |

---

## S — Responsabilidade única

**"Motivo para mudar" é um ator ou uma preocupação**, não "um método". O `BookService` do pacote tem uma responsabilidade: as regras de Book. Ele não deve também montar planilhas, enviar e-mails e chamar o gateway de pagamento.

Antes:
```java
@Service
public class BookService {

    public BookDTO create(BookDTO book) { ... }
    public Resource exportPage(Pageable pageable, String accept) { /* monta XLSX, CSV e PDF aqui */ }
    public void notifyNewBook(BookDTO book) { /* monta e envia o e-mail aqui */ }
}
```
Depois — cada preocupação na sua classe, o service orquestra:
```java
@Service
public class BookService {

    @Autowired
    private BookRepository repository;

    @Autowired
    private FileExporterFactory exporterFactory;

    @Autowired
    private ApplicationEventPublisher publisher;

    @Transactional
    public BookDTO create(BookDTO book) {
        if (book == null) throw new RequiredObjectIsNullException();
        var saved = repository.save(parseObject(book, Book.class));
        publisher.publishEvent(new BookCreatedEvent(saved.getId()));
        return parseObject(saved, BookDTO.class);
    }
}
```
O formato do arquivo é responsabilidade dos exporters (`file-import-export`); o e-mail, de um listener (`email`). Mudar o layout do PDF não toca o `BookService` nem seus testes.

**Nas camadas do pacote**, o SRP já está embutido: controller só HTTP, service só regra e transação, repository só dados (`code-organization`). As violações típicas são **regra no controller**, **query montada no service** e **o "God Service"** (`refactoring`: Extract Class, separar por caso de uso).

Sinais: mais de ~7 dependências injetadas; nome genérico (`Manager`, `Helper`, `Utils`, `Processor`); testes que precisam mockar coisas que o caso testado não usa.

---

## O — Aberto para extensão, fechado para modificação

Comportamento que **varia por tipo** (formato de arquivo, meio de pagamento, regra de frete) é um bom candidato. Com o Spring, a extensão natural é **uma interface + uma implementação por variação, todas beans**, injetadas como lista:

```java
public interface FileExporter {

    boolean supports(String mediaType);

    Resource exportFile(List<BookDTO> books) throws Exception;
}
```
```java
@Component
public class FileExporterFactory {

    @Autowired
    private List<FileExporter> exporters;

    public FileExporter getExporter(String mediaType) {
        return exporters.stream()
            .filter(exporter -> exporter.supports(mediaType))
            .findFirst()
            .orElseThrow(() -> new BadRequestException("Invalid export format!"));
    }
}
```
Um formato novo (JSON Lines, ODS) é **uma classe nova** com `@Component` — nenhuma linha existente muda, nenhum teste existente quebra.

- A factory com `if` de `file-import-export` está **correta** para três formatos fixos; migre para esta forma quando a lista crescer ou quando outros times adicionarem formatos. **Não antecipe** (YAGNI).
- `switch` sobre um **enum ou sealed interface** que você controla e que raramente cresce não é violação: o compilador avisa se um caso faltar (`java-modern-features`). O problema é o mesmo `switch` **repetido** em vários lugares.
- Pontos de extensão do próprio Spring seguem o OCP: `@ControllerAdvice` (`exception-handling`), `WebMvcConfigurer` (`web-config`), `OpenApiCustomizer` (`swagger-advanced`) — você estende sem editar o framework.

---

## L — Substituição de Liskov

Quem usa a abstração não pode precisar saber qual implementação recebeu. Uma implementação **não pode exigir mais** (pré-condições mais fortes) **nem entregar menos** (pós-condições mais fracas) que o contrato.

Violações comuns:
- Implementação que lança `UnsupportedOperationException` para parte da interface → a interface é grande demais (veja **I**).
- Um `FileImporter` que devolve `null` quando os outros devolvem lista vazia; um que fecha o `InputStream` recebido e outro que não.
- Herança por reaproveitamento: `PremiumBook extends Book` que muda o significado de `getPrice()`. Prefira **composição** (abaixo).
- Exceptions: uma implementação que lança uma exception que o contrato não prevê, obrigando o chamador a conhecer a classe concreta. No pacote, as exceptions de domínio são unchecked e documentadas (`exception-handling`).

**Teste de contrato** pega violações: uma classe de teste abstrata com os casos do contrato, estendida uma vez por implementação (`test-patterns`).

---

## I — Segregação de interfaces

Interfaces pequenas, desenhadas **pelo que o cliente precisa**:
- **Ports** no hexagonal (`ddd-hexagonal`): `LoadLoanPort` e `SaveLoanPort` em vez de um `LoanPersistencePort` com tudo — cada caso de uso depende só do que usa, e o fake de teste fica trivial.
- **`*ControllerDocs` por controller** (`swagger`): uma interface por recurso, não uma "ApiDocs" gigante.
- **Repositories:** estender `JpaRepository` expõe `deleteAll()` para todo mundo. Para agregados em que apagar em massa nunca deve acontecer, estenda `Repository<T, ID>` e declare só os métodos usados (`spring-data-jpa`).
- Clients HTTP (`@HttpExchange`): uma interface por serviço remoto, só com as chamadas que este serviço faz (`service-communication`).

Sinal: a implementação tem métodos vazios ou que lançam "not supported"; o mock de teste precisa stubar métodos irrelevantes.

---

## D — Inversão de dependência

A regra de negócio depende de **abstrações**; os detalhes (SMTP, S3, HTTP, banco) dependem delas e são **injetados**:
- O Spring já faz a injeção: o service recebe `JavaMailSender`, `S3Template`, `RestClient`, repositories — **nunca** os instancia com `new` por dentro (impossível de testar e de configurar).
- Respeite a preferência de injeção do projeto (field por padrão, constructor se escolhido — `code-organization`). A injeção por constructor deixa as dependências **visíveis** (e um constructor enorme denuncia uma violação de **S**), mas a inversão vale com qualquer uma.
- **Interface com uma única implementação não é obrigatória.** `BookService` não precisa de `BookServiceImpl`: o Mockito mocka classes, e o Spring injeta classes. Crie a interface quando houver **mais de uma implementação real**, quando ela for um **port** de um domínio hexagonal, ou quando a dependência é **externa e instável** (um parceiro, um provedor que pode ser trocado).
- Configuração também é dependência: valores por `@Value`/`@ConfigurationProperties`, nunca constantes com URL, timeout ou credencial no código.

---

## Princípios vizinhos

- **Coesão alta, acoplamento baixo:** o que muda junto fica junto (por isso o pacote agrupa por camada e o `modular-monolith` por domínio); módulos conversam por interfaces e eventos, não pelos internos uns dos outros.
- **DRY** — não duplique **conhecimento** (uma regra de negócio em dois lugares). Dois trechos parecidos que mudam por motivos diferentes **não** são duplicação: unificá-los cria acoplamento errado. Regra dos três antes de abstrair (`refactoring`).
- **KISS** — a solução mais simples que atende. Um `if` claro vence uma hierarquia de estratégias para dois casos.
- **YAGNI** — não construa extensão "para o futuro". A flexibilidade que ninguém pediu é custo agora e quase sempre do tipo errado depois.
- **Lei de Demeter** — fale com seus vizinhos: `loan.getUser().getAddress().getCity()` acopla o chamador a três classes. Pergunte ao objeto o que você precisa (`loan.deliveryCity()`) ou traga o dado pronto no DTO.
- **Composição sobre herança** — herde só quando é realmente um "é um" com o mesmo contrato (e o Liskov vale). Para reaproveitar comportamento, injete um colaborador. `RepresentationModel` (`hateoas`) e `ResponseEntityExceptionHandler` (`exception-handling`) são heranças **do framework**, desenhadas para isso — tudo bem.
- **Tell, don't ask** — em um domínio rico, o objeto aplica sua regra (`loan.renew(clock)`), em vez de o service pegar os campos, decidir e escrever de volta (`ddd-hexagonal`).

---

## Quando NÃO aplicar

- **CRUD simples** no layout flat-by-layer: controller → service → repository já é o suficiente. Não crie interfaces, factories e estratégias para um cadastro que só grava e lê.
- **Código que não muda:** o benefício do SOLID aparece na mudança. Uma classe estável, testada e feia pode ficar como está (`refactoring`: quando não refatorar).
- **Abstrair antes da segunda variação real.** Com uma implementação, você ainda não sabe qual é a abstração certa.
- **Por estética.** "Não está SOLID" não é motivo de mudança; "precisei tocar cinco arquivos para adicionar um formato" é.

---

## Na revisão de código

| Sinal no diff | Princípio | Pergunta |
|---|---|---|
| Service ganhando uma dependência de infra nova (e-mail, arquivo, HTTP) | S | Isso é regra deste service ou outra preocupação? |
| Mais um `else if` / `case` no mesmo lugar de sempre | O | Esta variação vai continuar crescendo? |
| `UnsupportedOperationException`, métodos vazios | L, I | A interface é grande demais? |
| `new` de um cliente/infra dentro do service | D | Isso não deveria ser injetado? |
| Interface + `Impl` com uma implementação, sem port nem dependência externa | D (excesso) | Que problema essa abstração resolve hoje? |
| Cadeia `a.getB().getC().getD()` | Demeter | Qual objeto deveria responder isso? |

Achados de design são, em geral, 🟡 **Minor** — 🟠 **Major** quando já causam bug, impedem o teste ou vão se espalhar (`code-reviewer`).

---

## Regras principais

- Use SOLID para diagnosticar dor real (difícil de mudar, difícil de testar), não para criar abstrações antecipadas.
- **S:** uma classe, um motivo para mudar; controller só HTTP, service só regra, infraestrutura (e-mail, arquivo, HTTP) em componentes próprios; desconfie de mais de ~7 dependências.
- **O:** variações por tipo como implementações de uma interface, injetadas como `List<...>` — quando a lista cresce; `switch` exaustivo sobre enum/sealed é aceitável.
- **L:** implementações cumprem o contrato inteiro (sem `UnsupportedOperationException`, sem `null` onde o contrato promete lista); composição em vez de herança para reaproveitar código; testes de contrato.
- **I:** interfaces pequenas pelo cliente: ports por caso de uso, `*ControllerDocs` por controller, repositories só com os métodos usados quando apagar em massa é perigoso.
- **D:** dependências injetadas, nunca `new` de infraestrutura no service; interface só com duas implementações reais, port de domínio ou dependência externa instável.
- DRY sobre conhecimento, não sobre código parecido; KISS; YAGNI; Lei de Demeter; tell, don't ask.
- CRUD simples continua simples.
- **Sem Lombok** — deliberado.
