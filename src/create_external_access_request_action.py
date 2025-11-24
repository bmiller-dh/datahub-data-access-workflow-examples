import json
import os
import traceback

import requests
from datahub_actions.action.action import Action
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.event.event_registry import EntityChangeEvent
from datahub_actions.pipeline.pipeline_context import PipelineContext
from datahub.configuration.common import ConfigModel

# DataHub action which listens for Data Access Request creation events and
# forwards the request on to an external system.
#
# Example creation event:
#
#     {
#         "event_type": "EntityChangeEvent_v1",
#         "event": {
#             "entityType": "actionRequest",
#             "entityUrn": "urn:li:actionRequest:9c8da2b7-e93d-42d0-853d-afe11cd4b26f",
#             "category": "LIFECYCLE",
#             "operation": "CREATE",
#             "auditStamp": {
#                 "time": 1763676045530,
#                 "actor": "urn:li:corpuser:michael.maltese@datahub.com"
#             },
#             "version": 0,
#             "parameters": {
#                 "qualifiedEntityName": "ORDER_ENTRY_DB.ANALYTICS.ORDER_DETAILS",
#                 "actorUrn": "urn:li:corpuser:michael.maltese@datahub.com",
#                 "entityUrn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,order_entry_db.analytics.order_details,PROD)",
#                 "actionRequestType": "WORKFLOW_FORM_REQUEST",
#                 "entityType": "dataset",
#                 "entityName": "ORDER_DETAILS",
#                 "actorEmail": "michael.maltese@datahub.com",
#                 "workflowUrn": "urn:li:actionWorkflow:7110b19c-45b9-4450-b8bb-ba47d9f522ba",
#                 "fields": "{\"business_justification\":[\"please and thank you\"]}",
#                 "workflowId": "7110b19c-45b9-4450-b8bb-ba47d9f522ba",
#                 "entityPlatformName": "Snowflake"
#             }
#         },
#         "meta": {
#             "batch_id": 104,
#             "msg_id": 21
#         }
#     }
#


class CreateExternalAccessRequestConfig(ConfigModel):
    external_uri: str


class CreateExternalAccessRequest(Action):
    @classmethod
    def create(cls, config_dict: dict, ctx: PipelineContext) -> Action:
        config = CreateExternalAccessRequestConfig.model_validate(config_dict)
        return cls(config, ctx)

    def __init__(self, config, ctx: PipelineContext):
        self.config = config
        print("Running with config:", config)

    def act(self, event: EventEnvelope) -> None:
        try:
            message = json.dumps(json.loads(event.as_json()), indent=4)
            print(message)

            if not isinstance(event.event, EntityChangeEvent):
                return

            operation = event.event.operation
            parameters = event.event.safe_parameters

            if operation != "CREATE":
                return

            resp = requests.post(self.config.external_uri, json=parameters)
            resp.raise_for_status()
            print(resp.json())

        except Exception as e:
            # Kill actions pipeline manager. Just throwing an exception will stop
            # this pipeline, but not the entire process.
            traceback.print_exc()
            os._exit(1)

    def close(self) -> None:
        pass
