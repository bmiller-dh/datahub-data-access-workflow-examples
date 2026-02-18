"""
Action for Glossary Approval (Proposal Workflows) - Requirement #4.

Listens for glossary proposal events: CREATE_GLOSSARY_TERM, TERM_ASSOCIATION.
Logs each event and optionally POSTs to an external_uri (e.g. approval workflow).
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

GLOSSARY_PROPOSAL_TYPES = frozenset({
    "CREATE_GLOSSARY_TERM",
    "TERM_ASSOCIATION",
})


class GlossaryProposalActionConfig(ConfigModel):
    external_uri: Optional[str] = None


class GlossaryProposalAction(Action):
    @classmethod
    def create(cls, config_dict: dict, ctx: PipelineContext) -> Action:
        config = GlossaryProposalActionConfig.model_validate(config_dict)
        return cls(config, ctx)

    def __init__(self, config: GlossaryProposalActionConfig, ctx: PipelineContext):
        self.config = config
        self.ctx = ctx
        print("[GlossaryProposalAction] Running with config:", config)

    def act(self, event: EventEnvelope) -> None:
        try:
            if not isinstance(event.event, EntityChangeEvent):
                return
            ev = event.event
            if ev.operation != "CREATE" or ev.entityType != "actionRequest":
                return
            params = ev.safe_parameters or {}
            action_type = params.get("actionRequestType") or ""
            if action_type not in GLOSSARY_PROPOSAL_TYPES:
                return

            payload = {
                "eventType": "glossary_proposal",
                "actionRequestType": action_type,
                "entityUrn": ev.entity_urn,
                "requestUrn": ev.entity_urn,
                "parameters": params,
                "actor": getattr(ev.audit_stamp, "actor", None) if ev.audit_stamp else None,
            }
            message = json.dumps(payload, indent=2)
            print("[GlossaryProposalAction] Glossary proposal:", message)

            if self.config.external_uri:
                resp = requests.post(self.config.external_uri, json=payload, timeout=30)
                resp.raise_for_status()
                print("[GlossaryProposalAction] Forwarded to external system:", resp.status_code)
        except Exception as e:
            traceback.print_exc()
            os._exit(1)

    def close(self) -> None:
        pass
