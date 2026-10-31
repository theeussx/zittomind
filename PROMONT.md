# ZittoMind

## Master Engineering Specification — Intelligent LLM Routing \& Optimization Infrastructure

**Versão:** 1.0  
**Linguagem principal:** Python 3.11+  
**Plataforma prioritária:** Linux  
**Arquitetura:** CLI + HTTP Proxy + Python SDK  
**Filosofia:** Local-first, privacy-first, quality-first  
**Objetivo:** Reduzir custos, tokens e latência sem comprometer a qualidade das respostas.

---

# 1\. PAPEL E RESPONSABILIDADE

Atue como uma equipe de engenharia de software de nível sênior, composta por:

- Principal Software Engineer.
- AI Infrastructure Architect.
- LLM Optimization Engineer.
- Machine Learning Engineer.
- Application Security Engineer.
- Site Reliability Engineer.
- Developer Experience Engineer.
- QA Automation Engineer.
- Technical Documentation Engineer.

Sua responsabilidade é **projetar, implementar, testar, auditar e documentar o ZittoMind**, uma ferramenta open-source de roteamento inteligente de modelos de linguagem.

O sistema deverá funcionar como uma camada intermediária entre aplicações e APIs de inteligência artificial, selecionando automaticamente o modelo mais adequado para cada requisição.

A escolha deverá considerar:

1. Complexidade da tarefa.
2. Dificuldade de raciocínio.
3. Contexto disponível.
4. Qualidade esperada.
5. Custo estimado.
6. Latência.
7. Capacidades do modelo.
8. Requisitos de ferramentas.
9. Restrições de privacidade.
10. Preferências do usuário.
11. Orçamento disponível.
12. Histórico de desempenho.
13. Confiabilidade dos provedores.
14. Políticas específicas do projeto.

Não entregue apenas uma demonstração. Desenvolva uma base funcional, segura, extensível, testável e adequada à publicação no GitHub.

---

# 2\. VISÃO DO PRODUTO

O ZittoMind deverá oferecer três formas de utilização:

### CLI

Execução direta pelo terminal.

``` bash
routemind ask "Explique o comando chmod"

routemind classify "Analise este algoritmo"

routemind serve

routemind doctor

routemind stats
```

### Proxy HTTP

Servidor local capaz de receber requisições de clientes compatíveis e encaminhá-las aos provedores.

Endereço padrão:

``` text
http://127.0.0.1:8787
```

### Python SDK

Interface programática para integração em outros sistemas.

``` python
from routemind import RouteMind

router = RouteMind()

result = await router.route(
    prompt="Explique esta função",
    profile="balanced",
)
```

O núcleo de roteamento deverá ser independente da CLI e do servidor HTTP.

---

# 3\. PRINCÍPIOS FUNDAMENTAIS

O projeto deve seguir:

**Quality First:** não sacrificar requisitos críticos para reduzir custos.

**Local First:** evitar chamadas externas desnecessárias.

**Privacy by Default:** minimizar transmissão e armazenamento de informações.

**Capability Aware:** verificar capacidades reais dos modelos.

**Provider Agnostic:** evitar dependência de um único provedor.

**Context Aware:** considerar o histórico necessário à tarefa.

**Cost Aware:** estimar e acompanhar custos.

**Latency Aware:** minimizar overhead.

**Observable by Design:** registrar decisões e métricas relevantes.

**Fail Safely:** comportamento previsível diante de falhas.

**Developer Friendly:** instalação e configuração simples.

**Evidence Based:** decisões adaptativas baseadas em avaliações confiáveis.

---

# 4\. ARQUITETURA GERAL

Fluxo conceitual:

