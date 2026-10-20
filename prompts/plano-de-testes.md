# Plano de testes e cobertura

**Quando usar:** montar o plano de testes de uma feature, gerar casos de borda, achar testes fracos e lacunas de cobertura, escrever os testes.
**Quem roda:** `squads:qa` (altera somente código de teste).
**Entrega:** plano por camada, casos de borda (limites, segurança/IDOR, concorrência, resiliência, compatibilidade), testes escritos e resultado real da execução.

## Prompt

```text
<Monte o plano de testes | Escreva os testes | Avalie a cobertura> de: <classe, módulo, endpoint ou feature>.

Critérios de aceite: <caminho ou lista | não há>
Threat model: <caminho | não há>
Camadas: <unidade | @WebMvcTest | @DataJpaTest | integração com Testcontainers | contrato | todas>
Riscos que me preocupam: <ex.: concorrência na renovação, permissão entre usuários>
Meta de cobertura: <ex.: 90% de linhas no módulo | padrão do projeto>
Entrega: <só o plano | plano + testes escritos e executados>
```

## Exemplo preenchido

```text
Escreva os testes de: POST /api/v1/loans/{id}/renew.

Critérios de aceite: docs/product/prd-renovacao.md (CA-1 a CA-6)
Threat model: docs/security/threat-model-renovacao.md
Camadas: @WebMvcTest, service com Mockito e integração com Testcontainers (MySQL)
Riscos que me preocupam: duas renovações simultâneas; leitor renovando empréstimo de outro
Meta de cobertura: padrão do projeto
Entrega: plano + testes escritos e executados
```

## Dicas

- Cada critério Given/When/Then e cada ameaça mitigada vira pelo menos um teste.
- `@Disabled` ou assert afrouxado para "passar" é sinal vermelho — o `qa` relata em vez de esconder.
