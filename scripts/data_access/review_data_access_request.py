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

REVIEW_REQUEST_MUTATION = """
mutation ($input: ReviewActionWorkflowFormRequestInput!) {
  reviewActionWorkflowFormRequest(input: $input)
}
"""


def main():
    # Handle command line args
    parser = argparse.ArgumentParser(prog=sys.argv[0])
    parser.add_argument("--request-urn", required=True)
    parser.add_argument("--result", choices=["ACCEPTED", "REJECTED"], required=True)
    parser.add_argument("--comment")

    args = parser.parse_args(sys.argv[1:])

    datahub_url, datahub_token = _get_config()

    # Initialize DataHub client
    datahub_client = DataHubGraph(
        DatahubClientConfig(
            server=datahub_url,
            token=datahub_token,
        )
    )

    # Take review request action
    result = datahub_client.execute_graphql(
        REVIEW_REQUEST_MUTATION,
        {
            "input": {
                "urn": args.request_urn,
                "result": args.result,
                "comment": args.comment,
            }
        },
    )
    print(result)


if __name__ == "__main__":
    main()
