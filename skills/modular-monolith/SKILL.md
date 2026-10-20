---
name: modular-monolith
description: Monolito modular com Spring Modulith — módulos por capacidade de negócio, API pública e internals encapsulados, verificação da estrutura em teste, eventos entre módulos com publication registry, @ApplicationModuleTest, dados por módulo e extração para microsserviço. Use quando organizar uma aplicação em módulos por domínio sem pagar o custo distribuído.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md), [`../code-style/SKILL.md`](../code-style/SKILL.md) e [`../microservices/SKILL.md`](../microservices/SKILL.md) (a decisão monolito × microsserviços). Para o modelo de domínio dentro de cada módulo, veja `ddd-hexagonal`. Para modularizar um monolito **existente**, comece pela análise de `monolith-decomposition` (quais componentes formam cada módulo e quem é dono de cada tabela).

# Monolito modular (Spring Modulith)

Um **monolito modular** é **uma aplicação, um deploy, um banco** — mas **organizada em módulos com fronteiras reais** (por capacidade de negócio), que se comunicam por **APIs públicas pequenas e eventos**, e cujos internals são **inacessíveis** aos outros. Você ganha **a maior parte da separação** dos microsserviços (coesão, baixo acoplamento, times com ownership) **sem** o custo distribuído (rede, consistência eventual, N pipelines). E, se um módulo precisar escalar/ser implantado sozinho, a **extração** é um passo pequeno (seção 7).

**Por que não "só pacotes"?** Em Java, qualquer classe `public` alcança qualquer outra: sem verificação, a fronteira é uma convenção que **erode** até virar um "big ball of mud". O **Spring Modulith** transforma a fronteira em **regra verificável** (teste que quebra o build) e dá a ferramenta para os módulos conversarem por eventos.

> **Layout do pack:** `code-organization` (flat-by-layer: `controllers/`, `services/`, `repository/`…) é ótimo para **um serviço pequeno com um domínio**. Quando a aplicação cresce para **vários domínios**, a organização **por camada técnica** mistura tudo (um `services/` com 40 classes de 6 domínios). Aí a organização muda para **por módulo de negócio no topo**, e cada módulo pode ter dentro o seu mini-layout.

## Dependencies

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>org.springframework.modulith</groupId>
            <artifactId>spring-modulith-bom</artifactId>
            <version>${spring-modulith.version}</version>
            <type>pom</type>
            <scope>import</scope>
        </dependency>
    </dependencies>
</dependencyManagement>

<dependency>
    <groupId>org.springframework.modulith</groupId>
    <artifactId>spring-modulith-starter-core</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.modulith</groupId>
    <artifactId>spring-modulith-starter-jpa</artifactId>
</dependency>
<dependency>
    <groupId>org.springframework.modulith</groupId>
    <artifactId>spring-modulith-starter-test</artifactId>
    <scope>test</scope>
</dependency>
```
`spring-modulith.version` em `<properties>` (fora do BOM do Boot — `maven-config`): **use a linha compatível com o Boot do projeto** (o Spring Modulith tem uma linha por geração do Boot) — confirme no Context7/documentação. O `starter-jpa` ativa o **event publication registry** persistido (seção 4); sem JPA, use só o `core`.

---

## 1. Módulos = packages de primeiro nível

Cada **sub-package direto** do package da aplicação é um **módulo**:
```
br.com.edimilsonldutra/
├── Startup.java
├── catalog/                       # módulo catalog
│   ├── Book.java                  #   (API pública do módulo: tipos no package raiz)
│   ├── BookService.java           #   ← interface de entrada do módulo
│   ├── BookCreated.java           #   ← evento publicado
│   └── internal/                  #   internals: NINGUÉM fora do módulo acessa
│       ├── BookRepository.java
│       ├── BookEntity.java
│       └── BookController.java
├── lending/                       # módulo lending
│   ├── LoanService.java
│   ├── LoanStarted.java
│   └── internal/
│       ├── LoanRepository.java
│       └── ...
└── shared/                        # tipos realmente compartilhados (poucos): Money, erros comuns
```
- **Tipos no package raiz do módulo** (`catalog.BookService`) = **API pública**. **Sub-packages** (`catalog.internal`) = **encapsulados**: o Modulith **proíbe** que outro módulo dependa deles.
- Classes **package-private** onde der (`BookRepository` sem `public`): o compilador também ajuda.
- **Módulos por capacidade de negócio**, nunca por camada (`web/`, `service/`) — o mesmo critério de `microservices` e `ddd-hexagonal` (cada módulo é um *bounded context* candidato).
- **Dentro de um módulo**, organize como fizer sentido: o flat-by-layer reduzido do pack, ou hexagonal (`ddd-hexagonal`) se o domínio for rico.

## 2. Verificar a estrutura (o teste que protege a arquitetura)

```java
class ModularityTests {

    private final ApplicationModules modules = ApplicationModules.of(Startup.class);

    @Test
    void verifiesModularStructure() {
        modules.verify();
    }

