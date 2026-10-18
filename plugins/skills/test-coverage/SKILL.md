---
name: test-coverage
description: Cobertura e eficácia da suíte — o que a cobertura mede e não prova, JaCoCo com Maven e Gradle (argLine com o agent do Mockito), padrão de 90% de linha e branch, diff coverage e catraca para legado, gate no CI (Codecov, Sonar), mutation testing com PIT e anti-patterns. Use quando configurar cobertura ou um gate no pipeline, ou analisar o que está descoberto.
---

Antes de aplicar este pattern, leia também [`../testing/SKILL.md`](../testing/SKILL.md), [`../test-patterns/SKILL.md`](../test-patterns/SKILL.md) (smells: teste que nunca falha), [`../integration-testing/SKILL.md`](../integration-testing/SKILL.md), [`../maven-config/SKILL.md`](../maven-config/SKILL.md) (surefire e o `argLine` do Mockito) e [`../github-actions-aws/SKILL.md`](../github-actions-aws/SKILL.md) (o pipeline).

# Cobertura de testes

**Cobertura é um instrumento, não um objetivo.** Ela responde **"que código os testes executaram?"** — e portanto mostra com segurança **o que NÃO foi testado**. Ela **não** responde "os testes são bons?": um teste sem nenhum `assert` dá **100% de cobertura** e **zero proteção**. Use-a para **achar lacunas**, nunca como prova de qualidade (**lei de Goodhart:** quando a medida vira meta, deixa de ser boa medida).

## 1. O que se mede

| Métrica | O que conta | Para que serve |
|---|---|---|
| **Linha** (*line*) | Linhas executadas | Visão geral (a mais citada; a mais **fraca**) |
| **Branch** (decisão/ramo) | Cada lado de `if`/`switch`/`&&`/`?:` executado | **A que mais importa para regra de negócio**: uma linha `if (a && b)` executa em 100% das linhas com um só teste, mas cobre **1 de 4** ramos |
| **Instrução** (*instruction*) | Instruções de bytecode | Granularidade fina (base do JaCoCo) |
| **Complexidade** | Caminhos independentes cobertos | Aponta métodos complexos descobertos |
| **Método / classe** | Chamados ao menos uma vez | Grosseira |

**Prefira branch a linha** nas camadas com regra de negócio (`domain`, `services`): `if (loan.isOverdue() && !member.isBlocked())` com **um** teste "cobre a linha" e deixa **três** combinações sem teste.

**O que a cobertura NÃO diz:** se os **asserts** são significativos; se **casos de borda** foram testados (a linha foi executada com **um** valor); se o **comportamento** está correto; se a **integração** funciona; se há **bugs de concorrência**. **Código não coberto = certamente sem proteção; código coberto = talvez.**

## 2. JaCoCo com Maven

```xml
<properties>
    <jacoco.version>{última estável}</jacoco.version>
    <argLine></argLine>
</properties>

<plugin>
    <groupId>org.jacoco</groupId>
    <artifactId>jacoco-maven-plugin</artifactId>
    <version>${jacoco.version}</version>
    <executions>
        <execution>
            <id>prepare-agent</id>
            <goals>
                <goal>prepare-agent</goal>
            </goals>
        </execution>
        <execution>
            <id>report</id>
            <phase>verify</phase>
            <goals>
                <goal>report</goal>
            </goals>
        </execution>
        <execution>
            <id>check</id>
            <phase>verify</phase>
            <goals>
                <goal>check</goal>
            </goals>
            <configuration>
                <rules>
                    <rule>
                        <element>BUNDLE</element>
                        <limits>
                            <limit>
                                <counter>LINE</counter>
                                <value>COVEREDRATIO</value>
                                <minimum>0.90</minimum>
                            </limit>
                            <limit>
                                <counter>BRANCH</counter>
                                <value>COVEREDRATIO</value>
                                <minimum>0.90</minimum>
                            </limit>
                        </limits>
                    </rule>
                </rules>
            </configuration>
        </execution>
    </executions>
    <configuration>
        <excludes>
            <exclude>**/Startup.class</exclude>
            <exclude>**/config/**</exclude>
            <exclude>**/data/dto/**</exclude>
        </excludes>
    </configuration>
</plugin>
```
- **`prepare-agent`** instala o agent do JaCoCo e **define a property `argLine`**; o **`report`** gera HTML (`target/site/jacoco/index.html`) e XML (`target/site/jacoco/jacoco.xml`, para CI/Sonar/Codecov); o **`check`** **falha o build** se as regras não forem cumpridas.
- **O `argLine` do surefire precisa incluir o do JaCoCo** (senão a cobertura sai **zerada**). A configuração do pack (`maven-config`) fica:
  ```xml
  <argLine>@{argLine} -javaagent:${org.mockito:mockito-core:jar} --enable-native-access=ALL-UNNAMED</argLine>
  ```
  O `@{argLine}` é avaliado **tarde** (depois do `prepare-agent`). **Por isso a property vazia `<argLine></argLine>` em `<properties>`**: se o JaCoCo for **pulado** (`-Djacoco.skip=true`), o `@{argLine}` não fica literal na linha de comando da JVM (erro `Could not find or load main class @{argLine}`).
