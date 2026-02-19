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
            # Debug: log every actionRequest event to see what DataHub sends
            entity_type = getattr(ev, "entityType", None) or getattr(ev, "entity_type", None)
            if entity_type == "actionRequest":
                operation = getattr(ev, "operation", None)
                category = getattr(ev, "category", None)
                params = ev.safe_parameters or {}
                action_request_type = params.get("actionRequestType") or params.get("actionRequestType") or ""
                print(
                    f"[MetadataProposalAction] actionRequest event: operation={operation!r} category={category!r} actionRequestType={action_request_type!r}",
                    flush=True,
                )
            op = getattr(ev, "operation", None)
            if op not in ("CREATE", "CREATED") or getattr(ev, "entityType", getattr(ev, "entity_type", None)) != "actionRequest":
                return
            params = ev.safe_parameters or {}
            action_type = (params.get("actionRequestType") or "").strip()
            if action_type not in METADATA_PROPOSAL_TYPES:
                print(f"[MetadataProposalAction] Skipping: actionRequestType {action_type!r} not in {sorted(METADATA_PROPOSAL_TYPES)}", flush=True)
                return
            entity_urn = getattr(ev, "entityUrn", None) or getattr(ev, "entity_urn", None) or ""
            stamp = getattr(ev, "auditStamp", None) or getattr(ev, "audit_stamp", None)
            actor = getattr(stamp, "actor", None) if stamp else None
            payload = {
                "eventType": "metadata_proposal",
                "actionRequestType": action_type,
                "entityUrn": entity_urn,
                "requestUrn": entity_urn,
                "parameters": params,
                "actor": actor,
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
