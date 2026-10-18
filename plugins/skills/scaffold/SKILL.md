---
name: scaffold
description: Cria um projeto Spring Boot 4 novo — gera a base pelo Spring Initializr, padroniza (Startup, application.yml, build com 4 espaços, agent do Mockito) e oferece, um a um, persistence, Flyway, exception handling, web config, Swagger e Bean Validation em torno de um exemplo Book, verificando o build. Use quando ainda não existe projeto.
argument-hint: "[nome-do-projeto]"
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) e [`../code-style/SKILL.md`](../code-style/SKILL.md) para as preferências do projeto, o package layout e o code style, e [`../maven-config/SKILL.md`](../maven-config/SKILL.md) para saber para que serve cada dependency. O Step 6 abaixo também aplica [`../spring-data-jpa/SKILL.md`](../spring-data-jpa/SKILL.md), [`../flyway-migrations/SKILL.md`](../flyway-migrations/SKILL.md), [`../exception-handling/SKILL.md`](../exception-handling/SKILL.md), [`../web-config/SKILL.md`](../web-config/SKILL.md), [`../swagger/SKILL.md`](../swagger/SKILL.md) e [`../bean-validation/SKILL.md`](../bean-validation/SKILL.md) diretamente, mas somente para os decorators que o desenvolvedor de fato escolheu — as seis vêm no mesmo tier Core desta skill, então todo link acima sempre resolve.

# Project scaffold

Cria primeiro um projeto **mínimo mas funcional** — build file, entrypoint, configuration e um smoke test — e depois acrescenta somente as capacidades que o desenvolvedor de fato pede, uma de cada vez. Nada além da base é adicionado de forma especulativa: um projeto que recusa todo decorator é apenas `Startup` mais uma web layer vazia, exatamente como seria um projeto simples do Spring Initializr, só que já no padrão do projeto (package layout, sem Lombok, build files com 4 espaços, um smoke test real). Use-a quando não há projeto ainda. Para um projeto existente, vá direto para as skills de tópico.

**O Spring Initializr gera a base** (ele conhece a versão atual do Spring Boot, as versões de plugin correspondentes e, para Gradle, entrega o wrapper, que não pode ser escrito à mão). O **passo de padronização** no Step 5 então transforma essa base em um projeto no padrão do pacote, e o **Step 6 aplica os decorators que foram escolhidos** chamando diretamente a sua própria skill Core. Precisa de acesso à internet; o fallback está no final.

**A application class é sempre `Startup`** (`Startup.java`) e seu teste é sempre `StartupTests` — nunca a classe `<Artifact>Application` que o Initializr gera.

---

## Step 1 — Pergunte: a base

Execute o Step 0 de `code-organization` **na mesma rodada**, para as duas preferências que nunca dependem de quais decorators são escolhidos (comentários, estilo de injection): use as respostas já salvas no `CLAUDE.md` do projeto ou nesta conversa, e pergunte somente o que falta, em uma mensagem (ou chamadas de `AskUserQuestion` de até quatro perguntas). Toda pergunta tem um default e "just use the defaults" é uma resposta válida — exceto o nome do artifact, que não tem default. **Database, entity/DTO mapper e posição das annotations do Swagger são perguntados no Step 2 abaixo, somente se o decorator correspondente for escolhido** — não aqui.

| Pergunta | Default | Notas |
|---|---|---|
| Group id e base package | `br.com.padrao` | O base package é igual ao group id, a menos que o desenvolvedor diga o contrário. |
| Artifact (nome do projeto) | nenhum — pergunte | kebab-case, por exemplo `library-api`. Nomeia a pasta, o jar e o database default (`library_api`), se persistence for escolhida. |
| Java version | a última LTS | Veja o Step 3. |
| Build tool | **Maven** | Se Gradle: DSL **Groovy** (`build.gradle`) ou **Kotlin DSL** (`build.gradle.kts`) — default Groovy. |
| Configuration file | **YAML** (`application.yml`) | Ou `application.properties`. |
| Idioma do texto voltado ao usuário | **English** (igual aos identifiers) | Veja "Naming convention" abaixo — perguntado uma vez, vale para todo decorator que produz texto que um client pode ler. |

Onde o projeto vai: na pasta atual se ela estiver vazia (uma pasta `.git` ou um `CLAUDE.md` não contam), caso contrário em uma nova pasta `<artifact>/` — diga qual você escolheu.