``` text
CLIENT
  |
  +-- CLI
  +-- HTTP Proxy
  +-- Python SDK
  |
  v
REQUEST GATEWAY
  |
  v
SECURITY & POLICY ENGINE
  |
  v
CONTEXT ANALYZER
  |
  v
LOCAL COMPLEXITY CLASSIFIER
  |
  +-- High confidence --> Continue
  |
  +-- Low confidence
          |
          v
    OPTIONAL LLM CLASSIFIER
          |
          v
ROUTING INTELLIGENCE ENGINE
  |
  +-- Capability Filter
  +-- Quality Estimator
  +-- Cost Estimator
  +-- Latency Estimator
  +-- Reasoning Policy
  +-- Project Policies
  +-- Routing Intelligence Score
  |
  v
MODEL SELECTOR
  |
  v
PROVIDER ADAPTER
  |
  +-- OpenAI
  +-- Anthropic
  +-- Ollama
  +-- Compatible Providers
  |
  v
RESPONSE HANDLER
  |
  v
METRICS / FEEDBACK / ADAPTIVE ENGINE
  |
  v
CLIENT
```

Cada componente deverá possuir responsabilidade clara.

Evite abstrações desnecessárias e dependências circulares.

---

# 5\. STACK TECNOLÓGICA

Utilize preferencialmente:

| Área | Tecnologia |
| --- | --- |
| Linguagem | Python 3.11+ |
| CLI | Typer |
| Interface terminal | Rich |
| API HTTP | FastAPI |
| Servidor | Uvicorn |
| HTTP assíncrono | httpx |
| Validação | Pydantic |
| Configuração | Pydantic Settings |
| Ambiente | python-dotenv |
| Banco local | SQLite |
| Testes | pytest |
| Testes assíncronos | pytest-asyncio |
| HTTP mocks | respx |
| Lint | Ruff |
| Tipagem | mypy |
| Métricas | Prometheus opcional |
| Distribuição | pip / pyproject.toml |
| Containerização | Docker opcional |

Prefira bibliotecas maduras e mantidas.

Não introduza Redis, PostgreSQL, filas distribuídas ou serviços externos sem necessidade comprovada.

---

# 6\. CLASSIFICAÇÃO HÍBRIDA DE COMPLEXIDADE

Implemente classificação em múltiplas etapas.

## 6.1. Análise local

Antes de qualquer chamada externa, analisar:

- Estrutura da mensagem.
- Quantidade de arquivos.
- Stack traces.
- Dependências entre tarefas.
- Complexidade algorítmica.
- Necessidade de planejamento.
- Uso de ferramentas.
- Histórico relevante.
- Sensibilidade à precisão.
- Requisitos arquiteturais.
- Quantidade de etapas.
- Tamanho esperado da resposta.

Não utilizar apenas palavras-chave ou tamanho do prompt.

## 6.2. Classificação externa opcional

Quando a confiança local for insuficiente, permitir consulta a um modelo econômico.

A classificação deverá retornar JSON validado.

``` json
{
  "complexity": "ADVANCED",
  "confidence": 0.94,
  "category": "distributed_system_debugging",
  "reasoning_requirement": "high",
  "context_dependency": true,
  "tool_dependency": true,
  "accuracy_sensitivity": "high",
  "estimated_output_size": "long"
}
```

A chamada externa deverá respeitar:

- Privacidade.
- Orçamento.
- Latência.
- Permissão do usuário.
- Minimização de dados.

## 6.3. Níveis de complexidade

`SIMPLE`: perguntas diretas e operações simples.

`MEDIUM`: tarefas intermediárias com múltiplas etapas.

`ADVANCED`: problemas complexos, arquitetura, algoritmos difíceis, auditorias e desenvolvimento extensivo.

Além desses níveis, analisar dimensões independentes:

``` text
reasoning_difficulty
context_size
output_size
tool_requirements
accuracy_sensitivity
latency_sensitivity
```

Uma tarefa longa não é necessariamente difícil.

Uma pergunta curta não é necessariamente simples.

---

# 7\. ROUTING INTELLIGENCE SCORE (RIS)

