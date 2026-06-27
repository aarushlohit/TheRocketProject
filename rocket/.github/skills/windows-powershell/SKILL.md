---
name: windows-powershell
description: 'Use PowerShell 5.1+ effectively on Windows — cmdlets, scripting, pipeline, file system, process management, error handling. Use when: PowerShell, Windows, .bat, .ps1, scripting, automation, Windows terminal, cmd.'
---

# Windows PowerShell

Best practices for PowerShell scripting and automation on Windows.

## Cmdlet Naming Convention

PowerShell uses `Verb-Noun` naming:
- `Get-Process`, `Set-Content`, `Invoke-WebRequest`, `ConvertTo-Json`
- Common verbs: `Get`, `Set`, `New`, `Remove`, `Invoke`, `Test`, `ConvertTo`, `Format`

## Scripting Best Practices

- Use `-Filter` over `-Include`/`-Exclude` for performance with `Get-ChildItem`.
- Prefer `$using:` scope in script blocks for remote/background jobs.
- Use splatting for cmdlets with many parameters:
  ```powershell
  $params = @{
      Path = "C:\logs"
      Recurse = $true
      Filter = "*.log"
  }
  Get-ChildItem @params
  ```
- Use `Try/Catch/Finally` for error handling:
  ```powershell
  try {
      $content = Get-Content -Path "config.json" -ErrorAction Stop
  } catch [System.IO.FileNotFoundException] {
      Write-Error "Config file not found"
  } catch {
      Write-Error "Unexpected error: $_"
  }
  ```

## Common Patterns

- **Check admin**: `if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator"))`
- **Test path before access**: `if (Test-Path $path) { ... }`
- **Join paths**: `Join-Path $parent $child` (not string concatenation)
- **Read JSON**: `Get-Content file.json | ConvertFrom-Json`
- **Write JSON**: `$data | ConvertTo-Json -Depth 10 | Set-Content file.json`
