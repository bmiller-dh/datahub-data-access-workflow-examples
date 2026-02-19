# Implementing the Four Workflow Requirements

This doc maps each requirement to what’s in this repo and how to run or extend it.

---

## 1. Data Product Access Requests

**Status:** Native support via Data Access Workflows (Private Beta).  
**Recommendation:** Use the existing Data Access Workflows; demo from your Demo Environment.

### What’s already built

- **Create the workflow:** `scripts/data_access/create_data_access_workflow.py`  
  Creates an ACCESS workflow with FORM_SUBMITTED trigger and APPROVAL step (e.g. “Dataset Access Request”). You already ran this and got a workflow URN.
- **React to requests (Actions):** Pipelines that listen for `actionRequest` events with `actionRequestType: "WORKFLOW_FORM_REQUEST"` and `workflowId` set to your workflow URN:
  - `src/simple-pipeline.yaml` – log events
  - `src/create-external-access-request-pipeline.yaml` – send new requests to an external system
  - `src/grant-external-permissions-pipeline.yaml` – when a request is accepted, call an external system to grant permissions
- **Approve/reject programmatically:** `scripts/data_access/review_data_access_request.py` – call with `--request-urn`, `--result ACCEPTED|REJECTED`, `--comment "..."`.
- **Optional mock server with UI:** The `mock-server/` app can receive approval POSTs from the grant pipeline and provides a web UI at http://localhost:8000/ to list **pending requests assigned to you** and click **Approve** or **Deny**. See the main [README step-by-step](README.md#step-by-step-data-access-request--approve--grant-eg-mock-server) and [mock-server/README.md](mock-server/README.md).

### How to run / demo

1. Ensure `DATAHUB_URL` and `DATAHUB_TOKEN` are set (e.g. from `.env`).
2. Create the workflow (if not already done):  
   `python scripts/data_access/create_data_access_workflow.py`
3. In each pipeline YAML you use, set `filter.event.parameters.workflowId` to your workflow URN (e.g. `d4b1fee1-e3e3-44e4-90ce-f947f8f76594` or the full URN).
4. Run an action pipeline, e.g.:  
   `datahub actions -c src/simple-pipeline.yaml`
5. In the UI, open a Dataset and use the “Request Access” (unlock) CTA to submit a request; the action will see the event.
6. To approve/reject from the CLI:  
   `python scripts/data_access/review_data_access_request.py --request-urn <request_urn> --result ACCEPTED --comment "Approved"`

### Optional: “Data Product” variant

Use the same script and workflow; the workflow is already generic (e.g. “Dataset Access Request”). To have a separate “Data Product Access Request” workflow, duplicate the script and change `name` and `description` (and optionally `entityTypes` or form fields). The same pipelines and review script work for any workflow URN you create.

---

## 2. Asset Certification

**Status:** Partial support.  
**Recommendation:** Use **Compliance Forms (VERIFICATION type)** plus **Structured Properties**.

### What DataHub provides

- **Compliance Forms** (Govern > Compliance Forms): type **VERIFICATION** so assignees must complete questions and then explicitly verify (sign-off).
- **Structured Properties** on assets (e.g. “Certification Status”, “Certified By”, “Certified Date”) can be collected and set via form prompts.
- Forms can be created in the UI (DataHub Cloud) or via the **Forms API** (GraphQL `createForm` / `updateForm` / `batchAssignForm`).

### What you can do in this repo

