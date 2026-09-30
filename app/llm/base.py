"""LLM interface. All providers return parsed JSON dicts or raise LLMError."""


class LLMError(Exception):
    """Model call failed, timed out, or returned unparseable output."""


class BaseLLM:
    def complete_json(self, system: str, user: str) -> dict:
        raise NotImplementedError

    def name(self) -> str:
        return self.__class__.__name__
