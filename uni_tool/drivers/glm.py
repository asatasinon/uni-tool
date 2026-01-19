"""
GLM driver for UniTools SDK.

Implements protocol adaptation for GLM's OpenAI-compatible tool calling.
"""

from __future__ import annotations

from uni_tool.core.models import ModelProfile
from uni_tool.drivers.openai import OpenAIDriver


class GLMDriver(OpenAIDriver):
    """
    Driver for GLM's OpenAI-compatible function calling format.
    """

    SUPPORTED_MODEL_PREFIXES = ("glm-",)

    def can_handle(self, profile: ModelProfile) -> int:
        """
        Score capability to handle the model profile.

        Returns 100 for GLM models, 0 otherwise.
        """
        model_name = profile.name.lower()
        for prefix in self.SUPPORTED_MODEL_PREFIXES:
            if model_name.startswith(prefix):
                return 100
        if "glm" in model_name:
            return 90
        return 0
