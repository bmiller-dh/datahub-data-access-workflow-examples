# Mock server (with UI)

Flask server that:

1. **Receives POSTs** from DataHub action pipelines at configurable endpoints.
2. **Web UI** at `http://localhost:8000/`: lists **pending Data Access Requests** (Approve/Deny) and **Recent approvals**, **Recent metadata proposals**, **Recent glossary proposals**, and **Recent certification events** when the corresponding pipelines are running and POST to this server. Glossary proposals are notifications only; approve or deny them in DataHub.

For the UI to list and approve/deny requests, the server needs **DATAHUB_URL** and **DATAHUB_TOKEN** (same as the examples project). **Rebuild the Docker image** after pulling or changing mock-server code so the dashboard shows all sections.

## Run with Docker

```bash
# Build
docker build -t grant-permissions-mock .

# Run with DataHub env (so the UI can list pending and Approve/Deny)
docker run --rm -d -p 8000:8000 --name grant-permissions-mock \
  -e DATAHUB_URL=https://your-instance.acryl.io \
  -e DATAHUB_TOKEN=your_personal_access_token \
  grant-permissions-mock

# Or use the parent project’s .env (from datahub-data-access-workflow-examples)
docker run --rm -d -p 8000:8000 --name grant-permissions-mock \
  --env-file ../.env \
  grant-permissions-mock

# Check health
curl http://localhost:8000/health

# Open UI
open http://localhost:8000/

# Stop
docker stop grant-permissions-mock
```

Without `DATAHUB_URL` and `DATAHUB_TOKEN`, the server still runs and receives POSTs from the pipeline, but the UI will show “Set DATAHUB_URL and DATAHUB_TOKEN for Approve/Deny”.

## Run locally (no Docker)

```bash
pip install -r requirements.txt
export DATAHUB_URL=https://your-instance.acryl.io
export DATAHUB_TOKEN=your_token
python app.py
```

Then open **http://localhost:8000/** to see pending requests and use **Approve** / **Deny**.

## Endpoints

| Route | Description |
|-------|-------------|
| `GET /` | Web UI: pending requests (Approve/Deny) + recent approvals, metadata proposals, glossary proposals, certification events |
| `GET /health` | Health check |
| `GET /api/pending` | JSON: pending Data Access Requests (assigned to token user) |
| `POST /api/review` | JSON body: `{ "requestUrn": "...", "result": "ACCEPTED"\|"REJECTED", "comment": "..." }` – calls DataHub review API |
| `GET /api/activity` | JSON: recent payloads received at `/grant_permissions` |
| `POST /grant_permissions` | Called by the grant-external-permissions pipeline when a request is approved |
| `GET /api/metadata_proposals` | JSON: recent payloads received at `/metadata_proposals` |
| `POST /metadata_proposals` | Called by the metadata-proposal-pipeline |
| `GET /api/glossary_proposals` | JSON: recent payloads received at `/glossary_proposals` |
| `POST /glossary_proposals` | Called by the glossary-proposal-pipeline |
| `GET /api/certification_events` | JSON: recent payloads received at `/certification_events` |
| `POST /certification_events` | Called by the certification-event-pipeline |

---

## How to test (end-to-end)

**1. Start the mock server** (with DataHub credentials so the UI works):

```bash
cd datahub-data-access-workflow-examples/mock-server
docker build -t grant-permissions-mock .
docker run --rm -d -p 8000:8000 --name grant-permissions-mock --env-file ../.env grant-permissions-mock
```

**2. Start the grant-external-permissions pipeline** (in another terminal):

```bash
cd datahub-data-access-workflow-examples
source venv/bin/activate
set -a && source .env && set +a
datahub actions -c src/grant-external-permissions-pipeline.yaml
```

**3. Open the UI:**  
Go to **http://localhost:8000/** in your browser.

- You should see **“DataHub configured”** and a **Pending requests (yours)** section.
- If you have a pending Data Access Request assigned to you, it will appear with **Approve** and **Deny** buttons.

**4. Click Approve** on a request:

- The UI sends the review to DataHub.
- The pipeline receives the approval event and POSTs to the mock server.
- Within a few seconds, **“Recent approvals received (from pipeline)”** should show the new event (scroll down; page auto-refreshes every 5 seconds). The same dashboard has **Recent metadata proposals**, **Recent glossary proposals**, and **Recent certification events** when those pipelines are running and POST to this server.

**5. (Optional) Create a new request in DataHub** if you have none:

- In DataHub, open any **Dataset** → click the unlock / **Request Access** button → submit the form.
- If you’re the dataset owner (or assigned reviewer), the request will appear in the mock UI under **Pending requests (yours)**. Click **Approve** or **Deny** to test.

**6. Stop when done:**

```bash
docker stop grant-permissions-mock
# Stop the pipeline with Ctrl+C in its terminal
```

---

## Testing certification events

**Quick check (no DataHub needed):** Confirm the "Recent certification events" section works by sending a fake event:

```bash
curl -s -X POST http://localhost:8000/certification_events \
  -H "Content-Type: application/json" \
  -d '{"eventType":"certification_structured_property","entityUrn":"urn:li:dataset:(urn:li:dataPlatform:bigquery,example.table,PROD)","operation":"UPSERT"}'
```

Then open **http://localhost:8000/** and scroll to **"Recent certification events"** — you should see one row (page refreshes every 5s, or refresh manually).

**Full flow (real certification from DataHub):**

1. **Mock server** running at http://localhost:8000 (with the certification routes).
2. **Certification pipeline** running:  
   `datahub actions -c src/certification-event-pipeline.yaml`
3. **In DataHub**, trigger a structured-property change on an asset:
   - **Option A:** Create a **Structured Property** (Govern → Settings → Structured Properties), then a **VERIFICATION** Compliance Form that uses it (or use `scripts/certification/create_asset_certification_form.py`). Assign the form to a dataset, open the form as the assignee, complete and verify — that sets the property and emits an event.
   - **Option B:** If your DataHub UI lets you edit structured properties on an asset (e.g. on the dataset profile), set or change one there.
4. Within a few seconds the pipeline should POST to the mock server; **"Recent certification events"** on http://localhost:8000/ will show the event.
