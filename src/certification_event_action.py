"""
Action for Asset Certification - Requirement #2.

Listens for STRUCTURED_PROPERTY change events on entities (e.g. from Compliance
Forms or certification workflows). Logs each event and optionally POSTs to
an external_uri (e.g. audit or notification service).
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


class CertificationEventActionConfig(ConfigModel):
    external_uri: Optional[str] = None


class CertificationEventAction(Action):
    @classmethod
    def create(cls, config_dict: dict, ctx: PipelineContext) -> Action:
        config = CertificationEventActionConfig.model_validate(config_dict)
        return cls(config, ctx)

    def __init__(self, config: CertificationEventActionConfig, ctx: PipelineContext):
        self.config = config
        self.ctx = ctx
        print("[CertificationEventAction] Running with config:", config)

    def act(self, event: EventEnvelope) -> None:
        try:
            if not isinstance(event.event, EntityChangeEvent):
                return
            ev = event.event
            if (ev.category or "") != "STRUCTURED_PROPERTY":
                return

            params = ev.safe_parameters or {}
            payload = {
                "eventType": "certification_structured_property",
                "entityUrn": ev.entityUrn,
                "entityType": ev.entityType,
                "operation": ev.operation,
                "modifier": getattr(ev, "modifier", None),
                "parameters": params,
                "actor": getattr(ev.audit_stamp, "actor", None) if ev.audit_stamp else None,
            }
            message = json.dumps(payload, indent=2)
            print("[CertificationEventAction] Structured property change:", message)

            if self.config.external_uri:
                resp = requests.post(self.config.external_uri, json=payload, timeout=30)
                resp.raise_for_status()
                print("[CertificationEventAction] Forwarded to external system:", resp.status_code)
        except Exception as e:
            traceback.print_exc()
            os._exit(1)

    def close(self) -> None:
        pass
