import os
from datetime import datetime
from pymongo import MongoClient
from langdetect import detect

from src.voice_agent.masking import ContentOptimizer


class TranscriptionLogger:
    def __init__(self, mongo_uri: str, db_name: str, collection_name="call_transcription"):
        self.client = MongoClient(mongo_uri)
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]

        self.transcription_entries = []
        self.session_id = None
        self.language = None

        self.masker = ContentOptimizer()

        self.log_dir = "Artifacts/call_logs"
        os.makedirs(self.log_dir, exist_ok=True)

    def start_transcription(self, session_id: str):
        self.session_id = session_id
        self.file_path = os.path.join(self.log_dir, f"{session_id}.txt")

        with open(self.file_path, "w") as f:
            f.write("CALL STARTED\n")

    def _log(self, text: str, speaker: str):
        if not text.strip():
            return

        text = self.masker.process(text)

        if not self.language:
            try:
                self.language = detect(text)
            except Exception:
                self.language = "en"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "speaker": speaker,
            "text": text,
            "sentiment": "disabled"
        }

        self.transcription_entries.append(entry)

        with open(self.file_path, "a") as f:
            f.write(f"{speaker}: {text}\n")

        self.collection.update_one(
            {"session_id": self.session_id},
            {"$set": {
                "session_id": self.session_id,
                "language": self.language,
                "entries": self.transcription_entries,
                "updated_at": datetime.now()
            }},
            upsert=True
        )

    def log_user_speech(self, text: str):
        self._log(text, "USER")

    def log_agent_response(self, text: str):
        self._log(text, "AGENT")

    def close_transcription(self):
        with open(self.file_path, "a") as f:
            f.write("CALL ENDED\n")

        return self.session_id, self.transcription_entries