### Naming convention: identifiers em inglês, texto voltado ao usuário no idioma do desenvolvedor

Regra fixa, espelhando `padrao-frontend:scaffold`: **todo identifier de código permanece em inglês** — packages, classes, campos, métodos, properties de DTO, nomes de arquivos de migration — independentemente desta resposta. **Somente o texto que um client de fato lê** segue o idioma escolhido aqui: um `message` do Bean Validation (veja `bean-validation`), a mensagem de uma domain exception (veja `exception-handling`), um `summary`/`description`/descrição de `@ApiResponse` do Swagger e o texto de `Info` do `OpenApiConfig` (veja `swagger`). Inglês é o default, o que também significa "nenhum trabalho extra" — as mensagens built-in do Hibernate Validator já estão em inglês, então nada extra é escrito; qualquer outro idioma significa escrever uma mensagem/descrição explícita e traduzida em todo lugar em que essas três skills deixariam uma implícita.

---

## Step 2 — Pergunte: o que adicionar

Tudo abaixo é opcional. Pergunte as seis em uma rodada (`AskUserQuestion`, até quatro por chamada), nesta ordem — fundacional primeiro, polimento por último — e explique logo de início: **todo decorator tem default "yes"**, então "just use the defaults" reproduz um projeto completo pronto para CRUD exatamente como esta skill gerava antes; recuse qualquer um para obter um scaffold menor e mais focado. Recusar as seis deixa a base mínima descrita acima.

| # | Decorator | Default | Adiciona | Pergunta(s) aninhada(s), feitas somente se este for "yes" |
|---|---|---|---|---|
| 1 | **Persistence** — Spring Data JPA | Yes | Uma entity, repository, DTO, mapper e service — a data layer do exemplo compartilhado abaixo. | Database (**MySQL** / PostgreSQL / SQL Server / Oracle / MariaDB); Entity ↔ DTO mapper (**Dozer** / MapStruct). |
| 2 | **Flyway migrations** | Yes — perguntado somente se #1 for "yes" | Propriedade do schema via SQL versionado, para que `ddl-auto: none` tenha algo em que se apoiar. | — |
| 3 | **Exception handling** | Yes | `CustomEntityResponseHandler` + as domain exceptions genéricas. Sem dependency, sem exigir persistence. | — |
| 4 | **Web config** | Yes | `WebConfig` (CORS). | Somente JSON (**default**) ou também XML e/ou YAML — veja `web-config`. |
| 5 | **Swagger / OpenAPI** | Yes | Dependency springdoc + `OpenApiConfig`. | Annotations em uma interface `*ControllerDocs` separada (**default**) ou direto no controller — veja a nota de trade-off do `swagger` antes de perguntar. |
| 6 | **Bean Validation** | Yes | `spring-boot-starter-validation` + o handler de falha de validation. | — |

**Flyway recusado depois de Persistence aceita** — avise antes de continuar (diga no idioma do desenvolvedor, mantendo o significado):

> Sem o Flyway, nada é dono do schema — `ddl-auto: none` não é negociável neste estilo (veja `code-organization`), então o Hibernate também não vai criar a tabela `books`. Você precisaria criá-la à mão antes que a aplicação consiga persistir qualquer coisa, e o smoke test abaixo não consegue provar um round trip de save/find. Manter o Flyway, ou continuar sem ele mesmo assim?

Se o desenvolvedor continuar mesmo assim, gere entity/repository/DTO/service/controller normalmente, mas diga claramente no Step 7 que a persistence **não** foi verificada de ponta a ponta.

### O exemplo compartilhado `Book` — como um decorator "se conecta"

Persistence é o que cria algo para decorar: escolhê-la constrói uma fatia vertical real — `Book` (`author`, `title`, `launchDate`, `price`), o mesmo domínio já usado como exemplo corrente em toda skill Core — com uma entity, repository, DTO, service e (já que `web` está sempre na base) um `BookController`. Todo outro decorator escolhido junto **estende essa mesma fatia**: o Flyway adiciona sua migration, o Exception Handling conecta `ResourceNotFoundException` ao service, o Web Config adiciona CORS e os media types escolhidos ao controller, o Swagger documenta o controller, o Bean Validation restringe o DTO. Veja o Step 6 para exatamente o que cada um faz.

