param(
  [int]$Limite = 0
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$Raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
$JsonPath = Join-Path $Raiz 'dados\candidatos-2026.json'
$FotosDir = Join-Path $Raiz 'fotos'

if (-not (Test-Path $JsonPath)) {
  Write-Host "ERRO: nao encontrei $JsonPath" -ForegroundColor Red
  Write-Host "Coloque este script na raiz do repositorio, ao lado do index.html." -ForegroundColor Yellow
  exit 1
}

New-Item -ItemType Directory -Force -Path $FotosDir | Out-Null

$texto = Get-Content -Raw -Encoding UTF8 $JsonPath
$dados = $texto | ConvertFrom-Json

# Aceita tanto um array puro quanto { candidatos: [...] }
if ($dados -is [System.Array]) {
  $lista = @($dados)
  $wrapper = $false
} elseif ($null -ne $dados.candidatos) {
  $lista = @($dados.candidatos)
  $wrapper = $true
} else {
  Write-Host 'ERRO: formato do JSON nao reconhecido.' -ForegroundColor Red
  exit 1
}

if ($Limite -gt 0) {
  $processar = @($lista | Select-Object -First $Limite)
} else {
  $processar = $lista
}

$headers = @{
  'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/152 Safari/537.36'
  'Accept' = 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
  'Referer' = 'https://divulgacandcontas.tse.jus.br/'
}

$ok = 0
$falhas = 0
$i = 0
$total = $processar.Count

Write-Host "Candidaturas a processar: $total" -ForegroundColor Cyan
Write-Host "Destino: $FotosDir" -ForegroundColor Cyan
Write-Host ''

foreach ($cand in $processar) {
  $i++
  $sq = [string]$cand.sqCandidato
  $url = [string]$cand.foto
  $nome = [string]$cand.nomeUrna

  if ([string]::IsNullOrWhiteSpace($sq) -or [string]::IsNullOrWhiteSpace($url)) {
    Write-Host "[$i/$total] PULADO - sem SQ ou URL: $nome" -ForegroundColor DarkYellow
    $falhas++
    continue
  }

  $arquivo = Join-Path $FotosDir ($sq + '.jpg')

  if (Test-Path $arquivo) {
    $tam = (Get-Item $arquivo).Length
    if ($tam -gt 500) {
      Write-Host "[$i/$total] JA EXISTE - $nome" -ForegroundColor DarkGray
      $cand.foto = './fotos/' + $sq + '.jpg'
      $ok++
      continue
    }
  }

  Write-Host "[$i/$total] Baixando $nome..." -NoNewline
  $baixou = $false

  for ($tentativa = 1; $tentativa -le 3 -and -not $baixou; $tentativa++) {
    try {
      $tmp = $arquivo + '.tmp'
      if (Test-Path $tmp) { Remove-Item $tmp -Force }
      Invoke-WebRequest -Uri $url -Headers $headers -OutFile $tmp -MaximumRedirection 5 -TimeoutSec 30

      if ((Test-Path $tmp) -and ((Get-Item $tmp).Length -gt 500)) {
        Move-Item $tmp $arquivo -Force
        $baixou = $true
      } else {
        if (Test-Path $tmp) { Remove-Item $tmp -Force }
        throw 'arquivo vazio ou invalido'
      }
    } catch {
      if ($tentativa -lt 3) { Start-Sleep -Seconds 1 }
    }
  }

  if ($baixou) {
    $cand.foto = './fotos/' + $sq + '.jpg'
    $ok++
    Write-Host ' OK' -ForegroundColor Green
  } else {
    $falhas++
    Write-Host ' FALHOU' -ForegroundColor Red
  }

  Start-Sleep -Milliseconds 120
}

# Faz backup antes de alterar o JSON.
$backup = $JsonPath + '.backup'
if (-not (Test-Path $backup)) {
  Copy-Item $JsonPath $backup
}

if ($wrapper) {
  $dados.candidatos = $lista
  $saida = $dados | ConvertTo-Json -Depth 10
} else {
  $saida = $lista | ConvertTo-Json -Depth 10
}

[System.IO.File]::WriteAllText($JsonPath, $saida, [System.Text.UTF8Encoding]::new($false))

Write-Host ''
Write-Host "Concluido. Fotos locais: $ok | Falhas: $falhas" -ForegroundColor Cyan
Write-Host "JSON atualizado: $JsonPath" -ForegroundColor Cyan
Write-Host "Backup: $backup" -ForegroundColor DarkGray
Write-Host ''
Write-Host 'Agora envie para o GitHub a pasta fotos e o dados/candidatos-2026.json atualizado.' -ForegroundColor Yellow
