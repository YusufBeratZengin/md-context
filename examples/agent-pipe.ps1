<#
.SYNOPSIS
Demonstrates querying md-context and piping the token-budgeted context pack into an agent.
#>

param(
    [string]$Vault = "tests/fixtures/vault",
    [string]$Query = "valve",
    [int]$Budget = 4000,
    [string]$CacheDir = ".cache"
)

$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"

Write-Host "==> Indexing vault at $Vault..."
md-context index $Vault --cache-dir $CacheDir

Write-Host "==> Querying: '$Query' (budget: $Budget tokens)..."
# In a real setup, pipe to your agent command
# e.g.: md-context query ... | your-agent-command
md-context query $Query --root $Vault --cache-dir $CacheDir --budget $Budget | ForEach-Object {
    Write-Host $_
}
