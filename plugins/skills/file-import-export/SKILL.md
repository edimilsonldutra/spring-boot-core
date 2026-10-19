---
name: file-import-export
description: Importar e exportar dados em XLSX e CSV no Spring Boot 4 — contratos FileImporter/FileExporter com factory, Apache POI (SXSSF para exportar em stream) e Commons CSV, interface MediaTypes, exportação por header Accept, criação em massa validada linha a linha em uma transação, limites, CSV injection, zip bomb e testes. Use quando a API precisar receber uma planilha ou CSV, ou devolver dados como XLSX/CSV.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) (packages `file/importer` e `file/exporter`), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../file-upload-download/SKILL.md`](../file-upload-download/SKILL.md) (limites e validação do upload), [`../bean-validation/SKILL.md`](../bean-validation/SKILL.md) e [`../pagination/SKILL.md`](../pagination/SKILL.md). PDF entra na mesma estrutura de exporters: [`../pdf-reports/SKILL.md`](../pdf-reports/SKILL.md).

# Importação e exportação de arquivos (XLSX e CSV)

Dois fluxos:
- **Importar** (criação em massa): o client envia um `.xlsx` ou `.csv`; a API lê, valida **cada linha**, grava tudo e devolve o que foi criado.
- **Exportar**: o client pede uma página de dados no formato que quer (`Accept: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `text/csv` ou `application/pdf`) e recebe o arquivo.

## 1. Dependencies

| Formato | Coordenadas | Versão |
|---|---|---|
| XLSX | `org.apache.poi:poi-ooxml` | `${apache.poi.version}` — fora do BOM (`maven-config`) |
| CSV | `org.apache.commons:commons-csv` | `${commons-csv.version}` — fora do BOM |

Adicione só os formatos que o projeto usa.

---

## 2. Estrutura

```
br.com.padrao/
└── file/
    ├── exporter/
    │   ├── MediaTypes.java
    │   ├── contract/FileExporter.java
    │   ├── factory/FileExporterFactory.java
    │   └── impl/{XlsxExporter, CsvExporter, PdfExporter}.java
    └── importer/
        ├── contract/FileImporter.java
        ├── factory/FileImporterFactory.java
        └── impl/{XlsxImporter, CsvImporter}.java
```

```java
public interface MediaTypes {

    String APPLICATION_XLSX_VALUE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
    String APPLICATION_CSV_VALUE = "text/csv";
    String APPLICATION_PDF_VALUE = "application/pdf";
}
```
A skill `swagger` referencia essas constantes nos endpoints de arquivo — nunca strings soltas.

```java
public interface FileImporter {

    List<BookDTO> importFile(InputStream inputStream) throws Exception;
}

public interface FileExporter {

    Resource exportFile(List<BookDTO> books) throws Exception;
}
```

As factories escolhem a implementação; as implementações são beans (`@Component`) para que possam receber dependências:
```java
@Component
public class FileImporterFactory {

    @Autowired
    private ApplicationContext context;

    public FileImporter getImporter(String fileName) {
        var name = fileName.toLowerCase(Locale.ROOT);
        if (name.endsWith(".xlsx")) return context.getBean(XlsxImporter.class);
        if (name.endsWith(".csv")) return context.getBean(CsvImporter.class);
        throw new BadRequestException("Invalid file format! Use XLSX or CSV.");
    }
}

@Component
public class FileExporterFactory {

    @Autowired
    private ApplicationContext context;

    public FileExporter getExporter(String acceptHeader) {
        if (MediaTypes.APPLICATION_XLSX_VALUE.equalsIgnoreCase(acceptHeader)) return context.getBean(XlsxExporter.class);
        if (MediaTypes.APPLICATION_CSV_VALUE.equalsIgnoreCase(acceptHeader)) return context.getBean(CsvExporter.class);
        if (MediaTypes.APPLICATION_PDF_VALUE.equalsIgnoreCase(acceptHeader)) return context.getBean(PdfExporter.class);
        throw new BadRequestException("Invalid export format!");
    }
}
```
Mensagens seguem o idioma salvo (`exception-handling`).

---

## 3. Importar

