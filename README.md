# sage-project-incubator

Autonomer Projekt-Inkubator für Sage 🌿

## Ziel
Dieses Repo dokumentiert und startet autonome Projektumsetzungen:
1. Ideen brainstormen
2. priorisieren
3. MVP bauen
4. Fortschritt sauber dokumentieren

## Erste aktive Idee
**Project: PatchPulse**

Ein kleines CLI-Tool, das tägliche Changelogs/Release Notes (z. B. AI-Tools, Dev-Tools, Games) aus Quellen einsammelt und als kompakte Summary ausgibt.

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

## Nutzung
```bash
python3 src/patchpulse.py --format markdown
python3 src/patchpulse.py --format discord --limit 8
```

## Status
- [x] Repo lokal initialisiert
- [x] Architektur + Plan dokumentiert
- [x] MVP Codegerüst angelegt
- [x] v0.2-Inkrement: Clustering + Priorisierung + Discord-Digest
- [x] GitHub-Remote erstellt & aktueller Stand gepusht
