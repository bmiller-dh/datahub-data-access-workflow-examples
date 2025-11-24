import argparse
import sys

from datahub.ingestion.graph.client import DatahubClientConfig, DataHubGraph

DATAHUB_URL = "https://<instance-name>.acryl.io"
DATAHUB_TOKEN = "<personal access token>"

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

    # Initialize DataHub client
    datahub_client = DataHubGraph(
        DatahubClientConfig(
            server=DATAHUB_URL,
            token=DATAHUB_TOKEN,
        )
    )

    # Create data access workflow
    result = datahub_client.execute_graphql(
        CREATE_WORKFLOW_MUTATION,
        {
            "input": {
                "name": "Dataset Access Request",
                "description": "Request access to sensitive datasets",
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
    print(result)
    print(f"Workflow created successfully: {result['upsertActionWorkflow']['urn']}")
    print(f"Workflow name: {result['upsertActionWorkflow']['name']}")


if __name__ == "__main__":
    main()
