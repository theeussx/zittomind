# Fase 5 — distribuição e integrações

Ollama usa exclusivamente http://127.0.0.1:11434/api/chat, texto e streaming NDJSON.
Antes de enviar o prompt, consulta `/api/tags` e exige que o modelo exato esteja
instalado localmente, com formato GGUF e sem metadados de modelo remoto. Modelos
ausentes, cloud ou respostas de inventário inválidas falham sem enviar o prompt.
Configure também `OLLAMA_NO_CLOUD=1` no serviço Ollama para desativar o recurso
cloud no daemon; a verificação do inventário não elimina alterações concorrentes
na configuração do daemon. ZittoMind não baixa modelos. Instale um modelo por
conta própria e registre limites verificados. Política strict/local-only aceita
somente Ollama.
Custos locais não são presumidos: configure preços zero apenas para representar
custo de API zero, não custo de hardware/energia.

Dashboard em /dashboard serve uma página estática; métricas exigem token digitado
na página, mantido somente na memória. Não há armazenamento de credenciais no
navegador, query string ou analytics. Escopo é o projeto configurado no proxy.

SDK Node em sdk/node, sem dependências, Node 20+:
```js
import { ZittoMind } from './sdk/node/index.js';
const client = new ZittoMind({ token: process.env.ZITTOMIND_PROXY_TOKEN });
console.log(await client.chat([{role: 'user', content: 'Olá'}]));
for await (const event of client.stream([{role: 'user', content: 'Olá'}])) {
  console.log(event);
}
```
Use AbortSignal para cancelamento. Fechar o iterador cancela a leitura HTTP.
Endpoints remotos exigem HTTPS; redirects são recusados.

Docker (opcional):
```sh
docker build -t zittomind:1.0 .
docker run --rm -p 127.0.0.1:8787:8787 \
  --env-file .env -v "$PWD/zittomind.yaml:/config/zittomind.yaml:ro" zittomind:1.0
```
O token é obrigatório; o container executa como usuário sem privilégios. Para
persistência, configure state_path em um volume gravável pelo UID 10001. O Ollama
loopback dentro do container exige compartilhar rede host no Linux; não troque
isso por destinos remotos arbitrários. O daemon Docker não estava disponível na
validação local; a construção da imagem fica coberta no workflow CI.

Compatibilidade deliberadamente limitada: Chat Completions textual, não Responses
API, Messages público Anthropic, tool calling ou multimodal. Codex CLI e Claude
Code não são anunciados como compatíveis. Credenciais de API são distintas das
assinaturas desses produtos. A API aceita somente o contrato documentado,
recusando parâmetros extras; isso evita descartar ferramentas/histórico em silêncio.

Referências oficiais: https://github.com/ollama/ollama/blob/main/docs/api.md
https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create
https://platform.claude.com/docs/en/api/http/messages
