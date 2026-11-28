#!/usr/bin/env bash
# Nur lesender DB-Zugang für Claude Code (CI-23, Entscheidung B).
# Aufruf:  scripts/db_lesen.sh "SELECT ..."     oder   scripts/db_lesen.sh -f abfrage.sql
# Fester Benutzer ci_agent_readonly, keine psqlrc, Abbruch beim ersten Fehler.
# Jeder Backslash wird abgelehnt: psql-Befehle wie \! oder \c könnten sonst
# eine Shell starten oder den Benutzer wechseln. Eigentlicher Schutz sind die
# Rechte der Rolle in der DB (siehe CI-27: pg_hba steht noch auf trust).
set -euo pipefail

fehler() { echo "db_lesen: $*" >&2; exit 2; }

if [[ $# -eq 1 && "$1" != -* ]]; then
    sql="$1"
elif [[ $# -eq 2 && "$1" == "-f" ]]; then
    [[ -f "$2" ]] || fehler "Datei nicht gefunden: $2"
    sql="$(cat -- "$2")"
else
    fehler 'Aufruf: db_lesen.sh "SELECT ..." | db_lesen.sh -f datei.sql'
fi

[[ "$sql" != *\\* ]] || fehler "Backslash nicht erlaubt (keine psql-Befehle)"

env_datei="$(cd "$(dirname "$0")/.." && pwd)/.env"
[[ -f "$env_datei" ]] || fehler ".env fehlt"
# .env nur auslesen, nicht ausführen
wert() { sed -n "s/^$1=//p" "$env_datei" | tail -n 1 | tr -d '\r' | sed -e 's/^"\(.*\)"$/\1/' -e "s/^'\(.*\)'$/\1/"; }

host="$(wert DB_HOST)"; port="$(wert DB_PORT)"; db="$(wert DB_NAME)"
PGPASSWORD="$(wert DB_AGENT_PASSWORD)"
export PGPASSWORD
export PGOPTIONS="-c default_transaction_read_only=on -c statement_timeout=60000"
unset PGSERVICE PGSERVICEFILE PGUSER PGDATABASE PGHOSTADDR

printf '%s\n' "$sql" | psql -X -v ON_ERROR_STOP=1 -P pager=off \
    -h "${host:-localhost}" -p "${port:-5432}" -U ci_agent_readonly -d "${db:-country_intelligence}"
