# ============================================================
# stop.ps1 : kyuka_calc（ポート5011）だけを確実に停止する
# 使い方: stop.bat をダブルクリック → その後 start.bat で再起動
# ============================================================

$conns = Get-NetTCPConnection -LocalPort 5011 -State Listen -ErrorAction SilentlyContinue

if (-not $conns) {
    Write-Host "ポート5011で動作中のプロセスはありません（既に停止しています）。"
    exit 0
}

$targetPids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($p in $targetPids) {
    $name = (Get-Process -Id $p -ErrorAction SilentlyContinue).ProcessName
    Write-Host "ポート5011を使用中のプロセス（PID $p / $name）を停止します..."
    Stop-Process -Id $p -Force
}

Write-Host "停止しました。start.bat で再起動してください。"
