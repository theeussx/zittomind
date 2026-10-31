# Contribuindo

Leia PROMONT.md e AGENTS.md. Use Python 3.11+ e instale `pip install -e '.[dev]'`
em um virtualenv. Execute pytest, Ruff (check e format --check) e mypy src/.

Mantenha o núcleo independente da CLI/API. Adicione testes de comportamento para
mudanças de políticas e adaptadores, usando respx para HTTP. Não use APIs pagas
em testes. Nunca inclua chaves, prompts privados ou resultados fictícios de benchmark.
Documente recursos incompletos e verificação realizada em cada PR.
