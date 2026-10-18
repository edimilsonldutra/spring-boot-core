---
name: refactoring
description: Refatoração segura de Java/Spring Boot — refatorar × mudar comportamento, quando não refatorar, rede de segurança com characterization tests, passos pequenos e verdes, catálogo de smells e refatorações, Parallel Change, Branch by Abstraction, Strangler Fig, expand → contract e revisão do PR. Use quando melhorar a estrutura de um código sem mudar o comportamento.
---

Antes de aplicar este pattern, leia também [`../code-organization/SKILL.md`](../code-organization/SKILL.md) e [`../code-style/SKILL.md`](../code-style/SKILL.md) (o estado-alvo do código), [`../testing/SKILL.md`](../testing/SKILL.md), [`../test-patterns/SKILL.md`](../test-patterns/SKILL.md) (characterization tests), [`../test-coverage/SKILL.md`](../test-coverage/SKILL.md) (cobertura do trecho e mutation score), [`../repository-understanding/SKILL.md`](../repository-understanding/SKILL.md) (achar hotspots e entender antes de mexer) e [`../technical-product-management/SKILL.md`](../technical-product-management/SKILL.md) (dívida técnica como decisão de produto).

# Refatoração

**Refatorar é mudar a estrutura interna do código sem mudar o seu comportamento observável.** O objetivo é torná-lo **mais fácil de entender e de modificar** — não mais "bonito". Se o comportamento muda, **não é refatoração**: é feature ou correção de bug, e deve ser feita **separadamente**.

## As duas "chapéus" (Kent Beck)

Em qualquer momento você usa **um** chapéu:
- **Chapéu de feature/bug:** muda o comportamento; escreve **testes novos**; os testes existentes **podem** mudar.
- **Chapéu de refatoração:** **não** muda o comportamento; **não** adiciona testes de comportamento novo (só para proteger); os testes existentes **continuam passando sem alteração**.
**Não misture** na mesma mudança (e, idealmente, nem no mesmo commit/PR): quando algo quebra, você não sabe se foi a refatoração ou a mudança de comportamento. *"Faça a mudança ser fácil (refatore), depois faça a mudança fácil."*

## 1. Quando refatorar — e quando NÃO

| Refatore quando | **Não** refatore quando |
|---|---|
| **Antes de uma feature** que o código atual torna difícil (prepare o terreno) | **Não há testes** e você não vai criá-los antes (veja a seção 2) |
| **Regra dos três**: a terceira vez que você duplica algo, extraia | O código **funciona e ninguém precisa alterá-lo** (código estável e "feio" tem custo zero) |
| Ao **corrigir um bug** em código confuso (deixe-o melhor do que encontrou) | O comportamento atual **não é compreendido** (primeiro entenda — `repository-understanding`; escreva characterization tests) |
| Código **hotspot** (muda muito **e** é complexo — onde está o custo) | Você está **perto de um prazo/deploy** crítico e a refatoração é **opcional** |
| A **dívida técnica** está medida e **priorizada** (`prioritization`) | A vontade é **reescrever do zero** (quase sempre um erro — seção 6) |
| Para **remover código morto**/complexidade acidental | Para **"padronizar por gosto"** ou aplicar um design pattern **sem problema real** |

**Refatore o que você está prestes a mudar**, não o repositório inteiro: refatoração **a serviço de uma mudança** tem retorno claro; refatoração "geral" sem objetivo é desperdício e risco.

## 2. A rede de segurança vem PRIMEIRO

Refatorar **sem testes** é "reescrever e torcer". Antes de tocar:
1. **Há testes que cobrem o comportamento da área?** Veja a **cobertura do trecho** (`test-coverage`: relatório do JaCoCo, **ramos** descobertos) e a **qualidade** (os testes falhariam se o código quebrasse? — mutation check/PIT).
2. **Se não há**, escreva **characterization tests** (`test-patterns`, seção 8): registre **o que o código faz hoje** (entradas → saídas reais, incluindo erros), mesmo que pareça errado — eles são a rede de proteção. **Depois** de refatorar, substitua por testes que descrevem o comportamento **correto** e trate os bugs que apareceram (como mudança de comportamento, **separada**).
3. **Rode os testes antes** de começar (devem estar **verdes**; se não estão, você não tem linha de base).
4. **Mantenha os testes rápidos** (você os roda a cada passo): unit tests sem Spring; integração só onde necessário (`integration-testing`).
5. Para áreas de **risco alto**, aumente a proteção: **testes de contrato** (`contract-testing`) se há consumidores; **ArchUnit** para não violar fronteiras (`ddd-hexagonal`); um **teste de integração** do fluxo crítico.
O padrão do pacote exige **90% de linha e branch** (`test-coverage`): código que você refatora **precisa estar dentro dele** — ou ser trazido para dentro **antes**.

