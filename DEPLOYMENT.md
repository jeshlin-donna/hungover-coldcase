# ColdCache deployment guide

Last verified: 2026-07-05.

ColdCache is stateful. A correct deployment must persist all four stores together:

1. application SQLite (`coldcache.db`)
2. uploaded case files (`cases/`)
3. Cognee data/vector storage
4. Cognee system metadata/cache

A stateless free web service is not sufficient. Losing any one store can leave the case list, evidence, or knowledge graph inconsistent.

## Recommended free topology

Use one **Oracle Cloud Always Free Ampere A1 VM** for the Docker Compose stack:

```text
Internet -> Caddy (TLS + Basic Auth)
              |-- /       -> static React/Nginx
              `-- /api/*  -> FastAPI (one worker)
                                  |
                                  `-- one persistent Docker volume
                                      |-- app SQLite + evidence
                                      `-- Cognee graph/vector/system data
```

This is the best zero-cost fit because OCI documents Always Free A1 capacity equivalent to 2 OCPUs / 12 GB RAM plus Always Free block storage, while ColdCache needs durable local storage and a long-running worker. Groq or xAI runs the LLM remotely, so the VM does not need Ollama.

Caveats: A1 capacity can be unavailable in a region, and Oracle may reclaim idle Always Free instances. Keep tested backups off the VM.

## 1. Provision the server

1. Create an OCI Always Free `VM.Standard.A1.Flex` Ubuntu instance in the tenancy's home region.
2. Allocate the available 2 OCPUs / 12 GB RAM if possible.
3. Give it an Always Free boot/block volume and a reserved public IP.
4. Open inbound TCP 22, 80, and 443. Do not expose port 8000.
5. Point a DNS `A` record such as `coldcache.example.com` at the public IP.
6. Install Git and Docker Engine with the Docker Compose plugin.

## 2. Deploy from GitHub

```bash
git clone https://github.com/samuelshine/hungover-coldcase.git
cd hungover-coldcase
cp .env.production.example .env.production
```

Edit `.env.production`: set `DOMAIN`, `LLM_API_KEY`, and the Basic Auth username. Generate a password hash:

```bash
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'use-a-long-password'
```

Put the hash inside single quotes in `BASIC_AUTH_HASH`, then deploy:

```bash
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build
docker compose --env-file .env.production -f docker-compose.production.yml ps
```

Caddy obtains HTTPS after DNS resolves. The site and API are protected by Basic Auth; the LLM key remains backend-only.

## 3. Provider choice: Groq vs Grok

These are different products.

### Groq (recommended zero-cost starting point)

The production template uses Groq's OpenAI-compatible endpoint:

```dotenv
LLM_PROVIDER=custom
LLM_MODEL=groq/llama-3.1-8b-instant
LLM_ENDPOINT=https://api.groq.com/openai/v1
LLM_API_KEY=gsk_...
```

Groq publishes free-plan rate limits. ColdCache persists failures for retry, but the cloud deployment deliberately has no local Ollama fallback.

### xAI Grok

If “Grok” means xAI's model, use:

```dotenv
LLM_PROVIDER=custom
LLM_MODEL=xai/grok-4.3
LLM_ENDPOINT=https://api.x.ai/v1
LLM_API_KEY=xai_...
```

The direct case chat/interrogation/what-if path supports xAI's OpenAI-compatible Chat Completions endpoint. xAI's API quickstart requires an account loaded with credits, so it is not the free option. Run a real keyed ingestion smoke test before relying on xAI for Cognee structured extraction; this audit did not have an xAI key to verify that provider-specific path.

## 4. Verify after deployment

```bash
curl -u investigator:'your-password' https://coldcache.example.com/api/health
curl -u investigator:'your-password' https://coldcache.example.com/api/ready
```

`/ready` must report writable storage, a reachable database, and `mode: live`.

Acceptance test:

1. Create a case.
2. Upload text plus an image/PDF in one drag-and-drop batch.
3. Leave optional context blank on one non-text file and provide it on another.
4. Wait for analysis, edit the extracted draft, and confirm it.
5. Wait for ingestion and inspect Evidence Board, Timeline, Interrogation, What-If, and Case Chat.
6. Reload, return to All Cases, reopen the case, and verify its evidence remains.
7. Restart the stack and repeat the persistence check.
8. Test a backup restore on a disposable instance.

## 5. Backups and updates

The backup script consistently copies SQLite and case files. Also archive the whole `coldcache_data` Docker volume so Cognee storage is included, and keep a copy outside OCI.

Update without deleting volumes:

```bash
git pull --ff-only
docker compose --env-file .env.production -f docker-compose.production.yml up -d --build
```

Never run `docker compose down -v` unless permanent data deletion is intentional.

## Optional split frontend

Cloudflare Pages can host the Vite frontend on its Free plan:

- root directory: `frontend`
- build command: `npm ci && npm run build`
- output directory: `dist`
- `VITE_API_BASE=https://api.example.com`

The included `_headers` and `_redirects` provide security headers and SPA routing. The backend still belongs on the durable VM, and `CORS_ORIGINS` must equal the exact frontend origin. Protect the backend with a real access layer; a static frontend cannot safely hold an API password or LLM secret.

Vercel Hobby is another suitable static-frontend option using `frontend/vercel.json`. It does not solve backend persistence.

## Platform fit

| Platform | Free frontend | Free backend | ColdCache verdict |
|---|---:|---:|---|
| Cloudflare Pages | yes | Workers, not this Python/Cognee runtime | good frontend only |
| Vercel Hobby | yes | serverless/ephemeral | good frontend only |
| Render | yes | free service is ephemeral and sleeps | demo only; cases disappear on restart |
| Render paid + disk | yes | durable | supported by `render.yaml`, but not free |
| OCI Always Free VM | included | long-running VM + block storage | recommended free full stack |

`render.yaml` now intentionally uses Render's paid `starter` plan because Render only attaches persistent disks to paid services. This prevents a data-losing “free persistent” deployment.

## Production boundaries

- Run exactly one FastAPI process with embedded SQLite/LanceDB/graph storage. Horizontal workers require a Postgres/object-store/remote-graph migration.
- Basic Auth is suitable for a private demo or small preview, not a substitute for per-user identity, audit logging, or evidence-level authorization.
- Do not host sensitive real-world evidence until retention, encryption, access control, legal jurisdiction, malware scanning, and incident response requirements are defined.
- Free tiers have quotas and can change. Confirm limits before deploying.
