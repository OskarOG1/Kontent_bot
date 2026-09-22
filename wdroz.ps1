param(
    [Parameter(Mandatory = $true)]
    [string]$Serwer
)

$ErrorActionPreference = "Stop"

$celKatalog = "/opt/edity-bot"
$archiwumLokalne = Join-Path $env:TEMP "edity-bot-head.tar"
$archiwumZdalne = "$celKatalog/edity-bot-head.tar"

$zmiany = git status --porcelain
if ($zmiany) {
    Write-Warning "Sa niezacommitowane zmiany, nie trafia na serwer:"
    $zmiany | ForEach-Object { Write-Warning $_ }
}

git archive HEAD --output $archiwumLokalne
if ($LASTEXITCODE -ne 0) {
    Write-Error "git archive HEAD nie powiodlo sie"
    exit 1
}

scp $archiwumLokalne "${Serwer}:${archiwumZdalne}"
if ($LASTEXITCODE -ne 0) {
    Write-Error "scp archiwum na serwer nie powiodlo sie"
    Remove-Item $archiwumLokalne -Force
    exit 1
}

Remove-Item $archiwumLokalne -Force

$komendaZdalna = "cd $celKatalog && rm -rf src tests zasoby && tar -xf edity-bot-head.tar && rm -f edity-bot-head.tar && docker compose up -d --build && docker compose logs --tail 20"

ssh $Serwer $komendaZdalna
if ($LASTEXITCODE -ne 0) {
    Write-Error "wdrozenie na serwerze nie powiodlo sie"
    exit 1
}