- **A versão do JaCoCo precisa suportar a versão do Java** (classes compiladas com Java 25 exigem um JaCoCo recente). Sintoma de versão antiga: `Unsupported class file major version`/`Could not analyze class` — **atualize o JaCoCo**, não desligue.
- **Fase `verify`**: a cobertura aparece em `./mvnw verify` (que roda **todos** os testes — `maven-config`, sem split unit/integration). Em `./mvnw test` o `report` **não** roda (está em `verify`).
- **O padrão do pacote é 90%**, de **linha E de branch**, medido **depois das exclusões legítimas** (abaixo). Em **projeto novo**, ligue o `check` com 90% **desde o primeiro commit** (é muito mais barato do que subir depois). Em **legado**, **não** imponha 90% a um projeto em 20% (o build ficaria vermelho para sempre e todos ignorariam o gate): comece pela **catraca** (seção 5) e **suba o piso até 90%**. O 90% é um **piso, não uma prova de qualidade**: só vale **com asserts de verdade** e, nas regras críticas, **com mutation score** (seção 8) — senão vira o teatro descrito na seção 10. Se o branch a 90% for inviável em um caso específico, **registre a exceção e o motivo** (ADR/`CLAUDE.md`), não afrouxe o número em silêncio.

### Exclusões legítimas

**Exclua o que não tem lógica a testar**, **não** o que é "difícil de testar":
| Exclua | Por quê |
|---|---|
| `Startup` (a classe `main`) | Só inicia o Spring; o `StartupTests` prova que o contexto sobe (`scaffold`) |
| `config/**` (beans de configuração) | Cola declarativa; validada pelos testes de integração |
| `data/dto/**`, entities/boilerplate | Getters/setters sem lógica (`code-organization`) |
| Código gerado (MapStruct impl, protobuf) | Não é seu |

**Nunca exclua** `services/`, `domain/` ou qualquer classe com regra de negócio para "subir o número" — isso **é** a falha que o número deveria acusar. **Registre o motivo** de cada exclusão (no pom ou no `CLAUDE.md`). O JaCoCo já ignora parte do código gerado (por exemplo, métodos sintéticos e, nas versões recentes, boilerplate de `record`); **confirme** na versão usada.

## 3. JaCoCo com Gradle

**Groovy DSL:**
```groovy
plugins {
    id 'jacoco'
}

jacoco {
    toolVersion = '{última estável}'
}

jacocoTestReport {
    dependsOn test
    reports {
        xml.required = true
        html.required = true
    }
    afterEvaluate {
        classDirectories.setFrom(files(classDirectories.files.collect {
            fileTree(dir: it, exclude: ['**/Startup.class', '**/config/**', '**/data/dto/**'])
        }))
    }
}

jacocoTestCoverageVerification {
    dependsOn jacocoTestReport
    violationRules {
        rule {
            limit {
                counter = 'LINE'
                minimum = 0.90
            }
            limit {
                counter = 'BRANCH'
                minimum = 0.90
            }
        }
    }
}

check {
    dependsOn jacocoTestCoverageVerification
}
```
**Kotlin DSL:** `plugins { jacoco }`, `tasks.jacocoTestReport { dependsOn(tasks.test); reports { xml.required = true; html.required = true } }`, `tasks.jacocoTestCoverageVerification { dependsOn(tasks.jacocoTestReport); violationRules { rule { limit { counter = "BRANCH"; minimum = "0.90".toBigDecimal() } } } }` e `tasks.check { dependsOn(tasks.jacocoTestCoverageVerification) }`. No Gradle o plugin já **encadeia o agent** ao `test` (sem `argLine` manual); com o agent do Mockito (`scaffold`), os `jvmArgs` ficam como já definidos. Lembre: o Gradle **pula testes "UP-TO-DATE"** — para forçar, `cleanTest test` (`maven-config`).

