# ZittoMind

Roteamento de LLMs em Python 3.11+, Linux, com classificação local, políticas
explícitas e adaptadores assíncronos. Implementação inicial da **Fase 1** do
[PROMONT.md](PROMONT.md). O nome público é ZittoMind: pacote `zittomind`, classe
`ZittoMind` e comando `zittomind`. Os exemplos antigos `routemind` da especificação
não são aliases instalados.

## Instalação e execução

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
zittomind --help
zittomind classify 'Explique o comando chmod' --json
zittomind doctor
zittomind ask 'Explique chmod' --config config/offline-example.yaml --dry-run --json
python examples/dry_run.py
```

O arquivo `config/offline-example.yaml` contém um identificador **fictício**, apenas
para simulação. Não representa um modelo real nem deve ser usado para geração.
Sem configuração, o catálogo fica vazio e `ask` falha com orientação para configurá-lo.

```bash
zittomind init
zittomind config
zittomind models
```

`init` cria `zittomind.yaml` sem sobrescrever arquivos existentes. Cadastre modelos
reais nesse arquivo, usando IDs, preços e capacidades verificados na documentação
do provedor. Exemplo de estrutura (substitua o ID e confirme todos os valores):

```yaml
models:
  - id: SUBSTITUA_POR_ID_VERIFICADO
    provider: openai
    enabled: true
    context_window: null
    max_output_tokens: null
    input_per_million: null
    output_per_million: null
    tier: ADVANCED
    priority: 50
    reasoning_mode: none
    supported_efforts: []
    output_parameter: max_completion_tokens
projects:
  default:
    profile: balanced
    privacy: standard
    allowed_providers: [openai]
    max_cost_per_request: 0.05
    external_classification: false
```

Limites desconhecidos bloqueiam a seleção. Preços desconhecidos bloqueiam seleção
quando há orçamento; sem orçamento, a decisão informa custo `null`. Preços são por
milhão de tokens e devem usar a mesma moeda do orçamento. `tier` e `priority` são
configurações do operador, **não avaliações de qualidade medidas**.

Para gerar, exporte `OPENAI_API_KEY` ou `ANTHROPIC_API_KEY` no ambiente e execute
`zittomind ask 'Sua pergunta'`. Isso usa a API paga do provedor. Assinaturas de
interfaces de chat não equivalem a credenciais de API. `.env.example` contém
somente placeholders; arquivos `.env` não são carregados automaticamente.

## SDK

```python
import asyncio
from zittomind import ZittoMind


async def main():
    result = await ZittoMind().route(
        prompt="Continue a análise",
        messages=[{"role": "user", "content": "Auditoria de segurança do serviço"}],
        project="default",
        profile="balanced",
        dry_run=True,
    )
    print(result.decision.model_dump_json(indent=2))