Implementar um sistema denominado **Routing Intelligence Score**, responsável por avaliar a adequação de cada modelo a uma determinada tarefa.

O RIS deverá combinar:

- Qualidade estimada por categoria.
- Histórico de benchmarks.
- Confiabilidade.
- Latência.
- Custo.
- Compatibilidade de capacidades.
- Feedback validado.
- Taxa de falhas.
- Preferências operacionais.

Exemplo de estrutura:

``` python
class RoutingScore:
    model_id: str
    task_category: str
    quality_score: float
    cost_score: float
    latency_score: float
    reliability_score: float
    final_score: float
    confidence: float
```

O cálculo deverá ser configurável e documentado.

Não utilizar valores fictícios como métricas reais.

Modelos sem dados suficientes deverão receber tratamento explícito de incerteza.

## 7.1. Requisitos do RIS

- Pontuação por categoria.
- Versionamento de métricas.
- Histórico de avaliações.
- Ajuste de pesos.
- Comparação entre modelos.
- Identificação de modelos subavaliados.
- Limites de confiança.
- Rollback de políticas.
- Modo somente observação.

O RIS não deverá substituir os filtros obrigatórios de capacidades e segurança.

---

# 8\. MOTOR DE SELEÇÃO DE MODELOS

A seleção deverá ocorrer em duas fases.

## Fase A — Elegibilidade

Eliminar modelos incompatíveis com:

- Context window.
- Modalidades exigidas.
- Ferramentas.
- Streaming.
- Structured output.
- Reasoning.
- Privacidade.
- Orçamento.
- Restrições do cliente.
- Disponibilidade.

## Fase B — Otimização

Classificar os modelos elegíveis usando:

- RIS.
- Custo esperado.
- Latência esperada.
- Perfil ativo.
- Política do projeto.
- Histórico de confiabilidade.

Nunca escolher um modelo incompatível apenas porque possui pontuação maior.

---

# 9\. PERFIS DE OPERAÇÃO

Implementar três perfis principais.

## ECONOMY

Priorizar redução de custos.

- Modelos econômicos quando adequados.
- Classificação local.
- Cache seguro.
- Reasoning reduzido quando apropriado.
- Limites mínimos de qualidade.

## BALANCED

Perfil padrão.

- Equilíbrio entre qualidade, custo e latência.
- Seleção dinâmica.
- Reasoning proporcional à dificuldade.
- Fallback controlado.

## PERFORMANCE

Priorizar qualidade e confiabilidade.

- Modelos de maior capacidade quando necessário.
- Reasoning elevado em tarefas difíceis.
- Menor tolerância à incerteza.
- Priorização de precisão.

Permitir perfis personalizados.

---

# 10\. POLÍTICAS POR PROJETO

Implementar configurações independentes para diferentes projetos.

Exemplo:

``` yaml
projects:
  arena-estrela:
    profile: performance
    privacy: strict
    max_cost_per_request: 0.10
    external_classification: false

  wardizitto:
    profile: balanced
    max_cost_per_request: 0.05

  experiments:
    profile: economy
    max_cost_per_request: 0.02

  default:
    profile: balanced
```

Os nomes e valores são exemplos configuráveis.

Permitir identificação do projeto por:

- Argumento CLI.
- Configuração explícita.
- Identificador de cliente.
- Diretório de trabalho, quando autorizado.

Não inferir identidade de projeto a partir de dados sensíveis.

---

# 11\. MODEL REGISTRY

Criar catálogo centralizado de modelos.

Cada entrada deverá conter:

``` yaml
id: example-model
provider: openai

capabilities:
  text: true
  tools: true
  streaming: true
  structured_output: true
  reasoning: true

limits:
  context_window: null
  max_output_tokens: null

pricing:
  input_per_million: null
  output_per_million: null

routing:
  enabled: true
  priority: 50
```

Implementar:

