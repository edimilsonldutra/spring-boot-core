---
name: email
description: Envio de e-mail no Spring Boot 4 com Spring Mail (SMTP) — configuração com timeouts e credenciais por variável de ambiente, package mail com EmailSender, HTML com Thymeleaf, anexos, envio assíncrono depois do commit, validação de destinatário e header injection, Mailpit no desenvolvimento, GreenMail nos testes e quando ir para SES/provedor. Use quando a aplicação precisar mandar e-mail (boas-vindas, recuperação de senha, notificações) ou quando um envio travar a request.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) (package `mail/`), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../bean-validation/SKILL.md`](../bean-validation/SKILL.md) e [`../maven-config/SKILL.md`](../maven-config/SKILL.md) (GreenMail). Na AWS: [`../aws-ses/SKILL.md`](../aws-ses/SKILL.md). Entrega garantida: [`../transactional-outbox/SKILL.md`](../transactional-outbox/SKILL.md).

# E-mail

Enviar e-mail parece uma chamada de método, mas é uma **chamada de rede lenta e falível** para um servidor SMTP. Os erros clássicos: enviar **dentro** da transação (o e-mail sai e o banco faz rollback), enviar **na thread da request** (o usuário espera o SMTP), **sem timeout** (uma thread presa para sempre) e expor um endpoint que vira **relay de spam**.

## 1. Quem envia: SMTP ou provedor

| Opção | Quando |
|---|---|
| **SMTP de um provedor transacional** (SES, SendGrid, Mailgun, Postmark…) | Produção. Entregabilidade (SPF/DKIM/DMARC), métricas, bounces |
| **API do provedor** (SDK/HTTP) | Quando precisa de templates do provedor, webhooks de entrega, envios em massa — na AWS, veja `aws-ses` |
| **SMTP de conta pessoal** (Gmail com senha de app) | **Só** desenvolvimento/curso. Limites baixos, cai em spam, credencial pessoal no projeto |
| **Mailpit** (SMTP falso com interface web) | Desenvolvimento local: nenhum e-mail sai de verdade |

O código abaixo usa `JavaMailSender` (SMTP), que funciona com qualquer um deles — trocar de provedor muda **configuração**, não código.

---

## 2. Dependency e configuração

```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-mail</artifactId>
</dependency>
```
Para HTML com template, também `spring-boot-starter-thymeleaf`. Ambos gerenciados pelo BOM.

```yaml
spring:
  mail:
    host: ${EMAIL_HOST:localhost}
    port: ${EMAIL_PORT:1025}
    username: ${EMAIL_USERNAME:}
    password: ${EMAIL_PASSWORD:}
    properties:
      mail.smtp.auth: ${EMAIL_SMTP_AUTH:false}
      mail.smtp.starttls.enable: ${EMAIL_STARTTLS:false}
      mail.smtp.starttls.required: ${EMAIL_STARTTLS:false}
      mail.smtp.connectiontimeout: 5000
      mail.smtp.timeout: 5000
      mail.smtp.writetimeout: 5000

mail:
  from: ${EMAIL_FROM:no-reply@example.com}
```
- **Credenciais só por variável de ambiente** (ou Secrets Manager/Parameter Store em produção — `aws-rds-secrets-manager`, `aws-parameter-store`). Nunca no `application.yml` commitado.
- **Os três timeouts são obrigatórios.** O default do Jakarta Mail é **infinito**: um SMTP que não responde prende a thread para sempre.
- Os defaults acima apontam para o **Mailpit** local. Em produção: porta 587 com `starttls.enable`/`required: true` e `auth: true`.
- O `from` é um endereço **do seu domínio**, verificado no provedor. Nunca use o e-mail digitado pelo usuário como remetente (spoofing; o provedor rejeita) — use-o no `Reply-To` se fizer sentido.
- No `application.yml` de teste (cópia completa — `code-organization`), host e porta apontam para o GreenMail (seção 7).

Mailpit no `docker-compose.yml` de desenvolvimento (`docker-and-docker-compose`):
```yaml
  mailpit:
    image: axllent/mailpit:v1.21
    ports:
      - "1025:1025"
      - "8025:8025"
