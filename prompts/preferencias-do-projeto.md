# Preferências do projeto (`CLAUDE.md`)

**Quando usar:** primeira vez com o plugin em um projeto, ou para mudar uma preferência (inclusive o perfil de modelo).
**Como rodar:** sessão normal (`claude`) e cole o prompt; usa a skill `project-claude-md`. Para garantir, comece com `/squads:project-claude-md`.
**Entrega:** `CLAUDE.md` com a seção `## Project preferences`, lida por todas as skills e agents — eles param de perguntar o que já está lá.

## Prompt

```text
Crie ou atualize o CLAUDE.md deste projeto com as preferências abaixo, lendo o projeto para preencher o resto (comandos, arquitetura, versões).

- Comments in generated code: <yes | no>
- Database: <MySQL | PostgreSQL | SQL Server | Oracle | MariaDB>
- Swagger annotations: <*ControllerDocs interface | directly on the controller>
- Build tool: <Maven | Gradle>
- Java version: <25 (LTS) | ...>
- Configuration file: <YAML | properties>
- Entity/DTO mapping: <Dozer | MapStruct>
- Dependency injection: <constructor | field>
- Model profile: <auto | economico | equilibrado | qualidade-maxima>

Mostre o arquivo antes de gravar.
```

## Exemplo preenchido

```text
Crie ou atualize o CLAUDE.md deste projeto com as preferências abaixo, lendo o projeto para preencher o resto (comandos, arquitetura, versões).

- Comments in generated code: no
- Database: PostgreSQL
- Swagger annotations: *ControllerDocs interface
- Build tool: Maven
- Java version: 25 (LTS)
- Configuration file: YAML
- Entity/DTO mapping: MapStruct
- Dependency injection: constructor
- Model profile: equilibrado

Mostre o arquivo antes de gravar.
```

## Dicas

- `Model profile` define o custo × qualidade padrão do orquestrador; um pedido explícito ("revise com opus") continua valendo por cima dele.
- Mantenha o heading `## Project preferences` e uma linha por preferência — é assim que as skills encontram os valores.
