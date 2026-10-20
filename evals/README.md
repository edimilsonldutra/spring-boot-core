# Evals de gatilho

Mede se **a skill certa dispara** para cada pedido, nos grupos de skills que competem entre si (testes, mensageria, arquitetura, autenticação, Swagger, produto, segurança e CI/CD). Roda com `claude plugin eval`.

Cada caso é uma pasta com:
- `prompt.md`: o pedido, como um usuário escreveria, e o limite de turnos e ferramentas;
- `graders/skill-esperada.md`: a skill que deve ser carregada (`tool_used` com `tool: Skill` e regex no nome);
- `graders/nao-<skill>.md` (opcional): uma skill vizinha que **não** deve ser carregada;
- `graders/resposta.md`: o critério da resposta, julgado por LLM.

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

Novo caso: copie uma pasta, troque o pedido e os graders. O sandbox do caso começa vazio, por isso o prompt avisa que o projeto não está aberto; sem esse aviso, o agent pede o repositório (o comportamento certo) e o caso falha por desenho.
