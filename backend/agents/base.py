"""
Every agent implements the same interface: takes the shared state, returns
the updated state. The Supervisor (later) calls agents through this
interface only — it never needs to know Scenario Agent's internals versus
TestCase Agent's internals.
"""

from abc import ABC, abstractmethod

from backend.models.state import WorkflowState


class BaseAgent(ABC):
    name: str

    @abstractmethod
    def run(self, state: WorkflowState) -> WorkflowState:
        """Read what this agent needs from state, write only its own slice, return it."""
        raise NotImplementedError