# Fase 4 — RIS, avaliações e políticas

RIS nunca substitui filtros obrigatórios. Usa avaliações explícitas por projeto,
modelo e categoria; HTTP 200 alimenta confiabilidade, não qualidade. Sem avaliações,
a ordem mantém prioridade/custo configurados e marca os modelos como subavaliados.

Fórmula: média ponderada de qualidade × confiança, custo normalizado
1/(1+100*custo), confiabilidade observada e latência normalizada 1/(1+segundos).
Confiança = n/(n+5), um indicador de suporte de amostra, não uma probabilidade
calibrada. Qualidade ausente é null; seu componente é zero. Pesos por perfil:
economy (.3,.5,.1,.1), balanced (.5,.2,.2,.1), performance (.75,.05,.15,.05).
`profiles` permite mapas personalizados; `min_confidence` define o piso da política.
`ris_enabled: false` desliga a ordenação RIS. Empates usam prioridade e ID.

`policies feedback MODEL QUALITY --category ... --project ...` registra avaliação
explicitamente autorizada. `policies import arquivo.json` preserva uma versão
imutável de `{"weights":{"quality":0.7,"cost":0.3}}`. `policies list` mostra histórico;
`policies rollback VERSION` seleciona uma versão (também usada para ativação).
`policies simulate VERSION --prompt ...` simula sem ativar ou gerar respostas.

`policies learn` exige cinco avaliações e propõe aumento limitado a 0.1 no peso
normalizado de qualidade, sem ativação automática. Não treina sobre prompts.
A versão ativa só muda a execução com `adaptive_enabled: true` e
`observation_only: false`; observação é o padrão. Políticas são do operador e
compartilham o registro de versões; avaliações são isoladas por projeto.

`benchmark --config config/offline-example.yaml` mede classificação e overhead,
comparando cinco estratégias: fixo econômico, fixo avançado, regras, híbrido local
e adaptativo. Os casos incluem texto curto difícil, longo simples, código, histórico,
ferramentas, saída estruturada e streaming. Casos são agendados concorrentemente.
Sem chamadas externas: qualidade de geração, latência do provedor e economia líquida
são null. O modo híbrido offline exercita apenas sua etapa local; não é uma medida
da qualidade de um classificador externo. Testes HTTP cobrem os protocolos reais
com fixtures. Nenhum desses resultados substitui avaliação com modelos reais.
