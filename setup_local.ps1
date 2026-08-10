Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-SetupLog {
    param([string]$Message)
    Write-Host "[setup-local] $Message"
}

function Resolve-PythonCommand {
    if ($env:PYTHON_BIN) { return $env:PYTHON_BIN }
    if (Get-Command python -ErrorAction SilentlyContinue) { return 'python' }
    if (Get-Command py -ErrorAction SilentlyContinue) { return 'py' }
    throw 'Python nao encontrado. Instale Python 3.13+.'
}

$pythonCommand = Resolve-PythonCommand

if (-not (Test-Path '.env')) {
    Write-SetupLog 'Criando .env a partir de .env.example'
    Copy-Item '.env.example' '.env'
}

if (-not (Test-Path '.venv')) {
    Write-SetupLog 'Criando ambiente virtual local'
    & $pythonCommand -m venv .venv
}

$venvPython = Join-Path (Resolve-Path '.venv').Path 'Scripts\python.exe'
Write-SetupLog 'Instalando dependencias'
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt

Write-SetupLog 'Executando pipeline local de contingencia'
& $venvPython src/pipeline_local_demo.py --regenerate-data

Write-SetupLog 'Concluido: veja data/processed e data/marts'