## 3. O ciclo: passos pequenos, verdes o tempo todo

```
verde → (1 passo pequeno) → rodar testes → verde → commit → próximo passo
```
- **Um passo = uma transformação mecânica** (renomear, extrair método, mover). Se um passo exige "pensar muito", é grande demais — divida.
- **Rode os testes a cada passo** (ou a cada poucos). Vermelho? **Desfaça o último passo** (`git restore`/`git revert` do commit pequeno) em vez de "consertar para a frente".
- **Prefira as refatorações automáticas da IDE** (IntelliJ: *Rename, Extract Method/Variable/Constant, Inline, Move, Change Signature*): são **mais seguras** que edição manual (atualizam todas as referências, inclusive em testes). O **compilador** é parte da rede: use tipos para que o erro apareça na compilação.
- **Commits pequenos, com mensagem `refactor:`** (e separados dos de `feat:`/`fix:`) — o histórico fica **revisável** commit a commit e **reversível**.
- **Escopo e critério de parada definidos antes** ("extrair a regra de multa do `LoanService` para o aggregate `Loan`; parar quando `LoanService` tiver só orquestração"). Sem critério de parada, a refatoração não termina.
- **Não "aproveite para" mudar comportamento, formatar o arquivo inteiro ou renomear tudo.**

## 4. Catálogo de smells → refatoração (Java/Spring)

