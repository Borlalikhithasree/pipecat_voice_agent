import json
from fastapi import WebSocket
from loguru import logger


async def parse_telephony_websocket(websocket: WebSocket):
    """
    Parse Twilio's initial two WebSocket messages:
      1. "connected" → protocol info
      2. "start" → streamSid, callSid, customParameters
    """

    stream_sid = None
    call_sid = None
    custom_params = {}

    # Twilio always sends 2 messages before audio starts
    for _ in range(2):
        message = await websocket.receive_text()
        data = json.loads(message)

        event = data.get("event")

        if event == "connected":
            logger.info("Twilio WebSocket connected event received")
            continue

        if event == "start":
            start_data = data.get("start", {})

            stream_sid = start_data.get("streamSid")
            call_sid = start_data.get("callSid")
            custom_params = start_data.get("customParameters", {})

            logger.info(f"Call Started: stream_sid={stream_sid}, call_sid={call_sid}")
            logger.info(f"Custom Params: {custom_params}")

    if not stream_sid or not call_sid:
        raise ValueError("❌ Missing streamSid or callSid in Twilio WebSocket messages")

    return "twilio", {
        "stream_sid": stream_sid,
        "call_sid": call_sid,
        "body": custom_params,
    }