Se **Persistence for recusada**, não há nada para decorar ainda — os outros decorators escolhidos ainda conectam infraestrutura genérica, real e funcional (uma config class, uma dependency, classes de exception) **sem inventar objeto de negócio**. Um scaffold "só Swagger e exception handling, sem database" é uma escolha legítima e honesta: ele sobe com uma superfície de API vazia, pronta para o primeiro controller real do desenvolvedor.

---

## Step 3 — Java version

O Spring Boot 4.1 precisa do **Java 17 ou mais novo**. Não chute o que é atual — leia:

```bash
curl -s https://api.adoptium.net/v3/info/available_releases
curl -s -H "Accept: application/vnd.initializr.v2.3+json" https://start.spring.io/
```
```powershell
Invoke-RestMethod https://api.adoptium.net/v3/info/available_releases
Invoke-RestMethod https://start.spring.io -Headers @{ Accept = "application/vnd.initializr.v2.3+json" }
```

- O Adoptium fornece `available_lts_releases`, `most_recent_lts` e `most_recent_feature_release`.
- O Initializr fornece `javaVersion.values` (as versões que este Spring Boot suporta — a menor é o mínimo) e `bootVersion.default` (o último Spring Boot estável).
- Sem internet, as releases LTS são 17, 21, 25, 29… (uma a cada quatro releases a partir da 17). No momento da escrita, as linhas LTS que o Boot 4.1 suporta são 17, 21 e 25.

**Ofereça as versões LTS que o Spring Boot suporta, e sempre sugira a mais recente** (o default, marcada como recomendada); as outras linhas LTS vêm em seguida, e o desenvolvedor pode digitar qualquer outro número. Depois valide a resposta:

| Resposta | O que fazer |
|---|---|
| Não é um número, ou está abaixo do mínimo (17) | Recuse e explique que o Spring Boot 4 precisa de 17 ou mais novo. **Nunca repasse:** o Initializr eleva silenciosamente 16 para 17 e escreve qualquer outra coisa (`abc`) no build file. |
| Uma release LTS | Aceite. |
| Uma release que **não** é LTS, até a feature release mais recente | Aceite **depois do aviso abaixo**. |
| Mais nova que a feature release mais recente | Recuse — ela não foi lançada, então não há JDK para fazer o build. |

**Aviso para uma Java version não-LTS** (diga no idioma do desenvolvedor, mantendo o significado):

> O Java N **não** é uma release LTS. Ele recebe correções de segurança por apenas cerca de seis meses, até a próxima release do Java, e depois o projeto precisa migrar de novo. Isso faz dele uma má escolha para produção — serve para aprender ou para experimentar uma nova feature da linguagem. A última LTS é a L. Manter o N, ou usar a L?

Se o desenvolvedor mantiver, continue e registre como `N (non-LTS)` nas preferências salvas.

**Esse JDK está instalado?** Execute `java -version` e verifique `JAVA_HOME`.
- O **Maven** compila com o JDK que o `mvn -v` reporta. Um JDK mais antigo que `java.version` falha com `release version N not supported` — aponte `JAVA_HOME` (e `PATH`) para o JDK certo, ou instale-o.
- O **Gradle** procura o JDK solicitado na máquina (um toolchain) e **não** baixa um. Se estiver faltando, o build para com `Cannot find a Java installation … matching: {languageVersion=N …}`. Instale esse JDK (qualquer vendor — Temurin, Corretto, Zulu, Liberica, Microsoft, Oracle), ou use o SDKMAN. O próprio Gradle roda no que `JAVA_HOME` apontar.

Nunca instale um JDK sem perguntar.

---

## Step 4 — Gere a base com o Spring Initializr

Uma request retorna um zip com o build file, wrapper, sources e configuration. `web` é sempre incluído; todo outro dependency id depende de quais decorators foram escolhidos no Step 2:

| Escolhido no Step 2 | Initializr id(s) adicionados |
|---|---|
| *(sempre)* | `web` |
| Persistence | `data-jpa`, `<database>`, `testcontainers` |
| Flyway migrations | `flyway` |
| Bean Validation | `validation` |
| Exception handling | nenhum — classes simples, escritas à mão no Step 6 |
| Web config | nenhum — classe simples, escrita à mão no Step 6 |
| Swagger / OpenAPI | nenhum — o springdoc não tem Initializr id; adicionado à mão no Step 6 (dependency + property de versão, veja `maven-config`) |

