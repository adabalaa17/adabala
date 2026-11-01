import asyncio
import os
from typing import Optional, Callable

class BaseAgentAdapter:
    """
    Base class for interacting with external CLI-based AI Agents (e.g., Aider, Claude Code, Goose).
    It manages the background terminal process, sending input, and capturing output.
    """
    def __init__(self, name: str, command: list[str], role: str = "General Developer"):
        self.name = name
        self.command = command
        self.role = role
        self.process: Optional[asyncio.subprocess.Process] = None
        self._output_queue: asyncio.Queue = asyncio.Queue()
        self._stop_event = asyncio.Event()

    async def start(self):
        """Starts the background terminal process for the agent."""
        print(f"[{self.name}] Starting process: {' '.join(self.command)}")
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy()
        )
        self._stop_event.clear()

        # Start background tasks to read stdout and stderr
        asyncio.create_task(self._read_stream(self.process.stdout, "STDOUT"))
        asyncio.create_task(self._read_stream(self.process.stderr, "STDERR"))

    async def _read_stream(self, stream: asyncio.StreamReader, stream_name: str):
        """Reads stream output line by line and queues it."""
        while not self._stop_event.is_set():
            if stream.at_eof():
                break
            try:
                line = await stream.readline()
                if line:
                    text = line.decode('utf-8').strip()
                    await self._output_queue.put(text)
                    print(f"[{self.name} {stream_name}] {text}") # Debug logging
            except Exception as e:
                print(f"[{self.name}] Error reading {stream_name}: {e}")
                break

    async def send_message(self, message: str):
        """Sends a message to the agent's standard input."""
        if self.process and self.process.stdin:
            encoded_msg = f"{message}\n".encode('utf-8')
            self.process.stdin.write(encoded_msg)
            await self.process.stdin.drain()
            print(f"[{self.name}] Sent: {message}")
        else:
            raise RuntimeError(f"[{self.name}] Process is not running.")

    async def wait_for_response(self, timeout: float = 30.0) -> str:
        """Waits for and aggregates output from the agent until silence or timeout."""
        response_lines = []
        try:
            # Wait for the first line with timeout
            first_line = await asyncio.wait_for(self._output_queue.get(), timeout=timeout)
            response_lines.append(first_line)

            # Keep reading while there is immediate output
            while not self._output_queue.empty():
                try:
                    # Very short timeout to capture immediately following lines
                    line = await asyncio.wait_for(self._output_queue.get(), timeout=0.5)
                    response_lines.append(line)
                except asyncio.TimeoutError:
                    break
        except asyncio.TimeoutError:
            pass # No output received within timeout

        return "\n".join(response_lines)

    async def stop(self):
        """Stops the agent process gracefully."""
        self._stop_event.set()
        if self.process:
            try:
                self.process.terminate()
                await self.process.wait()
            except ProcessLookupError:
                pass
            print(f"[{self.name}] Stopped.")

class GenericCLIAdapter(BaseAgentAdapter):
    """
    A generic adapter that can be configured by the user for any compatible CLI agent.
    """
    def __init__(self, name: str, command_string: str, role: str):
        # Very basic shell-like splitting. In reality, you'd use shlex
        command = command_string.split()
        super().__init__(name, command, role)