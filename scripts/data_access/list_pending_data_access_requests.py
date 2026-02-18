#!/usr/bin/env python3
"""
List Data Access Requests (workflow form requests) from DataHub.

Uses the listActionRequests GraphQL query. By default lists all workflow form
requests; use --status PENDING to show only pending (not yet completed) requests.
Use --mine to show only requests you are assigned to review (so you can approve them).
Copy a request URN to approve/reject with review_data_access_request.py.

Usage:
  export DATAHUB_URL DATAHUB_TOKEN
  python scripts/data_access/list_pending_data_access_requests.py
  python scripts/data_access/list_pending_data_access_requests.py --status PENDING
  python scripts/data_access/list_pending_data_access_requests.py --mine
  python scripts/data_access/list_pending_data_access_requests.py --mine --status PENDING
"""

import argparse
import base64
import json
import os
import sys

from datahub.ingestion.graph.client import DatahubClientConfig, DataHubGraph


def _current_user_urn_from_token(token: str) -> str | None:
    """Get corpuser URN from JWT sub claim."""
    try:
        parts = token.split(".")
        if len(parts) < 2:
            return None
        payload_b64 = parts[1]
        payload_b64 += "==" * (4 - len(payload_b64) % 4)
        payload = base64.urlsafe_b64decode(payload_b64)
        data = json.loads(payload)
        sub = data.get("sub")
        if sub:
            return f"urn:li:corpuser:{sub}"
    except Exception:
        pass
    return None

LIST_ACTION_REQUESTS_QUERY = """
query ListActionRequests($input: ListActionRequestsInput!) {
  listActionRequests(input: $input) {
    start
    count
    total
    actionRequests {
      urn
      type
      status
      result
      resultNote
      entity {
        ... on Dataset {
          urn
          name
          properties {
            name
          }
        }
      }
    }
  }
}
"""


def _get_config():
    url = os.environ.get("DATAHUB_URL")
    token = os.environ.get("DATAHUB_TOKEN")
    if not url or not token:
        missing = [k for k, v in [("DATAHUB_URL", url), ("DATAHUB_TOKEN", token)] if not v]
        print(f"Error: Set environment variables: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    return url, token


def main():
    parser = argparse.ArgumentParser(
        description="List Data Access Requests (workflow form requests). Use --status PENDING for pending only."
    )
    parser.add_argument(
        "--status",
        choices=["PENDING", "COMPLETED"],
        default=None,
        help="Filter by status (default: list all)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max number of requests to return (default: 50)",
    )
    parser.add_argument(
        "--mine",
        action="store_true",
        help="Show only requests you are assigned to review (filters by current user from token)",
    )
    args = parser.parse_args()

    datahub_url, datahub_token = _get_config()
    client = DataHubGraph(
        DatahubClientConfig(server=datahub_url, token=datahub_token)
    )

    input_params = {
        "start": 0,
        "count": args.limit,
        "type": "WORKFLOW_FORM_REQUEST",
        "allActionRequests": True,
    }
    if args.status:
        input_params["status"] = args.status
    if args.mine:
        user_urn = _current_user_urn_from_token(datahub_token)
        if not user_urn:
            print("Error: Could not get current user from token (use --mine only with a valid JWT).", file=sys.stderr)
            sys.exit(1)
        input_params["assignee"] = {"type": "USER", "urn": user_urn}

    result = client.execute_graphql(LIST_ACTION_REQUESTS_QUERY, {"input": input_params})
    data = result.get("listActionRequests") or {}
    total = data.get("total", 0)
    requests = data.get("actionRequests") or []

    if total == 0:
        print("No Data Access Requests found.")
        if args.status:
            print(f"  (filter: status={args.status})")
        if args.mine:
            print("  (filter: assigned to you — only these can be approved with your token)")
        return

    print(f"Found {total} Data Access Request(s):\n")
    for i, req in enumerate(requests, 1):
        urn = req.get("urn", "")
        status = req.get("status", "?")
        result_val = req.get("result") or "-"
        entity = req.get("entity") or {}
        name = (entity.get("name") or entity.get("properties", {}).get("name") or "-")
        entity_urn = (entity.get("urn") if isinstance(entity, dict) else "-")
        print(f"  {i}. {urn}")
        print(f"     Status: {status}  Result: {result_val}  Resource: {name}")
        print(f"     Entity: {entity_urn}")
        print()
    print("To approve a request:")
    print("  python scripts/data_access/review_data_access_request.py --request-urn <URN> --result ACCEPTED --comment \"Approved\"")
    print("To reject:")
    print("  python scripts/data_access/review_data_access_request.py --request-urn <URN> --result REJECTED --comment \"Rejected\"")


if __name__ == "__main__":
    main()
