import argparse
import sys

from datahub.ingestion.graph.client import DatahubClientConfig, DataHubGraph

DATAHUB_URL = "https://<instance-name>.acryl.io"
DATAHUB_TOKEN = "<personal access token>"

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

    # Initialize DataHub client
    datahub_client = DataHubGraph(
        DatahubClientConfig(
            server=DATAHUB_URL,
            token=DATAHUB_TOKEN,
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
