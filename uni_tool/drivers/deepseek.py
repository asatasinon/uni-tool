"""
DeepSeek driver for UniTools SDK.

Implements protocol adaptation for DeepSeek's OpenAI-compatible tool calling.
"""

from __future__ import annotations

from uni_tool.core.models import ModelProfile
from uni_tool.drivers.openai import OpenAIDriver


class DeepSeekDriver(OpenAIDriver):
    """
    Driver for DeepSeek's OpenAI-compatible function calling format.
    """

    SUPPORTED_MODEL_PREFIXES = ("deepseek-",)

    def can_handle(self, profile: ModelProfile) -> int:
        """
        Score capability to handle the model profile.

        Returns 100 for DeepSeek models, 0 otherwise.
        """
        model_name = profile.name.lower()
        for prefix in self.SUPPORTED_MODEL_PREFIXES:
            if model_name.startswith(prefix):
                return 100
        if "deepseek" in model_name:
            return 90
        return 0
