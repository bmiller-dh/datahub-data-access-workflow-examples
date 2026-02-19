# Scripts by workflow

Scripts are grouped by the workflow they support:

| Folder | Workflow | Contents |
|--------|----------|----------|
| **data_access/** | 1. Data Product Access Requests | Create workflow, list/delete workflows, list pending requests, approve/reject |
| **certification/** | 2. Asset Certification | Create VERIFICATION Compliance Form (optional) |
| **metadata/** | 3. Metadata Approval (proposals) | Placeholder for future helpers (e.g. list/approve proposals) |
| **glossary/** | 4. Glossary Approval | Placeholder for future helpers |

Pipelines and actions for all four live in **`src/`**; the mock server in **`mock-server/`** receives events from the grant, metadata-proposal, and glossary-proposal pipelines.

Run scripts from the **repo root** (`datahub-data-access-workflow-examples`) with venv activated and `.env` loaded, e.g.:

```sh
set -a && source .env && set +a
python scripts/data_access/create_data_access_workflow.py
python scripts/data_access/delete_data_access_workflows.py --list-only   # or --delete-all / --urn "<urn>"
python scripts/data_access/list_pending_data_access_requests.py --mine --status PENDING
python scripts/data_access/review_data_access_request.py --request-urn <URN> --result ACCEPTED
python scripts/certification/create_asset_certification_form.py --form-id asset-cert-2024 --property-urn "urn:li:structuredProperty:..."   # or --property-urn "propertyId"
```

Run from the **repo root** so the script path resolves correctly; or from `scripts/certification` run `python create_asset_certification_form.py ...`.
