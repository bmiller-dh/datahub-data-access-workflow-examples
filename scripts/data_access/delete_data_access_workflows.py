#!/usr/bin/env python3
"""
Delete Data Access Workflow definitions from DataHub.

Use this to remove duplicate or unwanted "Data Access" / "Request Access" workflows.
You can list workflows first (--list-only), delete by URN (--urn), or delete all
that are listed (--delete-all). Requires DATAHUB_URL and DATAHUB_TOKEN.

Usage:
  export DATAHUB_URL DATAHUB_TOKEN

  # List existing Data Access Workflows (no delete)
  python scripts/data_access/delete_data_access_workflows.py --list-only

  # Delete one workflow by URN
  python scripts/data_access/delete_data_access_workflows.py --urn "urn:li:actionWorkflow:<uuid>"

  # Delete all listed Data Access Workflows (after confirming with --list-only)
  python scripts/data_access/delete_data_access_workflows.py --delete-all

  # Delete multiple by URN
  python scripts/data_access/delete_data_access_workflows.py --urn "urn:li:actionWorkflow:uuid1" --urn "urn:li:actionWorkflow:uuid2"
"""

import argparse
import os
import sys

from datahub.ingestion.graph.client import DatahubClientConfig, DataHubGraph


def _get_config():
    url = os.environ.get("DATAHUB_URL")
    token = os.environ.get("DATAHUB_TOKEN")
    if not url or not token:
        missing = [k for k, v in [("DATAHUB_URL", url), ("DATAHUB_TOKEN", token)] if not v]
        print(f"Error: Set environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    return url, token


# List workflows; ListActionWorkflowResult may use "workflows" not "actionWorkflows".
LIST_WORKFLOWS_QUERY = """
query ListActionWorkflows($input: ListActionWorkflowsInput!) {
  listActionWorkflows(input: $input) {
    start
    count
    total
    workflows {
      urn
      name
      description
      category
    }
  }
}
"""

# Delete workflow definition by URN (DataHub GraphQL deleteActionWorkflow).
# Removes the workflow so new requests cannot use it; existing requests are unchanged.
DELETE_ACTION_WORKFLOW_MUTATION = """
mutation DeleteActionWorkflow($input: DeleteActionWorkflowInput!) {
  deleteActionWorkflow(input: $input)
}
"""


def list_workflows(client: DataHubGraph):
    # Try GraphQL listActionWorkflows first
    try:
        result = client.execute_graphql(
            LIST_WORKFLOWS_QUERY,
            {"input": {"start": 0, "count": 100}},
        )
    except Exception as e:
        # Fallback: list URNs by entity type if supported (no name/category)
        try:
            urns = list(
                client.get_urns_by_filter(
                    entity_types=["ACTION_WORKFLOW"],
                    batch_size=100,
                )
            )
            if not urns:
                return []
            return [{"urn": u, "name": "-", "category": "-"} for u in urns]
        except Exception as e2:
            print("Listing failed:", e, file=sys.stderr)
            print("Fallback also failed:", e2, file=sys.stderr)
            print("Use --urn with workflow URNs from the DataHub UI (e.g. Settings > Workflows).", file=sys.stderr)
            return []
    data = result.get("listActionWorkflows") or {}
    workflows = data.get("workflows") or data.get("actionWorkflows") or []
    return workflows


def main():
    parser = argparse.ArgumentParser(
        description="List or delete Data Access Workflow definitions in DataHub.",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="List Data Access Workflows and exit (no delete).",
    )
    parser.add_argument(
        "--delete-all",
        action="store_true",
        help="Delete all Data Access Workflows returned by list (use after --list-only to confirm).",
    )
    parser.add_argument(
        "--urn",
        action="append",
        default=[],
        help="Workflow URN to delete (e.g. urn:li:actionWorkflow:uuid). Can be repeated.",
    )
    args = parser.parse_args()

    datahub_url, datahub_token = _get_config()
    client = DataHubGraph(
        DatahubClientConfig(server=datahub_url, token=datahub_token),
    )

    if args.list_only:
        workflows = list_workflows(client)
        if not workflows:
            print("No Data Access Workflows found.")
            return
        print(f"Found {len(workflows)} Data Access Workflow(s):\n")
        for w in workflows:
            print(f"  {w.get('urn', '')}")
            print(f"    name: {w.get('name', '-')}  category: {w.get('category', '-')}")
        print("\nTo delete one: --urn \"<urn>\"")
        print("To delete all:  --delete-all")
        return

    urns_to_delete = list(args.urn)
    if args.delete_all:
        workflows = list_workflows(client)
        urns_to_delete = [w.get("urn") for w in workflows if w.get("urn")]
        if not urns_to_delete:
            print("No workflows to delete.")
            return
        print(f"Will delete {len(urns_to_delete)} workflow(s).")

    if not urns_to_delete:
        parser.error("Provide --urn <urn> (repeat for multiple) or --delete-all after --list-only.")

    for urn in urns_to_delete:
        urn = (urn or "").strip()
        if not urn.startswith("urn:li:actionWorkflow:"):
            print(f"Skip invalid URN: {urn!r}", file=sys.stderr)
            continue
        try:
            client.execute_graphql(
                DELETE_ACTION_WORKFLOW_MUTATION,
                {"input": {"urn": urn}},
            )
            print(f"Deleted: {urn}")
        except Exception as e:
            print(f"Failed to delete {urn}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