- Modelos configuráveis.
- Capacidades verificáveis.
- Preços atualizáveis.
- Desativação de modelos.
- Prioridades.
- Overrides.
- Validação de parâmetros.
- Identificação de modelos indisponíveis.

Consultar documentação oficial atual antes de definir modelos padrão.

Não assumir que todos os modelos suportam os mesmos parâmetros.

---

# 12\. REASONING POLICY ENGINE

Separar complexidade da tarefa e esforço de raciocínio.

Exemplos:

- Formatação extensa: reasoning baixo.
- Algoritmo difícil: reasoning alto.
- Explicação simples: reasoning mínimo.
- Auditoria de segurança: reasoning elevado.

Implementar tradução de parâmetros conforme o provedor.

OpenAI e Anthropic possuem mecanismos distintos.

Não presumir equivalência direta entre reasoning effort e thinking budget.

Permitir override manual.

---

# 13\. CONTEXT AWARENESS

O roteador deverá considerar contexto relevante.

Exemplo:

``` text
Usuário: Continue corrigindo o erro anterior.
```

Essa mensagem não deverá ser automaticamente classificada como SIMPLE.

Considerar:

- Histórico.
- Instruções.
- Ferramentas.
- Resultados de ferramentas.
- Objetivo da sessão.
- Dependências.
- Modelo exigido pelo cliente.

Implementar estabilidade de roteamento durante tarefas complexas.

Evitar troca de modelo quando isso comprometer continuidade ou compatibilidade.

---

# 14\. ADAPTIVE ROUTING ENGINE

Implementar aprendizado adaptativo opcional.

O sistema poderá melhorar decisões com base em:

- Benchmarks.
- Feedback explícito.
- Falhas por categoria.
- Latência.
- Custo.
- Confiabilidade.
- Resultados de testes.

Não considerar HTTP 200 como prova de qualidade.

Não utilizar prompts privados para treinamento sem autorização.

Implementar:

- Versionamento de políticas.
- Limites de atualização.
- Rollback.
- Modo observação.
- Desativação do aprendizado.
- Registro das alterações.

Inicialmente, utilizar regras determinísticas e métricas.

Métodos de aprendizado mais sofisticados deverão ser introduzidos somente após validação.

---

# 15\. SHADOW MODE

Criar modo de avaliação sem interferir na execução.

Nesse modo:

1. Receber a requisição.
2. Calcular a decisão hipotética.
3. Manter o modelo originalmente solicitado.
4. Registrar a decisão alternativa.
5. Comparar estimativas.
6. Gerar métricas.

Exemplo:

``` bash
routemind serve --shadow
```

Não executar uma segunda geração paga por padrão.

---

# 16\. CACHE INTELIGENTE

Implementar cache opcional.

Separar:

- Cache de classificação.
- Cache de metadados.
- Cache de preços.
- Cache de respostas, desabilitado por padrão.

Requisitos:

- TTL.
- Hash.
- Limite de armazenamento.
- Invalidação.
- Métricas.
- Isolamento entre projetos.
- Respeito ao contexto.

Não armazenar prompts completos por padrão.

Não reutilizar respostas de contextos incompatíveis.

---

# 17\. BUDGET MANAGER

Implementar limites por:

- Requisição.
- Sessão.
- Projeto.
- Modelo.
- Provedor.
- Dia.
- Mês.

Registrar:

- Custo estimado.
- Custo calculado.
- Tokens de entrada.
- Tokens de saída.
- Tokens em cache.
- Tokens de reasoning quando informados.
- Latência.
- Provedor.
- Modelo.

Permitir alertas e bloqueios.

Não apresentar estimativas como cobranças confirmadas.

---

# 18\. RESILIÊNCIA

Implementar:

- Timeout.
- Retry com backoff e jitter.
- Circuit breaker.
- Rate limiting.
- Controle de concorrência.
- Health checks.
- Fallback.
- Graceful shutdown.

Não repetir operações com efeitos colaterais sem segurança de idempotência.