### Implementações
```java
@Component
public class CsvImporter implements FileImporter {

    @Override
    public List<BookDTO> importFile(InputStream inputStream) throws Exception {
        var format = CSVFormat.DEFAULT.builder()
            .setHeader()
            .setSkipHeaderRecord(true)
            .setIgnoreEmptyLines(true)
            .setTrim(true)
            .get();
        try (var reader = new InputStreamReader(inputStream, StandardCharsets.UTF_8);
             var parser = format.parse(reader)) {
            var books = new ArrayList<BookDTO>();
            for (var record : parser) {
                books.add(toDto(record.get("title"), record.get("author"), record.get("launch_date"), record.get("price")));
            }
            return books;
        }
    }
}
```
(Em versões antigas do Commons CSV o builder termina em `.build()`; use a forma da versão resolvida em `maven-config`.)

```java
@Component
public class XlsxImporter implements FileImporter {

    @Override
    public List<BookDTO> importFile(InputStream inputStream) throws Exception {
        try (var workbook = new XSSFWorkbook(inputStream)) {
            var sheet = workbook.getSheetAt(0);
            var formatter = new DataFormatter();
            var books = new ArrayList<BookDTO>();
            for (var row : sheet) {
                if (row.getRowNum() == 0 || isEmpty(row)) continue;
                books.add(toDto(
                    formatter.formatCellValue(row.getCell(0)),
                    formatter.formatCellValue(row.getCell(1)),
                    readDate(row.getCell(2)),
                    formatter.formatCellValue(row.getCell(3))));
            }
            return books;
        }
    }
}
```
- **Cabeçalho por nome** (CSV) em vez de posição: o arquivo continua válido se o usuário reordenar colunas. Documente o modelo esperado (e ofereça um arquivo-modelo para download).
- **`DataFormatter`** lê a célula como o usuário a vê (números sem `.0`, sem notação científica). Datas em XLSX são números com formato: use `DateUtil.isCellDateFormatted(cell)` e `cell.getLocalDateTimeCellValue().toLocalDate()`.
- **Charset explícito** (`UTF_8`) no CSV — o default da plataforma muda entre Windows e Linux. Planilhas salvas pelo Excel como "CSV" podem vir em `windows-1252` ou com `;`: decida e documente o formato aceito.
- `toDto(...)`, `isEmpty(row)` e `readDate(...)` são métodos privados de cada importer (conversão e parsing; erros de conversão viram `BadRequestException` com o número da linha).

### Service — validação linha a linha, uma transação
```java
@Autowired
private FileImporterFactory importerFactory;

@Autowired
private Validator validator;

@Transactional
public List<BookDTO> massCreation(MultipartFile file) {
    if (file == null || file.isEmpty()) throw new BadRequestException("Please set a valid file!");
    try (var input = file.getInputStream()) {
        var books = importerFactory.getImporter(Objects.requireNonNull(file.getOriginalFilename())).importFile(input);
        if (books.size() > MAX_ROWS) throw new BadRequestException("The file exceeds " + MAX_ROWS + " rows!");
        validateRows(books);
        var entities = books.stream().map(dto -> parseObject(dto, Book.class)).toList();
        return parseListObjects(repository.saveAll(entities), BookDTO.class);
    } catch (BadRequestException e) {
        throw e;
    } catch (Exception e) {
        throw new FileStorageException("Error processing the file!", e);
    }
}

private void validateRows(List<BookDTO> books) {
    var errors = new ArrayList<String>();
    for (int i = 0; i < books.size(); i++) {
        for (var violation : validator.validate(books.get(i))) {
            errors.add("Row " + (i + 2) + ": " + violation.getPropertyPath() + " " + violation.getMessage());
        }
    }
    if (!errors.isEmpty()) throw new BadRequestException(String.join("; ", errors));
}
```
- **Tudo ou nada:** uma linha inválida rejeita o arquivo inteiro e devolve **todos** os erros com o número da linha (a linha 1 é o cabeçalho, por isso `i + 2`). O usuário corrige tudo de uma vez. Se o negócio aceita importação parcial, devolva um relatório explícito de linhas aceitas e rejeitadas — nunca descarte linhas em silêncio.
- **Bean Validation programático** (`jakarta.validation.Validator`, injetado pelo Boot com `spring-boot-starter-validation`) aplica as mesmas constraints do DTO que o endpoint JSON usa (`bean-validation`).
- **Limite de linhas** (`MAX_ROWS`) e o limite de tamanho do upload (`file-upload-download`). Arquivos muito grandes não cabem numa request síncrona: aceite o arquivo, processe em background (fila — `messaging`/`aws-s3-sqs`) e devolva `202` com um id de acompanhamento.
- `saveAll` com `IDENTITY` não faz batch de insert no Hibernate (cada insert precisa do id gerado). Para volumes grandes, meça (`jvm-performance`); considere `JdbcTemplate.batchUpdate` ou outra estratégia de id.
- Duplicatas dentro do arquivo e contra o banco: decida a regra (rejeitar, ignorar, atualizar) e trate-a explicitamente.

