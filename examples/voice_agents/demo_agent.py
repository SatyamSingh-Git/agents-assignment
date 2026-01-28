"""
Simple demo agent for testing intelligent interruption handling.
Uses OpenAI for everything (LLM, STT, TTS) - only needs OPENAI_API_KEY.
"""
import logging
import os
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
)
from livekit.agents.llm import function_tool
from livekit.plugins import openai, silero

logger = logging.getLogger("demo-agent")
load_dotenv()
load_dotenv(".env.local")


class DemoAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="You are Kelly, a friendly AI assistant. Keep responses brief and conversational.",
        )

    async def on_enter(self):
        self.session.generate_reply()


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        # Use OpenAI for everything (only need OPENAI_API_KEY or OPENROUTER_API_KEY)
        llm="openai/gpt-4o-mini",      # Free tier available
        stt="openai/whisper-1",         # OpenAI STT
        tts="openai/tts-1:alloy",       # OpenAI TTS
        
        vad=ctx.proc.userdata["vad"],
        
        # Interrupt filter is ENABLED BY DEFAULT with:
        # - ignore_words: ["yeah", "ok", "hmm", "uh-huh", etc.]
        # - command_words: ["stop", "wait", "hold on", etc.]
    )

    await session.start(agent=DemoAgent(), room=ctx.room)


if __name__ == "__main__":
    cli.run_app(server)
