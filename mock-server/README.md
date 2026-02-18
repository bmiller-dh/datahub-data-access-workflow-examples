# Mock grant_permissions server (with UI)

Flask server that:

1. **Receives POSTs** from the **grant-external-permissions** DataHub action when a Data Access Request is approved (payload at `http://localhost:8000/grant_permissions`).
2. **Web UI** at `http://localhost:8000/`: lists **pending Data Access Requests** assigned to you and provides **Approve** / **Deny** buttons that call DataHub’s review API.

For the UI to list and approve/deny requests, the server needs **DATAHUB_URL** and **DATAHUB_TOKEN** (same as the examples project).

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
| `GET /` | Web UI: pending requests (Approve/Deny) + recent pipeline events |
| `GET /health` | Health check |
| `GET /api/pending` | JSON: pending Data Access Requests (assigned to token user) |
| `POST /api/review` | JSON body: `{ "requestUrn": "...", "result": "ACCEPTED"\|"REJECTED", "comment": "..." }` – calls DataHub review API |
| `GET /api/activity` | JSON: recent payloads received at `/grant_permissions` |
| `POST /grant_permissions` | Called by the grant-external-permissions pipeline when a request is approved |

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
- Within a few seconds, **“Recent approvals received (from pipeline)”** at the bottom of the page should show the new event (page auto-refreshes every 5 seconds).

**5. (Optional) Create a new request in DataHub** if you have none:

- In DataHub, open any **Dataset** → click the unlock / **Request Access** button → submit the form.
- If you’re the dataset owner (or assigned reviewer), the request will appear in the mock UI under **Pending requests (yours)**. Click **Approve** or **Deny** to test.

**6. Stop when done:**

```bash
docker stop grant-permissions-mock
# Stop the pipeline with Ctrl+C in its terminal
```
