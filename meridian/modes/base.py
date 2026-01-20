from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from meridian.core.modes import Mode

TArtifact = TypeVar("TArtifact")


class ModeExecutor(ABC, Generic[TArtifact]):
    """Base executor for a MERIDIAN mode (stub)."""

    mode: Mode

    @abstractmethod
    def run(self) -> TArtifact: ...