    @Test
    void writesDocumentation() {
        new Documenter(modules).writeModulesAsPlantUml().writeIndividualModulesAsPlantUml();
    }
}
```
`verify()` **falha o build** se: um módulo acessa **internals** de outro, há **dependência cíclica** entre módulos, ou uma dependência **não declarada** viola `allowedDependencies`. É o equivalente do ArchUnit de `ddd-hexagonal` para **fronteiras de módulo**. Rode no CI (`./mvnw verify`).

Declare as dependências **permitidas** (a arquitetura explícita), em `package-info.java` do módulo:
```java
@ApplicationModule(allowedDependencies = {"catalog", "shared"})
package br.com.edimilsonldutra.lending;
```
`lending` só pode depender de `catalog` e `shared`. Adicionar uma dependência nova vira **uma decisão revisada em PR**, não um acidente. Para expor um sub-package como parte da API, use `@NamedInterface("api")` no `package-info.java` dele e `allowedDependencies = "catalog::api"`.

O `Documenter` gera **diagramas C4/PlantUML** dos módulos e das dependências **a partir do código** — documentação que nunca fica desatualizada. Versione a saída ou publique-a no CI.

---

## 3. Comunicação entre módulos

**Duas formas — escolha pela natureza da interação:**

| Necessidade | Mecanismo |
|---|---|
| **Consulta/comando** que precisa da resposta agora | Chamada ao **service público** do outro módulo (`catalog.BookService`) — uma chamada de método, na **mesma transaction** |
| **Reação a um fato** (algo aconteceu), sem acoplar quem publica a quem reage | **Evento** (`ApplicationEventPublisher` + `@ApplicationModuleListener`) |

**Prefira eventos** para efeitos colaterais entre módulos: o módulo `lending` publica `LoanStarted` e **não conhece** quem reage (`notification`, `statistics`). Isso é exatamente o desacoplamento dos microsserviços — sem rede.

```java
@Service
public class LoanService {

    private final ApplicationEventPublisher events;
    private final LoanRepository loans;

    public LoanService(ApplicationEventPublisher events, LoanRepository loans) {
        this.events = events;
        this.loans = loans;
    }

    @Transactional
    public void start(StartLoanCommand command) {
        var loan = loans.save(Loan.start(command));
        events.publishEvent(new LoanStarted(loan.getId(), command.bookId(), Instant.now()));
    }
}
```
```java
@Component
public class StatisticsLoanListener {

    @ApplicationModuleListener
    void on(LoanStarted event) {
        // atualiza as estatísticas do módulo statistics
    }
}
```
- **`@ApplicationModuleListener`** = `@Async` + `@Transactional(REQUIRES_NEW)` + `@TransactionalEventListener(AFTER_COMMIT)`: o listener roda **depois do commit** do publicador, **em outra thread e outra transaction** — isolado: se ele falha, **não desfaz** o empréstimo. Isso é **consistência eventual entre módulos**, como em microsserviços (`saga-pattern`: o mesmo raciocínio de compensação vale).
- O **evento é um record** no package raiz do módulo publicador (API pública) — contrato entre módulos (`java-modern-features`).
- O listener deve ser **idempotente** (pode ser reentregue — seção 4).

## 4. Event Publication Registry — um outbox embutido

O problema (`transactional-outbox`): publicar o evento e a perda do processo entre o commit e o listener. O **registry** do Modulith resolve isso para eventos **internos**: ao publicar, ele **grava a publicação** (uma linha por listener) **na mesma transaction do negócio** (tabela `event_publication`, criada pelo `starter-jpa`) e a **marca como concluída** quando o listener termina. Se a aplicação cair no meio, as publicações **incompletas** são **reenviadas** na reinicialização:
```yaml
spring:
  modulith:
    events:
      republish-outstanding-events-on-restart: true
```
Crie a tabela por **migration do Flyway** (não deixe o Modulith criar schema — `flyway-migrations`, `ddl-auto: none`); o schema está na documentação do Modulith para o seu banco. Efeito: entrega **at-least-once** dentro do monolito → **listeners idempotentes** (`idempotency`). Para eventos **que saem** do monolito (Kafka/SQS), o Modulith oferece **externalização** (`@Externalized` + módulos `spring-modulith-events-kafka`/`-amqp`/SQS), reusando o registry como outbox — alternativa ao `transactional-outbox` manual quando já usa Modulith (confirme os módulos disponíveis na sua versão).

Acompanhe publicações **incompletas** (alerta se ficarem paradas — um listener que sempre falha) e limpe as **concluídas** periodicamente (`CompletedEventPublications`/propriedades de limpeza).

---

## 5. Dados: cada módulo é dono das suas tabelas

O banco é **um só**, mas a regra dos microsserviços **vale internamente** — é o que torna a extração futura barata:
- **Tabelas de um módulo só são acessadas por esse módulo.** Prefixe-as (`catalog_book`, `lending_loan`) ou use **schemas** separados.
- **Sem JOIN e sem foreign key entre módulos.** `lending_loan.book_id` é um **identificador**, sem FK para `catalog_book` (uma FK cruzando módulos acopla os schemas e impede separar os bancos depois). Valide a existência pela **API do módulo** `catalog`.
- **Sem repository de um módulo injetado em outro** (o `verify()` já impede, pois `internal` é encapsulado).
- Migrations (`flyway-migrations`) **por módulo** (arquivos com o prefixo do módulo no nome), seguindo expand → contract.
- Transação: **uma por módulo/aggregate**; chamar o service de outro módulo **dentro** da mesma transaction é permitido, mas **cada vez que você faz isso, está acoplando as duas partes** — prefira eventos quando não precisa do resultado.

## 6. Testes por módulo

`@ApplicationModuleTest` sobe **apenas o módulo** (e o que ele declara depender), em vez da aplicação inteira — testes **mais rápidos e que provam o isolamento**:
```java
@ApplicationModuleTest
class LendingModuleTests {

