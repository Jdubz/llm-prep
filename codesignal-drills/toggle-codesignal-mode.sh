#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VSCODE_DIR="$ROOT_DIR/.vscode"
SETTINGS_JSON="$VSCODE_DIR/settings.json"
PRESET_JSON="$VSCODE_DIR/settings.codesignal-minimal.json"
BACKUP_JSON="$VSCODE_DIR/settings.pre-codesignal.json"

usage() {
  cat <<EOF
Usage:
  bash codesignal-drills/toggle-codesignal-mode.sh on
  bash codesignal-drills/toggle-codesignal-mode.sh off
  bash codesignal-drills/toggle-codesignal-mode.sh status

Behavior:
  on     Backup current .vscode/settings.json once, then apply minimal CodeSignal-like preset
  off    Restore backup if present, otherwise remove generated settings.json
  status Show current mode
EOF
}

ensure_files() {
  mkdir -p "$VSCODE_DIR"
  if [[ ! -f "$PRESET_JSON" ]]; then
    echo "Preset not found: $PRESET_JSON"
    exit 1
  fi
}

mode_on() {
  ensure_files
  if [[ -f "$SETTINGS_JSON" && ! -f "$BACKUP_JSON" ]]; then
    cp "$SETTINGS_JSON" "$BACKUP_JSON"
    echo "Backed up existing settings to $BACKUP_JSON"
  fi
  cp "$PRESET_JSON" "$SETTINGS_JSON"
  echo "CodeSignal mode enabled."
}

mode_off() {
  ensure_files
  if [[ -f "$BACKUP_JSON" ]]; then
    cp "$BACKUP_JSON" "$SETTINGS_JSON"
    rm -f "$BACKUP_JSON"
    echo "Restored previous settings."
  else
    rm -f "$SETTINGS_JSON"
    echo "No backup found; removed generated settings.json"
  fi
}

mode_status() {
  if [[ -f "$SETTINGS_JSON" ]] && cmp -s "$SETTINGS_JSON" "$PRESET_JSON"; then
    echo "status: codesignal-mode:on"
  else
    echo "status: codesignal-mode:off"
  fi
}

if [[ $# -ne 1 ]]; then
  usage
  exit 1
fi

case "$1" in
  on) mode_on ;;
  off) mode_off ;;
  status) mode_status ;;
  *)
    usage
    exit 1
    ;;
esac
