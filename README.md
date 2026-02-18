This repo contains examples for using [DataHub Data Access Workflows](https://docs.datahub.com/docs/managed-datahub/workflows/access-workflows) in conjunction with the [DataHub Actions Framework](https://docs.datahub.com/docs/actions) to integrate with external tools.

- **[Step-by-step guide](#step-by-step-data-access-request--approve--grant-eg-mock-server)** – Data Access Request → list pending → approve → grant pipeline → mock server (full flow).
- **See [WORKFLOWS.md](WORKFLOWS.md)** for how to implement: (1) Data Product Access Requests, (2) Asset Certification, (3) Metadata Approval (Proposal Workflows), and (4) Glossary Approval using what’s built here.

---

# Step-by-step: Data Access Request → Approve → Grant (e.g. mock server)

End-to-end flow: create a workflow, run the grant pipeline, list your pending requests, approve one, and see the approval event hit an external endpoint (mock server).

**Prerequisites:** DataHub instance (e.g. DataHub Cloud), Personal Access Token, Python 3.10+.

### Step 1 – One-time setup

```sh
cd datahub-data-access-workflow-examples
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -e .
cp .env.example .env
# Edit .env: set DATAHUB_URL and DATAHUB_TOKEN
```

### Step 2 – Create the Data Access Workflow (once per instance)

```sh
# From datahub-data-access-workflow-examples with venv activated and .env set
set -a && source .env && set +a
python scripts/data_access/create_data_access_workflow.py
```

Note the workflow URN printed (e.g. `urn:li:actionWorkflow:xxxxxxxx-xxxx-...`). Open `src/grant-external-permissions-pipeline.yaml` and set `filter.event.parameters.workflowId` to the short ID (the UUID part, e.g. `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).

### Step 3 – (Optional) Run the mock server (with UI)

To simulate an external system that receives approved requests and to use a **web UI** to Approve/Deny requests:

```sh
cd mock-server
docker build -t grant-permissions-mock .
docker run --rm -d -p 8000:8000 --name grant-permissions-mock --env-file ../.env grant-permissions-mock
# Open http://localhost:8000/ to see pending requests and Approve/Deny buttons
# Check: curl http://localhost:8000/health
```

The pipeline is configured to POST to `http://localhost:8000/grant_permissions` when a request is approved. With `--env-file ../.env`, the mock server can list pending requests and call DataHub’s review API when you click Approve or Deny in the UI. **See [mock-server/README.md](mock-server/README.md#how-to-test-end-to-end) for a full test procedure.**

### Step 4 – Start the grant-external-permissions pipeline

```sh
cd datahub-data-access-workflow-examples
source venv/bin/activate
set -a && source .env && set +a
datahub actions -c src/grant-external-permissions-pipeline.yaml
```

Leave this running (or run in background). It will receive events when requests are approved.

### Step 5 – List pending requests assigned to you

From the **repo root** (`workflows/`) you can use the wrapper (uses the project venv and .env automatically):

```sh
cd /path/to/workflows
python scripts/data_access/list_pending_data_access_requests.py --mine --status PENDING
```

Or from inside the examples project:

```sh
cd datahub-data-access-workflow-examples
source venv/bin/activate && set -a && source .env && set +a
python scripts/data_access/list_pending_data_access_requests.py --mine --status PENDING
```

Copy a request URN from the output (e.g. `urn:li:actionRequest:xxxxxxxx-...`).

### Step 6 – Approve (or reject) the request

```sh
cd datahub-data-access-workflow-examples
source venv/bin/activate && set -a && source .env && set +a
python scripts/data_access/review_data_access_request.py --request-urn "urn:li:actionRequest:xxxxxxxx-..." --result ACCEPTED --comment "Approved"
```

To reject: use `--result REJECTED`.

### Step 7 – Verify the external system received the approval

If the mock server is running, the pipeline will POST the approval payload to it.

- **In the mock UI:** Open **http://localhost:8000/** and check the **“Recent approvals received (from pipeline)”** section at the bottom (auto-refreshes every 5 seconds).
- **In logs:** `docker logs grant-permissions-mock` — you should see a line like `POST /grant_permissions received` with `entityUrn`, `actorUrn`, `result: ACCEPTED`.

---

# How to run the other workflows (2, 3, 4)

Use the same setup: from `datahub-data-access-workflow-examples`, activate the venv and load `.env`, then run the pipeline. Each pipeline logs matching events; you can set `external_uri` in the pipeline config to POST to your own service.

### 2. Asset Certification

**What it does:** Listens for **structured property** changes on entities (e.g. when someone completes a Compliance Form that sets a certification property).

**Run the pipeline:**

```sh
cd datahub-data-access-workflow-examples
source venv/bin/activate
set -a && source .env && set +a
datahub actions -c src/certification-event-pipeline.yaml
```

**Optional – create a VERIFICATION Compliance Form via API:**  
Create a structured property in DataHub first (Govern → Settings → Structured Properties), then:

```sh
python scripts/certification/create_asset_certification_form.py --form-id asset-cert-2024 --property-urn "urn:li:structuredProperty:yourCertPropertyUrn"
```

**How to trigger:** In DataHub, add or change a structured property on a dataset (e.g. via a Compliance Form or the asset profile). The pipeline will log the event.

---

### 3. Metadata Approval (proposals)

**What it does:** Listens for **metadata proposals** (tag, owner, domain, description, structured property). Logs each proposal; optional `external_uri` to forward to ticketing/approval.

**Run the pipeline:**

```sh
cd datahub-data-access-workflow-examples
source venv/bin/activate
set -a && source .env && set +a
datahub actions -c src/metadata-proposal-pipeline.yaml
```

**How to trigger:** In DataHub, **propose** a tag, owner, domain, description, or structured property on an asset (e.g. suggest a tag on a dataset). The pipeline will log it. To forward to a URL, add `external_uri: "http://your-service/..."` under `action.config` in `src/metadata-proposal-pipeline.yaml`.

---

### 4. Glossary Approval (proposals)

**What it does:** Listens for **glossary proposals** (new term or term association to an asset). Logs each proposal; optional `external_uri` to forward.

**Run the pipeline:**

```sh
cd datahub-data-access-workflow-examples
source venv/bin/activate
set -a && source .env && set +a
datahub actions -c src/glossary-proposal-pipeline.yaml
```

**How to trigger:** In DataHub, **propose** a new glossary term or propose adding a glossary term to a dataset. The pipeline will log it. To forward to a URL, add `external_uri` under `action.config` in `src/glossary-proposal-pipeline.yaml`.

---

# Dependencies

```sh
pip install -e .
```

# Configuration

Scripts and action pipelines use **environment variables** for the DataHub URL and token (no secrets in repo).

1. Copy the example env file and set your values:
   ```sh
   cp .env.example .env
   # Edit .env: set DATAHUB_URL and DATAHUB_TOKEN
   ```
2. Load the variables before running (e.g. in your shell or via `source .env` if your shell supports it):
   ```sh
   export DATAHUB_URL=https://<instance-name>.acryl.io
   export DATAHUB_TOKEN=<personal access token>
   ```
   For a `.env` file, you can use `set -a && source .env && set +a` (bash/zsh) or a tool like [direnv](https://direnv.net/). Do not commit `.env`.

Required variables:

- **DATAHUB_URL** – DataHub instance URL (e.g. `https://<instance-name>.acryl.io`)
- **DATAHUB_TOKEN** – [Personal Access Token](https://docs.datahub.com/docs/authentication/personal-access-tokens)

## Creating a DataHub Data Access Workflow

The script `scripts/data_access/create_data_access_workflow.py` will create an example Data Access Workflow.

Set `DATAHUB_URL` and `DATAHUB_TOKEN` (see [Configuration](#configuration)), then run:

```sh
python scripts/data_access/create_data_access_workflow.py
```

You should now be able to see your Data Access Workflow and make a Data Access Request by going to any Dataset page and clicking the "unlock" icon on the top right of the main entity header (next to the "View in {platform}" button).


# Examples

## Simple Action

The file `src/simple_action.py` implements a simple example DataHub Action that listens for all events pertaining to Data Access Requests and prints them to your terminal.

1. Set `DATAHUB_URL` and `DATAHUB_TOKEN` (see [Configuration](#configuration)).
2. Edit `src/simple-pipeline.yaml`: set `filter.event.parameters.workflowId` to the URN of your Data Access Workflow (must be already created).

To run:

```sh
datahub actions -c src/simple-pipeline.yaml
```

## Grant External Permissions Action

The file `src/grant_external_permissions_action.py` implements a simple example DataHub Action that listens for accepted Data Access Requests and sends them off to an external system. This can be used to approve data requests inside DataHub itself, then grant permissions in an external system.

1. Set `DATAHUB_URL` and `DATAHUB_TOKEN` (see [Configuration](#configuration)).
2. Edit `src/grant-external-permissions-pipeline.yaml`: set `filter.event.parameters.workflowId` to the URN of your Data Access Workflow (must be already created).
3. Implement logic that grants permissions inside an external system. Currently, this action simply sends the raw parameters to an imaginary HTTP endpoint.

To run:

```sh
datahub actions -c src/grant-external-permissions-pipeline.yaml
```

## Create External Access Request Action

The file `src/create_external_access_request_action.py` implements a simple example DataHub Action that listens for new Data Access Requests and sends them off to an external system. This can be used to allow users to request data inside DataHub itself, but send the request off to an external system to manage the request workflow and lifecycle elsewhere.

1. Set `DATAHUB_URL` and `DATAHUB_TOKEN` (see [Configuration](#configuration)).
2. Edit `src/create-external-access-request-pipeline.yaml`: set `filter.event.parameters.workflowId` to the URN of your Data Access Workflow (must be already created).
3. Implement logic that creates a request in an external system and stores a reference tying it back to the access request inside DataHub. Currently, this action simply sends the raw parameters to an imaginary HTTP endpoint.

To run:

```sh
datahub actions -c src/create-external-access-request-pipeline.yaml
```

This should also be paired with logic to take the result of the workflow in the external system and push it back into DataHub, so users can be notified that their request has been approved or denied. An example script for programmatically approving or denying a Data Access Request is `scripts/data_access/review_data_access_request.py`.

Set `DATAHUB_URL` and `DATAHUB_TOKEN` (see [Configuration](#configuration)).

To list pending (or all) Data Access Requests and get their URNs:

```sh
python scripts/data_access/list_pending_data_access_requests.py                    # all workflow form requests
python scripts/data_access/list_pending_data_access_requests.py --status PENDING   # pending only
python scripts/data_access/list_pending_data_access_requests.py --mine --status PENDING   # only requests assigned to you (so you can approve them)
```

Then approve or reject:

```sh
python scripts/data_access/review_data_access_request.py --request-urn <request_urn> --result ACCEPTED --comment "Approved"
# or --result REJECTED
```

## Other pipelines (see [WORKFLOWS.md](WORKFLOWS.md))

- **`src/metadata-proposal-pipeline.yaml`** – **Metadata Approval (#3).** Listens for metadata proposals (tag, owner, domain, description, structured property). Uses `metadata_proposal_action`; optional `external_uri` to forward to a ticketing/approval system.
- **`src/glossary-proposal-pipeline.yaml`** – **Glossary Approval (#4).** Listens for glossary proposals (term association, create glossary term). Uses `glossary_proposal_action`; optional `external_uri` to forward.
- **`src/certification-event-pipeline.yaml`** – **Asset Certification (#2).** Listens for structured property changes on entities (e.g. from Compliance Forms). Uses `certification_event_action`; optional `external_uri` to forward.

Run with: `datahub actions -c src/<pipeline>.yaml` (after setting env vars).

## Asset Certification (Compliance Forms)

For Requirement #2 (Asset Certification), use DataHub Compliance Forms (VERIFICATION type) and Structured Properties. Optionally create a form via API:

```sh
python scripts/certification/create_asset_certification_form.py --form-id asset-cert-2024 --property-urn "urn:li:structuredProperty:yourCertProperty"
```

Create the structured property in DataHub first (Govern > Settings > Structured Properties). Then assign the form to entities via the UI or GraphQL `batchAssignForm`.