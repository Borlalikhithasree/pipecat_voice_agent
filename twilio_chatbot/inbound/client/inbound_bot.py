import os
import PyPDF2
from dotenv import load_dotenv
from loguru import logger

# Pipecat core
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMMessagesFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask, PipelineParams

from pipecat.processors.aggregators.llm_response import (
    LLMUserResponseAggregator,
    LLMAssistantResponseAggregator,
)

# Services
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.groq.llm import GroqLLMService
from pipecat.services.groq.tts import GroqTTSService

# Transport
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams,
)
from pipecat.serializers.twilio import TwilioFrameSerializer

load_dotenv(override=True)

logger.remove()
logger.add(lambda msg: print(msg, end=""))


# --------------------- RAG: Load PDF --------------------- #
def load_rag_text() -> str:
    """
    Load first few pages of Loan_Recovery.pdf and truncate to ~800–1000 words
    so the prompt stays efficient.
    """
    # project_root / Data / Loan_Recovery.pdf
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    pdf_path = os.path.join(project_root, "Data", "Loan_Recovery.pdf")

    if not os.path.exists(pdf_path):
        logger.error(f"❌ Loan_Recovery.pdf not found at: {pdf_path}")
        return "Loan recovery policies include EMIs, penalties, repayment options, and settlement rules."

    try:
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            logger.info(f"📘 Loading PDF: {len(reader.pages)} pages")

            chunks = []
            # read first 5 pages max
            for page in reader.pages[:5]:
                text = page.extract_text() or ""
                text = text.strip()
                if text:
                    chunks.append(text)

        full_text = "\n\n".join(chunks)
        words = full_text.split()
        max_words = 900
        if len(words) > max_words:
            logger.warning(
                f"⚠️ Truncating PDF from {len(words)} to {max_words} words"
            )
            full_text = " ".join(words[:max_words])

        logger.info(f"✅ RAG loaded: {len(full_text.split())} words")
        return full_text

    except Exception as e:
        logger.error(f"🔥 PDF read error: {e}")
        return "Loan recovery guidelines include repayment plans, EMI rules, notices, and hardship assistance."


# --------------------- Main Bot --------------------- #
async def run_bot(websocket, stream_sid: str, call_sid: str):
    """
    Main inbound voice bot for Twilio:
    - Deepgram STT
    - Groq LLM (llama-3.3-70b)
    - Groq TTS (playai-tts)
    - RAG from Loan_Recovery.pdf
    """

    logger.info(
        f"🤖 Starting Loan Recovery Bot (Groq LLM + Deepgram STT + Groq TTS)"
    )

    # ---------- RAG context ---------- #
    rag_text = load_rag_text()

    system_prompt = f"""
You are a professional and empathetic **Loan Recovery Assistant** on a phone call.

You MUST follow these rules:

- Use ONLY the following knowledge base to answer questions:
{rag_text}

- Keep answers SHORT: 1–3 sentences.
- Speak clearly and slowly, like a human call center agent.
- Never threaten the caller.
- Offer repayment plans, EMI restructuring, or hardship options when appropriate.
- If you don't know something, say you'll connect them to a human agent.

Always sound calm, respectful, and supportive.
"""

    # ---------- Twilio serializer ---------- #
    serializer = TwilioFrameSerializer(
        stream_sid=stream_sid,
        call_sid=call_sid,
        account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
        auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
    )

    # ---------- Transport (FastAPI WebSocket) ---------- #
    transport = FastAPIWebsocketTransport(
        websocket=websocket,
        params=FastAPIWebsocketParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            add_wav_header=False,
            vad_analyzer=SileroVADAnalyzer(),
            serializer=serializer,
        ),
    )

    # ---------- Services ---------- #
    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        model="nova-2-phonecall",
        language="en-US",
    )

    llm = GroqLLMService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="llama-3.3-70b-versatile",
    )

    # Groq TTS (PlayAI)
    tts = GroqTTSService(
        api_key=os.getenv("GROQ_API_KEY"),
        model="playai-tts",
        voice="Celeste-PlayAI",  # you can change voice later if needed
    )

    user_agg = LLMUserResponseAggregator()
    assistant_agg = LLMAssistantResponseAggregator()

    # Initial messages with RAG-embedded system prompt
    initial_messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "assistant",
            "content": "Hello! Thank you for calling Loan Recovery Support. How can I help you today?",
        },
    ]

    # ---------- Pipeline ---------- #
    pipeline = Pipeline(
        [
            transport.input(),  # audio from Twilio
            stt,                # STT
            user_agg,           # collect user utterances
            llm,                # Groq LLM
            tts,                # Groq TTS
            transport.output(), # audio back to Twilio
            assistant_agg,
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            audio_in_sample_rate=8000,
            audio_out_sample_rate=8000,
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
    )

    # ---------- Events ---------- #
    @transport.event_handler("on_client_connected")
    async def on_connect(tr, client):
        logger.info("📞 Caller connected")
        # Kick off conversation with RAG-based system prompt + greeting
        await task.queue_frames([LLMMessagesFrame(initial_messages)])

    @transport.event_handler("on_client_disconnected")
    async def on_disconnect(tr, client):
        logger.info("☎️ Caller disconnected")
        await task.cancel()

    # ---------- Run pipeline ---------- #
    runner = PipelineRunner()
    await runner.run(task)

    logger.info(f"✅ Bot session ended for call {call_sid}")