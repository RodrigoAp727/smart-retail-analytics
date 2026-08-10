# Checklist de Publicacao no GitHub

Use este checklist para publicar o projeto com padrao profissional.

## 1. Configuracao do repositorio
- [ ] Criar repositorio com nome `smart-retail-analytics`.
- [ ] Definir Description:
  - `Retail analytics pipeline that turns raw sales data into decision-ready metrics for revenue, margin, and customer performance.`
- [ ] Definir Topics:
  - `data-engineering`
  - `analytics`
  - `data-analytics`
  - `financial-analysis`
  - `etl`
  - `python`
  - `postgresql`
  - `docker`
  - `power-bi`
  - `star-schema`
  - `scd2`
  - `sqlalchemy`
  - `pytest`
  - `github-actions`

## 2. Arquivos obrigatorios para subir
- [ ] `README.md`
- [ ] `LICENSE`
- [ ] `requirements.txt`
- [ ] `pyproject.toml`
- [ ] `setup.sh`
- [ ] `setup.ps1`
- [ ] `setup_local.sh`
- [ ] `setup_local.ps1`
- [ ] `.env.example`
- [ ] `.github/workflows/ci.yml`
- [ ] `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] `.github/ISSUE_TEMPLATE/bug_report.md`
- [ ] `.github/ISSUE_TEMPLATE/feature_request.md`
- [ ] `.github/ISSUE_TEMPLATE/config.yml`
- [ ] `CONTRIBUTING.md`
- [ ] `CHECKLIST_PUBLICACAO_GITHUB.md`
- [ ] `src/`
- [ ] `tests/`
- [ ] `database/`
- [ ] `docs/architecture.png`
- [ ] `docs/architecture.mmd`
- [ ] `dashboard/README.md`
- [ ] `dashboard/screenshots/README.md`
- [ ] `dashboard/screenshots/executive-overview.png`
- [ ] `dashboard/screenshots/operational-overview.png`
- [ ] `dashboard/screenshots/customer-abc-analysis.png`
- [ ] `dashboard/screenshots/monthly-trends.png`
- [ ] `data/samples/`

## 3. Seguranca e higiene
- [ ] Garantir que `.env` nao foi versionado.
- [ ] Garantir que nenhuma credencial real foi commitada.
- [ ] Garantir que `data/raw` nao foi versionado com dados volumosos desnecessarios.

## 4. Validacao antes do push
- [ ] `python -m ruff check src tests`
- [ ] `python -m pytest tests/test_transform.py`
- [ ] `python src/reporting/generate_dashboard_previews.py`

## 5. Entrega para recrutador
- [ ] Revisar se o topo do README comunica problema, solucao e impacto em ate 90 segundos.
- [ ] Confirmar que as imagens carregam no README.
- [ ] Confirmar que o modo local (`setup_local.ps1`) funciona sem Docker.
- [ ] Compartilhar o link do repositorio com 1 frase de contexto profissional.