## 4. Unit + integração: uma cobertura só

Como o pack roda **tudo na mesma fase** (surefire), há **um** arquivo `jacoco.exec` com a cobertura **combinada** de unit e integração — simples. **Se você dividir as fases** (Failsafe — `integration-testing`, seção 7), use **`prepare-agent-integration`** + `report-integration` e **junte** os `.exec` com `merge` antes do `report`/`check` — senão o relatório mostrará só **uma** das metades.
**Cuidado com a cobertura "emprestada":** um teste de integração que **executa** muito código mas **só confere o status 200** infla o número **sem proteger nada**. Veja a seção 8 (mutation).

## 5. A meta certa: código novo + catraca (ratchet)

O piso global de **90%** é o **alvo**, mas **uma meta global sozinha não basta**:
- Num **legado** em 30%, impô-la de uma vez é inatingível — a equipe ou ignora o gate ou **escreve testes ruins** só para o número. O caminho é a **catraca** abaixo, **subindo até 90%**.
- Num projeto grande já perto de 90%, o total **mal se move** quando o código **novo** vem todo descoberto — por isso o PR também precisa de **diff coverage**.
Use **duas regras**, em conjunto com o piso de 90%:
1. **Cobertura do código novo/alterado (diff coverage)**: o **PR** só passa se as **linhas/ramos que ele adiciona** tiverem cobertura ≥ X (**90%**). Mede o que **a equipe controla agora**, e **melhora o projeto organicamente**. Ferramentas: **SonarQube/SonarCloud "New Code"**, **Codecov "patch coverage"**, ou `diff-cover`:
   ```bash
   diff-cover target/site/jacoco/jacoco.xml --compare-branch=origin/main --fail-under=90
   ```
2. **Catraca (ratchet):** o **piso global é a cobertura atual** e **só sobe** — o build **falha se a cobertura cair** abaixo do último valor aprovado. Evita regressão sem exigir um patamar irreal; a cada melhoria, **suba o piso**.
Veja a seção 6 para como o **90%** se aplica a cada camada.

## 6. O 90% do pacote e como ele se aplica por camada

O pacote adota **90% de linha e de branch** como piso do projeto (regra `BUNDLE` do `check`, seção 2). O **risco** decide onde **ir além**:
| Camada | Meta de **branch** | Como se chega lá |
|---|---|---|
| **`domain` / `services`** (regra de negócio) | **≥ 90%** (e, nas regras críticas, **mutation score** — seção 8) | **Unit tests** puros (`testing`, `test-patterns`): é onde mora o valor e o bug caro; **ramos de erro e limites** incluídos |
| **Controllers / adapters** | Contam no **90% do bundle** | Cobertos por **slice** (`@WebMvcTest`, `@DataJpaTest`) e **integração** (`integration-testing`); regra mínima, o risco é de **contrato** |
| **Config / DTO / `Startup`** | **Excluídos** (com motivo registrado) | Sem lógica; o contexto subindo já é provado |
| **Código legado sem teste** | **Catraca** + **diff coverage de 90%** | Subir o piso a cada melhoria, **até 90%** |

Como o `check` roda sobre o **bundle inteiro**, **todas as camadas** (unit + slice + integração, na mesma execução — seção 4) **somam** para os 90%; ainda assim, **não compense** `services`/`domain` fracos com testes de integração "largos" — o **mutation score** (seção 8) e a leitura do relatório expõem isso.

**O número importa menos que a pergunta:** *"as regras críticas e os ramos de erro estão cobertos **com asserts de verdade**?"* **Leia o relatório**, não só o percentual: abra as classes de negócio e veja os **ramos vermelhos/amarelos** (o JaCoCo pinta ramos parcialmente cobertos) — são **perguntas sem teste**.

## 7. No CI

