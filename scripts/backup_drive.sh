#!/bin/bash
# DB-Backup: pg_dump -> backups/ -> Kopie nach CountryIntelligence/backups (Drive für Desktop). Backlog #30.
# Bricht bei jedem Fehler laut ab (kein stilles Weitermachen). Löscht nichts.
# Rohdaten (data/raw, 6,6 GB) sind NICHT enthalten: eigenes Archiv nach dem Umzug (#138).
#
# Aufruf (Shell auf dem Mac, Repo-Wurzel):   bash scripts/backup_drive.sh
# Zeitplan: scripts/launchd/de.julian.ci-backup.plist (siehe Kopf dort).

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
DB="country_intelligence"
LOG="$REPO/logs/backup.log"
mkdir -p "$REPO/backups" "$REPO/logs"
exec > >(tee -a "$LOG") 2>&1

echo "=== Backup $(date '+%Y-%m-%d %H:%M:%S')"

# Drive-Ordner finden: Ordner "CountryIntelligence" in Drive für Desktop (versteckte Ordner wie .Encrypted ausgenommen). Wenn es nicht genau einen gibt:
# abbrechen, nicht raten. Bei Bedarf fest eintragen: CI_DRIVE="/…/CountryIntelligence"
CI_DRIVE="${CI_DRIVE:-}"
if [ -z "$CI_DRIVE" ]; then
  kandidaten=()
  for wurzel in "$HOME"/Library/CloudStorage/GoogleDrive-* /Volumes/GoogleDrive* "$HOME/Google Drive"*; do
    [ -d "$wurzel" ] || continue
    while IFS= read -r d; do kandidaten+=("$d"); done \
      < <(find "$wurzel" -maxdepth 3 -type d -name CountryIntelligence -not -path "*/.*")
  done
  anzahl=${#kandidaten[@]}
  if [ "$anzahl" -ne 1 ]; then
    echo "FEHLER: $anzahl Ordner 'CountryIntelligence' in Drive gefunden, erwartet genau 1. CI_DRIVE oben fest eintragen." >&2
    [ "$anzahl" -gt 0 ] && printf '  %s\n' "${kandidaten[@]}" >&2
    echo "Gesucht unter: ~/Library/CloudStorage/GoogleDrive-*, /Volumes/GoogleDrive*, ~/Google Drive*" >&2
    exit 1
  fi
  CI_DRIVE="${kandidaten[0]}"
fi
if [ ! -d "$CI_DRIVE" ] || [ "$(basename "$CI_DRIVE")" != "CountryIntelligence" ]; then
  echo "FEHLER: CI_DRIVE ist kein vorhandener Ordner namens CountryIntelligence: $CI_DRIVE" >&2
  ls -ld "$CI_DRIVE" >&2 || true   # zeigt den echten Grund (z. B. Operation not permitted)
  exit 1
fi
ZIEL="$CI_DRIVE/backups"
mkdir -p "$ZIEL"

PG_DUMP="$(command -v pg_dump)" || { echo "FEHLER: pg_dump nicht im PATH" >&2; exit 1; }
echo "pg_dump: $PG_DUMP ($("$PG_DUMP" --version))"

DATEI="$REPO/backups/db_backup_$(date +%Y%m%d).dump"
if [ -e "$DATEI" ]; then
  DATEI="$REPO/backups/db_backup_$(date +%Y%m%d_%H%M).dump"
fi

"$PG_DUMP" -Fc -d "$DB" -f "$DATEI"

# Kontrolle: Datei lesbar und nicht verdächtig klein (letzte Dumps ca. 150 MB).
GROESSE=$(stat -f %z "$DATEI")
EINTRAEGE=$(pg_restore -l "$DATEI" | grep -c " TABLE DATA ")
echo "Dump: $DATEI, $GROESSE Bytes, $EINTRAEGE Tabellen mit Daten"
if [ "$GROESSE" -lt 100000000 ]; then
  echo "FEHLER: Dump kleiner als 100 MB – nicht nach Drive kopiert, bitte ansehen." >&2
  exit 1
fi

cp "$DATEI" "$ZIEL/"
KOPIE="$ZIEL/$(basename "$DATEI")"
[ "$(stat -f %z "$KOPIE")" -eq "$GROESSE" ] || { echo "FEHLER: Kopie in Drive hat andere Größe" >&2; exit 1; }
echo "Kopie: $KOPIE"

# Kein Auflisten des Drive-Ordners: macOS verweigert es Hintergrundprozessen (launchd), Kopieren per Pfad geht.
# Ob die Datei online angekommen ist, zeigt Drive selbst (Ordner CountryIntelligence/backups).
echo "=== fertig"
