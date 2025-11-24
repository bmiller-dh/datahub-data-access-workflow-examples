import json
import os
import traceback

from datahub_actions.action.action import Action
from datahub_actions.event.event_envelope import EventEnvelope
from datahub_actions.pipeline.pipeline_context import PipelineContext
from datahub.configuration.common import ConfigModel

# DataHub action which listens for Data Access Request events and logs them
# to the terminal.


class SimpleActionConfig(ConfigModel):
    pass


class SimpleAction(Action):
    @classmethod
    def create(cls, config_dict: dict, ctx: PipelineContext) -> Action:
        config = SimpleActionConfig.model_validate(config_dict)
        return cls(config, ctx)

    def __init__(self, config, ctx: PipelineContext):
        self.config = config
        print("Running with config:", config)

    def act(self, event: EventEnvelope) -> None:
        try:
            message = json.dumps(json.loads(event.as_json()), indent=4)
            print(message)

        except Exception as e:
            # Kill actions pipeline manager. Just throwing an exception will stop
            # this pipeline, but not the entire process.
            traceback.print_exc()
            os._exit(1)

    def close(self) -> None:
        pass