Em `github-actions-aws`, o job `build-test` já roda `./mvnw -B clean verify`; com o JaCoCo configurado, **o `check` falha o pipeline** quando a regra é violada. Acrescente a **publicação do relatório**:
```yaml
      - name: Build, test and coverage gate
        run: ./mvnw -B clean verify

      - name: Upload coverage report
        uses: actions/upload-artifact@v4
        with:
          name: jacoco-report
          path: target/site/jacoco/

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v5
        with:
          files: target/site/jacoco/jacoco.xml
          token: ${{ secrets.CODECOV_TOKEN }}
```
(Confirme as versões atuais das actions e fixe por SHA — `github-actions-aws`; o **token** vem de *secrets*; em PRs de forks os secrets não existem — o gate local do `verify` continua valendo.) O **Codecov** comenta no PR a **cobertura do patch** e a variação do projeto; o **SonarQube/SonarCloud** faz o mesmo e adiciona **quality gate** ("Coverage on New Code ≥ 90%", sem novos bugs/vulnerabilidades):
```bash
./mvnw -B verify sonar:sonar -Dsonar.coverage.jacoco.xmlReportPaths=target/site/jacoco/jacoco.xml
```
(`SONAR_TOKEN` por *secret*; configure o plugin/versão e o host conforme a documentação atual.) **Faça o gate no PR**, não só na `main`: o custo de corrigir é menor **antes do merge**.

## 8. Mutation testing (PIT) — a medida que a cobertura não dá

A cobertura diz **o código foi executado**; o **mutation testing** diz **os testes teriam pegado um bug**. O **PIT (Pitest)** **muda o código de propósito** (mutantes: trocar `>` por `>=`, remover uma chamada, inverter um `if`, retornar `null`) e roda os testes: se **algum teste falha**, o mutante foi **morto** (bom); se **todos passam**, o mutante **sobreviveu** (os testes **não protegem** aquela lógica). O **mutation score** = mortos ÷ total.
```xml
<plugin>
    <groupId>org.pitest</groupId>
    <artifactId>pitest-maven</artifactId>
    <version>${pitest.version}</version>
    <dependencies>
        <dependency>
            <groupId>org.pitest</groupId>
            <artifactId>pitest-junit5-plugin</artifactId>
            <version>${pitest-junit5.version}</version>
        </dependency>
    </dependencies>
    <configuration>
        <targetClasses>
            <param>br.com.padrao.services.*</param>
            <param>br.com.padrao.domain.*</param>
        </targetClasses>
        <targetTests>
            <param>br.com.padrao.services.*Test</param>
            <param>br.com.padrao.domain.*Test</param>
        </targetTests>
        <mutationThreshold>70</mutationThreshold>
        <outputFormats>
            <param>HTML</param>
            <param>XML</param>
        </outputFormats>
    </configuration>
</plugin>
```
Rode com `./mvnw org.pitest:pitest-maven:mutationCoverage` (relatório em `target/pit-reports`). **Como usar bem:**
- **Só nas camadas de regra** (`services`, `domain`) e **apenas com os unit tests** (`targetTests`): o PIT executa a suíte **muitas vezes**; com testes que sobem Spring/containers, vira **horas**. Por isso **não vai no build de todo commit**.
- **Rode à noite** (job agendado) ou **só nas classes alteradas** (`-DwithHistory`/modo incremental), e **nos PRs de áreas críticas**.
- **Mutantes sobreviventes** são a **lista de testes a escrever/fortalecer**: *"mudar `>` por `>=` na regra de multa não quebrou nenhum teste"* → falta o **teste do valor-limite** (`test-patterns`, seção 6). Esse é o ganho: **achar o teste que não tem assert ou não cobre o limite**.
- **Mutantes equivalentes** (a mudança **não altera** o comportamento observável) sobrevivem sem ser falha de teste — **ignore-os** com critério; não persiga 100% de mutation score.
- **Metas:** use como **tendência e lista de trabalho**; um *threshold* (acima, 70%) só depois de **medir** a linha de base.
- Pode precisar de **ajuste do `argLine`/JVM args** para o **agent do Mockito** (`maven-config`) e a versão do plugin compatível com o **JUnit 5** da plataforma/Java — confirme na documentação atual.
Uma suíte com **90% de cobertura e 40% de mutation score** é **teatro**; **90% de cobertura com alto mutation score** nas regras críticas **protege de verdade**.

