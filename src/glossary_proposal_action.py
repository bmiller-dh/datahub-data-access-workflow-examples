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


def _is_glossary_proposal(action_request_type: str) -> bool:
    """Accept known types or any type that looks glossary/term-related."""
    if not action_request_type:
        return False
    if action_request_type in GLOSSARY_PROPOSAL_TYPES:
        return True
    upper = action_request_type.upper()
    return "TERM" in upper or "GLOSSARY" in upper


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
            entity_type = getattr(ev, "entityType", None) or getattr(ev, "entity_type", None)
            op = getattr(ev, "operation", None)
            category = getattr(ev, "category", None)
            # Log every entity change so we can see what DataHub sends (e.g. for glossary term proposals)
            print(
                f"[GlossaryProposalAction] event: entityType={entity_type!r} category={category!r} operation={op!r}",
                flush=True,
            )
            if entity_type == "actionRequest":
                op = getattr(ev, "operation", None)
                category = getattr(ev, "category", None)
                params = ev.safe_parameters or {}
                action_type = (params.get("actionRequestType") or "").strip()
                print(
                    f"[GlossaryProposalAction] actionRequest event: operation={op!r} category={category!r} actionRequestType={action_type!r} param_keys={list(params.keys())!r}",
                    flush=True,
                )
            if entity_type != "actionRequest":
                return
            params = ev.safe_parameters or {}
            action_type = (params.get("actionRequestType") or "").strip()
            # If type is empty (DataHub sometimes omits it for glossary), still forward
            if action_type and not _is_glossary_proposal(action_type):
                print(f"[GlossaryProposalAction] Skipping: actionRequestType {action_type!r} not glossary/term-related", flush=True)
                return
            if not action_type:
                action_type = "GLOSSARY_PROPOSAL"
            entity_urn = getattr(ev, "entityUrn", None) or getattr(ev, "entity_urn", None) or ""
            entity_urn = str(entity_urn) if entity_urn is not None else ""
            stamp = getattr(ev, "auditStamp", None) or getattr(ev, "audit_stamp", None)
            actor = getattr(stamp, "actor", None) if stamp else None
            actor = str(actor) if actor is not None else None
            # Ensure parameters are JSON-serializable (params can contain non-serializable types)
            try:
                safe_params = json.loads(json.dumps(params, default=str))
            except Exception:
                safe_params = {k: str(v) for k, v in (params or {}).items()}
            payload = {
                "eventType": "glossary_proposal",
                "actionRequestType": action_type,
                "entityUrn": entity_urn,
                "requestUrn": entity_urn,
                "parameters": safe_params,
                "actor": actor,
            }
            print("[GlossaryProposalAction] Glossary proposal (forwarding):", entity_urn[:80] if entity_urn else "(no urn)", flush=True)
            if self.config.external_uri:
                print("[GlossaryProposalAction] POST to", self.config.external_uri, flush=True)
                resp = requests.post(self.config.external_uri, json=payload, timeout=30)
                resp.raise_for_status()
                print("[GlossaryProposalAction] Forwarded to external system:", resp.status_code, flush=True)
            else:
                print("[GlossaryProposalAction] No external_uri configured, skipping POST", flush=True)
        except Exception as e:
            print("[GlossaryProposalAction] ERROR:", e, flush=True)
            traceback.print_exc()
            os._exit(1)

    def close(self) -> None:
        pass
