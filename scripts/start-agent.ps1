param(
    [ValidateSet("gpt-5.6-luna", "gpt-5.6-terra", "gpt-5.6-sol", "deepseek-v4-pro")]
    [string]$Model = "gpt-5.6-luna",

    [ValidateSet("medium", "high", "xhigh", "max")]
    [string]$Reasoning = "high",

    [ValidateSet("phase", "continue")]
    [string]$RunMode = "phase"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot

if (-not (Get-Command codex -ErrorAction SilentlyContinue)) {
    throw "Codex CLI was not found on PATH. Install or open Codex once, then retry."
}

$LaunchPrompt = @"
Read AGENTS.md, docs/development/implementation-agent-prompt.md, and ROADMAP.md completely before acting.
Run mode is: $RunMode.
Resume the single ACTIVE roadmap phase from the repository's current state. Implement it end to end, validate it, and update ROADMAP.md using observed evidence. In phase mode, activate the next phase but stop before implementing it. Do not commit, push, deploy, use paid APIs, or change global configuration. End with the required evidence report.
"@

$CodexArguments = @(
    "-C", $ProjectRoot,
    "-m", $Model,
    "-c", "model_reasoning_effort=`"$Reasoning`"",
    "-s", "workspace-write",
    "-a", "on-request",
    $LaunchPrompt
)

Write-Host "Starting PromoGuard implementation agent"
Write-Host "Project: $ProjectRoot"
Write-Host "Model: $Model | Reasoning: $Reasoning | Mode: $RunMode"

& codex @CodexArguments
