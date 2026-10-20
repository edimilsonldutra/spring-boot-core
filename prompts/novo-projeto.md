# Novo projeto Spring Boot

**Quando usar:** criar um projeto do zero no padrão do pacote (flat-by-layer, sem Lombok, Flyway, Swagger, `ExceptionResponse`).
**Como rodar:** sessão normal (`claude`) e cole o prompt; a skill `scaffold` é escolhida pela descrição. Para garantir, comece com `/squads:scaffold`.
**Entrega:** projeto compilando, com build e testes executados de verdade.

## Prompt

```text
Crie um projeto Spring Boot chamado <nome-do-projeto>.

Group id e base package: <br.com.edimilsonldutra | outro>
Banco: <MySQL | PostgreSQL | SQL Server | Oracle | MariaDB>
Build: <Maven | Gradle>
Configuração: <YAML | properties>
Mapeamento entity/DTO: <Dozer | MapStruct>
Injeção de dependência: <construtor | field>
Comentários no código gerado: <sim | não>
Recursos iniciais: <ex.: CRUD de <Entity> com campos <...>, Swagger, autenticação JWT, Docker Compose, GitHub Actions>
```

## Exemplo preenchido

```text
Crie um projeto Spring Boot chamado biblioteca-api.

Group id e base package: br.com.edimilsonldutra
Banco: MySQL
Build: Maven
Configuração: YAML
Mapeamento entity/DTO: MapStruct
Injeção de dependência: construtor
Comentários no código gerado: não
Recursos iniciais: CRUD de Book (title, author, price, launchDate), Swagger, Docker Compose e GitHub Actions
```

## Dicas

- Logo depois, rode [`preferencias-do-projeto.md`](preferencias-do-projeto.md) para salvar essas escolhas no `CLAUDE.md`.
