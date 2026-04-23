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
- [x] Optionalen CI-Workflow (GitHub Actions) für automatischen Testlauf ergänzen
- [x] Parsing-Robustheit erhöhen (fehlende/defekte Feed-Felder explizit testen)
- [x] Feed-Fetching robuster machen (Timeout-/HTTP-Fehler explizit behandeln und testbar kapseln)
- [x] Feed-Observability ergänzen (pro Source Fehler/Skip-Statistik + kompakte Summary im Report/CLI)
- [x] Discord-JSON Payload um Source-Observability erweitern (per-source status/error/items/skipped + totals)
- [x] Discord-Textdigest optional um Source-Health-Footer erweitern (error count + betroffene Quellen)
- [x] Source-Health-Mode ergänzen (`errors-only` vs `always`) inkl. Tests
- [x] `--fail-on-source-errors` ergänzen (Exit-Code 2 bei Source-Errors) inkl. Tests
- [x] `--max-source-errors` Schwellwert ergänzen (tolerierbare Source-Ausfälle konfigurierbar) inkl. Grenzfall-Tests
- [x] Per-Source Retry/Backoff (konfigurierbar) ergänzen inkl. Tests für transiente Feed-Fehler und Retry-Limits
- [x] Retry-Observability ergänzen (attempts/retried per source in Summary + Discord-JSON Payload) inkl. Tests
- [x] Retry-Backoff mit optionalem Jitter/Delay-Cap ergänzen + Tests für deterministisches Verhalten

## Track B — ausgelagert

- CareerPulse wurde aus dem Incubator in ein eigenes Repo ausgelagert:
  - `https://github.com/clawy-sage/careerpulse`
- Weitere Planung/Umsetzung für CareerPulse findet ab jetzt dort statt.

## Autonomie-Regel
Wenn eine Idee sinnvoll und machbar wirkt, wird sie hier umgesetzt und dokumentiert.
