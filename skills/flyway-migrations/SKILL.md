---
name: flyway-migrations
description: Migrations Flyway no Spring Boot 4 — dependencies (starter e módulo do banco), naming V{N}__Descricao.sql, DDL/DML e tipos do MySQL, diferenças para MariaDB, PostgreSQL, SQL Server e Oracle, seeds não determinísticos, sequenciamento e mudanças sem downtime (expand → contract). Use quando criar ou alterar tabelas, colunas, índices ou seed data.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) e [`../code-style/SKILL.md`](../code-style/SKILL.md) para as preferências do projeto (database), o package layout base e as convenções de code style.

# Flyway Migrations

O schema pertence exclusivamente ao Flyway — o Hibernate nunca toca no DDL (`ddl-auto: none`). Os arquivos de migration são SQL puro, sem migrations baseadas em Java. Os exemplos usam MySQL (o database escolhido por default no Step 0 de `code-organization`); veja "Os cinco databases suportados" abaixo quando o desenvolvedor escolheu outro.

---

## Dependencies (Spring Boot 4)

O Boot 4 dividiu a auto-configuration em módulos: o `flyway-core` sozinho **não executa mais migrations na inicialização**. Use o starter mais o módulo do database (as versões vêm do Boot BOM — veja `maven-config`):
```xml
<dependency>
    <groupId>org.springframework.boot</groupId>
    <artifactId>spring-boot-starter-flyway</artifactId>
</dependency>
<dependency>
    <groupId>org.flywaydb</groupId>
    <artifactId>flyway-mysql</artifactId>
</dependency>
```
Nenhuma configuração `spring.flyway.*` é necessária para o location default `classpath:db/migration`; o Flyway roda quando a aplicação inicia, contra o datasource configurado.

---

## Localização e naming de arquivos

```
src/main/resources/db/migration/
├── V1__Create_Table_Person.sql
├── V2__Populate_Table_Person.sql
├── V3__Create_Table_Books.sql
├── V4__Insert_Data_In_Books.sql
├── V5__Alter_Table_Person.sql
...
```

**Pattern de naming:** `V{version}__{Description_With_Underscores}.sql`
- Dois underscores entre o número da versão e a descrição.
- A descrição usa `Title_Case_With_Underscores`.
- O tipo de operação sempre abre a descrição: `Create_Table_`, `Alter_Table_`, `Insert_Data_In_`, `Populate_`, `Add_Column_`, `Drop_Column_`.
- Os números de versão são inteiros sequenciais — nunca reutilize, nunca edite uma migration já aplicada.

---

## Patterns de DDL do MySQL

**Sem integer display widths.** Escreva `bigint` e `int`, nunca `bigint(20)` ou `int(10)`: o MySQL 8+ depreca display widths e loga o warning `1681 Integer display width is deprecated` a cada execução. A largura nunca mudou o range de qualquer forma.

### Create table
```sql
CREATE TABLE IF NOT EXISTS `person` (
  `id`         bigint       NOT NULL AUTO_INCREMENT,
  `first_name` varchar(80)  NOT NULL,
  `last_name`  varchar(80)  NOT NULL,
  `address`    varchar(100) NOT NULL,
  `gender`     varchar(6)   NOT NULL,
  PRIMARY KEY (`id`)
);
```