## 9. Como ler e agir sobre os números

- **Cobertura caiu num PR?** Pergunte **o que ficou sem teste** (abra o diff no relatório), não "quanto falta para o número".
- **Ramo de erro descoberto** (o `else`, o `catch`, a validação que lança): é **o primeiro a escrever** — erros de borda são onde os bugs moram (`qa`: casos de borda, `test-patterns`).
- **Classe de negócio com cobertura baixa**: **risco alto** → priorize (`prioritization`: risco e custo de atraso).
- **Código que "não dá para testar"** quase sempre é **sinal de design** (acoplamento, estático, `new` dentro da regra) — **refatore** (injete `Clock`, extraia a regra para o `domain`), **não exclua**.
- **Tendência > valor absoluto:** acompanhe a cobertura **do código novo** e o **mutation score** ao longo do tempo.
- **Nunca** use cobertura para **avaliar pessoas** ou times (produz testes vazios e esconde risco real); use para **achar lacunas** e **conversar sobre risco**.
- **Relatório de cobertura também é revisado** (`code-reviewer`): o PR traz testes **com asserts** para o código novo? Os ramos de erro estão cobertos?

## 10. Anti-patterns

- **Exigir 100%**, ou **aplicar o 90% sem as condições** (exclusões **honestas**, **asserts de verdade**, mutation score nas regras críticas): o número vira alvo e **incentiva teste sem assert, getters e exclusões criativas** (lei de Goodhart).
- **Baixar o piso em silêncio** para o build passar (em vez de escrever o teste, ou registrar uma exceção justificada).
- **Cobertura como KPI de pessoa/time** ou condição de bônus.
- **Testes sem `assert`** só para executar linhas (cobertura sem proteção).
- **Excluir código de negócio** "difícil" para subir o número.
- **Só linha, nunca branch**.
- **Meta global em legado** (build vermelho eterno → todos ignoram) em vez de **diff coverage + catraca**.
- **Cobertura zerada por `argLine` errado** (agent do JaCoCo não carregado) **sem ninguém notar**: o `check` com mínimo > 0 pega.
- **Contar teste de integração que não afirma nada** como cobertura útil.
- **PIT em toda a suíte, em todo commit** (inviável) — ou **nunca rodar mutation** e confiar só na cobertura.
- **Perseguir 100% de mutation score** (mutantes equivalentes).
- **Gate só na `main`** (descobre tarde).

---

## Regras principais

- **Cobertura mostra o que NÃO foi testado; não prova qualidade.** Prefira **branch** a linha nas camadas com regra de negócio; leia o **relatório**, não só o percentual.
- **JaCoCo** (`prepare-agent` + `report` + `check` na fase `verify`; Gradle `jacocoTestReport` + `jacocoTestCoverageVerification` no `check`); **`@{argLine}`** no surefire com a property vazia `<argLine></argLine>`; **JaCoCo recente** para o Java do projeto.
- **Exclua só o que não tem lógica** (`Startup`, `config`, DTOs, gerado), **com motivo registrado**; **nunca** `services`/`domain`.
- **Padrão do pacote: 90% de linha e de branch** (`check` do JaCoCo, depois das exclusões legítimas), **ligado desde o primeiro commit em projeto novo**; em **legado**, **catraca + diff coverage de 90%** e subir o piso **até 90%** (nunca impor de uma vez). Exceções **registradas com motivo**, nunca um piso baixado em silêncio.
- **Gate no PR** (`verify` falha + relatório no PR via Codecov/Sonar); relatório HTML/XML como artefato; `unit + integração` na **mesma** cobertura (ou `merge` se dividir as fases).
- **Mutation testing (PIT)** só em `services`/`domain` com unit tests, **agendado/incremental**, para **achar testes sem assert e limites não testados**; ignore mutantes equivalentes; **cobertura alta com mutation score baixo é teatro**.
- **Código difícil de cobrir = sinal de design**: refatore, não exclua; **erros/limites primeiro**.
- **90% é um piso, não uma prova**: só vale com **asserts de verdade** (+ mutation score nas regras críticas). **Nunca** cobertura como avaliação de pessoas; **nunca** 100% como mandato; **nunca** testes sem assert.
- **Sem Lombok** — deliberado.
