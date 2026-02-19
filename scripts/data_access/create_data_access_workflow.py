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

CREATE_WORKFLOW_MUTATION = """
mutation upsertActionWorkflow($input: UpsertActionWorkflowInput!) {
  upsertActionWorkflow(input: $input) {
    urn
  }
}
"""


def main():
    # Handle command line args
    parser = argparse.ArgumentParser(prog=sys.argv[0])
    parser.parse_args(sys.argv[1:])

    datahub_url, datahub_token = _get_config()

    # Initialize DataHub client
    datahub_client = DataHubGraph(
        DatahubClientConfig(
            server=datahub_url,
            token=datahub_token,
        )
    )

    # Create data access workflow
    result = datahub_client.execute_graphql(
        CREATE_WORKFLOW_MUTATION,
        {
            "input": {
                "name": "External Auth Data Access Workflow",
                "description": "Request access to datasets via external auth workflow",
                "category": "ACCESS",
                "trigger": {
                    "type": "FORM_SUBMITTED",
                    "form": {
                        "entityTypes": [
                            "DATASET"
                        ],  # Limit to dataset entities, but can apply to many types.
                        "entrypoints": [
                            {
                                "type": "HOME",  # Display on Home Page
                                "label": "Request Dataset Access",  # Home Page CTA
                            },
                            {
                                "type": "ENTITY_PROFILE",  # Display on Entity Profile Page
                                "label": "Request Access",  # Entity Profile Page CTA
                            },
                        ],
                        "fields": [
                            {
                                "id": "business_justification",
                                "name": "Business Justification",
                                "description": "Please explain why you need access to this dataset",
                                "valueType": "RICH_TEXT",
                                "cardinality": "SINGLE",
                                "required": True,
                            },
                            {
                                "id": "access_duration",
                                "name": "Access Duration",
                                "description": "How long do you need access?",
                                "valueType": "STRING",
                                "allowedValues": [
                                    {"stringValue": "30_DAYS"},
                                    {"stringValue": "90_DAYS"},
                                    {"stringValue": "PERMANENT"},
                                ],
                                "cardinality": "SINGLE",
                                "required": False,
                            },
                            # Create a conditionally visible field. Only visible based on previous field answer.
                            {
                                "id": "permanent_access_justification",
                                "name": "Permanent Access Justification",
                                "description": "Since you've requested permanent access, please provide additional justification for why this is necessary",
                                "valueType": "RICH_TEXT",
                                "cardinality": "SINGLE",
                                "required": True,
                                "condition": {
                                    "type": "SINGLE_FIELD_VALUE",
                                    "singleFieldValueCondition": {
                                        "field": "access_duration",
                                        "values": ["PERMANENT"],
                                        "condition": "EQUAL",
                                        "negated": False,
                                    },
                                },
                            },
                        ],
                    },
                },
                "steps": [
                    {
                        "id": "data_steward_review",
                        "type": "APPROVAL",
                        "description": "Data steward review and approval",
                        "actors": {
                            "userUrns": [],
                            "groupUrns": [],
                            "roleUrns": [],
                            "dynamicAssignment": {"type": "ENTITY_OWNERS"},
                        },
                    }
                ],
            }
        },
    )
    urn = result["upsertActionWorkflow"]["urn"]
    print(f"Workflow created successfully: {urn}")


if __name__ == "__main__":
    main()
