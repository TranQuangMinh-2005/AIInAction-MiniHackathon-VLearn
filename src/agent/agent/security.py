"""
Security guard: phát hiện và chặn prompt injection, jailbreak, content độc hại.
"""

import re

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|the\s+above)\s+(instructions?|directions?|prompts?)",
    r"(forget|disregard)\s+(all\s+)?(previous|your)\s+(instructions?|rules?)",
    r"(system\s*)?prompt\s*(leak|leaking|extract|steal|show\s*me)",
    r"what\s+is\s+your\s+(system\s*)?prompt",
    r"tell\s+me\s+your\s+(system\s*)?prompt",
    r"reveal\s+your\s+(instructions?|prompt)",
    r"output\s+your\s+(instructions?|prompt)",
    r"print\s+the\s+(above|previous|system).*prompt",
    # Vietnamese
    r"bỏ\s+qua\s+(tất\s+cả\s+)?(hướng\s+dẫn|chỉ\s+dẫn|lời\s+khuyên)\s+(trước\s+đó|phía\s+trên|trên)",
    r"(quên|bỏ)\s+(hướng\s+dẫn|luật|lệnh)\s+(của\s+bạn|trước\s+đó)",
    r"(cho|đưa|hiển\s+thị|in)\s+(tôi|tao|mình)\s+(system\s*)?prompt",
    r"tiết\s+lộ\s+(prompt|hướng\s+dẫn)\s+của\s+bạn",
]

JAILBREAK_PATTERNS = [
    r"\bDAN\b.*\b(do\s+anything\s+now|mode)",
    r"pretend\s+(you\s+are|to\s+be)\s+(an?\s+)?(unfiltered|unethical|evil)",
    r"roleplay\s+as\s+(an?\s+)?(unfiltered|unethical|hacker)",
    r"you\s+are\s+now\s+(free|unshackled|jailbroken|liberated)",
    r"developer\s+mode|god\s*mode|jailbreak",
    r"without\s+(any\s+)?(restrictions?|limitations?|filters?|rules?)",
    r"bypass\s+(your\s+)?(filters?|restrictions?|safety)",
    r"ignore\s+(your\s+)?(safety|ethical|content)\s+(guidelines?|policies?|rules?)",
]

HARMFUL_PATTERNS = [
    r"(cách|how\s*to|hướng\s*dẫn)\s+(hack|tấn\s*công|crack|phá\s*hoại)",
    r"(tạo|make|create)\s+(virus|malware|ransomware|trojan)",
    r"\b(bạo\s*lực|khủng\s*bố|terrorism)\b",
    r"(tự\s*tử|suicide|tự\s*hại|self\s*harm)",
]

MAX_QUESTION_LENGTH = 2000


def is_prompt_injection(text: str) -> bool:
    text_lower = text.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


def is_jailbreak(text: str) -> bool:
    text_lower = text.lower()
    for pattern in JAILBREAK_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


def is_harmful(text: str) -> bool:
    text_lower = text.lower()
    for pattern in HARMFUL_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            return True
    return False


def validate_input(question: str) -> tuple[bool, str]:
    """Trả về (is_safe, reason)."""
    if not question or not question.strip():
        return False, "Câu hỏi trống."

    if len(question) > MAX_QUESTION_LENGTH:
        return False, f"Câu hỏi quá dài (tối đa {MAX_QUESTION_LENGTH} ký tự)."

    if is_prompt_injection(question):
        return False, "Phát hiện prompt injection. Vui lòng đặt câu hỏi học thuật."

    if is_jailbreak(question):
        return False, "Phát hiện jailbreak attempt. Vui lòng đặt câu hỏi học thuật."

    if is_harmful(question):
        return False, "Phát hiện nội dung không phù hợp. Vui lòng đặt câu hỏi học thuật."

    return True, ""
