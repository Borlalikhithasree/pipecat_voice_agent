import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from twilio.rest import Client
from loguru import logger
from dotenv import load_dotenv

# Import bot logic
from .outbound_bot import run_bot

# Twilio WebSocket event parser
from .server_utils import parse_telephony_websocket

# Pipecat transport
from pipecat.transports.websocket.fastapi import (
    FastAPIWebsocketTransport,
    FastAPIWebsocketParams,
)
from pipecat.serializers.twilio import TwilioFrameSerializer

load_dotenv(override=True)

# ----------------- TWILIO CONFIG -----------------
twilio_client = Client(
    os.getenv("TWILIO_ACCOUNT_SID"),
    os.getenv("TWILIO_AUTH_TOKEN")
)

TWILIO_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")     # Your Twilio number
TO_NUMBER = os.getenv("TO_NUMBER")                   # Your mobile number


# ----------------- FASTAPI LIFESPAN -----------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("📞 Starting Outbound Twilio RAG Bot Server")
    yield
    logger.info("🛑 Shutting Down Twilio Bot Server")


app = FastAPI(lifespan=lifespan)


# ----------------- CORS -----------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------- HEALTH CHECK -----------------
@app.get("/")
async def root():
    return {"status": "ok", "message": "Outbound RAG Bot is running"}


# ----------------- START OUTBOUND CALL -----------------
@app.post("/start-call")
async def start_call(request: Request):
    try:
        data = await request.json()
        customer_id = data.get("customer_id", "unknown")

        if not TO_NUMBER:
            return JSONResponse(status_code=400, content={"error": "Missing TO_NUMBER in .env"})

        server_host = os.getenv("SERVER_HOST")
        websocket_url = f"wss://{server_host}/ws"

        logger.info(f"🔗 WebSocket URL: {websocket_url}")

        # TwiML for outbound call
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Connect>
    <Stream url="{websocket_url}">
      <Parameter name="customer_id" value="{customer_id}" />
      <Parameter name="call_type" value="outbound" />
    </Stream>
  </Connect>
</Response>
"""

        # ⬅ SEND OUTBOUND CALL
        call = twilio_client.calls.create(
            to=TO_NUMBER,
            from_=TWILIO_NUMBER,
            twiml=twiml
        )

        logger.info(f"📞 Outbound call started to {TO_NUMBER}. Call SID: {call.sid}")

        return {"status": "success", "call_sid": call.sid}

    except Exception as e:
        logger.error(f"❌ Error starting outbound call: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ----------------- WEBSOCKET AUDIO STREAM -----------------
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("🔌 Twilio WebSocket Connected")

    try:
        # Parse Twilio "connected" + "start" messages
        _, call_data = await parse_telephony_websocket(websocket)

        stream_sid = call_data["stream_sid"]
        call_sid = call_data["call_sid"]
        metadata = call_data.get("body", {})

        logger.info(f"📡 streamSid={stream_sid}, callSid={call_sid}")
        logger.info(f"📝 Metadata: {metadata}")

        # Create Pipecat transport
        transport = FastAPIWebsocketTransport(
            websocket=websocket,
            params=FastAPIWebsocketParams(
                audio_in_enabled=True,
                audio_out_enabled=True,
                add_wav_header=False,
                serializer=TwilioFrameSerializer(
                    stream_sid=stream_sid,
                    call_sid=call_sid,
                    account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
                    auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
                ),
            ),
        )

        # Run bot logic
        await run_bot(transport, metadata)

    except WebSocketDisconnect:
        logger.info("❌ WebSocket Disconnected")

    except Exception as e:
        logger.error(f"❌ WebSocket Error: {e}")
        await websocket.close()


# ----------------- RUN SERVER -----------------
if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 7860))

    logger.info(f"🚀 Running server on {host}:{port}")

    uvicorn.run("twilio_chatbot.outbound.server:app", host=host, port=port, reload=True)