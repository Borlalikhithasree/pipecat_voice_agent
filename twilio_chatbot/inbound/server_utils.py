import json
from loguru import logger


async def parse_telephony_websocket(websocket):
    """
    Read initial Twilio WebSocket messages and extract:
    - stream_sid
    - call_sid
    """

    logger.info("⏳ Waiting for Twilio 'connected' + 'start' events...")

    stream_sid = None
    call_sid = None

    for _ in range(2):
        msg = await websocket.receive_text()
        data = json.loads(msg)

        event = data.get("event")

        if event == "connected":
            logger.info("📡 Twilio WebSocket connected event")
            continue

        if event == "start":
            start = data["start"]
            stream_sid = start["streamSid"]
            call_sid = start["callSid"]

    logger.info(f"Parsed stream_sid={stream_sid}")
    logger.info(f"Parsed call_sid={call_sid}")

    return "twilio", {"stream_sid": stream_sid, "call_sid": call_sid}