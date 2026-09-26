#!/bin/bash
set -euo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
config="$root/.devcontainer/devcontainer.json"
installer="$root/.devcontainer/install_beforehand.bash"
grep -qF '"ghcr.io/devcontainers/features/dotnet:2"' "$config"
grep -A 2 -F '"ghcr.io/devcontainers/features/dotnet:2"' "$config" | grep -qF '"version": "10.0"'
grep -qF '"PATH": "${containerEnv:PATH}:/home/vscode/.local/bin:/home/vscode/bin:/home/vscode/.dotnet/tools"' "$config"
grep -qE 'sudo apt install -y .*blender' "$installer"
printf 'PASS: .NET 10 Feature and Blender package configured\n'
