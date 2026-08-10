Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-SetupLog {
    param([string]$Message)

    Write-Host "[setup] $Message"
}

function Invoke-ExternalCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Command,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed: $Command $($Arguments -join ' ')"
    }
}

function Wait-ForPostgres {
    param(
        [string]$DockerCommand,
        [string]$ContainerName = 'smart-retail-postgres',
        [int]$MaxAttempts = 24,
        [int]$SecondsBetweenAttempts = 5
    )

    for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
        $status = & $DockerCommand inspect --format='{{json .State.Health.Status}}' $ContainerName 2>$null
        if ($status -eq '"healthy"') {
            return
        }

        Write-SetupLog "Waiting for PostgreSQL healthcheck ($attempt/$MaxAttempts)"
        Start-Sleep -Seconds $SecondsBetweenAttempts
    }

    throw 'PostgreSQL did not become healthy in time.'
}

function Resolve-PythonCommand {
    if ($env:PYTHON_BIN) {
        return $env:PYTHON_BIN
    }

    if (Get-Command python -ErrorAction SilentlyContinue) {
        return 'python'
    }

    if (Get-Command py -ErrorAction SilentlyContinue) {
        return 'py'
    }

    throw 'Python was not found in PATH. Install Python 3.13+ or set PYTHON_BIN.'
}

function Resolve-DockerCommand {
    if (Get-Command docker -ErrorAction SilentlyContinue) {
        return 'docker'
    }

    $dockerCli = 'C:\Program Files\Docker\Docker\resources\bin\docker.exe'
    if (Test-Path $dockerCli) {
        return $dockerCli
    }

    throw 'Docker CLI was not found. Install Docker Desktop and reopen the terminal.'
}

if (-not (Test-Path '.env')) {
    Write-SetupLog 'Creating .env from .env.example'
    Copy-Item '.env.example' '.env'
}

$pythonCommand = Resolve-PythonCommand
$dockerCommand = Resolve-DockerCommand

if (-not (Test-Path '.venv')) {
    Write-SetupLog 'Creating local virtual environment'
    & $pythonCommand -m venv .venv
}

$venvPython = Join-Path (Resolve-Path '.venv').Path 'Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    throw 'Virtual environment Python executable was not found.'
}

Write-SetupLog 'Installing Python dependencies'
Invoke-ExternalCommand -Command $venvPython -Arguments @('-m', 'pip', 'install', '--upgrade', 'pip')
Invoke-ExternalCommand -Command $venvPython -Arguments @('-m', 'pip', 'install', '-r', 'requirements.txt')

Write-SetupLog 'Starting PostgreSQL container'
Invoke-ExternalCommand -Command $dockerCommand -Arguments @('compose', 'up', '-d', 'postgres')
Wait-ForPostgres -DockerCommand $dockerCommand

Write-SetupLog 'Running ETL pipeline container'
Invoke-ExternalCommand -Command $dockerCommand -Arguments @('compose', 'run', '--rm', 'pipeline')

Write-SetupLog 'Pipeline execution finished'

$envContent = @{}
Get-Content '.env' | ForEach-Object {
    if ($_ -match '^(?<key>[A-Z0-9_]+)=(?<value>.*)$') {
        $envContent[$matches.key] = $matches.value
    }
}

$databaseName = if ($envContent.ContainsKey('DATABASE_NAME')) { $envContent['DATABASE_NAME'] } else { 'smart_retail' }
$databaseUser = if ($envContent.ContainsKey('DATABASE_USER')) { $envContent['DATABASE_USER'] } else { 'postgres' }
$databaseSchema = if ($envContent.ContainsKey('DATABASE_SCHEMA')) { $envContent['DATABASE_SCHEMA'] } else { 'analytics' }

Write-Host ''
Write-Host 'Power BI connection:'
Write-Host 'Host: localhost'
Write-Host 'Port: 5432'
Write-Host "Database: $databaseName"
Write-Host "User: $databaseUser"
Write-Host "Schema: $databaseSchema"