Preencha os valores dos Steps 1/2 (as partes `<>`) e execute **dentro da pasta de destino**:

```bash
curl -sSf "https://start.spring.io/starter.zip?type=<type>&language=java&javaVersion=<N>&groupId=<group>&artifactId=<artifact>&name=<artifact>&packageName=<package>&packaging=jar&configurationFileFormat=<yaml|properties>&dependencies=<comma-separated ids from the table>" -o starter.zip
unzip -q starter.zip && rm starter.zip
```
```powershell
Invoke-WebRequest "https://start.spring.io/starter.zip?type=<type>&language=java&javaVersion=<N>&groupId=<group>&artifactId=<artifact>&name=<artifact>&packageName=<package>&packaging=jar&configurationFileFormat=<yaml|properties>&dependencies=<comma-separated ids from the table>" -OutFile starter.zip
Expand-Archive starter.zip -DestinationPath . ; Remove-Item starter.zip
```

- `type` — `maven-project`, `gradle-project` (Groovy DSL) ou `gradle-project-kotlin` (Kotlin DSL).
- `bootVersion` é deixado de fora de propósito: o Initializr então usa a última release estável. Verifique que a versão do parent no build file gerado é uma release — sem `SNAPSHOT`, `M1`, `RC1`.
- `<database>` é o Initializr id da tabela abaixo — presente somente quando Persistence foi escolhida. Ele traz o JDBC driver, o módulo do Flyway (se o Flyway também foi escolhido) e o módulo do Testcontainers daquele database.
- Confirme que o build file gerado diz a Java version que o desenvolvedor escolheu.
- Sem `lombok`, nunca. `devtools`, `actuator`, `security` e o resto não são adicionados aqui — cada um tem sua própria skill.

Se Persistence foi escolhida, a tabela de databases de antes ainda vale:

| Database | Initializr id | Test container (Testcontainers 2) | Imagem | Datasource URL | User |
|---|---|---|---|---|---|
| **MySQL** | `mysql` | `org.testcontainers.mysql.MySQLContainer` | `mysql:9` | `jdbc:mysql://localhost:3306/{db}?useTimezone=true&serverTimezone=UTC` | `root` |
| **PostgreSQL** | `postgresql` | `org.testcontainers.postgresql.PostgreSQLContainer` | `postgres:17` | `jdbc:postgresql://localhost:5432/{db}` | `postgres` |
| **SQL Server** | `sqlserver` | `org.testcontainers.mssqlserver.MSSQLServerContainer` — adicione `.acceptLicense()` | `mcr.microsoft.com/mssql/server:2022-latest` | `jdbc:sqlserver://localhost:1433;databaseName={db};encrypt=false` | `sa` |
| **Oracle** | `oracle` | `org.testcontainers.oracle.OracleContainer` | `gvenzl/oracle-free:23-slim-faststart` | `jdbc:oracle:thin:@//localhost:1521/FREEPDB1` | `app` |
| **MariaDB** | `mariadb` | `org.testcontainers.mariadb.MariaDBContainer` | `mariadb:11` | `jdbc:mariadb://localhost:3306/{db}` | `root` |

`{db}` é o artifact com `-` substituído por `_` (`library_api`). A password default é `admin123` (o SQL Server precisa de uma forte: `Admin123!`). Somente valores de desenvolvimento; a real vem de `DB_PASSWORD`.

---

## Step 5 — O passo de padronização

A saída do Initializr é genérica. Transforme-a em um projeto no padrão do pacote — todo item abaixo, nesta ordem.

### 5.1 Limpeza

- Delete `HELP.md`.
- **Maven wrapper:** sempre mantenha `mvnw`, `mvnw.cmd` e `.mvn/`, para que o projeto faça build sem Maven instalado. Os comandos são `./mvnw` (Windows `mvnw.cmd`) onde estas skills dizem `mvn`; um desenvolvedor que tenha Maven ainda pode digitar `mvn`.
- **Gradle wrapper:** sempre mantenha `gradlew`, `gradlew.bat` e `gradle/wrapper/` — os comandos são `./gradlew` (Windows `gradlew.bat`).
- Mantenha `.gitignore` e `.gitattributes`.
- Delete a(s) test class(es) gerada(s) pelo Initializr: `<Artifact>ApplicationTests` sempre, mais `Test<Artifact>Application` e `TestcontainersConfiguration` (ela fixa `mysql:latest` — nunca um `latest` solto) quando Persistence foi escolhida.

