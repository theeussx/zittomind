# Segurança

Nunca envie credenciais ou prompts privados em issues. Para reportar um problema,
use o canal privado de security advisories do repositório, se habilitado; caso não
esteja disponível, peça um canal privado ao mantenedor sem publicar a exploração.

Esta versão é uma SDK/CLI local. Não exponha um serviço improvisado na rede.
Políticas e registros YAML são entradas confiáveis do operador. O software não
executa ferramentas recebidas em prompts. Endpoints de API são fixos. Não há
retries ou fallback automático que possam duplicar cobranças ou transferir dados
para outro provedor. Logs internos são mínimos; saídas e erros do aplicativo que
incorpora a SDK precisam de sua própria política de retenção e sanitização.
