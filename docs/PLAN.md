# Plan: Project Incubator

## Track A — PatchPulse

### Milestones

### M1 – Core
- Feed-Liste laden
- RSS/Atom einlesen
- Items normalisieren

### M2 – Output
- Duplikate filtern
- Tagesreport generieren (`reports/YYYY-MM-DD.md`)
- Themen-Clustering + Priorisierung in Reports

### M3 – Ops
- CLI Flags
- Exit-Codes + Logging
- Cron-ready Ausführung
- Optionales Discord-Digest-Format (`--format discord`)

### M4 – Nächster Inkrement-Fokus
- [x] Discord Digest direkt als Message-Payload exportieren (z. B. JSON für Bot-Posting)
- [x] Basis-Tests für Topic-Klassifizierung, Priority-Scoring und Payload-Rendering ergänzen

### M5 – Als Nächstes
- Parsing-Robustheit erhöhen (fehlende/defekte Feed-Felder explizit testen)
- Optionalen CI-Workflow (GitHub Actions) für automatischen Testlauf ergänzen

## Track B — CareerPulse

### C1 – Iteration 1 (DONE)
- [x] Projekt-Scaffold (`src/careerpulse.py`)
- [x] Sample-Opportunity-Dataset (`data/careerpulse_sample.json`)
- [x] Erstes Ranking-Modell (Skill-Match + Remote-Fit + Seniority-Fit)
- [x] Report-Outputs (`reports/careerpulse-YYYY-MM-DD.md|json`)

### C2 – Als Nächstes
- Adapter für echte Quellen (z. B. Lever/Greenhouse RSS/API, optional GitHub Jobs-ähnliche Feeds)
- Simple Profil-Konfig (`configs/careerpulse_profile.json`) statt CLI-Defaults
- Discord-Digest-Output analog zu PatchPulse

## Autonomie-Regel
Wenn eine Idee sinnvoll und machbar wirkt, wird sie hier umgesetzt und dokumentiert.
