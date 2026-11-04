# Log Monitoring & Analysis Platform

Mini-Project ELK / NoSQL / Docker - IT Business School (3GLA, Scenario D: SaaS)
Student: Ghalia Bellalouna - Instructor: Mr. Mohamed Najeh Issaoui

Upload CSV / JSON / TXT log files, index them with Logstash into Elasticsearch, then search, export and visualize them (Flask web app + Kibana). Module G adds alerting; module K adds tests and CI.

## Stack
Flask 3, Elasticsearch 8, Logstash 8, Kibana 8, MongoDB 7, Redis 7, Docker Compose.

## Quick start
> Available from week 2 (`docker-compose.yml` not added yet).

```bash
cp .env.example .env
docker compose up
```
Web app: http://localhost:8000 - Kibana: http://localhost:5601

## Repository layout
| Path | Content |
|---|---|
| `webapp/` | Flask app (API + Jinja2 UI) |
| `alert-worker/` | Alert evaluation worker (module G) |
| `logstash/pipelines/` | csv / json (+txt) pipelines |
| `elasticsearch/` | Index template `logs-saas-*` |
| `kibana/` | Exported visualizations and dashboard (ndjson) |
| `scripts/` | Faker log generator |
| `tests/` | pytest suite (module K) |
| `uploads/` | Shared volume watched by Logstash (git-ignored) |
| `docs/` | Analysis, architecture, figures |
| `.github/workflows/` | CI (module K) |

## Documentation
- `docs/figures/ELK_architecture_figures.drawio` - C4 and sequence diagrams
- Analysis and architecture documents: add exports to `docs/`

## Progress
| Week | Epic | Status |
|---|---|---|
| W1 | Analysis and design | In progress |
| W2 | Setup and infrastructure | Not started |
| W3 | Backend core | Not started |
| W4 | Frontend and Kibana | Not started |
| W5 | Modules G and K | Not started |
| W6 | Finalize and deliver | Not started |

## Workflow
- Branches: `main` (stable) and short-lived `feature/ELK-<n>-<name>` branches, merged by pull request.
- Commits reference the Jira key, e.g. `ELK-12: add Flask skeleton`.
