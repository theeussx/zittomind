# Fase 3 — contratos de operação

O ledger SQLite armazena somente metadados de uso e decisões. Reservas usam
BEGIN IMMEDIATE, inclusive entre conexões/processos. Falhas com cobrança incerta
mantêm a reserva; não há liberação silenciosa após restart. Valores calculados
usam tokens reportados e preços configurados, nunca são chamados de faturas.

Escopos de orçamento: projeto, sessão, modelo, provedor, dia UTC e mês UTC.
Todos são isolados pelo projeto; limite por requisição também é aplicado antes
da seleção. O identificador de sessão é obrigatório quando houver limite de sessão.

Cache de respostas é opt-in, em memória, com chave hash da requisição completa,
modelo e política; classificação e metadados têm caches separados. TTL e limite
em número de itens evitam crescimento sem limite. Reiniciar esvazia o cache.

Fallback exige política explícita, não altera modelo fixado e não repete streams.
Tentativas com cobrança incerta continuam contabilizadas conservadoramente.
Shadow seleciona alternativa sem segunda geração: executa o modelo solicitado.
