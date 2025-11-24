This repo contains examples for using [DataHub Data Access Workflows](https://docs.datahub.com/docs/managed-datahub/workflows/access-workflows) in conjunction with the [DataHub Actions Framework](https://docs.datahub.com/docs/actions) to integrate with external tools.

# Dependencies

```sh
pip install -e .
```

## Creating a DataHub Data Access Workflow

The script `scripts/create_data_access_workflow.py` will create an example Data Access Workflow.

First, edit the file to set `DATAHUB_URL` (e.g. `https://<instance-name>.acryl.io`) and `DATAHUB_TOKEN` (see [Personal Access Tokens](https://docs.datahub.com/docs/authentication/personal-access-tokens)) at the top of the file.

Then run:

```sh
python scripts/create_data_access_workflow.py
```

You should now be able to see your Data Access Workflow and make a Data Access Request by going to any Dataset page and clicking the "unlock" icon on the top right of the main entity header (next to the "View in {platform}" button).


# Examples

## Simple Action

The file `src/simple_action.py` implements a simple example DataHub Action that listens for all events pertaining to Data Access Requests and prints them to your terminal.

First, edit `src/simple-pipeline.yaml`:
- Set `datahub.server` (e.g. `https://<instance-name>.acryl.io`) and `datahub.token` (see [Personal Access Tokens](https://docs.datahub.com/docs/authentication/personal-access-tokens)) at the top of the file
- Set `filter.events.parameters.workflowId` to the URN of your Data Access Workflow (must be already created)

To run:

```sh
datahub actions -c src/simple-pipeline.yaml
```

## Grant External Permissions Action

The file `src/grant_external_permissions_action.py` implements a simple example DataHub Action that listens for accepted Data Access Requests and sends them off to an external system. This can be used to approve data requests inside DataHub itself, then grant permissions in an external system.

First, edit `src/grant-external-permissions-pipeline.yaml`:
- Set `datahub.server` (e.g. `https://<instance-name>.acryl.io`) and `datahub.token` (see [Personal Access Tokens](https://docs.datahub.com/docs/authentication/personal-access-tokens)) at the top of the file
- Set `filter.events.parameters.workflowId` to the URN of your Data Access Workflow (must be already created)
- Implement logic that grants permissions inside an external system. Currently, this action simply sends the raw parameters to an imaginary HTTP endpoint.

To run:

```sh
datahub actions -c src/grant-external-permissions-pipeline.yaml
```

## Create External Access Request Action

The file `src/create_external_access_request_action.py` implements a simple example DataHub Action that listens for new Data Access Requests and sends them off to an external system. This can be used to allow users to request data inside DataHub itself, but send the request off to an external system to manage the request workflow and lifecycle elsewhere.

First, edit `src/grant-external-permissions-pipeline.yaml`:
- Set `datahub.server` (e.g. `https://<instance-name>.acryl.io`) and `datahub.token` (see [Personal Access Tokens](https://docs.datahub.com/docs/authentication/personal-access-tokens)) at the top of the file
- Set `filter.events.parameters.workflowId` to the URN of your Data Access Workflow (must be already created)
- Implement logic that creates a request in an external system and stores a reference tying to back to the access request inside DataHub. Currently, this action simply sends the raw parameters to an imaginary HTTP endpoint.

To run:

```sh
datahub actions -c src/grant-external-permissions-pipeline.yaml
```

This should also be paired with logic to take the result of the workflow in the external system and push it back into DataHub, so users can be notified that their request has been approved or denied. An example script for programatically approving or denying a Data Acess Request can be found in `scripts/review_data_access_request.py`.

You'll need to edit `scripts/review_data_access_request.py` to set `DATAHUB_URL` (e.g. `https://<instance-name>.acryl.io`) and `DATAHUB_TOKEN` (see [Personal Access Tokens](https://docs.datahub.com/docs/authentication/personal-access-tokens)) at the top of the file.

To run:

```sh
python scripts/review_data_access_request.py --request-urn <request_urn> --result ACCEPTED --comment "from your friendly neighborhood data request bot"
```