| Smell (cheiro) | Sinal | Refatoração |
|---|---|---|
| **Long Method** | Método com várias responsabilidades, > ~20–30 linhas, níveis de abstração misturados | **Extract Method**; nomes que explicam o "porquê" (sem comentários — o pacote não os usa) |
| **God Service / Large Class** | `*Service` com 20 métodos e 10 dependências; muda por vários motivos | **Extract Class**; **mover regra para o domínio**; separar por caso de uso |
| **Anemic Domain Model** | Entity só com getters/setters; toda regra em `*Service` | **Move Method** para a entity/aggregate; setters viram métodos de negócio (`ddd-hexagonal`) |
| **Feature Envy** | Método que usa mais dados de **outra** classe que da sua | **Move Method** para a classe dos dados |
| **Primitive Obsession** | `String email`, `double price`, `Long customerId/orderId` intercambiáveis | **Replace Primitive with Value Object** (`record Email`, `Money`, `OrderId`) |
| **Data Clumps / Long Parameter List** | Os mesmos 3–4 parâmetros andam juntos; assinatura com 6+ | **Introduce Parameter Object** (record) |
| **Duplicated Code** | Mesma lógica em vários lugares | **Extract Method/Class**, **Pull Up**; regra dos três |
| **Shotgun Surgery** | Uma mudança de negócio exige editar 8 arquivos | **Move/Inline** para agrupar o que muda junto |
| **Divergent Change** | Uma classe muda por razões não relacionadas | **Extract Class** (uma razão para mudar) |
| **Switch / if-else em cascata por tipo** | `if (type == X) … else if (type == Y)` repetido | **Replace Conditional with Polymorphism**, ou `sealed interface` + `switch` com pattern matching exaustivo (`java-modern-features`) |
| **Nested Conditionals** | `if` dentro de `if` dentro de `if` | **Guard clauses** (`if (x == null) throw …` em uma linha — `code-style`), **Extract Method** |
| **Magic Numbers/Strings** | `if (days > 14)` | **Extract Constant** / configuração (`@ConfigurationProperties`) / VO de política |
| **Tempo/aleatoriedade/estático** | `LocalDate.now()`, `UUID.randomUUID()`, singletons estáticos dentro da lógica | **Injetar `Clock`/`Supplier`**; **Replace Static with Dependency** (testável) |
| **Feature Envy do controller** | Controller com regra de negócio, `if`s e queries | **Move** para o service/domínio; controller só HTTP |
| **Entity exposta** | `@Entity` retornada pelo controller | **Introduce DTO** + mapper (`code-organization`) |
| **N+1 / lazy em loop** | `for (…) repository.findById(…)` | **Replace Loop with Query** (`JOIN FETCH`, `findAllById`, projection — `spring-data-jpa`) |
| **Exceptions engolidas / genéricas** | `catch (Exception e) {}`, `throw new RuntimeException` | **Replace with domain exception** + handler (`exception-handling`) |
| **Middle Man / Speculative Generality** | Classes que só delegam; interfaces com **uma** implementação "por precaução"; flags nunca usadas | **Inline Class/Method**; **remover** a abstração sem uso |
| **Dead Code** | Métodos/classes/flags sem referência | **Delete** (o Git guarda o histórico) — **depois** de confirmar que ninguém usa (reflection, Spring wiring, JSON, SQL) |
| **Comentário como desodorante** | Comentário explicando código confuso | **Rename**/**Extract Method** até o código se explicar |
| **Estado mutável compartilhado** | Beans singleton com campos mutáveis | **Imutabilidade** (records, `final`), estado no escopo da chamada |
| **Mensagens de erro/regra espalhadas** | Strings de mensagem duplicadas | **Centralizar** na exception/VO |

### Exemplos curtos

**Extract Method + guard clauses**
```java
// antes
public BookDTO create(BookDTO book) {
    if (book != null) {
        if (book.getTitle() != null && !book.getTitle().isBlank()) {
            logger.info("Creating one book!");
            var entity = parseObject(book, Book.class);
            return parseObject(repository.save(entity), BookDTO.class);
        } else {
            throw new BadRequestException("title required");
        }
    } else {
        throw new RequiredObjectIsNullException();
    }
}
```
```java
// depois
public BookDTO create(BookDTO book) {
    if (book == null) throw new RequiredObjectIsNullException();
    requireTitle(book);
    logger.info("Creating one book!");
    return parseObject(repository.save(parseObject(book, Book.class)), BookDTO.class);
}

private static void requireTitle(BookDTO book) {
    if (book.getTitle() == null || book.getTitle().isBlank()) throw new BadRequestException("title required");
}
```

**Replace Primitive with Value Object (record)**
```java
public record Money(BigDecimal amount, String currency) {

    public Money {
        Objects.requireNonNull(amount);
        if (amount.signum() < 0) throw new IllegalArgumentException("amount must not be negative");
    }
}
```
`double price` espalhado vira `Money`: a validação mora **num só lugar** e a troca é guiada pelo **compilador** (cada uso quebra até ser ajustado).

**Move behavior para o aggregate (anêmico → rico)**
```java
// antes: no service
if (loan.getStatus() == LoanStatus.ACTIVE) { loan.setStatus(LoanStatus.RETURNED); loan.setReturnedAt(now); }

// depois: no aggregate
loan.returnBook(clock);
```
**Conditional → sealed + pattern switch**
```java
return switch (result) {
    case Approved a -> "Approved: " + a.authorizationCode();
    case Declined d -> "Declined: " + d.reason();
    case PendingReview p -> "Under review #" + p.caseId();
};
```
Adicionar um tipo novo **quebra a compilação** até ser tratado (`java-modern-features`).

**Injetar `Clock`**
```java
public Fee lateFee(Loan loan, Clock clock) {
    var overdueDays = ChronoUnit.DAYS.between(loan.dueDate(), LocalDate.now(clock));
    return overdueDays <= 0 ? Fee.none() : Fee.perDay(overdueDays);
}
```
Testável com `Clock.fixed(...)`; **sem** `LocalDate.now()` escondido (`test-patterns`).

## 5. Refatorações específicas de Spring/Java

| Refatoração | Cuidado |
|---|---|
| **Mover `@Transactional`** para a fronteira certa (service/use case) | Conferir que a **chamada interna** (`this.metodo()`) não ignora o proxy (`spring-data-jpa`) |
| **Quebrar dependência circular** entre beans | **Evento** (`@ApplicationModuleListener`), extrair interface/serviço comum — **não** `@Lazy` como remendo |
| **`RestTemplate`/Feign → `RestClient`/`@HttpExchange`** | Manter **timeouts** e o tratamento de erro (`service-communication`, `resilience`) |
| **`java.util.Date` → `java.time`** | **Muda o contrato JSON** (`"2017-11-29"`): é mudança de comportamento observável (`spring-data-jpa`) |
| **Introduzir DTO/mapper** | Sem alterar o JSON público (teste de contrato) |
| **Reorganizar packages** (flat-by-layer → módulos) | Mover **sem** alterar código; atualizar `@ComponentScan`/imports; Modulith `verify()` (`modular-monolith`) |
| **Extrair módulo/serviço** | **Strangler Fig** (seção 6); contratos (`contract-testing`) |
| **Upgrade de versão** (Java, Spring Boot, Jakarta, Jackson 3) | Uma versão major **por vez**; **OpenRewrite** (`rewrite-maven-plugin` com recipes do Spring) automatiza migrações mecânicas — **revise o diff**; confirme as recipes na documentação atual |
| **Trocar field injection por constructor injection** | **Só** se a preferência do projeto (`## Project preferences`) for constructor — o padrão do pacote é field; **não** mude por gosto |
| **Remover Lombok** (se o repositório o usa; o pacote o proíbe) | **Delombok** (ferramenta/IDE gera os getters/setters explícitos) e remova a dependência — mecânico, mas **grande**: faça por módulo |

Cuidado com o que o **compilador não vê**: **reflexão**, **Spring wiring por nome**, **SpEL**, **JPQL/queries nativas**, **JSON (nomes de campo)**, **`application.yml`**, **testes que usam strings**. Renomear classe/campo exige **buscar nesses textos** (`Grep`) — e os **testes de integração** pegam o que escapa.

## 6. Mudanças grandes: sem big bang

Refatoração que **não cabe em passos pequenos verdes** (API pública, banco, módulo inteiro) usa técnicas de **transição**:
- **Parallel Change (expand → migrate → contract):** (1) **expanda**: adicione a nova forma **ao lado** da antiga; (2) **migre** os usos, um a um (cada passo verde e implantável); (3) **contraia**: remova a antiga **quando ninguém mais a usa**. É o mesmo princípio de `flyway-migrations` e `release-management` (deprecação).
- **Branch by Abstraction:** introduza uma **interface** na frente da implementação antiga, **construa a nova** atrás da mesma interface, **troque por flag/configuração** (`release-management`), valide e **remova a antiga**. Tudo no **trunk**, sem branch longa.
- **Strangler Fig** (`microservices`): substitua **uma capacidade por vez**, roteando gradualmente, mantendo o sistema funcionando.
- **Banco de dados:** **nunca** renomear/remover coluna em um passo — **expand → contract** com migrations compatíveis com a versão anterior (`flyway-migrations`).
- **Comparação em sombra (*shadow/scientist*):** rode o **antigo e o novo** com a **mesma entrada**, **sirva o antigo** e **compare** os resultados (log de divergências) antes de trocar — ótimo para regras de cálculo críticas.
- **Evite a reescrita total ("rewrite")**: costuma levar mais tempo que o previsto, **perde regras de negócio escondidas** no código velho e entrega **zero valor** até o fim. Prefira **estrangular**.
- **Entregue incrementalmente**: cada passo **implantável** (atrás de flag se arriscado), para **reverter** barato.

## 7. Prioridade e orçamento: refatorar o que importa

- **Hotspots** (`repository-understanding`, seção 9): **alto churn × alta complexidade**. Código estável, mesmo feio, **não é prioridade**. Meça: `git log --since=6.months --name-only … | sort | uniq -c | sort -rn`.
- **Dívida técnica é decisão de produto** (`technical-product-management`, `prioritization`): quantifique o **custo atual (juros)** — tempo de ciclo, bugs, incidentes na área — e o custo de pagar; **reserve capacidade** (ex.: parte da sprint) em vez de "tempo roubado"; **refatore no fluxo da feature** quando possível ("deixe a trilha mais limpa do que encontrou").
- **Refatoração tem item no backlog**, com **escopo, critério de parada, valor justificado** (`user-stories`: habilitadora) e **dono** — não "melhorar o módulo X" sem fim.
- **Medidas antes/depois** (use poucas e honestas): complexidade ciclomática e tamanho dos hotspots, **cobertura e mutation score** do trecho, **tempo de ciclo** das mudanças naquela área, nº de bugs/incidentes. **Meta é facilitar mudança**, não um número.

## 8. Revisar um PR de refatoração (`code-reviewer`)

- **É só refatoração?** Há **mudança de comportamento escondida** (regra, mensagem, ordem de operações, transação, JSON, SQL)? Se sim → **separar**.
- **Os testes existentes passaram sem alteração?** Teste **modificado** em PR de refatoração é **bandeira vermelha** (o comportamento mudou, ou o teste era frágil — justifique).
- **Commit a commit**: cada commit é um passo pequeno, com mensagem `refactor:`; mover/renomear em commit **separado** das mudanças de conteúdo (o diff fica legível).
- **Cobertura e mutation do trecho** não caíram (`test-coverage`); a **cobertura** ≥ 90%.
- **Riscos que o compilador não vê** (reflexão, wiring, JPQL, JSON) foram checados?
- **Escopo**: respeitou o objetivo e o critério de parada, ou virou "aproveitei para…"?
- **Compatibilidade**: API pública/contrato/banco continuam **compatíveis com a versão anterior** (`contract-testing`, `flyway-migrations`)?
- **O resultado é mais simples?** Se o código ficou **mais abstrato sem resolver um problema real** (interfaces, factories, camadas), é **over-engineering**, não melhoria.

## 9. Definition of Done de uma refatoração

- [ ] **Comportamento observável inalterado** (evidência: testes existentes verdes **sem alteração**; contrato/JSON/SQL idênticos).
- [ ] **Rede de segurança** antes (cobertura/characterization) e **cobertura do trecho dentro do padrão** (90%).
- [ ] **Commits pequenos** `refactor:`, separados de feature/fix.
- [ ] **Critério de parada** atingido e **escopo respeitado**.
- [ ] **Sem regressão de desempenho** nos caminhos críticos (quando relevante — `jvm-performance`).
- [ ] **Código morto removido** com confirmação de que não é usado (inclusive por reflexão/config).
- [ ] **PR revisado** (`code-reviewer`); **documentação** atualizada (`CLAUDE.md` se comandos/estrutura mudaram — `project-claude-md`; ADR se a estrutura mudou — `architect`).
- [ ] Se arriscada: **implantada atrás de flag/gradualmente**, com rollback (`release-management`).

## 10. Anti-patterns

- **Refatorar sem testes** (ou **apagar/afrouxar testes** para "passar").
- **Misturar refatoração com feature/bug** no mesmo commit/PR.
- **"Refatoração geral"** sem objetivo nem critério de parada; **big-bang rewrite**.
- **Refatorar código estável** que ninguém altera; **padronizar por gosto**.
- **Design pattern sem problema** (factory/strategy/abstração "para o futuro") — over-engineering.
- **Passos grandes** em vez de pequenos e verdes; **commits gigantes** ilegíveis.
- **Renomear/mover sem checar reflexão, wiring, JPQL e JSON.**
- **Mudar API pública/contrato/banco de uma vez** (sem expand → contract).
- **Remover "código morto"** sem investigar (*Chesterton's fence*).
- **Ignorar a cobertura/qualidade** do trecho refatorado; **refatorar às pressas perto de um deploy**.
- **Esconder dívida** (nunca priorizar) **ou** transformar toda sprint em refatoração (sem entrega de valor).

---

## Regras principais

- **Refatorar = mudar a estrutura, não o comportamento.** **Duas chapéus, nunca juntas**: refatoração, feature e bug em **commits/PRs separados**.
- **Rede de segurança primeiro**: testes verdes antes, **characterization tests** se não houver, **cobertura do trecho dentro dos 90%** (e mutation score nas regras críticas).
- **Passos pequenos, verdes a cada passo**, commits `refactor:`; **vermelho → desfaça o último passo**; prefira **refatorações automáticas da IDE** e o **compilador** como rede; **escopo e critério de parada** definidos antes.
- **Use o catálogo de smells** (Long Method, God Service, Anemic Model, Primitive Obsession, N+1, switch por tipo…) e **a refatoração correspondente**; **records/`Clock`/sealed + pattern switch** quando couber.
- **Cuidado com o que o compilador não vê** (reflexão, wiring, SpEL, JPQL, JSON, YAML): **busque** nesses textos e confirme com testes de integração.
- **Mudanças grandes sem big bang**: **Parallel Change (expand → contract)**, Branch by Abstraction, Strangler Fig, banco **expand → contract**, comparação em sombra; **evite reescrever do zero**.
- **Refatore o que vai mudar** e os **hotspots** (churn × complexidade); **dívida técnica é decisão de produto** (capacidade reservada, item com valor e critério de parada).
- **No PR de refatoração**: nenhum comportamento escondido, **testes existentes sem alteração**, cobertura mantida, escopo respeitado; **mais abstrato sem problema real = over-engineering**.
- **Field injection é o padrão do pacote**: só troque por constructor se a **preferência do projeto** disser; **Lombok** (proibido) sai por **delombok**, por módulo.
- **Sem Lombok** — deliberado.
