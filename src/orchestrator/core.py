import asyncio
from datetime import datetime, timedelta
from typing import List, Dict
from src.adapters.base import BaseAgentAdapter
from src.memory.db import mongo_db, vector_db

class Orchestrator:
    def __init__(self):
        self.agents: Dict[str, BaseAgentAdapter] = {}
        self.is_paused_for_cto = False
        self.current_plan = "Initial Project Setup Phase"
        self.sprint_days = 3
        # For testing/demo purposes, we use seconds instead of days.
        # In production, replace `seconds` with `days`.
        self.sprint_duration = timedelta(seconds=30)
        self.last_meeting_time = datetime.now()

    def register_agent(self, agent: BaseAgentAdapter):
        self.agents[agent.name] = agent
        print(f"[Orchestrator] Registered agent: {agent.name} with role: {agent.role}")

    async def start_all_agents(self):
        for agent in self.agents.values():
            await agent.start()

    async def stop_all_agents(self):
        for agent in self.agents.values():
            await agent.stop()

    async def run_meeting_phase(self):
        """
        The core of the 3-day cycle. Agents stop standard work, discuss the project,
        check for vulnerabilities, and compile a report for the CTO.
        """
        print("\n--- INITIATING 3-DAY SPRINT MEETING ---")
        meeting_notes = []

        # Simulate discussion by asking each agent for input based on their role
        for name, agent in self.agents.items():
            prompt = (
                f"SYSTEM: It is time for the 3-day sprint meeting. "
                f"Your role is {agent.role}. Based on the current plan '{self.current_plan}', "
                f"what are your updates, vulnerability checks, and suggestions for the next 3 days?"
            )
            await agent.send_message(prompt)
            response = await agent.wait_for_response(timeout=5.0)

            # If the agent doesn't respond (e.g. a dummy shell), we mock a response for demo
            if not response.strip():
                response = f"[{name}] (Simulated response) Everything looks good. Suggesting we refactor the auth module."

            note = f"Agent {name} ({agent.role}): {response}"
            meeting_notes.append(note)
            print(note)

            # Save to shared agent memory so other agents can recall this later
            memory_id = f"meeting_{datetime.now().timestamp()}_{name}"
            vector_db.add_memory(memory_id, text=response, metadata={"agent": name, "type": "meeting_note"})

        print("--- MEETING CONCLUDED. GENERATING REPORT ---")

        # Aggregate and save to MongoDB for the CTO
        report_data = {
            "timestamp": datetime.now(),
            "previous_plan": self.current_plan,
            "meeting_notes": meeting_notes,
            "status": "pending_cto_approval"
        }
        report_id = await mongo_db.save_report(report_data)
        print(f"[Orchestrator] Report {report_id} generated and waiting for CTO approval.")

        # Update global state to ensure the dashboard knows we are paused
        state_col = await mongo_db.get_collection("orchestrator_state")
        await state_col.update_one(
            {"type": "global_state"},
            {"$set": {"is_paused": True}},
            upsert=True
        )

        self.is_paused_for_cto = True
        self.last_meeting_time = datetime.now()

    async def main_loop(self):
        """
        The continuous 24/7 background loop.
        """
        print("[Orchestrator] Starting continuous 24/7 background loop...")
        await self.start_all_agents()

        try:
            while True:
                if self.is_paused_for_cto:
                    # Query MongoDB to see if the CTO has updated the status and provided a new plan.
                    state_col = await mongo_db.get_collection("orchestrator_state")
                    global_state = await state_col.find_one({"type": "global_state"})
                    if global_state and not global_state.get("is_paused", True):
                        self.is_paused_for_cto = False
                        self.current_plan = global_state.get("current_plan", self.current_plan)
                        self.last_meeting_time = datetime.now()
                        print(f"[Orchestrator] Resuming operations with new plan: {self.current_plan}")
                    else:
                        print("[Orchestrator] Paused. Agents are waiting for CTO approval on the dashboard...")
                        await asyncio.sleep(5)
                        continue

                now = datetime.now()
                if now - self.last_meeting_time >= self.sprint_duration:
                    await self.run_meeting_phase()
                else:
                    # Normal working phase. Agents would theoretically be working on `self.current_plan`.
                    print(f"[Orchestrator] Working on plan: '{self.current_plan}'. Next meeting in {self.sprint_duration - (now - self.last_meeting_time)}...")
                    await asyncio.sleep(5)
        except asyncio.CancelledError:
            print("[Orchestrator] Shutting down...")
        finally:
            await self.stop_all_agents()

# Utility to start the orchestrator
async def run_orchestrator(dummy_agents: bool = True):
    orch = Orchestrator()
    if dummy_agents:
        # Register a couple of dummy agents using basic 'cat' to simulate echo/CLI interaction
        # In production, these would be `aider`, `claude-code`, etc.
        from src.adapters.base import GenericCLIAdapter
        orch.register_agent(GenericCLIAdapter("OpenHands", "cat", "Security & QA Engineer"))
        orch.register_agent(GenericCLIAdapter("Aider", "cat", "Lead Developer"))

    await orch.main_loop()

if __name__ == "__main__":
    asyncio.run(run_orchestrator())