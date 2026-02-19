"""
Create a VERIFICATION-type Compliance Form for Asset Certification (Requirement #2).

Uses the DataHub Forms API. Requires a structured property URN to attach (e.g. a
"Certification Status" or "Certified Date" property). Create structured properties
in DataHub first (Govern > Settings > Structured Properties), then pass the URN here.

Usage:
  export DATAHUB_URL DATAHUB_TOKEN
  python scripts/certification/create_asset_certification_form.py --form-id asset-cert-2024 --property-urn "urn:li:structuredProperty:certificationStatus"
  python scripts/certification/create_asset_certification_form.py --form-id asset-cert-2024 --property-urn "certificationStatus"
"""
import argparse
import os
import sys

from datahub.ingestion.graph.client import DatahubClientConfig, DataHubGraph

CREATE_FORM_MUTATION = """
mutation createForm($input: CreateFormInput!) {
  createForm(input: $input) {
    urn
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


def _normalize_property_urn(value: str) -> str:
    """Accept full URN (urn:li:structuredProperty:...) or just the property id; return full URN."""
    if not value or not value.strip():
        return value
    s = value.strip()
    if s.startswith("urn:li:structuredProperty:"):
        return s
    return f"urn:li:structuredProperty:{s}"


def main():
    parser = argparse.ArgumentParser(
        description="Create a VERIFICATION Compliance Form for asset certification."
    )
    parser.add_argument(
        "--form-id",
        required=True,
        help="Unique form id (e.g. asset-cert-2024)",
    )
    parser.add_argument(
        "--property-urn",
        required=True,
        help='Structured property URN or id (e.g. urn:li:structuredProperty:certificationStatus or certificationStatus)',
    )
    parser.add_argument(
        "--name",
        default="Asset Certification",
        help="Form display name",
    )
    parser.add_argument(
        "--description",
        default="Verify and certify data assets; applies the selected structured property.",
        help="Form description",
    )
    parser.add_argument(
        "--user",
        action="append",
        dest="users",
        default=[],
        help="User URN to assign (e.g. urn:li:corpuser:jane). Can be repeated.",
    )
    args = parser.parse_args()
    property_urn = _normalize_property_urn(args.property_urn)

    datahub_url, datahub_token = _get_config()
    client = DataHubGraph(
        DatahubClientConfig(server=datahub_url, token=datahub_token)
    )

    result = client.execute_graphql(
        CREATE_FORM_MUTATION,
        {
            "input": {
                "id": args.form_id,
                "name": args.name,
                "description": args.description,
                "type": "VERIFICATION",
                "prompts": [
                    {
                        "id": "cert-prop",
                        "title": "Certification",
                        "description": "Apply certification structured property to the asset",
                        "type": "STRUCTURED_PROPERTY",
                        "structuredPropertyParams": {
                            "urn": property_urn,
                        },
                    }
                ],
                "actors": {
                    "users": args.users or [],
                    "groups": [],
                },
            }
        },
    )
    urn = result.get("createForm", {}).get("urn")
    if urn:
        print(f"Form created: {urn}")
        print("Assign to entities via UI (Govern > Compliance Forms) or GraphQL batchAssignForm.")
    else:
        print(result, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
