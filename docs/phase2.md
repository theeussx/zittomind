# Proxy HTTP — Fase 2

`ZITTOMIND_PROXY_TOKEN=... zittomind serve` inicia em 127.0.0.1:8787.
Todas as rotas exigem `Authorization: Bearer ...`; sem token não inicia.
O operador seleciona o projeto com `--project`; o cliente não pode trocar sua política.
Sem CORS liberado, docs remotas ou access logs. Corpo limitado a 500 KB mesmo sem
Content-Length. Validação não ecoa conteúdo recebido.

Rotas: GET /health, GET /v1/models e POST /v1/chat/completions.
Contrato: mensagens textuais system/user/assistant, última mensagem user, model
(auto ou ID fixado), max_tokens e stream. Outros campos são recusados com 422.
Configure `streaming: true` apenas em modelos com suporte verificado.

SSE transmite eventos reais do OpenAI Chat Completions ou Anthropic Messages.
Erro antes do primeiro evento retorna 502; erro parcial gera evento error sem
[DONE], sem retry. Cancelamento fecha o stream upstream. Esta compatibilidade
textual não implica suporte a todas as APIs OpenAI, Codex CLI ou Claude Code.

Referências: https://fastapi.tiangolo.com/advanced/custom-response/
https://platform.claude.com/docs/en/build-with-claude/streaming