```
A interface em `http://localhost:8025` mostra cada e-mail enviado. Fixe a tag da versão atual (nunca `latest`).

---

## 3. Package `mail/` — o EmailSender

```java
@Component
public class EmailSender {

    private static final Logger logger = LoggerFactory.getLogger(EmailSender.class);

    @Autowired
    private JavaMailSender mailSender;

    @Value("${mail.from}")
    private String from;

    public void send(String to, String subject, String htmlBody, List<File> attachments) {
        try {
            var message = mailSender.createMimeMessage();
            var helper = new MimeMessageHelper(message, true, StandardCharsets.UTF_8.name());
            helper.setFrom(from);
            helper.setTo(validAddress(to));
            helper.setSubject(subject);
            helper.setText(htmlBody, true);
            for (var file : attachments) {
                helper.addAttachment(file.getName(), file);
            }
            mailSender.send(message);
            logger.info("E-mail sent");
        } catch (MessagingException | MailException e) {
            throw new EmailException("Error sending e-mail!", e);
        }
    }

    private InternetAddress validAddress(String address) throws AddressException {
        var internetAddress = new InternetAddress(address, true);
        internetAddress.validate();
        return internetAddress;
    }
}
```
- **`MimeMessageHelper(message, true, "UTF-8")`**: `true` habilita multipart (necessário para anexos e imagens inline); o charset evita acentos quebrados.
- **Valide o endereço** (`InternetAddress(address, true)` em modo estrito) e o DTO com `@Email`/`@NotBlank` (`bean-validation`). O helper escapa os headers, mas **nunca** monte headers (`Subject`, `To`) concatenando texto do usuário com quebras de linha — é o caminho de *header injection*.
- **Não logue o destinatário nem o corpo** em nível INFO: e-mail é dado pessoal e o corpo pode ter token de redefinição de senha (`privacy-lgpd`). Logue um id de correlação.
- `EmailException` segue o padrão de `exception-handling` (`RuntimeException`, `serialVersionUID`, constructor com `cause`). Mensagens no idioma salvo.
- Anexos: limite tamanho e quantidade; para arquivos vindos de upload, aplique as validações de `file-upload-download`. Arquivos grandes: mande um **link** (presigned URL), não o anexo.

### Corpo em HTML com Thymeleaf
```java
@Component
public class EmailTemplates {

    @Autowired
    private SpringTemplateEngine templateEngine;

    public String render(String template, Map<String, Object> variables) {
        var context = new Context(Locale.forLanguageTag("pt-BR"));
        context.setVariables(variables);
        return templateEngine.process(template, context);
    }
}
```
O `Locale` segue o idioma salvo do texto voltado ao usuário (`code-organization`).
Template em `src/main/resources/templates/mail/welcome.html`, com `th:text="${name}"` — o `th:text` **escapa** o conteúdo (um nome com `<script>` vira texto). Nunca use `th:utext` com dado do usuário. Mande também uma versão texto (`helper.setText(textBody, htmlBody)`) — melhora a entregabilidade.

---

## 4. Quando enviar: depois do commit, fora da request

O e-mail é **consequência** de algo que aconteceu no negócio (usuário criado, senha pedida). O padrão:

```java
public record UserRegisteredEvent(Long userId, String email, String name) {}
```
```java
@Transactional
public UserDTO register(UserDTO user) {
    var saved = repository.save(parseObject(user, User.class));
    publisher.publishEvent(new UserRegisteredEvent(saved.getId(), saved.getEmail(), saved.getName()));
    return parseObject(saved, UserDTO.class);
}
```
```java
@Component
public class WelcomeEmailListener {

    @Autowired
    private EmailSender emailSender;

    @Autowired
    private EmailTemplates templates;

    @Async
    @TransactionalEventListener(phase = TransactionPhase.AFTER_COMMIT)
    public void on(UserRegisteredEvent event) {
        var body = templates.render("mail/welcome", Map.of("name", event.name()));
        emailSender.send(event.email(), "Welcome!", body, List.of());
    }
}
```
- **`AFTER_COMMIT`**: o e-mail só sai se o usuário foi de fato gravado. Enviar dentro da transação manda "bem-vindo" para um cadastro que fez rollback.
- **`@Async`** (com `@EnableAsync` e um executor com fila e tamanho definidos — `spring.task.execution.pool.*`): a request não espera o SMTP. Exceptions em métodos `@Async void` não chegam ao caller — logue-as (um `AsyncUncaughtExceptionHandler`) e monitore.
- **O limite deste padrão:** se a aplicação cair entre o commit e o envio, o e-mail **se perde**. Quando perder não é aceitável (comprovante, cobrança), use **outbox** (`transactional-outbox`) ou uma fila (`aws-ses` descreve SES + SQS), com retry e **idempotência** (`idempotency`) para não mandar duas vezes.

