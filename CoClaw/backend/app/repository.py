from __future__ import annotations

from collections.abc import Iterable

from .models import Agent, Container, OpenClawInstance, Session


class InMemoryRepository:
    """In-memory repository for MVP.

    Can be replaced by a DB-backed implementation later.
    """

    def __init__(self) -> None:
        self._containers: dict[str, Container] = {}
        self._instances: dict[str, OpenClawInstance] = {}
        self._agents: dict[str, Agent] = {}
        self._sessions: dict[str, Session] = {}

    def upsert_container(self, container: Container) -> None:
        self._containers[container.id] = container

    def upsert_instance(self, instance: OpenClawInstance) -> None:
        self._instances[instance.id] = instance

    def upsert_agent(self, agent: Agent) -> None:
        self._agents[agent.id] = agent

    def upsert_session(self, session: Session) -> None:
        self._sessions[session.id] = session

    def list_containers(self) -> Iterable[Container]:
        return self._containers.values()

    def list_instances(self) -> Iterable[OpenClawInstance]:
        return self._instances.values()

    def list_agents(self) -> Iterable[Agent]:
        return self._agents.values()

    def list_sessions(self) -> Iterable[Session]:
        return self._sessions.values()
