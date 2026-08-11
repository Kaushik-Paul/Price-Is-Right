from llm_config import LLMConfig, create_llm_client, get_llm_config

SYSTEM_PROMPT = """Create a concise description of a product. Respond only in this format. Do not include part numbers.
Title: Rewritten short precise title
Category: eg Electronics
Brand: Brand name
Description: 1 sentence description
Details: 1 sentence on features"""


class Preprocessor:
    def __init__(
        self,
        model_name=None,
        reasoning_effort=None,
        base_url=None,
        api_key=None,
    ):
        config = get_llm_config()
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0
        self.model_name = model_name or config.model
        self.reasoning_effort = reasoning_effort
        self.base_url = base_url or config.base_url
        self.api_key = api_key or config.api_key
        self.openai = create_llm_client(
            LLMConfig(
                base_url=self.base_url,
                api_key=self.api_key,
                model=self.model_name,
            )
        )

    def messages_for(self, text: str) -> list[dict]:
        return [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": text}]

    def preprocess(self, text: str) -> str:
        messages = self.messages_for(text)
        response = self.openai.chat.completions.create(
            messages=messages,
            model=self.model_name,
        )
        if response.usage:
            self.total_input_tokens += response.usage.prompt_tokens
            self.total_output_tokens += response.usage.completion_tokens
        return response.choices[0].message.content