---

## 5. Endpoint de envio (cuidado)

O curso costuma expor `POST /api/email/v1` (JSON com `to`, `subject`, `body`) e `POST /api/email/v1/withAttachment` (multipart) para praticar. Em uma aplicação real, **um endpoint que manda e-mail para qualquer destinatário com qualquer conteúdo é um relay de spam**:
- exija autenticação e uma permissão específica (`authentication`);
- limite destinatários (só usuários do sistema, ou domínio permitido) e use **templates** do servidor — o client não envia HTML livre;
- aplique rate limit por usuário (`api-gateway`/`resilience`);
- devolva `202 Accepted` quando o envio é assíncrono.

---

## 6. Entregabilidade (produção)

Domínio com **SPF, DKIM e DMARC** configurados no DNS, remetente verificado no provedor, tratamento de **bounces e reclamações** (suprimir endereços que rejeitam), link de descadastro em e-mails não transacionais. Os detalhes estão em `aws-ses` e valem para qualquer provedor.

---

## 7. Testes

- **GreenMail** (`com.icegreen:greenmail`, escopo `test`, com a exclusão de `org.eclipse.angus:jakarta.mail` — `maven-config`) sobe um SMTP em memória:
```java
@RegisterExtension
static GreenMailExtension greenMail = new GreenMailExtension(ServerSetupTest.SMTP)
    .withConfiguration(GreenMailConfiguration.aUser().withLogin("user", "secret"))
    .withPerMethodLifecycle(false);

@DynamicPropertySource
static void mail(DynamicPropertyRegistry registry) {
    registry.add("spring.mail.host", () -> "localhost");
    registry.add("spring.mail.port", () -> ServerSetupTest.SMTP.getPort());
    registry.add("spring.mail.username", () -> "user");
    registry.add("spring.mail.password", () -> "secret");
}

@Test
void sendsTheWelcomeEmail() {
    emailSender.send("ana@example.com", "Welcome!", "<p>Hi</p>", List.of());

    var received = greenMail.getReceivedMessages();
    assertThat(received).hasSize(1);
    assertThat(GreenMailUtil.getBody(received[0])).contains("Hi");
}
```
- Fluxo assíncrono (listener `@Async`): espere com **Awaitility** (`await().atMost(...).untilAsserted(...)`), nunca `Thread.sleep` (`integration-testing`).
- Teste que **rollback não envia**: uma transação que falha depois do `publishEvent` resulta em zero mensagens.
- Unit test do `EmailSender` com `JavaMailSender` mockado só para casos de erro (endereço inválido → `EmailException`).

---

## Regras principais

- `spring-boot-starter-mail`; host, usuário e senha por variável de ambiente; **connection/read/write timeouts** sempre configurados.
- Remetente fixo do seu domínio; e-mail do usuário nunca como `From`.
- `MimeMessageHelper` com UTF-8; endereços validados; nenhum header montado por concatenação com texto do usuário.
- HTML por template (Thymeleaf `th:text`, nunca `th:utext` com dado do usuário) e versão texto.
- Envio **depois do commit** (`@TransactionalEventListener(AFTER_COMMIT)`) e **fora da thread da request** (`@Async` com executor dimensionado); outbox/fila quando o e-mail não pode se perder.
- Endpoint que envia e-mail exige autenticação, destinatários restritos, templates do servidor e rate limit.
- Não logue destinatário, corpo nem tokens.
- Mailpit no desenvolvimento; GreenMail nos testes; Awaitility para o fluxo assíncrono.
- **Sem Lombok** — deliberado.
