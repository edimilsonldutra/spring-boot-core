---
name: aws-ses
description: E-mail transacional com Amazon SES — domínio verificado (DKIM, SPF, DMARC), saída do sandbox, envio pela API com Spring Cloud AWS, templates Thymeleaf, envio assíncrono por fila, bounces e complaints com supressão, IAM por remetente e testes. Use quando enviar e-mail pela AWS ou investigar entregabilidade.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md), [`../aws-sdk-java/SKILL.md`](../aws-sdk-java/SKILL.md) e [`../aws-sns-sqs/SKILL.md`](../aws-sns-sqs/SKILL.md) (filas e SNS para envio assíncrono e eventos de entrega).

# Amazon SES

O **SES** envia e-mail transacional (boas-vindas, recuperação de senha, comprovantes) em escala e com baixo custo. O trabalho real **não** é o código de envio — é **entregabilidade**: domínio autenticado, reputação e tratamento de rejeições. Sem isso, seus e-mails caem em spam (ou a conta é suspensa).

## 1. Antes do código: identidade e reputação

1. **Verifique uma identidade**: de preferência o **domínio** (`example.com`), não um e-mail avulso. O SES fornece registros DNS (**DKIM**: 3 CNAMEs) que você publica no Route 53/DNS.
2. **Autenticação do domínio:** **DKIM** (assinatura, via SES), **SPF** (use um *custom MAIL FROM* `mail.example.com` para alinhar o SPF) e **DMARC** (`_dmarc.example.com`, comece com `p=none` e evolua para `quarantine/reject`). Sem alinhamento, grandes provedores (Gmail/Yahoo) **rejeitam ou mandam para spam**.
3. **Sandbox:** toda conta nova começa no **sandbox**: só envia para **destinatários verificados** e com cota baixa. **Solicite acesso à produção** (*production access*) descrevendo o caso de uso, a origem das listas e o tratamento de bounces/complaints.
4. **Cotas:** limite diário e **taxa por segundo** — o código respeita (fila/rate limit), senão `Throttling`.
5. **Região:** o SES é **por região**; envie da mesma região da identidade e da aplicação.

## 2. Dependencies e configuração

**Spring Cloud AWS** (fornece um `JavaMailSender`/`MailSender` que envia pela **API do SES**, com credenciais pela default chain — nenhuma senha SMTP):
```xml
<dependency>
    <groupId>io.awspring.cloud</groupId>
    <artifactId>spring-cloud-aws-starter-ses</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-thymeleaf</artifactId>
</dependency>
```
```yaml
spring:
  cloud:
    aws:
      region:
        static: us-east-1

app:
  mail:
    from: "Library <no-reply@example.com>"
    configuration-set: library-default
```
(BOM do Spring Cloud AWS na **linha compatível com o Boot** — `aws-sdk-java`.) O remetente (`from`) deve pertencer a uma **identidade verificada**.

**Alternativa — SMTP do SES** com `spring-boot-starter-mail`: `spring.mail.host: email-smtp.us-east-1.amazonaws.com`, `port: 587` + STARTTLS (`spring.mail.properties.mail.smtp.starttls.enable: true`), com **credenciais SMTP próprias do SES** (geradas no SES, **não** são as access keys) guardadas no Secrets Manager (`aws-rds-secrets-manager`). Funciona e é portável, mas é um **segredo de longa duração** a mais; **prefira a API com IAM** (credenciais temporárias).

## 3. Enviando

```java
@Service
public class EmailService {

    private static final Logger logger = LoggerFactory.getLogger(EmailService.class);

    @Autowired
    private JavaMailSender mailSender;

    @Autowired
    private TemplateEngine templateEngine;

    @Value("${app.mail.from}")
    private String from;

    public void sendWelcome(String to, String name) {
        var context = new Context();
        context.setVariable("name", name);
        var html = templateEngine.process("welcome", context);
        try {
            var message = mailSender.createMimeMessage();
            var helper = new MimeMessageHelper(message, true, "UTF-8");
            helper.setFrom(from);
            helper.setTo(to);
            helper.setSubject("Welcome to Library");
            helper.setText(html, true);
            mailSender.send(message);
            logger.info("Welcome email sent to {}", mask(to));
        } catch (MessagingException e) {
            throw new MailPreparationException("Error preparing the email!", e);
        }
    }
}
```
- Template em `src/main/resources/templates/welcome.html` (Thymeleaf escapa variáveis — **evita injeção de HTML**; **nunca** concatene input do usuário no HTML do e-mail).
- **Sempre** envie **versão HTML + texto alternativo** (`helper.setText(plain, html)`) — melhora entregabilidade; `UTF-8`; assunto sem CAPS/palavras de spam; link de descadastro em e-mail de marketing (para transacional, não exigido, mas bom).
- **Logue com o destinatário mascarado** (`j***@example.com`) — e-mail é dado pessoal (LGPD, `observability`). Nunca logue o corpo (pode ter token de reset).
- **E-mail de recuperação de senha**: token **de uso único e curto**, link sobre HTTPS, sem revelar se o e-mail existe (`authentication`).
- **Anexos** (raw MIME): limite de tamanho do SES (40 MB por mensagem, incl. codificação); prefira **link para o S3 com presigned URL** (`aws-s3-sqs`) a anexos grandes.