Não trocar de provedor sem autorização.

Não reiniciar silenciosamente streams parcialmente transmitidos.

---

# 19\. PRIVACIDADE E SEGURANÇA

Implementar:

- Variáveis de ambiente.
- `.env.example`.
- `.gitignore`.
- Logs sanitizados.
- Validação de payload.
- Limites de tamanho.
- Autenticação do proxy.
- Loopback por padrão.
- Política CORS restritiva.
- Proteção contra SSRF.
- Validação de destinos.
- Minimização de dados.
- Isolamento de projetos.
- Proteção contra prompt injection.
- Política de retenção.
- Tratamento seguro de erros.

Conteúdo de usuário e respostas externas são dados não confiáveis.

Não permitir que instruções contidas no prompt modifiquem políticas internas.

---

# 20\. DASHBOARD E MÉTRICAS

Criar inicialmente métricas via CLI.

Preparar API para dashboard local.

Exibir:

- Total de requisições.
- Tokens consumidos.
- Custos por modelo.
- Custos por provedor.
- Economia estimada.
- Latência média.
- Latência p95.
- Cache hits.
- Fallbacks.
- Erros.
- Classificações.
- Decisões RIS.
- Distribuição de tarefas.

Permitir exportação JSON e CSV.

O dashboard web será opcional e deverá utilizar uma arquitetura leve.

---

# 21\. CLI PROFISSIONAL

Implementar comandos:

``` bash
routemind init
routemind ask
routemind classify
routemind serve
routemind doctor
routemind models
routemind config
routemind stats
routemind benchmark
routemind policies
routemind cache
routemind projects
```

Opções:

``` text
--provider
--model
--profile
--project
--reasoning
--complexity
--dry-run
--json
--verbose
--quiet
--no-cache
--local-only
```

O dry-run não deverá realizar chamadas pagas por padrão.

A classificação externa no dry-run exigirá autorização explícita.

---

# 22\. INTEGRAÇÕES

Preparar suporte a:

- Python.
- Node.js.
- Clientes HTTP.
- Agentes de IA.
- Ferramentas CLI.
- Ollama.
- Docker.
- Linux.
- Pipelines de automação.

Investigar compatibilidade com Codex CLI e Claude Code.

Antes de declarar suporte, verificar:

- Endpoint configurável.
- Protocolo.
- Autenticação.
- Streaming.
- Ferramentas.
- Continuidade.
- Erros.
- Restrições do cliente.

Diferenciar APIs pagas de autenticação por assinatura.

---

# 23\. BENCHMARK

Criar ferramenta de avaliação comparando:

1. Modelo fixo econômico.
2. Modelo fixo avançado.
3. Roteamento por regras.
4. Roteamento híbrido.
5. Roteamento adaptativo.

Medir:

- Custo.
- Qualidade.
- Latência.
- Overhead.
- Taxa de erro.
- Economia líquida.
- Classificações incorretas.
- Fallbacks.
- Desempenho por categoria.

Incluir casos adversariais:

- Prompt curto e difícil.
- Prompt longo e simples.
- Contexto extenso.
- Ferramentas.
- Código complexo.
- Saída estruturada.
- Concorrência.
- Streaming.

Não inventar resultados.

---

# 24\. ESTRUTURA DE ARQUIVOS

``` text
routemind/
├── src/routemind/
│   ├── cli/
│   ├── api/
│   ├── core/
│   │   ├── classifier.py
│   │   ├── router.py
│   │   ├── reasoning.py
│   │   ├── policies.py
│   │   ├── capabilities.py
│   │   ├── context.py
│   │   ├── scoring.py
│   │   └── registry.py
│   ├── providers/
│   │   ├── base.py
│   │   ├── openai.py
│   │   ├── anthropic.py
│   │   └── ollama.py
│   ├── services/
│   │   ├── budget.py
│   │   ├── cache.py
│   │   ├── metrics.py
│   │   ├── fallback.py
│   │   ├── circuit_breaker.py
│   │   ├── adaptive.py
│   │   └── shadow.py
│   ├── infrastructure/
│   │   ├── database.py
│   │   ├── logging.py
│   │   └── http.py
│   ├── schemas/
│   ├── config.py
│   └── __init__.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── regression/
│   └── security/
├── benchmarks/
├── examples/
├── docs/
├── config/
├── .github/workflows/
├── .env.example
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── Dockerfile
├── README.md
├── CONTRIBUTING.md
├── SECURITY.md
└── LICENSE
```

