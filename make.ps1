<#
.SYNOPSIS
    마른길 개발 명령 모음.

.DESCRIPTION
    깨끗한 clone 에서 시작할 때 — 이 한 줄이면 끝난다:

        .\make.ps1 setup

    사전 확인(python·node) -> 설치 -> check 까지 이어서 한다.
    자세한 설명은 README.md 의 Quick Start 참조.

.EXAMPLE
    .\make.ps1 check
#>
[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [ValidateSet('setup', 'install', 'install-model', 'api', 'web', 'contracts', 'fixtures',
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
        Write-Bad "프론트 의존성이 없다. 먼저 실행: .\make.ps1 setup"
        exit 1
    }
}

# 외부 실행 파일(pip·npm·venv)은 실패해도 예외를 던지지 않는다. $ErrorActionPreference
# 는 cmdlet 에만 걸리므로 여기서 종료 코드를 직접 본다. 확인하지 않으면 pip 가 깨진
# 채로 npm 단계까지 흘러가고, 마지막에야 이유를 알 수 없는 실패가 나온다.
function Assert-ExitCode($what) {
    if ($LASTEXITCODE -ne 0) {
        Write-Bad "$what 실패 (exit $LASTEXITCODE)"
        exit 1
    }
}

# 설치 전에 python·node 가 실제로 실행되는지 본다. 없는 상태로 install 을 돌리면
# "'python' 용어가 cmdlet 이름으로 인식되지 않습니다" 만 남아서, 처음 clone 한
# 사람은 무엇을 깔아야 하는지 알 수 없다.
function Assert-Prereq {
    Write-Step '사전 확인'
    $missing = 0

    if (Get-Command python -ErrorAction SilentlyContinue) {
        $out = & python -c "import sys;print(sys.version_info[0],sys.version_info[1])"
        $parts = if ($out) { "$out".Trim() -split '\s+' } else { @() }
        if ($parts.Count -lt 2) {
            # Microsoft Store 스텁은 실행돼도 아무것도 출력하지 않고 스토어를 연다.
            Write-Bad 'python 이 실행되지 않는다. Microsoft Store 스텁일 수 있다 - python.org 에서 설치한다.'
            $missing++
        }
        elseif ([int]$parts[0] -lt 3 -or ([int]$parts[0] -eq 3 -and [int]$parts[1] -lt 11)) {
            Write-Bad "Python $($parts[0]).$($parts[1]) - 3.11 이상이 필요하다 (pyproject.toml requires-python)."
            $missing++
        }
        else { Write-Ok "Python $($parts[0]).$($parts[1])" }
    }
    else {
        Write-Bad 'python 이 PATH 에 없다. python.org 에서 3.11 이상을 설치하고 "Add python.exe to PATH" 를 켠다.'
        $missing++
    }

    if (Get-Command npm -ErrorAction SilentlyContinue) {
        Write-Ok "Node $(node --version) / npm $(npm --version)"
    }
    else {
        Write-Bad 'npm 이 PATH 에 없다. https://nodejs.org 에서 LTS 를 설치한다.'
        $missing++
    }

    if ($missing -gt 0) {
        Write-Host "`n위 $missing 건을 설치한 뒤 PowerShell 창을 새로 열고 다시 실행한다." -ForegroundColor Red
        Write-Host "PATH 변경은 이미 열려 있는 창에 반영되지 않는다." -ForegroundColor Yellow
        exit 1
    }
}

function Invoke-Install {
    Write-Step 'Python 가상환경'
    if (-not (Test-Path $Py)) {
        python -m venv $Venv
        Assert-ExitCode 'python -m venv'
    }
    & $Py -m pip install --upgrade pip --quiet
    Assert-ExitCode 'pip 업그레이드'
    & $Py -m pip install -r (Join-Path $Root 'requirements-dev.txt')
    Assert-ExitCode '앱 의존성 설치'
    Write-Ok '앱 의존성 설치 완료'

    Write-Step '프론트엔드 의존성'
    Push-Location $WebDir
    try {
        if (Test-Path (Join-Path $WebDir 'package-lock.json')) { npm ci } else { npm install }
    } finally { Pop-Location }
    Assert-ExitCode '프론트 의존성 설치'
    Write-Ok '프론트 의존성 설치 완료'
}

# 한 단계 실행하고 성패를 기록한다. 실패해도 즉시 멈추지 않고 끝까지 돌린 뒤
# 마지막에 요약한다 - 한 번에 무엇이 깨졌는지 다 보는 편이 빠르다.
function Invoke-Step($name, $script) {
    # `& $script` 의 출력은 성공 스트림으로 흘러 함수 반환값에 섞인다. Out-Host 로
    # 화면에만 보내지 않으면 반환값이 [출력 여러 줄 + $bool] 배열이 되고, PowerShell
    # 에서 비어 있지 않은 배열은 참이라 `if ($results[$k])` 가 실패한 단계도 통과로
    # 읽는다. 실제로 pytest 가 깨진 채 "전부 통과. 커밋해도 된다"를 출력했다.
    Write-Step $name
    & $script | Out-Host
    $ok = ($LASTEXITCODE -eq 0)
    if ($ok) { Write-Ok $name } else { Write-Bad $name }
    return $ok
}

# 실패 건수를 돌려준다. 안에서 쓰는 Write-Step/Ok/Bad 는 전부 Write-Host 라
# 성공 스트림에 섞이지 않는다 - Invoke-Step 주석의 함정을 여기서 되풀이하지 않는다.
function Invoke-Check {
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
    return $failed
}

switch ($Task) {

    # clone 직후 한 줄로 끝내는 명령. 사전 확인 -> 설치 -> 검증까지 이어서 한다.
    # install 과 check 를 따로 치게 두면 검증을 건너뛴 사람이 반드시 나온다.
    'setup' {
        Assert-Prereq
        Invoke-Install

        Write-Step '검증'
        $failed = Invoke-Check
        if ($failed -gt 0) {
            Write-Host "`n설치는 됐지만 검증 $failed 건이 실패했다. 개발을 시작하기 전에 위 메시지를 본다." -ForegroundColor Red
            exit 1
        }

        Write-Host "`n환경 준비 완료. 바로 시작해도 된다." -ForegroundColor Green
        Write-Host "  .\make.ps1 api    백엔드  http://127.0.0.1:8000" -ForegroundColor Yellow
        Write-Host "  .\make.ps1 web    프론트  http://127.0.0.1:5173" -ForegroundColor Yellow
    }

    'install' {
        Assert-Prereq
        Invoke-Install
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
        $failed = Invoke-Check
        if ($failed -gt 0) {
            Write-Host "`n실패 $failed 건. 고치고 다시 실행하라." -ForegroundColor Red
            exit 1
        }
        Write-Host "`n전부 통과. 커밋해도 된다." -ForegroundColor Green
    }

    default {
        Write-Host @'
마른길 개발 명령

  .\make.ps1 setup           clone 직후 이것 하나. 사전 확인 + 설치 + 검증까지
  .\make.ps1 install         설치만 (검증은 따로 check)
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
