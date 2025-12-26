from datetime import datetime, timedelta
import threading
from typing import Optional
from pymongo import MongoClient

from src.utils.logger import logging

# OPTIONAL confidence (SAFE)
try:
    from src.voice_agent.confidence import AIAnalyzer
except Exception:
    AIAnalyzer = None


class CallLogger:
    def __init__(self, mongo_uri: str, db_name: str, collection_name: str = "calls"):
        self.lock = threading.Lock()
        self.active_calls = {}

        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

        try:
            self.analyzer = AIAnalyzer() if AIAnalyzer else None
        except Exception:
            print("⚠ Confidence analysis disabled")
            self.analyzer = None

    def start_call(self, participant) -> Optional[str]:
        attrs = getattr(participant, "attributes", {}) or {}

        call_id = attrs.get(
            "twilio.callSid",
            f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        caller = attrs.get("twilio.from", "Unknown")
        receiver = attrs.get("twilio.to", "Unknown")

        start_time = datetime.now()

        with self.lock:
            self.active_calls[call_id] = start_time

        self.collection.insert_one({
            "call_id": call_id,
            "caller": caller,
            "receiver": receiver,
            "call_status": "active",
            "start_time": start_time.isoformat(),
            "end_time": None,
            "duration_seconds": None,
            "duration_hms": None,
            "language": None,
            "ai_confidence": None,
        })

        logging.info(f"📞 Call started: {call_id}")
        return call_id

    def end_call(self, call_id: str, transcription_entries: list):
        start_time = self.active_calls.pop(call_id, None)
        if not start_time:
            return

        end_time = datetime.now()
        duration = int((end_time - start_time).total_seconds())

        update = {
            "call_status": "ended",
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "duration_hms": str(timedelta(seconds=duration)),
        }

        self.collection.update_one({"call_id": call_id}, {"$set": update})
        logging.info(f"✅ Call ended: {call_id}")

    def close(self):
        self.client.close()