Adapte a estrutura se houver justificativa técnica.

Não criar arquivos vazios apenas para aparentar organização.

---

# 25\. TESTES E QUALIDADE

Utilizar:

- pytest.
- pytest-asyncio.
- respx.
- Ruff.
- mypy.
- GitHub Actions.

Testar:

- Classificação.
- Seleção.
- RIS.
- Reasoning.
- Contexto.
- Políticas.
- Orçamento.
- Cache.
- Fallback.
- Circuit breaker.
- Streaming.
- Cancelamento.
- Concorrência.
- Segurança.
- Configuração.
- Shadow mode.
- Erros de provedores.

Testes unitários não deverão depender de APIs pagas.

Não declarar testes aprovados sem executá-los.

---

# 26\. ROADMAP

## Fase 1 — Núcleo funcional

- Configuração.
- CLI.
- Classificador local.
- Classificador externo opcional.
- Model Registry.
- Routing Engine.
- Reasoning Policy.
- Adaptadores OpenAI e Anthropic.
- Dry-run.
- Logs.
- Testes.

## Fase 2 — Proxy

- FastAPI.
- Endpoints.
- Streaming.
- Segurança.
- Tratamento de erros.
- Compatibilidade documentada.

## Fase 3 — Otimização

- Cache.
- Budget Manager.
- Métricas.
- Fallback.
- Circuit Breaker.
- Shadow Mode.
- Políticas por projeto.

## Fase 4 — Inteligência

- RIS.
- Feedback.
- Adaptive Routing.
- Benchmarks.
- Versionamento.
- Rollback.

## Fase 5 — Ecossistema

- Ollama.
- Dashboard.
- SDKs.
- Integrações CLI.
- Distribuição.
- Documentação avançada.

Cada fase deverá resultar em software executável e testável.

---

# 27\. MELHORIAS ADICIONAIS OBRIGATÓRIAS

## 27.1. Routing Explainability

Implementar um modo que explique por que determinado modelo foi escolhido.

Exemplo:

``` text
Decision ID: 8f32

Complexity: ADVANCED
Profile: BALANCED

Selected: configured-advanced-model

Reasons:
- Requires multi-step reasoning
- Tool support required
- High accuracy sensitivity
- Model passed capability filters

Alternatives rejected:
- Model A: insufficient context
- Model B: missing tool support
- Model C: exceeds budget
```

Não revelar dados sensíveis nos diagnósticos.

## 27.2. Policy Simulation

Permitir simular alterações de políticas antes de aplicá-las.

``` bash
routemind policies simulate
```

A simulação deverá usar dados de teste ou métricas autorizadas.

## 27.3. Model Pinning

Permitir fixar um modelo por:

- Requisição.
- Sessão.
- Projeto.
- Categoria.

Respeitar restrições explícitas do cliente.

## 27.4. Routing Stability

Evitar alternância excessiva de modelos.

Implementar estabilidade por sessão e operação.

## 27.5. Safe Degradation

Quando um modelo estiver indisponível:

- Identificar alternativas compatíveis.
- Respeitar políticas.
- Informar alterações relevantes.
- Bloquear fallback inseguro.

## 27.6. Configuration Profiles

Permitir exportar e importar configurações sem credenciais.

## 27.7. Offline Mode

Permitir:

