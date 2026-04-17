from __future__ import annotations

from .models import Agent, Container, InstanceStatus, OpenClawInstance, Session
from .repository import InMemoryRepository


class HarnessService:
    """Service boundary to interact with src/openclaw_harness capabilities.

    Keep UI/API layers decoupled from direct script/command invocation.
    """

    def __init__(self) -> None:
        # TODO: replace with real harness integration.
        self._repo = InMemoryRepository()
        self._seed_data()

    @property
    def repository(self) -> InMemoryRepository:
        return self._repo

    def _seed_data(self) -> None:
        container = Container(
            id="ctr-001",
            name="openclaw-gateway",
            image="openclaw/gateway:latest",
            status=InstanceStatus.RUNNING,
        )
        self._repo.upsert_container(container)

        instances = [
            OpenClawInstance(
                id="inst-001",
                container_id=container.id,
                name="gateway-main",
                status=InstanceStatus.RUNNING,
                endpoint="http://localhost:8080",
            ),
            OpenClawInstance(
                id="inst-002",
                container_id=container.id,
                name="gateway-shadow",
                status=InstanceStatus.STOPPED,
                endpoint="http://localhost:8081",
            ),
        ]
        for instance in instances:
            self._repo.upsert_instance(instance)

        agent = Agent(
            id="agent-001",
            instance_id="inst-001",
            name="assistant",
            model="gpt-4.1",
            online=True,
        )
        self._repo.upsert_agent(agent)

        session = Session(id="sess-001", agent_id=agent.id, user_id="demo-user", active=True)
        self._repo.upsert_session(session)