### Envio assíncrono (não bloqueie a request)

Enviar e-mail **dentro** da request prende a thread na rede do SES e acopla a latência da API à do e-mail; se o SES falha, a request falha. Padrão: a API **publica um evento/mensagem** e um **consumer envia**:
```
HTTP /signup ──► grava o usuário + (outbox) ──► SQS "email-requests" ──► EmailListener ──► SES
                                                                              └─ falha → retry → DLQ
```
- Publique via **outbox** quando o e-mail depende de uma mudança no banco (`transactional-outbox`) e use o **`messageId`/eventId para idempotência** (SQS entrega *at-least-once*: sem isso o usuário recebe **dois** e-mails — `messaging`).
- Consumer com **retry limitado e DLQ** (`aws-sns-sqs`); **rate limit** respeitando a taxa do SES (limite a concorrência do listener).
- Erros **permanentes** (endereço inválido) → não retente.

## 4. Bounces, complaints e reputação (obrigatório em produção)

O SES **monitora a sua reputação**: taxa alta de **bounce** (endereço inexistente) ou **complaint** (marcou como spam) leva a **revisão e suspensão** do envio. Você **precisa**:
1. Criar um **configuration set** (`library-default`) com **destino de eventos** → um **tópico SNS** (`aws-sns-sqs`) para `Bounce`, `Complaint` (e opcionalmente `Delivery`, `Reject`).
2. Assinar uma **fila SQS** nesse tópico e **processar os eventos**: ao receber *hard bounce* ou *complaint*, **suprima** o endereço (marque como inválido/descadastrado na sua base) e **nunca mais envie** a ele.
3. Usar a **suppression list** do SES (conta/configuration set) como rede de segurança e **monitorar** `Reputation.BounceRate` e `Reputation.ComplaintRate` no CloudWatch (alarmes: bounce < 5%, complaint < 0,1% é a faixa de segurança comum — confirme os limites atuais da AWS).
4. Passar o configuration set no envio (header `X-SES-CONFIGURATION-SET`/`configurationSetName` na API).
- **Não envie** para listas compradas/sem consentimento; **valide** o e-mail no cadastro (e considere *double opt-in*).

## 5. IAM de menor privilégio

```json
{
  "Effect": "Allow",
  "Action": ["ses:SendEmail", "ses:SendRawEmail"],
  "Resource": "arn:aws:ses:us-east-1:123456789012:identity/example.com",
  "Condition": { "StringEquals": { "ses:FromAddress": "no-reply@example.com" } }
}
```
A condição **`ses:FromAddress`** impede a aplicação (ou um atacante com a role) de enviar **como outro remetente**. Via IRSA/task role — **nunca access keys**. O processamento de bounces precisa só de `sqs:*` na fila de eventos.

## 6. Testes

- **Unit** do `EmailService` com o `JavaMailSender` mockado: o `MimeMessage` tem `from`, `to`, assunto e o HTML esperado (`testing`).
- **GreenMail** (SMTP falso, já usado no pack — `maven-config`) para provar o envio e o conteúdo de ponta a ponta quando se usa a rota SMTP; ou **LocalStack** (`.withServices("ses")`) para a API do SES (cobertura limitada; confirme). Credenciais **falsas** só no teste.
- Teste o **consumer de bounces** (mensagem de `Bounce` → endereço suprimido) e a **idempotência** (mesmo `messageId` duas vezes → um e-mail).
- O **sandbox** real e a entregabilidade só se validam na conta AWS (envie para os verificadores de spam/inbox tests de dev).

---

## Regras principais

- Verifique o **domínio** com **DKIM + SPF (custom MAIL FROM) + DMARC**; saia do **sandbox** com solicitação de produção bem descrita.
- **API do SES via IAM** (Spring Cloud AWS) de preferência; SMTP só com credenciais SMTP próprias no Secrets Manager.
- Templates Thymeleaf (escape automático), **HTML + texto**, UTF-8; **nunca** concatene input no HTML; logue destinatário **mascarado** e **nunca** o corpo.
- **Envio assíncrono** por fila (com outbox quando preciso), **idempotente** por `messageId`, com retry limitado, **DLQ** e rate limit pela cota do SES.
- **Bounces/complaints**: configuration set → SNS → SQS → **suprimir endereços**; alarmes de reputação; sem listas sem consentimento.
- IAM mínimo com **`ses:FromAddress`** e ARN da identidade; nunca access keys.
- Anexos grandes por **presigned URL do S3**; recuperação de senha com token curto e uso único.
- Testes: mock/GreenMail/LocalStack + consumer de bounce + idempotência.
- **Sem Lombok** — deliberado.