### 5.2 O entrypoint e seu teste

Delete `<Artifact>Application.java` e crie, em `src/main/java/<package path>/`:

**`Startup.java`**
```java
package {package};

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class Startup {

    public static void main(String[] args) {
        SpringApplication.run(Startup.class, args);
    }
}
```

**Se Persistence foi escolhida**, o smoke test inicia o context inteiro — Flyway e JPA incluídos — contra um **database real em um container** (o Docker precisa estar rodando). Em `src/test/java/<package path>/`:

**`StartupTests.java`** (MySQL mostrado; troque o import, o tipo e a imagem pela tabela)
```java
package {package};

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.testcontainers.service.connection.ServiceConnection;
import org.testcontainers.junit.jupiter.Container;
import org.testcontainers.junit.jupiter.Testcontainers;
import org.testcontainers.mysql.MySQLContainer;

@SpringBootTest
@Testcontainers
class StartupTests {

    @Container
    @ServiceConnection
    static MySQLContainer database = new MySQLContainer("mysql:9");

    @Test
    void contextLoads() {
    }
}
```
O `@ServiceConnection` entrega a URL e as credenciais do container para a aplicação, então este teste não precisa de um `application.yml` próprio. Se o projeto tem a skill `integration-testing`, o `AbstractIntegrationTest` dela depois substitui este pattern nos testes reais; o smoke test pode ficar.

**Se Persistence foi recusada**, não há database para o qual iniciar um container — o smoke test apenas prova que o context carrega:
```java
package {package};

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class StartupTests {

    @Test
    void contextLoads() {
    }
}
```

### 5.3 Configuration

Delete o `application.yaml`/`application.properties` do Initializr e escreva o que o desenvolvedor escolheu. **YAML é `application.yml`, nunca `.yaml`.** A base contém somente o que foi de fato escolhido — cada bloco abaixo é escrito somente quando seu decorator está presente:

**`src/main/resources/application.yml`** (todo decorator escolhido, valores de MySQL mostrados — o caso "tudo"; remova os blocos cujo decorator foi recusado)
```yaml
cors:                                          # only if Web Config was chosen
  originPatterns: http://localhost:8080,http://localhost:3000

spring:
  application:
    name: {artifact}
  datasource:                                  # only if Persistence was chosen
    url: jdbc:mysql://localhost:3306/{db}?useTimezone=true&serverTimezone=UTC
    username: root
    password: ${DB_PASSWORD:admin123}
  jpa:                                          # only if Persistence was chosen
    hibernate:
      ddl-auto: none
    properties:
      hibernate:
        check_nullability: true
    show-sql: false
    open-in-view: false

logging:
  level:
    root: INFO

springdoc:                                      # only if Swagger was chosen
  api-docs:
    enabled: true
  paths-to-match:
    - /api/**/v1/**
  swagger-ui:
    enabled: true
```
Os comentários `# only if …` acima só marcam a qual decorator cada bloco pertence — **não os copie** para o arquivo gerado (a preferência default é sem comentários). Com **nenhum decorator escolhido**, o arquivo é apenas `spring.application.name` e o bloco `logging`.

**`src/main/resources/application.properties`** — as mesmas chaves, achatadas, seguindo a mesma regra por decorator:
```properties
spring.application.name={artifact}
spring.datasource.url=jdbc:mysql://localhost:3306/{db}?useTimezone=true&serverTimezone=UTC
spring.datasource.username=root
spring.datasource.password=${DB_PASSWORD:admin123}
spring.jpa.hibernate.ddl-auto=none
spring.jpa.properties.hibernate.check_nullability=true
spring.jpa.show-sql=false
spring.jpa.open-in-view=false
logging.level.root=INFO
```
Use a URL e o user do database escolhido. `ddl-auto: none` e `check_nullability: true` não são opções quando Persistence é escolhida (veja `code-organization`). Com a escolha properties, todo bloco YAML das outras skills é escrito como chaves flat com pontos em `application.properties` — diga isso uma vez e continue fazendo.

### 5.4 O build file

O Initializr indenta com tabs: **reescreva os build files com 4 espaços**, e remova o ruído: com a preferência de comentários em "no", o comentário `<!-- lookup parent from repository -->` e os elementos vazios `<url/>`, `<description/>`, `<licenses>`, `<developers>` e `<scm>` (preencha `<description>` somente se o desenvolvedor deu uma).

