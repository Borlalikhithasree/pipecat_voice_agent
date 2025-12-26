from src.voice_agent.transcription_logger import TranscriptionLogger
from src.voice_agent.call_logger import CallLogger

MONGO_URI = "mongodb+srv://voiceuser:Likhithasree%401509@cluster0.aii25rw.mongodb.net/"
DB = "pipecat_db"


class DummyParticipant:
    def __init__(self):
        self.attributes = {
            "twilio.callSid": "CA123456789",
            "twilio.from": "+917731862569",
            "twilio.to": "+18573679132",
        }


def main():
    print("🚀 Starting transcription test")

    tlog = TranscriptionLogger(MONGO_URI, DB)
    clog = CallLogger(MONGO_URI, DB)

    participant = DummyParticipant()

    call_id = clog.start_call(participant)
    tlog.start_transcription(call_id)

    tlog.log_user_speech("Hello, my password is not working")
    tlog.log_agent_response("I can help you reset it")

    session_id, entries = tlog.close_transcription()
    clog.end_call(call_id, entries)

    print("✅ TEST COMPLETED SUCCESSFULLY")


if __name__ == "__main__":
    main()