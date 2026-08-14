<#
.SYNOPSIS
    마른길 개발 명령 모음.

.DESCRIPTION
    깨끗한 clone 에서 시작할 때:

        .\make.ps1 install
        .\make.ps1 check

    자세한 설명은 README.md 의 Quick Start 참조.

.EXAMPLE
    .\make.ps1 check
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('install', 'install-model', 'api', 'web', 'contracts', 'fixtures',
                 'test', 'webtest', 'typecheck', 'build', 'check', 'help')]
    [string]$Task = 'help'
)

$ErrorActionPreference = 'Stop'
$Root = $PSScriptRoot
$Venv = Join-Path $Root '.venv'
$Py = Join-Path $Venv 'Scripts\python.exe'
$WebDir = Join-Path $Root 'web'

function Write-Step($text) { Write-Host "`n=== $text ===" -ForegroundColor Cyan }
function Write-Ok($text) { Write-Host "  OK  $text" -ForegroundColor Green }
function Write-Bad($text) { Write-Host "  !!  $text" -ForegroundColor Red }

function Assert-Venv {
    if (-not (Test-Path $Py)) {
        Write-Bad "Python 가상환경이 없다. 먼저 실행: .\make.ps1 install"
        exit 1
    }
}

function Assert-Node {
    if (-not (Test-Path (Join-Path $WebDir 'node_modules'))) {
        Write-Bad "프론트 의존성이 없다. 먼저 실행: .\make.ps1 install"
        exit 1
    }
}

# 한 단계 실행하고 성패를 기록한다. 실패해도 즉시 멈추지 않고 끝까지 돌린 뒤
# 마지막에 요약한다 - 한 번에 무엇이 깨졌는지 다 보는 편이 빠르다.
function Invoke-Step($name, $script) {
    Write-Step $name
    & $script
    if ($LASTEXITCODE -ne 0) {
        Write-Bad $name
        return $false
    }
    Write-Ok $name
    return $true
}

switch ($Task) {

    'install' {
        Write-Step 'Python 가상환경'
        if (-not (Test-Path $Py)) { python -m venv $Venv }
        & $Py -m pip install --upgrade pip --quiet
        & $Py -m pip install -r (Join-Path $Root 'requirements-dev.txt')
        Write-Ok '앱 의존성 설치 완료'

        Write-Step '프론트엔드 의존성'
        Push-Location $WebDir
        try {
            if (Test-Path (Join-Path $WebDir 'package-lock.json')) { npm ci } else { npm install }
        } finally { Pop-Location }
        Write-Ok '프론트 의존성 설치 완료'

        Write-Host "`n다음: .\make.ps1 check" -ForegroundColor Yellow
    }

    'install-model' {
        Assert-Venv
        Write-Step '모델 파이프라인 의존성 (pandas·scikit-learn·pyarrow)'
        & $Py -m pip install -r (Join-Path $Root 'requirements-model.txt')
        Write-Ok '설치 완료'
    }

    'api' {
        Assert-Venv
        Write-Step '백엔드 개발 서버'
        $apiHost = $env:MAREUNGIL_API_HOST; if (-not $apiHost) { $apiHost = '127.0.0.1' }
        $apiPort = $env:MAREUNGIL_API_PORT; if (-not $apiPort) { $apiPort = '8000' }
        Write-Host "  http://${apiHost}:${apiPort}/docs" -ForegroundColor Yellow
        Push-Location $Root
        try { & $Py -m uvicorn api.main:app --reload --host $apiHost --port $apiPort }
        finally { Pop-Location }
    }

    'web' {
        Assert-Node
        Write-Step '프론트엔드 개발 서버'
        Write-Host '  http://127.0.0.1:5173' -ForegroundColor Yellow
        Push-Location $WebDir
        try { npm run dev } finally { Pop-Location }
    }

    'fixtures' {
        Assert-Venv
        Write-Step 'DS 픽스처 재생성'
        Push-Location $Root
        try { & $Py scripts/build_demo_assess_fixtures.py } finally { Pop-Location }
    }

    'contracts' {
        Assert-Venv
        Push-Location $Root
        try { & $Py -m contracts.validate } finally { Pop-Location }
        exit $LASTEXITCODE
    }

    'test' {
        Assert-Venv
        Push-Location $Root
        try { & $Py -m pytest } finally { Pop-Location }
        exit $LASTEXITCODE
    }

    'typecheck' {
        Assert-Node
        Push-Location $WebDir
        try { npm run typecheck } finally { Pop-Location }
        exit $LASTEXITCODE
    }

    'webtest' {
        Assert-Node
        Push-Location $WebDir
        try { npm run test } finally { Pop-Location }
        exit $LASTEXITCODE
    }

    'build' {
        Assert-Node
        Push-Location $WebDir
        try { npm run build } finally { Pop-Location }
        exit $LASTEXITCODE
    }

    'check' {
        Assert-Venv
        Assert-Node
        $results = [ordered]@{}
        $results['계약 검증'] = Invoke-Step '계약 검증' { Push-Location $Root; try { & $Py -m contracts.validate } finally { Pop-Location } }
        $results['Python 테스트'] = Invoke-Step 'Python 테스트' { Push-Location $Root; try { & $Py -m pytest } finally { Pop-Location } }
        $results['TypeScript 검사'] = Invoke-Step 'TypeScript 검사' { Push-Location $WebDir; try { npm run typecheck } finally { Pop-Location } }
        $results['프론트 테스트'] = Invoke-Step '프론트 테스트' { Push-Location $WebDir; try { npm run test } finally { Pop-Location } }
        $results['프론트 빌드'] = Invoke-Step '프론트 빌드' { Push-Location $WebDir; try { npm run build } finally { Pop-Location } }

        Write-Step '요약'
        $failed = 0
        foreach ($k in $results.Keys) {
            if ($results[$k]) { Write-Ok $k } else { Write-Bad $k; $failed++ }
        }
        if ($failed -gt 0) {
            Write-Host "`n실패 $failed 건. 고치고 다시 실행하라." -ForegroundColor Red
            exit 1
        }
        Write-Host "`n전부 통과. 커밋해도 된다." -ForegroundColor Green
    }

    default {
        Write-Host @'
마른길 개발 명령

  .\make.ps1 install         Python .venv + 프론트 의존성 설치 (최초 1회)
  .\make.ps1 install-model   모델 파이프라인 의존성 (AI·데이터 담당만)

  .\make.ps1 api             백엔드 개발 서버   http://127.0.0.1:8000
  .\make.ps1 web             프론트 개발 서버   http://127.0.0.1:5173

  .\make.ps1 contracts       모든 계약 픽스처 검증
  .\make.ps1 fixtures        DS 픽스처 재생성
  .\make.ps1 test            Python 테스트
  .\make.ps1 webtest         프론트 smoke test
  .\make.ps1 typecheck       TypeScript 검사
  .\make.ps1 build           프론트 production build

  .\make.ps1 check           위 검증 전부 (커밋·PR 전에 이것만 통과하면 된다)
'@
    }
}
