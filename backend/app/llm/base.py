from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers so models can be swapped seamlessly."""

    @abstractmethod
    async def generate_json(self, prompt: str, system_instruction: str, max_tokens: int = 1024) -> Dict[str, Any]:
        """Generate structured JSON response."""
        pass

    @abstractmethod
    async def generate_text(self, prompt: str, system_instruction: str, max_tokens: int = 1024) -> str:
        """Generate textual response."""
        pass
