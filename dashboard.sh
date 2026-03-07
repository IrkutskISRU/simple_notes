#!/usr/bin/env bash

reset

section() {
  local title="$1"
  echo ""
  local total_width=40
  local inner=" $title "
  local side_len=$(( (total_width - ${#inner}) / 2 ))
  (( side_len < 0 )) && side_len=0

  local line
  printf -v line '%*s' "$side_len" ''
  line=${line// /─}

  # gray lines + yellow title (sublime‑style)
  printf '\033[38;5;240m%s \033[1;33m%s\033[38;5;240m %s\033[0m\n' "$line" "$title" "$line"
}

section "ОРГАНИЗАЦИОННЫЕ"
notes list org

section "САЙТ"
notes list site

section "MAC OS"
notes list mac

section "РАБОТА"
notes list work

section "СПРИНТ"
notes list agile

echo ""
