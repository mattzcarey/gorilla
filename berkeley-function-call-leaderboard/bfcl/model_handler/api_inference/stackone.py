import os

from openai import OpenAI

from bfcl.model_handler.api_inference.openai import OpenAIHandler
from bfcl.model_handler.model_style import ModelStyle


class StackOneHandler(OpenAIHandler):
    def __init__(self, model_name, temperature) -> None:
        super().__init__(model_name, temperature)
        self.model_style = ModelStyle.OpenAI
        self.client = OpenAI(
            base_url="https://function-calling-agent.stackonehq.workers.dev/v1", api_key=os.getenv("STACKONE_API_KEY")
        )
        self.is_fc_model = True
