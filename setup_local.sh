#!/usr/bin/env bash
set -euo pipefail

echo "[setup-local] Iniciando modo local sem Docker"

if [ ! -f .env ]; then
  echo "[setup-local] Criando .env a partir de .env.example"
  cp .env.example .env
fi

PYTHON_BIN="${PYTHON_BIN:-python}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  PYTHON_BIN="python3"
fi

if [ ! -d .venv ]; then
  echo "[setup-local] Criando ambiente virtual local"
  "$PYTHON_BIN" -m venv .venv
fi

if [ -f .venv/bin/activate ]; then
  # shellcheck disable=SC1091
  . .venv/bin/activate
elif [ -f .venv/Scripts/activate ]; then
  # shellcheck disable=SC1091
  . .venv/Scripts/activate
fi

echo "[setup-local] Instalando dependencias"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "[setup-local] Executando pipeline local de contingencia"
python src/pipeline_local_demo.py --regenerate-data

echo "[setup-local] Concluido. Artefatos em data/processed e data/marts"