### Create table com UNIQUE KEY
```sql
CREATE TABLE IF NOT EXISTS `users` (
  `id`                      bigint       NOT NULL AUTO_INCREMENT,
  `user_name`               varchar(255) DEFAULT NULL,
  `full_name`               varchar(255) DEFAULT NULL,
  `password`                varchar(255) DEFAULT NULL,
  `account_non_expired`     bit(1)       DEFAULT NULL,
  `account_non_locked`      bit(1)       DEFAULT NULL,
  `credentials_non_expired` bit(1)       DEFAULT NULL,
  `enabled`                 bit(1)       DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_name` (`user_name`)
);
```
`ENGINE=InnoDB` é o storage engine default do MySQL 8+/9 e é o que as foreign keys exigem; escrevê-lo explicitamente é opcional.

### Create join table (ManyToMany)
```sql
CREATE TABLE IF NOT EXISTS `user_permission` (
  `id_user`       bigint NOT NULL,
  `id_permission` bigint NOT NULL,
  PRIMARY KEY (`id_user`, `id_permission`),
  KEY `fk_user_permission_permission` (`id_permission`),
  CONSTRAINT `fk_user_permission`
    FOREIGN KEY (`id_user`) REFERENCES `users` (`id`),
  CONSTRAINT `fk_user_permission_permission`
    FOREIGN KEY (`id_permission`) REFERENCES `permission` (`id`)
);
```

Foreign keys com `ON DELETE CASCADE` (quando os registros filhos devem morrer com o pai):
```sql
CREATE TABLE IF NOT EXISTS `person_books` (
  `person_id` bigint NOT NULL,
  `book_id`   int    NOT NULL,
  PRIMARY KEY (`person_id`, `book_id`),
  FOREIGN KEY (`person_id`) REFERENCES `person`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`book_id`)   REFERENCES `books`(`id`)  ON DELETE CASCADE
);
```
A coluna de uma foreign key deve ter exatamente o tipo da coluna que ela referencia (`int` → `int`, `bigint` → `bigint`).

### Add column
```sql
ALTER TABLE `person`
  ADD COLUMN `enabled` BIT(1) NOT NULL DEFAULT b'1' AFTER `gender`;
```

Várias colunas em um único `ALTER`:
```sql
ALTER TABLE person
  ADD COLUMN wikipedia_profile_url VARCHAR(255) DEFAULT 'https://example.com',
  ADD COLUMN photo_url             VARCHAR(255) DEFAULT 'https://example.com/default.jpg';
```

---

## Convenções de tipos de dados do MySQL

| Caso de uso | Tipo |
|---|---|
| Primary key | `bigint NOT NULL AUTO_INCREMENT` |
| Referência FK a PK `bigint` | `bigint NOT NULL` |
| Referência FK a PK `int` | `int NOT NULL` |
| Strings curtas (name, gender) | `varchar(N)` com length explícito |
| Strings longas (URL, description) | `varchar(255)` |
| Boolean / flag | `bit(1)` — valores `b'1'` / `b'0'` |
| Decimal money/price | `decimal(65,2)` |
| Date + time | `datetime(6)` |
| Somente date | `DATE` |
| Texto livre (legado) | `longtext` — prefira `varchar(255)` em tabelas novas |

Atenção à ligação com a entity: um `@Column(nullable = false)` do JPA não faz a coluna do database ser `NOT NULL`. Se a migration deixa a coluna nullable (`longtext`, `DEFAULT NULL`), somente o `check_nullability` do Hibernate (veja `spring-data-jpa`) impede que um null seja salvo — declare `NOT NULL` na migration para toda coluna que a entity exige.

Um campo `LocalDate` mapeia para uma coluna `DATE` **ou** `datetime`; o tipo da coluna é decisão da migration, e uma coluna `datetime(6)` existente continua funcionando quando a entity passa de `java.util.Date` para `LocalDate`.

---

## Patterns de DML

### INSERT — colunas explícitas, com backticks
```sql
INSERT INTO `books` (`author`, `launch_date`, `price`, `title`) VALUES
    ('Robert C. Martin', '2009-01-10 00:00:00.000000', 77.00, 'Clean Code'),
    ('Eric Evans',       '2017-11-07 15:09:01.674000', 92.00, 'Domain Driven Design');
```

### INSERT com valores BIT (users/flags)
```sql
INSERT INTO `users` (`user_name`, `full_name`, `password`,
                     `account_non_expired`, `account_non_locked`,
                     `credentials_non_expired`, `enabled`) VALUES
    ('leandro', 'Leandro Costa', '{hashed_password}', b'1', b'1', b'1', b'1');
```

### INSERT em join table
```sql
INSERT INTO `user_permission` (`id_user`, `id_permission`) VALUES
    (1, 1),
    (1, 2),
    (2, 1);