- **Option A – UI:** In DataHub Cloud, create a VERIFICATION form, add questions (e.g. Structured Property prompts), assign assets and assignees, publish. No code in this repo required.
- **Option B – API:** Use the [Compliance Forms API](https://docs.datahub.com/docs/api/tutorials/forms) (e.g. `createForm` with `type: VERIFICATION` and `STRUCTURED_PROPERTY` prompts). You can add a script here that calls the same GraphQL endpoint you use for workflows (`DATAHUB_URL` + `DATAHUB_TOKEN`) and runs `createForm` + `batchAssignForm` so certification is defined in code.
- **Option C – React to certification updates:** **`src/certification-event-pipeline.yaml`** uses **`certification_event_action`** to listen for `EntityChangeEvent_v1` with `category: "STRUCTURED_PROPERTY"`. It logs each change and optionally POSTs to `config.external_uri` (e.g. audit or notification service).

### Optional pipeline for certification-related events

`src/certification-event-pipeline.yaml` (included below) listens for **Structured Property** changes on entities. When an asset gets a structured property (e.g. from a Compliance Form), the action runs. You can replace the action with one that updates a catalog, sends a notification, or calls an external system.

---

## 3. Metadata Approval (Proposal Workflows)

**Status:** Proposals are native; approval can be wired to a Data Workflow Action.  
**Recommendation:** Use the Actions framework to listen for **metadata proposal** events and integrate with your approval/ticketing system.

### What DataHub provides

- Users can **propose** metadata changes: Tags, Glossary Terms, Owners, Domains, Descriptions, Structured Properties.
- Proposals create **actionRequest** entities. Reviewers approve/reject in the UI (inbox).
- The Actions framework emits **EntityChangeEvent_v1** for these with `entityType: "actionRequest"`, `category: "LIFECYCLE"`, `operation: "CREATE"`, and `parameters.actionRequestType` set to e.g.:
  - `TAG_ASSOCIATION`
  - `TERM_ASSOCIATION` (glossary term on asset)
  - `OWNER_ASSOCIATION`
  - `DOMAIN_ASSOCIATION`
  - `UPDATE_DESCRIPTION`
  - `STRUCTURED_PROPERTY_ASSOCIATION`

### What’s in this repo

- **`src/metadata-proposal-pipeline.yaml`** – Listens for **actionRequest** lifecycle events (filter relaxed so CREATE and other operations are received). Uses **`metadata_proposal_action`**, which handles TAG_ASSOCIATION, OWNER_ASSOCIATION, DOMAIN_ASSOCIATION, UPDATE_DESCRIPTION, STRUCTURED_PROPERTY_ASSOCIATION. Logs each event and POSTs to `config.external_uri` when set (e.g. `http://localhost:8000/metadata_proposals` for the mock dashboard).

### How to run

1. Set `DATAHUB_URL` and `DATAHUB_TOKEN`.
2. Run:  
   `datahub actions -c src/metadata-proposal-pipeline.yaml`
3. Propose a tag/owner/description/etc. in the UI; the action will log it and, if `external_uri` is set in the pipeline config, POST the payload to that URL.

### Extending

- Add a custom action (e.g. `metadata_proposal_action`) that reads `event["parameters"]["actionRequestType"]` and `event["parameters"]["resourceUrn"]` and only forwards “metadata” types to your approval system.
- If your approval process is external, use the same pipeline and action to create a ticket; when the ticket is approved, you can apply the change in DataHub via GraphQL (or have the user approve in DataHub and use the existing inbox).

---

## 4. Glossary Approval (Proposal Workflow)

**Status:** Same as #3 – proposals are native; approval can be wired to a Data Workflow Action.  
**Recommendation:** Use the same Actions pipeline and route on `actionRequestType` for glossary-specific proposals.

### What DataHub provides

- Users can propose **new Glossary Terms** (`CREATE_GLOSSARY_TERM`) or **Glossary Term associations** to assets (`TERM_ASSOCIATION`).
- These appear as **actionRequest** events with `parameters.actionRequestType`:
  - `CREATE_GLOSSARY_TERM`
  - `TERM_ASSOCIATION`

### What’s in this repo

- **`src/glossary-proposal-pipeline.yaml`** – Listens for **actionRequest** lifecycle events. Uses **`glossary_proposal_action`**, which forwards events whose `actionRequestType` is glossary/term-related (CREATE_GLOSSARY_TERM, TERM_ASSOCIATION, or any type containing "TERM"/"GLOSSARY"); if DataHub sends an empty `actionRequestType`, it is treated as a glossary proposal. **All operations** (PENDING, COMPLETED, CREATE, etc.) are forwarded so proposals appear on the mock dashboard at every stage. Logs each event and POSTs to `config.external_uri` when set (e.g. `http://localhost:8000/glossary_proposals`).

### How to run

1. Set `DATAHUB_URL` and `DATAHUB_TOKEN`.
2. If you use the global `datahub` CLI (pipx), inject this repo so the custom action is found:  
   `pipx inject acryl-datahub /path/to/datahub-data-access-workflow-examples`  
   (After changing action code, run `pipx inject --force acryl-datahub /path/to/...` and restart the pipeline.)
3. Run:  
   `datahub actions -c src/glossary-proposal-pipeline.yaml`
4. Propose a glossary term (or term association) in the UI; the action will forward it to the mock server (or your `external_uri`) and it will appear under **Recent glossary proposals** on the dashboard.

---

## Summary

| Requirement              | Mechanism                         | In this repo                                                                 |
|--------------------------|-----------------------------------|-------------------------------------------------------------------------------|
| 1. Data Product Access   | Data Access Workflows             | `create_data_access_workflow.py`, `*pipeline.yaml` (workflowId), `review_data_access_request.py` |
| 2. Asset Certification   | Compliance Forms (VERIFICATION) + Structured Properties | `certification-event-pipeline.yaml` + `certification_event_action`; optional `create_asset_certification_form.py` |
| 3. Metadata Approval    | Proposal workflows → Actions      | `metadata-proposal-pipeline.yaml` + `metadata_proposal_action` |
| 4. Glossary Approval    | Proposal workflows → Actions      | `glossary-proposal-pipeline.yaml` + `glossary_proposal_action` |

All pipelines use `DATAHUB_URL` and `DATAHUB_TOKEN` from the environment (e.g. `.env`). Load them before running any script or `datahub actions` command.
