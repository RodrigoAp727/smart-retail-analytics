# Guia de Contribuicao

Este projeto foi desenhado para portfolio, mas segue padroes de colaboracao profissional.

## Fluxo recomendado
1. Crie uma branch com nome objetivo: `feat/...`, `fix/...`, `docs/...`.
2. Execute validacoes locais antes de abrir PR.
3. Abra Pull Request usando o template em `.github/PULL_REQUEST_TEMPLATE.md`.

## Validacoes locais
```bash
python -m ruff check src tests
python -m pytest
```

## Padroes de codigo
- Nomes tecnicos em ingles para tabelas, colunas e funcoes.
- Comentarios e docstrings em portugues.
- Nenhuma credencial hardcoded; use `.env`.

## Commits
Use mensagens claras e orientadas ao efeito de negocio ou tecnica aplicada.
Exemplos:
- `feat: adiciona curva ABC para priorizacao de clientes`
- `fix: corrige imputacao de custo nulo na transformacao`
- `docs: melhora instrucoes de setup local sem docker`