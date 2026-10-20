# Decisão de arquitetura

**Quando usar:** escolher entre opções (monólito modular × microsserviços, broker, banco, runtime, cache) ou registrar uma decisão como ADR.
**Quem roda:** `squads:architect`. Se faltarem requisitos, use o `squads:orchestrator`, que chama o `product-manager` antes.
**Entrega:** recomendação no topo, alternativas com trade-offs, riscos, custos, como reverter e o ADR (gravado com sua confirmação).

## Prompt

```text
Preciso decidir: <a pergunta, ex.: "Kafka ou SQS para os eventos de pedido?">

Contexto: <sistema atual, o que motivou a decisão>
Opções consideradas: <lista | sugira>
Requisitos de qualidade:
- Carga e crescimento: <números>
- Latência: <p95/p99>
- Disponibilidade e RTO/RPO: <números>
- Consistência: <forte | eventual aceitável em quê>
- Segurança e LGPD: <dados envolvidos, região>
- Custo: <orçamento ou teto mensal>
Restrições: <nuvem adotada, tecnologia obrigatória, tamanho e experiência da equipe, prazo>
Saída: <recomendação | ADR em docs/adr/ | design doc em docs/design/>
```

## Exemplo preenchido

```text
Preciso decidir: Kafka (MSK) ou SNS+SQS para publicar eventos de empréstimo para 3 consumidores.

Contexto: monólito modular na AWS (EKS + RDS); notificações e relatórios vão virar serviços separados.
Opções consideradas: MSK, SNS+SQS, EventBridge.
Requisitos de qualidade:
- Carga e crescimento: 30 eventos/s, pico 200/s, crescimento de 2x ao ano
- Latência: entrega em até 5 s
- Disponibilidade e RTO/RPO: 99,9%, RPO 0 para eventos
- Consistência: eventual aceitável; ordem por empréstimo
- Segurança e LGPD: eventos com ID do leitor, região sa-east-1
- Custo: até US$ 300/mês
Restrições: equipe de 4 pessoas sem experiência em Kafka.
Saída: ADR em docs/adr/
```

## Dicas

- Sem números, o `architect` assume e declara as premissas — confira-as antes de aprovar o ADR.
- Simplicidade é o padrão: peça explicitamente a opção mais simples que atende e o gatilho para revisitar a decisão.