```

### Bulk INSERT via SELECT + CROSS JOIN (seed data)
Use quando associar muitos registros programaticamente:
```sql
INSERT INTO person_books (person_id, book_id)
SELECT p.id, b.id
FROM (SELECT id FROM person WHERE id <= 12) p
CROSS JOIN (SELECT id FROM books ORDER BY RAND() LIMIT 20) b;
```

### UPDATE com CASE (update condicional em massa)
Use quando popular uma coluna nova com valores distintos por linha. O branch `ELSE` mantém o valor existente para as linhas que não casam:
```sql
UPDATE person
SET photo_url = CASE
    WHEN id = 1 THEN 'https://example.com/photos/01.jpg'
    WHEN id = 2 THEN 'https://example.com/photos/02.jpg'
    ELSE photo_url
END
WHERE id <= 18;
```

---

## Seed data não determinístico

`ORDER BY RAND()` em um script de seed roda uma vez, mas faz com que **dois databases novos sejam diferentes** — todo desenvolvedor, container e execução de CI recebe outro conjunto de associações. Isso é aceitável para dados de demo e uma armadilha para testes:
- nunca faça assert sobre quais linhas o seed aleatório associou; faça assert sobre linhas que a migration insere explicitamente;
- quando o seed data tem valores repetidos (por exemplo vários books com o mesmo title), uma query ordenada por aquela coluna tem empates, e a ordem entre as linhas empatadas pode mudar entre execuções. Ordene também por um desempate (`ORDER BY title, id`) ou evite valores repetidos nas fixtures que os testes leem;
- O container MySQL do Testcontainers deve ser criado com `.withConfigurationOverride("mysql-default-conf")` para manter a configuração de servidor de baixa memória que a classe de container mais antiga aplicava implicitamente (veja `spring-data-jpa` e `integration-testing`).

---

## Convenção de sequenciamento de migrations

Agrupe operações relacionadas em arquivos separados — uma preocupação por arquivo:

| Arquivo | Tipo |
|---|---|
| `V1__Create_Table_Person.sql` | DDL — estrutura da tabela |
| `V2__Populate_Table_Person.sql` | DML — seed data |
| `V3__Create_Table_Books.sql` | DDL — próxima tabela |
| `V4__Insert_Data_In_Books.sql` | DML — seed data |
| `V5__Alter_Table_Person.sql` | DDL — mudança incremental |
| `V6__Populate_Person_With_Many.sql` | DML — bulk seed |
| `V8__Alter_Table_Person_Adding_Photo_And_Wiki.sql` | DDL — adiciona colunas |
| `V9__Inserting_Wikipedia_Url.sql` | DML — popula a nova coluna |
| `V11__Create_Join_Table_Person_Books.sql` | DDL — tabela de relationship |
| `V12__Insert_Data_In_Join_Table_Person_Books.sql` | DML — dados de relationship |
| `V13`…`V18` | Permission, users e user_permission: o DDL de cada tabela seguido do seu DML de seed |

Pattern: sempre DDL primeiro, depois o DML que depende dele. Nunca misture DDL e DML no mesmo arquivo.

---

## Os cinco databases suportados

MySQL é o default; PostgreSQL, SQL Server, Oracle e MariaDB são suportados. A arquitetura não muda (Flyway, SQL puro, versões sequenciais, separação DDL/DML) — o SQL muda. Cada linha abaixo foi executada com o Flyway contra o database real (MySQL 9.1, MariaDB 11, PostgreSQL 17, SQL Server 2022, Oracle Free 23) com tabelas, identity columns, um default boolean, uma join table com `ON DELETE CASCADE`, seeds, um `ALTER TABLE` e um `INSERT ... SELECT` aleatório. Os mapeamentos de tipo e o lado JPA (`GenerationType.IDENTITY`, `Boolean`, `LocalDate`/`LocalDateTime`) não mudam.

| Preocupação | MySQL | MariaDB | PostgreSQL | SQL Server | Oracle |
|---|---|---|---|---|---|
| Chave auto-increment | `bigint NOT NULL AUTO_INCREMENT` + `PRIMARY KEY (id)` | igual ao MySQL | `bigint GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY` | `bigint IDENTITY(1,1) PRIMARY KEY` | `NUMBER(19) GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY` |
| Boolean | `bit(1)`, `b'1'` | igual ao MySQL | `boolean`, `true` | `bit`, `1` | `NUMBER(1)`, `1` |
| Texto curto | `varchar(n)` | `varchar(n)` | `varchar(n)` | `varchar(n)` | `VARCHAR2(n)` |
| Timestamp | `datetime(6)` | `datetime(6)` | `timestamp(6)` | `datetime2(6)` | `TIMESTAMP(6)` |
| Money / price | `decimal(65,2)` (máximo do MySQL) | igual | `decimal(19,2)` | `decimal(19,2)` (precisão máxima 38) | `NUMBER(19,2)` (precisão máxima 38) |
| Quoting de identifiers | backticks | backticks | nenhum (nomes em minúsculas) | nenhum | nenhum |
| `CREATE TABLE IF NOT EXISTS` | sim | sim | sim | não — `CREATE TABLE` simples | não — `CREATE TABLE` simples |
| Adicionar uma coluna | `ADD COLUMN c ... [AFTER x]` | igual ao MySQL | `ADD COLUMN c ...` | `ADD c ...` (sem `COLUMN`) | `ADD (c ...)` |
| Literal de timestamp em seeds | `'2009-01-10 00:00:00'` | igual | `'2009-01-10 00:00:00'` | `'2009-01-10T00:00:00'` (ISO com `T`) | `TIMESTAMP '2009-01-10 00:00:00'` |
| Várias linhas em um `INSERT` | `VALUES (...), (...)` | igual | igual | igual | um `INSERT` por linha |
| Linhas aleatórias para seeds | `ORDER BY RAND() LIMIT n` | igual | `ORDER BY random() LIMIT n` | `SELECT TOP (n) ... ORDER BY NEWID()` | `ORDER BY DBMS_RANDOM.VALUE FETCH FIRST n ROWS ONLY` |
| Módulo de database do Flyway | `flyway-mysql` | `flyway-mysql` | `flyway-database-postgresql` | `flyway-sqlserver` | `flyway-database-oracle` |

Regras que decorrem disso:
- Use `decimal(19,2)` (ou `NUMBER(19,2)`) para money fora do MySQL/MariaDB: `decimal(65,2)` não existe no SQL Server nem no Oracle.
- Prefira `GENERATED BY DEFAULT AS IDENTITY` a `GENERATED ALWAYS` no PostgreSQL e no Oracle para que os scripts de seed ainda possam inserir ids explícitos.
- Onde `IF NOT EXISTS` não está disponível, omita-o: o Flyway já executa cada versão uma vez.
- Não faça quoting de identifiers fora do MySQL/MariaDB; use nomes em `lower_snake_case` e evite palavras reservadas (`user`, `order`, `group`…) — é por isso que a tabela de users se chama `users`.
- `UNIQUE (title, author)` dentro de `CONSTRAINT name UNIQUE (...)` é a forma portável; `UNIQUE KEY name (...)` é somente MySQL/MariaDB.
- Repetir um `NOT NULL` da entity funciona igual em todo lugar.
- Tanto `VARCHAR2` (Oracle) quanto `varchar` (outros) são escritos com length explícito.
- As imagens do Oracle Free e do SQL Server são grandes (vários GB) e lentas para iniciar — veja `integration-testing` para timeouts de startup de container. Um database fora desses cinco não é coberto: mantenha a arquitetura e traduza com a documentação do próprio database.

---

## Operação segura (produção, multi-instância, zero downtime)

**Várias réplicas.** O Flyway usa um lock no database (a tabela `flyway_schema_history`), então réplicas que sobem juntas não aplicam a mesma migration duas vezes — as outras esperam. Mesmo assim, em Kubernetes prefira rodar as migrations em um **Job** ou `initContainer` dedicado quando elas forem demoradas, para que um pod não fique "not ready" por minutos e o rollout não estoure o timeout (veja `kubernetes`).

**Usuário do database.** A aplicação em runtime não precisa de permissão de DDL. Se a política da empresa exigir, use um usuário de migration (`spring.flyway.user`/`password`, com DDL) separado do usuário do datasource (somente DML).

**Settings que valem a pena conhecer** (nenhuma é necessária no caso simples):
```yaml
spring:
  flyway:
    validate-on-migrate: true
    clean-disabled: true
    baseline-on-migrate: false