**Maven** — substitua todo o `<build>` pelo build padrão do pacote, que adiciona o Mockito agent e o native access que os testes precisam no Java 21+ (veja `maven-config`) — necessário independentemente de quais decorators foram escolhidos, já que todo projeto tem pelo menos o smoke test:
```xml
<build>
    <plugins>
        <plugin>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-maven-plugin</artifactId>
        </plugin>
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-dependency-plugin</artifactId>
            <executions>
                <execution>
                    <goals>
                        <goal>properties</goal>
                    </goals>
                </execution>
            </executions>
        </plugin>
        <plugin>
            <groupId>org.apache.maven.plugins</groupId>
            <artifactId>maven-surefire-plugin</artifactId>
            <configuration>
                <argLine>-javaagent:${org.mockito:mockito-core:jar} --enable-native-access=ALL-UNNAMED</argLine>
            </configuration>
        </plugin>
    </plugins>
</build>
```

**Gradle, Groovy DSL** (`build.gradle`) — adicione uma configuration `mockitoAgent` e faça a test task usá-la. Deixe todo o resto que o Initializr escreveu:
```groovy
configurations {
    mockitoAgent
}

dependencies {
    mockitoAgent('org.mockito:mockito-core') { transitive = false }
    // ... the dependencies Initializr generated
}

tasks.named('test') {
    useJUnitPlatform()
    jvmArgs "-javaagent:${configurations.mockitoAgent.asPath}", '--enable-native-access=ALL-UNNAMED'
}
```

**Gradle, Kotlin DSL** (`build.gradle.kts`):
```kotlin
val mockitoAgent = configurations.create("mockitoAgent")

dependencies {
    mockitoAgent("org.mockito:mockito-core") { isTransitive = false }
    // ... the dependencies Initializr generated
}

tasks.withType<Test> {
    useJUnitPlatform()
    jvmArgs("-javaagent:${mockitoAgent.asPath}", "--enable-native-access=ALL-UNNAMED")
}
```
A Java version fica onde o Initializr a colocou: `<java.version>` nas properties do Maven, `languageVersion = JavaLanguageVersion.of(N)` no toolchain do Gradle. A versão do `mockito-core` vem do Spring Boot BOM.

Não adicionados ainda, de propósito, independentemente dos decorators escolhidos: `devtools`, `actuator`, `security` e as outras libraries com skill própria — o Step 6 abaixo adiciona exatamente o que cada decorator *escolhido* precisa, nada mais.

---

## Step 6 — Aplique os decorators escolhidos

Aplique os decorators escolhidos no Step 2 **nesta ordem** — os posteriores assumem que os anteriores, se escolhidos, já existem. Pule um item numerado inteiramente se ele foi recusado; nada sobre ele é escrito, mencionado em código ou deixado meio configurado.

### 6.1 Persistence — Spring Data JPA

Se escolhido, aplique [`../spring-data-jpa/SKILL.md`](../spring-data-jpa/SKILL.md) para criar o exemplo ilustrativo compartilhado: uma entity, `Book` (`id`, `author`, `title`, `launchDate`, `price`), com seu repository, DTO, o mapper wrapper (Dozer ou MapStruct, conforme o Step 2), um `BookService` e — já que `web` está sempre na base — um `BookController` expondo `/api/book/v1`, seguindo os formatos exatos da seção Code Patterns de `code-organization`. Esta é a fatia que todo decorator abaixo estende.

Se recusado, pule este step; ainda não há entity, DTO, service ou controller no projeto.

### 6.2 Flyway migrations

Se escolhido (possível somente quando 6.1 também foi escolhido), aplique [`../flyway-migrations/SKILL.md`](../flyway-migrations/SKILL.md) para `V1__Create_Table_Books.sql`, casando com as colunas da entity `Book`, na sintaxe do database escolhido no Step 2.

Se 6.1 foi escolhido mas este foi recusado, não escreva uma migration — diga claramente no Step 7 que a tabela `books` ainda não existe e que a persistence não está verificada até que uma seja adicionada (veja o aviso no Step 2).

### 6.3 Exception handling

