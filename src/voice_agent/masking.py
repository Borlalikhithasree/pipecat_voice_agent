import re

SENSITIVE_WORDS = ["password", "pass", "pwd", "otp"]

class ContentOptimizer:
    def __init__(self, mask="****"):
        self.mask = mask

    def process(self, text: str) -> str:
        for word in SENSITIVE_WORDS:
            text = re.sub(word, self.mask, text, flags=re.IGNORECASE)
        return text