```
- `clean-disabled: true` (já é o default desde o Flyway 9) — nunca habilite `clean` em um ambiente com dados reais: ele **apaga o schema**.
- `baseline-on-migrate: true` somente ao adotar o Flyway em um database que **já existe** e tem tabelas; nunca em um database novo (ele pularia a V1).
- `validate-on-migrate: true` (default) falha a aplicação se o checksum de uma migration aplicada mudou. É o comportamento desejado — não o desligue para "fazer passar".

**Repeatable migrations.** `R__Create_View_Book_Summary.sql` (prefixo `R__`, sem número) é reaplicada sempre que o conteúdo muda — útil para views, functions e procedures. Rodam depois de todas as versionadas.

**Mudanças sem downtime: expand → migrate → contract.** Com rolling update, a versão antiga e a nova da aplicação convivem com o **mesmo** schema por alguns minutos. Portanto:
1. *Expand* (release N): adicione a coluna nova **nullable** ou com default; a versão antiga continua funcionando.
2. *Migrate* (release N): a aplicação passa a escrever nas duas; um `UPDATE` em lotes preenche o histórico.
3. *Contract* (release N+1): só depois que nenhuma instância antiga existe, remova a coluna velha ou coloque `NOT NULL`.

Nunca, em uma única release: renomear/remover coluna usada pela versão anterior, nem adicionar `NOT NULL` sem default em tabela com dados. Em tabelas grandes, `UPDATE` e `CREATE INDEX` travam — faça em lotes e, onde o database suporta, crie o índice online (`CREATE INDEX CONCURRENTLY` no PostgreSQL exige `-- flyway:executeInTransaction=false`).

**Índices.** Toda foreign key e toda coluna usada em `WHERE`/`ORDER BY` frequente merece um índice, criado em uma migration própria (`V20__Create_Index_Books_Title.sql`). O MySQL cria índice para FK automaticamente; o PostgreSQL **não**.

---

## Regras principais

- Nunca edite uma migration que já foi aplicada — os checksums do Flyway vão quebrar. Sempre crie uma nova versão.
- `CREATE TABLE IF NOT EXISTS` no MySQL, MariaDB e PostgreSQL — previne falha em re-execução em casos de borda; omita-o no SQL Server e no Oracle, onde a sintaxe não está disponível.
- Faça backtick em todos os identifiers no MySQL: `` `table_name` ``, `` `column_name` ``.
- Sem integer display widths: `bigint`, `int` — nunca `bigint(20)`, `int(10)`.
- `DEFAULT CHARSET=latin1` somente ao fazer join com tabelas legadas que já o usam; prefira omitir o charset (default do charset do servidor) em tabelas novas.
- Flags booleanas: sempre `BIT(1)` no MySQL, mapeadas para `Boolean` em Java.
- Senhas em seed data são sempre pré-hasheadas — nunca texto puro.
- Separe DDL e DML em arquivos distintos — uma preocupação por migration.
- `NOT NULL` na migration para toda coluna que uma entity marca com `nullable = false`.
- Use `spring-boot-starter-flyway` + o módulo do database — nunca `flyway-core` sozinho no Boot 4.
- Seeds podem ser aleatórios (`ORDER BY RAND()`), os testes não devem depender da parte aleatória.
- Em produção: `clean-disabled: true`, nunca `baseline-on-migrate` em database novo, e mudanças destrutivas em duas releases (expand → contract).
