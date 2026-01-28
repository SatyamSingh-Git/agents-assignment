import logging
import os
from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RunContext,
    cli,
    metrics,
    room_io,
)
from livekit.agents.llm import function_tool
from livekit.plugins import silero, openai
from livekit.plugins.turn_detector.multilingual import MultilingualModel

# Configure logging
logger = logging.getLogger("deepseek-agent")

# Load environment variables
load_dotenv()
load_dotenv(".env.local")


class MyAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="Your name is Kelly. You interact with users via voice. Keep responses concise and natural.",
        )

    async def on_enter(self):
        # Trigger initial greeting
        self.session.generate_reply()


server = AgentServer()


def prewarm(proc: JobProcess):
    """Pre-load VAD model to reduce latency."""
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext):
    # Retrieve API Key - prefer OPENROUTER_API_KEY, fallback to OPENAI_API_KEY
    api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
    
    if not api_key:
        logger.warning("No API Key found! Please set OPENROUTER_API_KEY or OPENAI_API_KEY")

    # Configure LLM to use OpenRouter
    # Note: DeepSeek via OpenRouter usually uses "deepseek/deepseek-chat" or "deepseek/deepseek-r1"
    my_llm = openai.LLM(
        model="deepseek/deepseek-chat",  
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    session = AgentSession(
        # STT/TTS: Using standard defaults - ensure you have keys for these (e.g. Deepgram/Cartesia)
        # If you don't have these, change them to "openai" and ensure your OpenRouter key supports it (or separate OpenAI key)
        stt="deepgram/nova-3", 
        tts="cartesia/sonic-2:9626c31c-bec5-4cca-baa8-f8ba9e84c8bc",
        
        llm=my_llm,  # Use our custom configured DeepSeek LLM
        
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
        resume_false_interruption=True,
        # NOTE: Intelligent interruption filtering is ENABLED BY DEFAULT
        # with default ignore_words and command_words configured in AgentSession
    )

    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    await session.start(
        agent=MyAgent(), 
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(),
        ),
    )


if __name__ == "__main__":
    cli.run_app(server)
