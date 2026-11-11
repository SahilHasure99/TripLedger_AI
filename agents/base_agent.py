"""Abstract base class that every agent in the system inherits from."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from utils.logger import get_logger


class BaseAgent(ABC):
    """Common interface + shared utilities for all agents."""

    name: str = "base_agent"

    def __init__(self) -> None:
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Execute the agent's task. Must be implemented by subclasses."""
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name!r}>"