### Controller
```java
@PostMapping(value = "/massCreation", produces = {
    MediaType.APPLICATION_JSON_VALUE,
    MediaType.APPLICATION_XML_VALUE,
    MediaType.APPLICATION_YAML_VALUE})
@Override
public List<BookDTO> massCreation(@RequestParam("file") MultipartFile file) {
    return service.massCreation(file);
}
```

---

## 4. Exportar

### Implementações
```java
@Component
public class XlsxExporter implements FileExporter {

    @Override
    public Resource exportFile(List<BookDTO> books) throws Exception {
        try (var workbook = new SXSSFWorkbook(100); var output = new ByteArrayOutputStream()) {
            var sheet = workbook.createSheet("Books");
            var header = sheet.createRow(0);
            var columns = List.of("ID", "Title", "Author", "Launch Date", "Price");
            for (int i = 0; i < columns.size(); i++) header.createCell(i).setCellValue(columns.get(i));

            var rowIndex = 1;
            for (var book : books) {
                var row = sheet.createRow(rowIndex++);
                row.createCell(0).setCellValue(book.getId());
                row.createCell(1).setCellValue(book.getTitle());
                row.createCell(2).setCellValue(book.getAuthor());
                row.createCell(3).setCellValue(book.getLaunchDate());
                row.createCell(4).setCellValue(book.getPrice().doubleValue());
            }
            workbook.write(output);
            return new ByteArrayResource(output.toByteArray());
        }
    }
}
```
- **`SXSSFWorkbook(100)`** mantém só 100 linhas na memória e despeja o resto em arquivo temporário — o `XSSFWorkbook` carrega tudo na memória e estoura com dezenas de milhares de linhas. Feche o workbook (o `close()` do SXSSF remove os temporários).
- A célula de data precisa de um `CellStyle` com formato de data (`creationHelper.createDataFormat().getFormat("yyyy-mm-dd")`), senão aparece como número.
- `autoSizeColumn` no SXSSF só enxerga as linhas na janela e é caro: use larguras fixas ou `trackAllColumnsForAutoSizing()` com moderação.

```java
@Component
public class CsvExporter implements FileExporter {

    @Override
    public Resource exportFile(List<BookDTO> books) throws Exception {
        var output = new ByteArrayOutputStream();
        var format = CSVFormat.DEFAULT.builder().setHeader("ID", "Title", "Author", "Launch Date", "Price").get();
        try (var writer = new OutputStreamWriter(output, StandardCharsets.UTF_8);
             var printer = new CSVPrinter(writer, format)) {
            for (var book : books) {
                printer.printRecord(book.getId(), safe(book.getTitle()), safe(book.getAuthor()), book.getLaunchDate(), book.getPrice());
            }
        }
        return new ByteArrayResource(output.toByteArray());
    }

    private String safe(String value) {
        if (value == null || value.isEmpty()) return value;
        return "=+-@\t\r".indexOf(value.charAt(0)) >= 0 ? "'" + value : value;
    }
}
```
- **CSV/formula injection:** um texto do usuário que começa com `=`, `+`, `-`, `@`, tab ou CR é executado como **fórmula** quando a planilha é aberta no Excel/LibreOffice (pode exfiltrar dados ou chamar comandos). O `safe` prefixa `'`. Aplique o mesmo cuidado às células de texto no XLSX quando os dados vêm de usuários.
- O `CSVPrinter` cuida de aspas, vírgulas e quebras de linha dentro dos campos — nunca monte CSV concatenando strings.
- Para o Excel abrir UTF-8 com acentos corretamente, alguns times escrevem o BOM (`﻿`) no início — decida e documente.