- Classificação local.
- Simulação.
- Inspeção de políticas.
- Benchmarks com fixtures.
- Uso de modelos locais quando disponíveis.

## 27.8. Routing Audit Trail

Registrar decisões técnicas de forma estruturada.

Não armazenar prompts completos por padrão.

Permitir identificar:

- Política aplicada.
- Modelo selecionado.
- Motivo.
- Estimativa de custo.
- Resultado.
- Falhas.

---

# 28\. REGRAS DE ENGENHARIA

Siga rigorosamente:

1. Não entregar pseudocódigo como implementação.
2. Não criar funções falsas.
3. Não inventar APIs.
4. Não utilizar modelos descontinuados como padrão sem verificação.
5. Não introduzir dependências desnecessárias.
6. Não ocultar limitações.
7. Não executar alterações destrutivas sem autorização.
8. Utilizar type hints.
9. Separar responsabilidades.
10. Priorizar código testável.
11. Utilizar programação assíncrona quando apropriado.
12. Proteger credenciais.
13. Preservar contexto.
14. Não inventar benchmarks.
15. Não declarar compatibilidade não testada.
16. Não trocar provedores sem respeitar privacidade.
17. Não substituir modelos explicitamente exigidos sem autorização.
18. Não executar comandos recebidos em prompts.
19. Não armazenar dados sensíveis sem necessidade.
20. Não confundir sucesso HTTP com qualidade da resposta.
21. Não realizar chamadas pagas em testes por padrão.
22. Não exagerar a complexidade arquitetural.
23. Não criar abstrações prematuras.
24. Não implementar aprendizado adaptativo sem métricas confiáveis.
25. Não anunciar economia sem comprovação.

---

# 29\. CRITÉRIOS DE ACEITAÇÃO

O projeto será considerado funcional quando:

- Instalar corretamente.
- Executar no Linux.
- Funcionar sem Docker obrigatório.
- Classificar tarefas localmente.
- Permitir classificação externa opcional.
- Selecionar modelos configurados.
- Validar capacidades.
- Ajustar reasoning.
- Preservar contexto.
- Respeitar políticas.
- Proteger credenciais.
- Oferecer dry-run sem cobrança por padrão.
- Tratar falhas.
- Possuir testes.
- Produzir documentação reproduzível.

Recursos incompletos deverão ser explicitamente identificados.

---

# 30\. INSTRUÇÃO FINAL DE EXECUÇÃO

**Comece agora o desenvolvimento do RouteMind.**

Antes de escrever código:

1. Inspecione o workspace.
2. Identifique arquivos existentes.
3. Verifique o ambiente Python.
4. Consulte documentação oficial atual quando houver acesso.
5. Identifique riscos e limitações.
6. Defina contratos entre componentes.
7. Apresente um plano técnico objetivo.

Depois, implemente a **Fase 1 — Núcleo funcional**.

Crie diretamente os arquivos no repositório quando houver acesso ao sistema de arquivos.

Priorize:

- `config.py`
- `schemas.py`
- `classifier.py`
- `registry.py`
- `capabilities.py`
- `reasoning.py`
- `router.py`
- `main.py`
- Adaptadores de provedores.
- Testes unitários.
- `.env.example`
- `pyproject.toml`
- `requirements.txt`
- `README.md`

Não entregue apenas explicações.

Produza código real, executável, modular e testável.

Após a implementação:

1. Execute os testes.
2. Execute lint.
3. Execute verificação de tipos.
4. Corrija problemas.
5. Demonstre comandos funcionais.
6. Documente limitações.
7. Registre funcionalidades concluídas.
8. Indique a próxima fase.

Se alguma dependência externa impedir a conclusão, documente o bloqueio e continue com as partes independentes.

**Objetivo final: transformar o RouteMind em uma infraestrutura open-source confiável, eficiente e extensível, capaz de otimizar automaticamente modelos, reasoning, custos, latência e qualidade para aplicações e agentes de inteligência artificial.**