Se escolhido, aplique [`../exception-handling/SKILL.md`](../exception-handling/SKILL.md) para o `CustomEntityResponseHandler` e as domain exceptions genéricas (`ResourceNotFoundException`, `RequiredObjectIsNullException`, `BadRequestException`). Se 6.1 também está presente, conecte `BookService.findById` para lançar `ResourceNotFoundException` via `.orElseThrow(...)`, exatamente como mostrado no pattern de Service de `code-organization`.

Sem 6.1, o handler e as exceptions ainda compilam e funcionam sozinhos — apenas não têm nada específico do projeto para capturar ainda.

### 6.4 Web config

Se escolhido, aplique [`../web-config/SKILL.md`](../web-config/SKILL.md) para o `WebConfig` (CORS) com `cors.originPatterns` no `application.yml`; faça a pergunta própria dela de somente JSON vs. +XML/+YAML se o Step 2 ainda não a respondeu, e adicione o `JacksonConfig` somente se YAML foi escolhido. Se 6.1 também está presente, declare os media types escolhidos em `produces`/`consumes` do `BookController`.

### 6.5 Swagger / OpenAPI

Se escolhido, aplique [`../swagger/SKILL.md`](../swagger/SKILL.md) para a dependency do springdoc (com sua property de versão — veja `maven-config`), o `OpenApiConfig` e o bloco `springdoc` no `application.yml`. Se 6.1 também está presente, documente o `BookController` (ou `BookControllerDocs`, conforme a posição escolhida no Step 2) com `@Operation`/`@ApiResponse`.

Sem 6.1, o Swagger UI ainda sobe — com uma superfície de API vazia, o que é um resultado válido, ainda que silencioso.

### 6.6 Bean Validation

Se escolhido, aplique [`../bean-validation/SKILL.md`](../bean-validation/SKILL.md) para a dependency `spring-boot-starter-validation` e o handler de `MethodArgumentNotValidException`. Se 6.1 também está presente, adicione constraints ao `BookDTO` (`@NotBlank` em `author`/`title`, `@NotNull @PastOrPresent` em `launchDate`, `@NotNull @Positive` em `price`) e `@Valid` no endpoint create do controller.

---

## Step 7 — Verifique

Execute o build real e olhe o resultado — um scaffold que não foi construído não é um scaffold. O que "passando" significa depende do que foi escolhido: com Persistence, espere que o `StartupTests` com container passe (alguns minutos na primeira execução, baixando a imagem do database); sem ela, espere o teste simples de context-loads.

```bash
./mvnw clean package        # Windows: mvnw.cmd clean package — Gradle: ./gradlew build
```

Deve terminar com `BUILD SUCCESS` (Gradle: `BUILD SUCCESSFUL`) e deixar `target/<artifact>-0.0.1-SNAPSHOT.jar` (Gradle: `build/libs/`).

- **Docker não está rodando** (relevante somente com Persistence escolhida): o smoke test não encontra um container runtime. Inicie o Docker e execute de novo. Se o desenvolvedor não puder, faça o build com `-DskipTests` (Gradle: `-x test`) e diga claramente que o context **não** foi verificado.
- **Erros de Java do Step 3** (`release version N not supported`, `Cannot find a Java installation`) — corrija o JDK, não o build file.

**Se Persistence foi escolhida**, um database que case com o `application.yml` precisa estar escutando para executar a aplicação (os testes iniciam o seu próprio; a aplicação não). Um descartável, com os valores do Step 4:
```bash
docker run -d --name <artifact>-db -p 3306:3306 -e MYSQL_ROOT_PASSWORD=admin123 -e MYSQL_DATABASE=<db> mysql:9
```
PostgreSQL — `-p 5432:5432 -e POSTGRES_PASSWORD=admin123 -e POSTGRES_DB=<db> postgres:17`; MariaDB — `-p 3306:3306 -e MARIADB_ROOT_PASSWORD=admin123 -e MARIADB_DATABASE=<db> mariadb:11`; Oracle — `-p 1521:1521 -e ORACLE_PASSWORD=admin123 -e APP_USER=app -e APP_USER_PASSWORD=admin123 gvenzl/oracle-free:23-slim-faststart`. O SQL Server não cria o database a partir de uma variável de ambiente — crie `<db>` antes da primeira execução (veja `docker-and-docker-compose`). Se um database local já ocupa a porta, publique outra e sobrescreva a URL com `SPRING_DATASOURCE_URL`.

