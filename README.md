# Hausmonitor V4

Konsolidierte FastAPI-PWA mit vollständigem Nivellement- und Rissmonitoring.

## Enthaltene Funktionen

### Nivellement
- SW, SO, Anbau, Terrasse SW und Terrasse SO mit fünf Einzelablesungen
- Mittelwert, Standardabweichung, Standardfehler und Signal/Rausch-Bewertung
- Haus- und Terrassendifferenz sowie Änderung gegenüber der ersten vollständigen Kampagne
- Temperatur, Grundwasser, Niederschlag, Wetter, Lichtquelle und Notizen
- Fotos je Kampagne
- Zeit-, Grundwasser- und Temperaturdiagramme
- lineare Trend- und Korrelationsauswertung
- vollständiger CSV-Export mit Rohablesungen
- CSV-Reimport dieses Exportformats
- PDF-Gesamtbericht

### Rissmonitoring
- frei benennbare Messstellen mit Ort, Beschreibung, Einheit und optionalem Referenzwert
- Messungen mit Datum/Uhrzeit, Lufttemperatur, Messwert, Notiz und Foto
- absoluter Messwert und Änderung gegenüber der ersten Messung
- Einzel- und Übersichtsdiagramme
- CSV-Gesamtexport
- PDF-Gesamtbericht einschließlich Fotos
- einzelne Messungen löschen und Messstellen archivieren

## Update einer laufenden Installation

Vorher unbedingt sichern:

```bash
cd /root/hausmonitor
./scripts/backup.sh || true
cp -a data /root/hausmonitor-data-backup
cp .env /root/hausmonitor-env-backup
```

Nach Austausch oder Git-Pull:

```bash
cd /root/hausmonitor
docker-compose down
docker-compose up -d --build
docker ps
docker logs --tail=100 hausmonitor-v4
```

Die vorhandene Datenbank `data/hausmonitor.db` bleibt erhalten. Beim ersten Start werden fehlende Tabellen und additive Spalten automatisch angelegt.

## Frische Installation

```bash
cp .env.example .env
openssl rand -hex 32
nano .env
docker-compose up -d --build
```

App im LAN: `http://IP-DES-LXC:8000`

## GitHub aktualisieren

Den entpackten Inhalt dieses Ordners in das Repository übernehmen. `.env` und `data/` gehören nicht in GitHub. Im LXC anschließend:

```bash
cd /root/hausmonitor
git pull origin main
docker-compose down
docker-compose up -d --build
```

## Backup

```bash
./scripts/backup.sh
```

Gesichert werden Datenbank, Nivellement-Fotos, Rissfotos und `.env`. Zusätzlich ist ein regelmäßiges Proxmox-LXC-Backup empfehlenswert.

## Interpretation

Statistische Signale, Regressionssteigungen und Korrelationen sind Monitoring-Hilfen. Sie ersetzen keine geotechnische, statische oder bautechnische Begutachtung.
