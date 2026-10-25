# Evals de gatilho

Mede se **a skill certa dispara** para cada pedido, nos grupos de skills que competem entre si (testes, mensageria, arquitetura, autenticação, Swagger, produto, segurança e CI/CD). Roda com `claude plugin eval`.

Cada caso é uma pasta com:
- `prompt.md`: o pedido, como um usuário escreveria, e o limite de turnos e ferramentas;
- `graders/skill-esperada.md`: a skill que deve ser carregada (`tool_used` com `tool: Skill` e regex no nome);
- `graders/nao-<skill>.md` (opcional): uma skill vizinha que **não** deve ser carregada;
- `graders/resposta.md` (ou `resposta-<parte>.md`, um por afirmação): o critério da resposta, julgado por LLM.

## Rodar

```bash
# suíte inteira, uma rodada por caso (~US$ 3,50)
claude plugin eval . --runs 1 --ablation none --no-publish --max-cost-usd 6 -j 4

# um caso, três rodadas (para confirmar uma falha antes de mexer em description)
claude plugin eval . --case openapi-como-contrato --runs 3 --ablation none --no-publish
```

- `--ablation none` é necessário: no modo padrão (com e sem o plugin), o grader `tool_used: Skill` só é exibido e não entra na nota.
- Uma rodada é amostra, não prova: **confirme com 3 rodadas** antes de concluir que uma skill não dispara.
- Antes de culpar a description, veja **qual skill disparou** (`--keep-temp` e o `trace.jsonl` em `out/`): uma vizinha que cobre o mesmo assunto pode ser uma resposta correta, e então o caso aceita as duas.
- Os resultados ficam em `evals/results/` (fora do Git).

## Quando rodar

- Ao mudar a `description` de uma skill ou criar uma skill que compete com outra.
- Antes de incorporar ideias novas ao plugin: a suíte mostra se a mudança ajudou ou só aumentou o texto.

## Critério do juiz (`resposta.md`)

O juiz é o Haiku, com o prompt "You are grading the output of a coding agent against a criterion… Respond with exactly one word: PASS or FAIL", três votos e maioria. O voto só conta como PASS se a resposta dele tiver `PASS` e **não** tiver `FAIL` em lugar nenhum.
- **Cobre o que a resposta orienta, não o que o agent executou.** O caso só tem ferramentas de leitura. Um critério como "exporta o PNG e confere antes de entregar" reprova toda resposta honesta que diz "não executei", como aconteceu nas três primeiras versões de `diagrama-aws`. Escreva "orienta exportar e conferir" e diga ao juiz que declarar que não conferiu é aceitável.
- **O aviso de leitura vai em todo critério.** Sem ele, até o juiz do desenho reprova quem escreve "não rodei o script".
- **Uma afirmação por juiz.** Os três votos de uma rodada saem sempre iguais, então uma resposta na fronteira de um critério longo reprova a rodada inteira. Dois critérios curtos (em `diagrama-aws`: o desenho e a conferência) são mais estáveis e mostram qual parte falhou.
- **Só o que o pedido exige.** Exigência que o usuário do caso não pediu vira motivo de reprovação aleatória.
- **Teste antes de gastar rodadas.** Reproduza o juiz com `claude -p --model haiku --system-prompt "You are a strict, terse evaluation judge for coding-agent traces." --tools ""`, usando o prompt acima com o critério e a `evidence` de `evals/results/*/aggregate-result.json`. Peça uma justificativa para ver o motivo. Confira também que uma resposta errada (a skill vizinha, o recurso no lugar errado) continua reprovando.
- **Resposta longa: julgue com o Sonnet.** Em `diagrama-aws` (resposta de ~7.500 caracteres com script), o Haiku reprovou respostas equivalentes ao acaso: 0.72 em 5 rodadas, e o Haiku reproduzido à parte aprovava as mesmas respostas. Com `--judge-model sonnet`, o mesmo caso deu 1.00 em 5 rodadas. Antes de reescrever um critério que oscila, rode de novo com o Sonnet: se passar, o problema é o juiz, não a skill.

Novo caso: copie uma pasta, troque o pedido e os graders. O sandbox do caso começa vazio, por isso o prompt avisa que o projeto não está aberto; sem esse aviso, o agent pede o repositório (o comportamento certo) e o caso falha por desenho.