Depois `./mvnw spring-boot:run` (Gradle: `./gradlew bootRun`). **Sem Persistence**, nenhum database é necessário — apenas execute e acesse os endpoints que os decorators escolhidos criaram; sem nenhum escolhido, toda URL responde 404, que é o resultado saudável.

---

## Step 8 — Salve e feche

1. **Ofereça salvar** as respostas no `CLAUDE.md` do projeto (só escreva se o desenvolvedor concordar), adicionando estas linhas ao bloco `## Project preferences` de `code-organization` — as da base mais uma linha por decisão de decorator:
```markdown
- Java version: 25 (LTS)
- Build tool: Maven
- Configuration file: YAML
- User-facing text language: English
- Persistence (Spring Data JPA): yes
- Flyway migrations: yes
- Exception handling: yes
- Web config (CORS/content negotiation): yes, JSON only
- Swagger/OpenAPI: yes
- Bean Validation: yes
```
   Um projeto Gradle diz `Gradle (Groovy DSL)` ou `Gradle (Kotlin DSL)`; uma versão não-LTS diz `26 (non-LTS)`; um decorator recusado diz `no`.
2. **Feche com um checklist preenchido com os valores reais** — nunca placeholders genéricos: o que foi criado (liste os arquivos); o comando exato para build, para testar e para executar; se Persistence foi escolhida, o database que a aplicação espera (URL, user, a variável `DB_PASSWORD`) e como iniciar um. Liste **somente os decorators que foram recusados** como próximos passos — por exemplo, se o Swagger foi pulado: "execute `swagger` sempre que quiser documentação da API"; se tudo foi escolhido, diga isso e aponte para `project-claude-md` para fechar.
3. `git init` e um primeiro commit ficam a critério do desenvolvedor. **No Windows os wrapper scripts perdem o bit de executável**, e o runner Linux de CI então falha com `Permission denied` — antes do primeiro commit execute `git add --chmod=+x mvnw gradlew` (somente o que existir). Ofereça a mensagem de commit somente se o plugin `padrao-git` estiver instalado (mencione-o em prosa, nunca dependa dele).

---

## Sem internet

O Initializr fica inacessível atrás de alguns proxies corporativos. **Maven:** escreva o `pom.xml` a partir do skeleton e das tabelas de dependencies de `maven-config` (resolva as versões como aquela skill diz, e somente as dependencies que os decorators escolhidos precisam), adicione o wrapper com `mvn wrapper:wrapper` quando o Maven estiver instalado e conseguir alcançar um repository, depois continue no Step 5.2. **Gradle:** o wrapper jar não pode ser escrito à mão, então o scaffold precisa do Initializr — ofereça Maven, ou tentar de novo mais tarde. Nunca invente um Gradle wrapper.

---

## Regras principais

- A application class é `Startup`, o teste é `StartupTests` — sempre. Nunca deixe uma `<Artifact>Application` para trás, e delete todo teste gerado que ainda aponte para ela.
- **Nada além da base é adicionado a não ser que o desenvolvedor tenha escolhido no Step 2.** Seis decorators independentes, cada um com default "yes" para que "use the defaults" reproduza um projeto completo — mas um desenvolvedor que recusa os seis recebe exatamente `Startup` mais uma web layer vazia.
- Persistence é o que cria o exemplo compartilhado `Book`; todo outro decorator estende esse mesmo exemplo quando ele existe, e conecta somente infraestrutura genérica e funcional quando não existe.
- O Flyway só pode ser perguntado se Persistence foi escolhida; recusá-lo depois de aceitar Persistence exige primeiro o aviso de propriedade do schema.
- Identifiers são sempre em inglês; o texto voltado ao usuário (mensagens de validation/exception, texto do Swagger) segue o idioma escolhido no Step 1 — veja `bean-validation`, `exception-handling` e `swagger` para exatamente quais strings isso cobre.
- Pergunte, depois gere: a Java version tem como default a última LTS, e um número não-LTS sempre recebe o aviso antes de ser usado.
- Valide a Java version você mesmo — o Initializr aceita quase qualquer texto e transforma 16 em 17 silenciosamente.
- `application.yml` (nunca `.yaml`) por default; `application.properties` somente quando escolhido, com as mesmas chaves.
- Indentação de quatro espaços em todo build file; sem Lombok; sem tag de imagem `latest` solta.
- O scaffold só termina depois de um `./mvnw clean package` / `./gradlew build` real — ou uma declaração explícita de que não foi verificado, e por quê.
