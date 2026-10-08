# Builds dist\donation_army.pack from mod\script\ and installs it into the game data folder.
$ErrorActionPreference = "Stop"
$root   = $PSScriptRoot
$cli    = "C:\dev\gaming\rpfm\rpfm_cli.exe"
$schema = "$env:APPDATA\FrodoWazEre\rpfm\config\schemas\schema_wh3.ron"
$dist   = "$root\dist"
$pack   = "$dist\donation_army.pack"

New-Item -ItemType Directory -Force -Path $dist | Out-Null
Remove-Item -Force $pack -ErrorAction SilentlyContinue
& $cli -g warhammer_3 pack create -p $pack
if ($LASTEXITCODE -ne 0) { throw "rpfm_cli pack create failed" }
& $cli -g warhammer_3 pack add -p $pack -t "$schema" -F "$root\mod\script;script"
if ($LASTEXITCODE -ne 0) { throw "rpfm_cli pack add failed" }

$gameData = "C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III\data"
try {
	Copy-Item $pack "$gameData\donation_army.pack" -Force
	Write-Output "Installed -> $gameData\donation_army.pack"
} catch {
	Write-Output "WARNING: could not copy into game data folder (run elevated, or copy manually): $($_.Exception.Message)"
}

Write-Output "=== Pack contents ==="
& $cli -g warhammer_3 pack list -p $pack
