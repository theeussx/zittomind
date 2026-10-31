# ZittoMind 1.0

Infraestrutura local-first de roteamento LLM para Python 3.11+ e Linux. CLI,
SDK Python, proxy HTTP autenticado, Ollama local, métricas e SDK Node. Implementa
as cinco etapas do [PROMONT](PROMONT.md), com o alcance e as limitações abaixo.
O nome público é `zittomind` / `ZittoMind`; `routemind` não é um alias instalado.

## Começar sem chamadas pagas

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
zittomind classify 'Explique chmod' --json
zittomind ask 'Explique chmod' --config config/offline-example.yaml --dry-run --json
zittomind benchmark --config config/offline-example.yaml
python examples/dry_run.py
```

O exemplo offline usa um modelo fictício exclusivamente para simulação.
`zittomind init` cria `zittomind.yaml` sem sobrescrever arquivo existente e configura
SQLite em `.zittomind/state.sqlite3`. Sem catálogo, geração é recusada. Na SDK,
configuração sem state_path usa memória; configure um arquivo para persistência.

Cadastre IDs, limites e preços verificados dos modelos reais. Nenhum modelo remoto
é ativado por padrão. Preços são por milhão de tokens na mesma moeda do orçamento.
Limites desconhecidos bloqueiam seleção; preços desconhecidos bloqueiam quando há
limites de orçamento. Tier e prioridade são declarações do operador, não benchmarks.

```yaml
state_path: .zittomind/state.sqlite3
models:
  - id: SUBSTITUA_POR_MODELO_LOCAL_INSTALADO
    provider: ollama
    context_window: 8192
    max_output_tokens: 2048
    streaming: true
    tier: MEDIUM
    input_per_million: 0
    output_per_million: 0
projects:
  default:
    privacy: strict
    allowed_providers: [ollama]
    profile: balanced
    budgets: {day: 1.0, month: 10.0}
```

Esse YAML é um modelo de configuração, não uma recomendação de capacidades.
Os zeros representam somente custo de API configurado. Confira os limites do modelo.
Para OpenAI/Anthropic, configure `provider`, limites, preços, privacidade standard
e exporte `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`. Isso usa APIs pagas; assinatura de
chat não substitui credencial de API. `.env` não é carregado automaticamente.

## CLI e SDK

Comandos: `init`, `ask`, `classify`, `serve`, `doctor`, `models`, `config`, `stats`,
`benchmark`, `policies`, `cache`, `projects`. Consulte `--help` para opções.
`ask` oferece modelo/provedor/projeto/perfil fixados, reasoning, complexity,
dry-run, local-only, no-cache, shadow e session. Para exportar configuração sem
credenciais, use `zittomind config > export.json`; o carregador YAML aceita JSON.

```python
import asyncio
from zittomind import ZittoMind


async def main():
    router = ZittoMind()  # lê zittomind.yaml
    try:
        result = await router.route("Explique chmod", dry_run=True)
        print(result.decision.model_dump_json(indent=2))
        # async for chunk in router.stream('Explique chmod'): print(chunk)
    finally:
        router.close()


asyncio.run(main())
```

Histórico textual é passado em `messages` (system/user/assistant). Contexto, limites,
privacidade e orçamento são filtrados antes da pontuação. Pins por requisição,
projeto e categoria são respeitados; sessões mantêm o modelo durante a vida da SDK.
Não há troca de provedor em fallback sem autorização explícita na política.

## Proxy e dashboard

```sh
export ZITTOMIND_PROXY_TOKEN='defina-um-token-forte'
zittomind serve --config zittomind.yaml
curl http://127.0.0.1:8787/v1/models \
  -H "Authorization: Bearer $ZITTOMIND_PROXY_TOKEN"
```

Padrão: 127.0.0.1:8787. Projeto é escolhido pelo operador com `serve --project`;
o cliente não pode trocar de política. Rotas autenticadas: `/health`, `/v1/models`,
`/v1/chat/completions`, `/metrics`, DELETE `/cache`. `/dashboard` é apenas a página
estática; os dados exigem token. Sem CORS liberado ou access logs.

O proxy suporta o subconjunto textual Chat Completions: `model` (`auto` ou ID),
`messages`, `max_tokens`, `stream`. Campos extras são rejeitados. SSE transmite
deltas reais; erros parciais não reiniciam geração nem emitem sucesso `[DONE]`.

## Operação, custos e aprendizado

- Reservas SQLite atômicas por requisição, sessão, projeto, modelo, provedor, dia e
  mês UTC. Falhas incertas mantêm reservas. Tokens reportados e preços configurados
  geram custos calculados, não faturas. Estimativas usam limite conservador por bytes.
- Cache TTL limitado em memória, isolado por projeto e contexto. Respostas só com
  `response_cache: true`. `--no-cache` desabilita uso naquela requisição.
- Timeout, concorrência, rate limit, circuit breaker. `safe_retries` habilita até
  três retries somente para HTTP 429, com backoff/jitter. Fallback é opt-in.
- `--shadow --model ID` calcula alternativa, mas gera apenas no modelo original.
- RIS combina avaliações explícitas por categoria, confiabilidade, custo e latência.
  Modelos sem avaliações têm incerteza explícita. Perfis personalizados em `profiles`.
- Feedback, propostas limitadas de atualização, versões imutáveis, observação,
  simulação e rollback via `policies`. Adaptação é desabilitada por padrão.
- `stats` exporta agregados JSON; `stats --csv` exporta eventos sanitizados. Retenção
  de eventos configurável, 30 dias por padrão; ledger de orçamento é conservado.

Reasoning é declarado por modelo (`none`, `openai_effort`, `anthropic_budget`,
`anthropic_adaptive`), com `supported_efforts` e `thinking_budgets` explícitos.
Parâmetros incompatíveis são recusados; não se presume equivalência entre provedores.

Classificação externa requer consentimento na requisição e na política, um modelo
classificador configurado e orçamento. Envia somente atributos derivados, nunca
texto original; isso limita sua capacidade semântica. `--external-classification`
também autoriza essa chamada no dry-run. Sem a opção, dry-run não faz chamadas pagas.

## Validação e limites

```sh
python -m pytest
ruff check .
ruff format --check .
mypy src/
node --test sdk/node/index.test.js
python -m build
```

Testes usam HTTP simulado, sem APIs pagas. Benchmark offline mede classificação e
custo de processamento e compara cinco políticas; não mede qualidade de geração,
latência real de provedores ou economia líquida. Confiança heurística não é uma
probabilidade calibrada. Não foram feitos benchmarks pagos nem validação de modelos
reais. Docker não foi executado localmente porque o daemon estava indisponível.

Ferramentas, multimodalidade, saída estruturada e APIs completas de Responses ou
Messages públicos ainda são recusadas. Não há compatibilidade declarada com Codex
CLI/Claude Code nem aprendizado neural. Pins de sessão e caches são locais ao
processo. O dashboard é local e leve, não um serviço multiusuário.

Detalhes por fase: [proxy](docs/phase2.md), [operação](docs/phase3.md),
[RIS e benchmarks](docs/phase4.md), [integrações e Docker](docs/phase5.md).
Veja também [segurança](SECURITY.md), [contribuição](CONTRIBUTING.md) e
[plano de execução](docs/superpowers/plans/2026-10-31-v1.md).
