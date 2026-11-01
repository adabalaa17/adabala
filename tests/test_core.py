import pytest
import asyncio
from src.adapters.base import GenericCLIAdapter
from src.orchestrator.core import Orchestrator

@pytest.mark.asyncio
async def test_agent_registration():
    orch = Orchestrator()
    agent = GenericCLIAdapter("TestAgent", "echo hello", "Tester")
    orch.register_agent(agent)
    assert "TestAgent" in orch.agents
    assert orch.agents["TestAgent"].role == "Tester"

@pytest.mark.asyncio
async def test_agent_adapter_run():
    agent = GenericCLIAdapter("TestAgent", "echo hello", "Tester")
    await agent.start()
    response = await agent.wait_for_response(timeout=1.0)
    await agent.stop()
    assert "hello" in response.lower()