asyncio.run(main())
```

A SDK aceita as mesmas opções principais de `ask`: `model`, `provider`, `profile`,
`project`, `reasoning`, `complexity`, `max_output_tokens`, `local_only`, `dry_run` e
`external_classification`. Histórico textual tem papéis system/user/assistant.
O núcleo não depende de Typer nem de um servidor HTTP.

## Decisões, políticas e reasoning

Filtros de privacidade, modelo fixado, provedor permitido, contexto, saída,
capacidade declarada e orçamento precedem a ordenação. `economy` ordena pelo custo
estimado e depois prioridade; `balanced` e `performance` usam prioridade e custo
nesta versão. Não há métricas suficientes para diferenciar esses dois perfis por
qualidade/latência. Empates são resolvidos pelo ID para estabilidade determinística.
Um modelo fixado nunca é substituído. Projetos desconhecidos são recusados.

O classificador considera instruções e histórico, estrutura de código, passos,
continuação, ferramentas e sinais de raciocínio. Confiança é heurística, não
probabilidade calibrada. É limitado em idiomas e casos desconhecidos e pode errar;
`--complexity` permite override. Comprimento isolado não determina dificuldade.

Reasoning só é enviado quando declarado no registro do modelo:

- `openai_effort`: envie `reasoning_effort`; configure `supported_efforts`.
- `anthropic_budget`: configure também `thinking_budgets`, por exemplo
  `{low: 1024, medium: 2048, high: 4096}`. O orçamento precisa ser menor que
  `max_output_tokens` da requisição.
- `anthropic_adaptive`: envia `thinking.type=adaptive` e `output_config.effort`.
- `none`: omite parâmetros; override explícito é recusado.

Não há tradução automática entre effort e budget. O operador deve verificar
suporte no modelo escolhido. A Anthropic recebe instruções system iniciais no
campo próprio; instruções system posteriores ao início do diálogo são recusadas
para evitar alterar a semântica da conversa.

Classificação externa está desligada por padrão. Para ativá-la, configure na
política `external_classification: true`, `classifier_model` e
`classifier_max_cost`, além de passar `--external-classification`. Ela é usada
somente abaixo de 0.75 de confiança local, envia apenas atributos derivados e
valida o JSON retornado. Não pode reduzir a complexidade detectada localmente.
Consome parte do orçamento estimado da requisição e pode custar mesmo que a
seleção posterior falhe. **A opção explícita também autoriza esse custo em dry-run**;
sem ela, dry-run é inteiramente local. Dados derivados têm utilidade limitada:
este caminho não oferece compreensão semântica do texto original.

## Segurança e custos

Endpoints oficiais são fixos; não há URLs fornecidas pelo prompt, redirecionamento
HTTP nem uso automático de proxies do ambiente. Chaves são lidas em tempo de
execução e não fazem parte da configuração exportada. Logs internos registram ID
de decisão e provedor, sem prompts, respostas ou credenciais. Não há persistência
automática. O JSON da CLI pode conter a resposta solicitada: trate sua saída como
sensível. Não registre exceções de validação da SDK sem sanitização, pois Pydantic
pode incluir dados de entrada.

`privacy: strict` e `--local-only` bloqueiam provedores remotos. Como Ollama ainda
não foi implementado, geração nessas condições é recusada. Classificação local
continua disponível. Prompts são dados, sem execução de comandos ou alteração de
políticas. YAML é configuração confiável do operador, validada com campos extras
proibidos. Requisições possuem limites de tamanho.

O custo de entrada usa um limite conservador por bytes UTF-8 mais overhead; não é
um tokenizador oficial. A saída estimada usa o máximo solicitado, incluindo o
espaço de reasoning. Esses números não garantem uma cobrança máxima do provedor.
Tokens retornados pelo provedor são reportados separadamente. Não há economia ou
qualidade comprovada anunciada.

## Verificação

```bash
python -m pytest
ruff check .
ruff format --check .
mypy src/
```

Testes usam HTTP simulado com respx, sem APIs pagas. CI configura Python
3.11/3.12/3.13; a validação local foi feita com Python 3.12. Não foi realizada
validação de credenciais, disponibilidade ou geração contra provedores reais.

## Estado e próximos passos

Entregues: configuração validada, SDK, CLI (`init`, `ask`, `classify`, `models`,
`config`, `doctor`), classificação local/externa opcional, catálogo, filtros,
reasoning, explicação da decisão, estimativas por requisição, logs mínimos,
adaptadores textuais OpenAI/Anthropic, testes e CI.

Próxima entrega: **Fase 2**, proxy FastAPI autenticado em loopback, protocolos,
streaming e testes de cancelamento. Não há `serve` nesta versão.

Fases 3–5 ainda não implementadas: cache, contabilidade persistente e orçamentos
por sessão/dia/mês, retries seguros, fallback, circuit breaker, métricas agregadas,
shadow mode, RIS medido, aprendizado, feedback, versionamento/rollback de políticas,
benchmarks comparativos, pinning por sessão/categoria, Ollama, dashboard e SDK Node.
Também ficam pendentes perfis personalizados e tradução de ferramentas,
multimodalidade e saída estruturada. Essas modalidades são recusadas, sem descarte
silencioso. Não há compatibilidade declarada com Codex CLI ou Claude Code.

Referências oficiais consultadas para os adaptadores:
[OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create),
[Anthropic Messages](https://platform.claude.com/docs/en/api/http/messages),
[Anthropic thinking](https://platform.claude.com/docs/en/build-with-claude/extended-thinking).