    @Autowired
    private LoanService loans;

    @Test
    void startingALoanPublishesLoanStarted(Scenario scenario) {
        scenario.stimulate(() -> loans.start(new StartLoanCommand(1L, 42L)))
                .andWaitForEventOfType(LoanStarted.class)
                .matchingMappedValue(LoanStarted::bookId, 42L)
                .toArriveAndVerify(event -> assertThat(event.loanId()).isNotNull());
    }
}
```
O **`Scenario`** do Modulith aguarda o evento assíncrono (sem `Thread.sleep`). Use **mocks dos beans de outros módulos** (`@MockitoBean`) para isolar. Banco real em container como no resto do pack (`integration-testing`, `testing`). O teste `ModularityTests` (seção 2) cobre a estrutura.

---

## 7. Extraindo um módulo para microsserviço

Se (e **só se**) um módulo precisar de **escala/deploy independentes** (`microservices`, seção 1), a extração é mecânica porque as fronteiras já existem:
1. O módulo já tem **API pública pequena**, **internals encapsulados**, **tabelas só dele** e se comunica por **eventos** — pré-condições atendidas.
2. **Mova** o package para um novo projeto (`scaffold`), com seu **próprio banco** (copie as tabelas do módulo; sincronize por CDC/eventos durante a transição — Strangler Fig).
3. **Troque as chamadas de método** ao service público por **chamadas de API** (`service-communication`, com `resilience`) e os **eventos internos** por **eventos de integração** em um broker (`messaging`, `transactional-outbox`) — a assinatura do evento (record) já era o contrato.
4. Consumidores passam a depender de **contrato** (`contract-testing`), não de código em memória.
Um monolito modular **bem feito** torna esse passo uma **semana de trabalho**, não uma reescrita. Um monolito **sem módulos** torna-o um projeto de meses.

## 8. Armadilhas

- **Módulos por camada** (`controller/`, `service/`) — não são módulos de negócio.
- **`shared/` virando depósito**: tudo "compartilhado" vira acoplamento oculto. Só tipos **realmente** transversais e estáveis (`Money`, erros comuns); o que tem regra de negócio tem dono.
- **Ciclos** entre módulos (A usa B e B usa A): o `verify()` aponta; resolva com **evento** ou movendo a responsabilidade.
- **Chamadas síncronas em cadeia** entre módulos ("por ser mesmo processo é barato") — vira acoplamento que **bloqueia** a extração. Prefira eventos.
- **Entities JPA vazando** entre módulos (um módulo usando a `Book` JPA de outro): exponha **records/DTOs** na API pública, não entities (`code-organization`).
- **Não rodar o `verify()` no CI** — a fronteira volta a ser convenção.
- **Banco compartilhado sem disciplina** (JOINs cruzando módulos "só desta vez").
- **Migrar para microsserviços "porque já está modular"** — modularidade era o objetivo; só extraia com **motivo concreto**.

---

## Regras principais

- **Monolito modular é o ponto de partida** (`microservices`): um deploy, módulos **por capacidade de negócio** como packages de primeiro nível.
- **API pública no package raiz do módulo; internals em sub-package/package-private**; nada de entities JPA expostas — records/DTOs.
- **`ApplicationModules.verify()` no CI** (sem acesso a internals, sem ciclos, `allowedDependencies` explícito); documentação gerada pelo `Documenter`.
- Entre módulos: **chamada ao service público** só quando precisa da resposta; **eventos** (`@ApplicationModuleListener`) para reagir a fatos — **após o commit**, assíncrono, isolado.
- **Event publication registry** (outbox embutido, tabela por Flyway, `republish-outstanding-events-on-restart`) → entrega at-least-once → **listeners idempotentes**; monitore publicações paradas.
- **Cada módulo é dono das suas tabelas**: sem JOIN e sem FK entre módulos, IDs como referência, migrations por módulo.
- Teste cada módulo com `@ApplicationModuleTest` + `Scenario` (sem `sleep`); banco real em container.
- **Extraia para microsserviço só com motivo concreto**; a extração troca chamadas por APIs e eventos internos por eventos de integração.
- Organize por **módulo de negócio** quando houver vários domínios; flat-by-layer (`code-organization`) para um serviço de domínio único.
- Confirme na versão resolvida os módulos/propriedades do Spring Modulith.
- **Sem Lombok** — deliberado.
