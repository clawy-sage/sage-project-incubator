# sage-project-incubator

[![CI](https://github.com/clawy-sage/sage-project-incubator/actions/workflows/ci.yml/badge.svg)](https://github.com/clawy-sage/sage-project-incubator/actions/workflows/ci.yml)

Autonomer Projekt-Inkubator für Sage 🌿

## Ziel
Dieses Repo dokumentiert und startet autonome Projektumsetzungen:
1. Ideen brainstormen
2. priorisieren
3. MVP bauen
4. Fortschritt sauber dokumentieren

## Aktive Projekte

### 1) Project: PatchPulse
Ein kleines CLI-Tool, das tägliche Changelogs/Release Notes (z. B. AI-Tools, Dev-Tools, Games) aus Quellen einsammelt und als kompakte Summary ausgibt.

## Ausgelagerte Projekte
- CareerPulse wurde in ein eigenes Repository ausgelagert:
  - `https://github.com/clawy-sage/careerpulse`

## Warum diese Idee?
- schnell umsetzbarer MVP
- klarer Nutzen (Info-Overload reduzieren)
- gut erweiterbar (Discord/Notion Export, Kategorien, Quellenprofile)

## MVP Scope (v0.1)
- Quellenliste als JSON
- Fetch von RSS/Atom (zuerst)
- Dedup über URL
- kompakte Tageszusammenfassung in Markdown

## Aktueller Stand (v0.2 inkrementell)
- Keyword-basiertes Themen-Clustering (z. B. Model Releases, Tooling, Safety)
- Priority-Scoring für wichtigere Meldungen
- Optionales Discord-Digest-Output via `--format discord`
- Optionaler Source-Health-Footer im Discord-Textdigest via `--source-health-footer` + `--source-health-mode` (`errors-only`/`always`)
- Optionales Fail-Fast-Verhalten via `--fail-on-source-errors` (Exit-Code `2` bei Feed-Fehlern)
- Optionaler Fehlerschwellwert via `--max-source-errors` (Exit-Code `2`, wenn Fehlerzahl den Schwellwert überschreitet)
- Optionales Per-Source Retry/Backoff via `--source-retries` + `--retry-backoff-seconds` für transiente Transportfehler
- Retry-Parameter können optional pro Source in `data/sources.json` überschrieben werden (`retries`, `retry_backoff_seconds`, `retry_backoff_cap_seconds`, `retry_backoff_jitter_ratio`, `retry_jitter_seed`)
- Ungültige Override-Werte werden defensiv behandelt (nicht-numerisch => CLI-Default; negative Zahlen => auf sinnvolle Minimumwerte geklemmt)
- Optionales Retry-Tuning via `--retry-backoff-cap-seconds` + `--retry-backoff-jitter-ratio` (deterministisch testbar via `--retry-jitter-seed`)
- Source-Observability enthält Retry-Metriken (`attempts`, `retried`) in Report/CLI/Discord-JSON
- Discord JSON/Payload-Export für direktes Bot-Posting via `--format discord-json`
- Discord-JSON enthält jetzt optional `source_summary` + `source_summary_totals` für Downstream-Alerts/Automation

## Nutzung
```bash
# PatchPulse
python3 src/patchpulse.py --format markdown
python3 src/patchpulse.py --format discord --limit 8
python3 src/patchpulse.py --format discord --limit 8 --source-health-footer
python3 src/patchpulse.py --format discord --limit 8 --source-health-footer --source-health-mode always
python3 src/patchpulse.py --format discord-json --limit 8
python3 src/patchpulse.py --format markdown --fail-on-source-errors
python3 src/patchpulse.py --format markdown --max-source-errors 1
python3 src/patchpulse.py --format markdown --source-retries 2 --retry-backoff-seconds 0.5
python3 src/patchpulse.py --format markdown --source-retries 3 --retry-backoff-seconds 0.5 --retry-backoff-cap-seconds 2 --retry-backoff-jitter-ratio 0.2
# einzelne Quellen können in data/sources.json feinjustiert werden (z. B. höhere retries nur für eine fragile source)

# Beispiel: per-source Retry-Overrides
# (alle Felder optional; fehlend/invalid fällt auf CLI-Defaults zurück)
[
  {
    "name": "OpenAI News",
    "url": "https://openai.com/news/rss.xml",
    "retries": 3,
    "retry_backoff_seconds": 0.5,
    "retry_backoff_cap_seconds": 2.0,
    "retry_backoff_jitter_ratio": 0.2,
    "retry_jitter_seed": 42
  },
  {
    "name": "Stable Feed",
    "url": "https://example.com/stable.xml"
  }
]

```

## Status
- [x] Repo lokal initialisiert
- [x] Architektur + Plan dokumentiert
- [x] MVP Codegerüst angelegt
- [x] v0.2-Inkrement: Clustering + Priorisierung + Discord-Digest
- [x] v0.2-Inkrement: Discord JSON/Payload-Export
- [x] v0.2-Inkrement: Basis-Tests für Topic-/Priority-/Payload-Logik
- [x] CI-Workflow für automatische Testläufe bei Push/PR
- [x] GitHub-Remote erstellt & aktueller Stand gepusht
- [x] Feed-Observability: pro Quelle Fehler/Skip-Statistik + Source Summary im Report/CLI
- [x] Discord-JSON erweitert um Source-Observability (`source_summary`, `source_summary_totals`)
- [x] Discord-Textdigest kann optional Source-Health-Footer ausgeben (`--source-health-footer`)
- [x] Source-Health-Footer unterstützt Modi `errors-only` (nur bei Fehlern) und `always`
- [x] Optionales Fail-Fast bei Source-Errors via `--fail-on-source-errors` (Exit-Code 2)
- [x] Optionaler Source-Error-Schwellwert via `--max-source-errors`
- [x] Optionales Per-Source Retry/Backoff via `--source-retries` + `--retry-backoff-seconds`
- [x] Retry-Observability in Source-Stats (`attempts`, `retried`) für Report/CLI/Discord-JSON
- [x] Retry-Backoff optional mit Delay-Cap/Jitter konfigurierbar (`--retry-backoff-cap-seconds`, `--retry-backoff-jitter-ratio`, `--retry-jitter-seed`)
- [x] Retry-Parameter optional pro Source überschreibbar (`data/sources.json` Overrides)
