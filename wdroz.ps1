param(
    [Parameter(Mandatory = $true)]
    [string]$Serwer,
    [string]$Galaz = "main",
    [switch]$Wymus
)

$ErrorActionPreference = "Stop"

$celKatalog = "/opt/edity-bot"
$archiwumLokalne = Join-Path $env:TEMP "edity-bot-main.tar"
$archiwumZdalne = "$celKatalog/edity-bot-main.tar"

git fetch origin $Galaz
if ($LASTEXITCODE -ne 0) {
    Write-Error "git fetch origin $Galaz nie powiodlo sie"
    exit 1
}

$commitLokalny = git rev-parse $Galaz
$commitZdalny = git rev-parse origin/$Galaz
if ($commitLokalny -ne $commitZdalny -and -not $Wymus) {
    Write-Error "$Galaz i origin/$Galaz wskazuja rozne commity: zsynchronizuj galaz (git checkout $Galaz, git pull), albo podaj -Wymus"
    exit 1
}

$zmiany = git status --porcelain
if ($zmiany) {
    Write-Warning "Sa niezacommitowane zmiany, nie trafia na serwer:"
    $zmiany | ForEach-Object { Write-Warning $_ }
}

git archive $Galaz --output $archiwumLokalne
if ($LASTEXITCODE -ne 0) {
    Write-Error "git archive $Galaz nie powiodlo sie"
    exit 1
}

scp $archiwumLokalne "${Serwer}:${archiwumZdalne}"
if ($LASTEXITCODE -ne 0) {
    Write-Error "scp archiwum na serwer nie powiodlo sie"
    Remove-Item $archiwumLokalne -Force
    exit 1
}

Remove-Item $archiwumLokalne -Force

$komendaZdalna = "cd $celKatalog && rm -rf src tests zasoby && tar -xf edity-bot-main.tar && rm -f edity-bot-main.tar && docker compose up -d --build && docker compose logs --tail 20"

ssh $Serwer $komendaZdalna
if ($LASTEXITCODE -ne 0) {
    Write-Error "wdrozenie na serwerze nie powiodlo sie"
    exit 1
}
