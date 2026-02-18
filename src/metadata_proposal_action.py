"""
Action for Metadata Approval (Proposal Workflows) - Requirement #3.

Listens for metadata proposal events: TAG_ASSOCIATION, OWNER_ASSOCIATION,
DOMAIN_ASSOCIATION, UPDATE_DESCRIPTION, STRUCTURED_PROPERTY_ASSOCIATION.
Logs each event and optionally POSTs to an external_uri (e.g. ticketing system).
"""

import json
import os
import traceback
from typing import Optional

import requests
from datahub_actions.action.action import Action
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.event.event_registry import EntityChangeEvent
from datahub_actions.pipeline.pipeline_context import PipelineContext
from datahub.configuration.common import ConfigModel

METADATA_PROPOSAL_TYPES = frozenset({
    "TAG_ASSOCIATION",
    "OWNER_ASSOCIATION",
    "DOMAIN_ASSOCIATION",
    "UPDATE_DESCRIPTION",
    "STRUCTURED_PROPERTY_ASSOCIATION",
})


class MetadataProposalActionConfig(ConfigModel):
    external_uri: Optional[str] = None


class MetadataProposalAction(Action):
    @classmethod
    def create(cls, config_dict: dict, ctx: PipelineContext) -> Action:
        config = MetadataProposalActionConfig.model_validate(config_dict)
        return cls(config, ctx)

    def __init__(self, config: MetadataProposalActionConfig, ctx: PipelineContext):
        self.config = config
        self.ctx = ctx
        print("[MetadataProposalAction] Running with config:", config)

    def act(self, event: EventEnvelope) -> None:
        try:
            if not isinstance(event.event, EntityChangeEvent):
                return
            ev = event.event
            if ev.operation != "CREATE" or ev.entityType != "actionRequest":
                return
            params = ev.safe_parameters or {}
            action_type = params.get("actionRequestType") or ""
            if action_type not in METADATA_PROPOSAL_TYPES:
                return

            payload = {
                "eventType": "metadata_proposal",
                "actionRequestType": action_type,
                "entityUrn": ev.entity_urn,
                "requestUrn": ev.entity_urn,
                "parameters": params,
                "actor": getattr(ev.audit_stamp, "actor", None) if ev.audit_stamp else None,
            }
            message = json.dumps(payload, indent=2)
            print("[MetadataProposalAction] Metadata proposal:", message)

            if self.config.external_uri:
                resp = requests.post(self.config.external_uri, json=payload, timeout=30)
                resp.raise_for_status()
                print("[MetadataProposalAction] Forwarded to external system:", resp.status_code)
        except Exception as e:
            traceback.print_exc()
            os._exit(1)

    def close(self) -> None:
        pass
