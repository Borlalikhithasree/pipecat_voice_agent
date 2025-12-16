import os
from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import Response
from loguru import logger
from dotenv import load_dotenv

from .server_utils import parse_telephony_websocket
from .client.inbound_bot import run_bot

load_dotenv()

app = FastAPI()


# -------------------- Twilio Voice Webhook -------------------- #
@app.post("/voice")
async def voice_webhook(request: Request):
    """
    Twilio hits this when a call comes in.
    We respond with <Stream> TwiML that points Twilio
    to our /ws WebSocket endpoint.
    """

    host = os.getenv("SERVER_HOST", request.url.hostname)
    ws_url = f"wss://{host}/ws"

    logger.info(f"📞 Incoming call → WebSocket: {ws_url}")

    twiml = f"""
<Response>
    <Connect>
        <Stream url="{ws_url}" />
    </Connect>
</Response>
"""

    return Response(content=twiml.strip(), media_type="application/xml")


# -------------------- Twilio Media Stream WebSocket -------------------- #
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("🔌 WebSocket connected from Twilio")

    try:
        _, call_data = await parse_telephony_websocket(websocket)

        stream_sid = call_data["stream_sid"]
        call_sid = call_data["call_sid"]

        logger.info(f"📡 stream_sid = {stream_sid}")
        logger.info(f"📞 call_sid   = {call_sid}")

        # Start the RAG + Groq + Deepgram bot
        await run_bot(websocket, stream_sid, call_sid)

    except Exception as e:
        logger.error(f"❌ WebSocket Error: {e}")

    finally:
        logger.info("🔚 WebSocket closed.")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "twilio_chatbot.inbound.server:app",
        host="0.0.0.0",
        port=7860,
        reload=True,
    )