### Service e controller
```java
@Transactional(readOnly = true)
public Resource exportPage(Pageable pageable, String acceptHeader) {
    logger.info("Exporting a Book page!");
    var books = repository.findAll(pageable).map(entity -> parseObject(entity, BookDTO.class)).getContent();
    try {
        return exporterFactory.getExporter(acceptHeader).exportFile(books);
    } catch (BadRequestException e) {
        throw e;
    } catch (Exception e) {
        throw new FileStorageException("Error during file export!", e);
    }
}
```
```java
@GetMapping(value = "/exportPage", produces = {
    MediaTypes.APPLICATION_XLSX_VALUE,
    MediaTypes.APPLICATION_CSV_VALUE,
    MediaTypes.APPLICATION_PDF_VALUE})
@Override
public ResponseEntity<Resource> exportPage(
    @RequestParam(value = "page", defaultValue = "0") Integer page,
    @RequestParam(value = "size", defaultValue = "12") Integer size,
    @RequestParam(value = "direction", defaultValue = "asc") String direction,
    HttpServletRequest request) {

    var pageable = toPageable(page, size, direction);
    var acceptHeader = request.getHeader(HttpHeaders.ACCEPT);
    var file = service.exportPage(pageable, acceptHeader);
    var extension = switch (acceptHeader) {
        case MediaTypes.APPLICATION_XLSX_VALUE -> ".xlsx";
        case MediaTypes.APPLICATION_PDF_VALUE -> ".pdf";
        default -> ".csv";
    };
    return ResponseEntity.ok()
        .contentType(MediaType.parseMediaType(acceptHeader))
        .header(HttpHeaders.CONTENT_DISPOSITION,
            ContentDisposition.attachment().filename("books_exported" + extension).build().toString())
        .body(file);
}
```
- O formato vem do **header `Accept`** (coerente com `web-config`, que nunca seleciona formato por parâmetro de URL). Um `Accept` não suportado responde `406` pelo próprio Spring (o `produces` não casa).
- A exportação **também é paginada** (`toPageable` com tamanho máximo — `pagination`). Para "exportar tudo", gere o arquivo em background ou escreva em stream (`StreamingResponseBody` lendo o banco em lotes) — nunca carregue a tabela inteira na memória.
- Documente com `@Content(mediaType = MediaTypes.APPLICATION_XLSX_VALUE)` etc. (`swagger`).

---

## 5. Segurança

- **Zip bomb e XML malicioso:** XLSX é um ZIP com XML. O POI já se protege (`ZipSecureFile` com razão mínima de compressão; parsers XML sem entidades externas) — **não** desligue essas proteções (`ZipSecureFile.setMinInflateRatio(0)`) para "fazer um arquivo passar".
- Valide o arquivo antes de abrir: tamanho (`file-upload-download`) e assinatura (XLSX começa com `PK`, Tika detecta `application/x-tika-ooxml`/o tipo OOXML).
- Exportação expõe dados em massa: confira a **autorização** do endpoint, não exporte campos sensíveis por padrão e registre quem exportou o quê (`privacy-lgpd`).

---

## 6. Testes

- **Unit:** cada importer com um arquivo pequeno em `src/test/resources` (linhas válidas, célula vazia, data inválida, colunas reordenadas no CSV); cada exporter lendo de volta o arquivo gerado (`new XSSFWorkbook(resource.getInputStream())`, `CSVParser`) e conferindo cabeçalho e valores; o `safe` com `=SUM(1)`.
- **Service:** arquivo com uma linha inválida → `BadRequestException` com o número da linha e **nada gravado** (rollback).
- **Integração** (`integration-testing`): upload multipart do CSV/XLSX → `200` com os livros criados; `exportPage` com `accept(MediaTypes.APPLICATION_XLSX_VALUE)` → `200`, `Content-Type` e `Content-Disposition` corretos e o arquivo legível; `Accept` desconhecido → `406`.

---

## Regras principais

- Contratos `FileImporter`/`FileExporter` com factories; implementações são beans; formatos em `MediaTypes`, nunca strings soltas.
- Importação valida **cada linha** com o `Validator` (mesmas constraints do DTO) e grava **tudo ou nada** em uma transação, devolvendo todos os erros com o número da linha.
- Limites de tamanho e de linhas; arquivos grandes vão para processamento em background.
- CSV com charset explícito e `CSVPrinter`/`CSVParser` — nunca concatenação; cabeçalho por nome na leitura.
- Exportação XLSX com `SXSSFWorkbook` (stream), workbook sempre fechado; exportação paginada.
- Formato de exportação escolhido pelo header `Accept`; `Content-Disposition` com `ContentDisposition.attachment()`.
- Proteja contra CSV/formula injection (prefixo `'`) e não desligue as proteções de zip bomb do POI.
- Exportação em massa exige autorização e cuidado com dados pessoais.
- **Sem Lombok** — deliberado.
