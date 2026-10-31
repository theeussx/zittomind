"""Deterministic heuristics, with explicitly uncalibrated confidence."""

import re

from zittomind.schemas import Classification, Complexity, Effort, Request


def classify(request: Request) -> Classification:
    text = "\n".join(
        [m.content for m in request.messages] + [request.prompt]
    ).casefold()
    advanced = any(
        term in text
        for term in (
            "p = np",
            "p=np",
            "prove",
            "demonstre",
            "auditoria",
            "security audit",
            "distribuído",
            "distributed",
            "arquitetura",
            "deadlock",
        )
    )
    code = "```" in text or "traceback" in text
    steps = len(re.findall(r"(?m)^\s*\d+[.)]", text))
    continuation = bool(request.messages) or any(
        t in text for t in ("continue", "anterior", "previous")
    )
    complexity: Complexity = "SIMPLE"
    if advanced or (code and steps >= 3):
        complexity = "ADVANCED"
    elif code or steps >= 2 or continuation or request.tools:
        complexity = "MEDIUM"
    complexity = request.complexity or complexity
    efforts: dict[Complexity, Effort] = {
        "SIMPLE": "low",
        "MEDIUM": "medium",
        "ADVANCED": "high",
    }
    return Classification(
        complexity=complexity,
        confidence=0.8 if advanced else 0.6,
        category="reasoning" if advanced else "general",
        reasoning_requirement=efforts[complexity],
        context_dependency=continuation,
        tool_dependency=request.tools,
        accuracy_sensitivity="high" if advanced else "normal",
        estimated_output_size="long" if request.max_output_tokens > 2048 else "short",
    )
