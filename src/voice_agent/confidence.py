from typing import Optional
from dataclasses import dataclass
from datetime import datetime
import os

try:
    from langchain_aws import ChatBedrockConverse
    from langchain_core.prompts import PromptTemplate
    from langchain_core.output_parsers import JsonOutputParser
except Exception:
    ChatBedrockConverse = None


@dataclass
class AnalysisResult:
    ai_confidence_percentage: float
    error_percentage: float
    main_topics: list
    key_points: list
    action_items: list
    intent_category: str
    conversation_language: str
    analysis_timestamp: str


class AIAnalyzer:
    def __init__(self):
        self.enabled = False

        if not ChatBedrockConverse:
            return

        if not all([
            os.getenv("AWS_ACCESS_KEY_ID"),
            os.getenv("AWS_SECRET_ACCESS_KEY"),
            os.getenv("AWS_REGION"),
        ]):
            return

        try:
            self.client = ChatBedrockConverse(
                model="us.amazon.nova-micro-v1:0",
                max_tokens=300,
                disable_streaming=True,
                region_name=os.getenv("AWS_REGION"),
            )

            self.parser = JsonOutputParser(pydantic_object=AnalysisResult)
            self.enabled = True
        except Exception:
            self.enabled = False

    def analyze_transcription(self, transcript: str) -> Optional[AnalysisResult]:
        if not self.enabled or not transcript or len(transcript.strip()) < 10:
            return None
        return None