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
- Discord JSON/Payload-Export für direktes Bot-Posting via `--format discord-json`

## Nutzung
```bash
# PatchPulse
python3 src/patchpulse.py --format markdown
python3 src/patchpulse.py --format discord --limit 8
python3 src/patchpulse.py --format discord-json --limit 8

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
