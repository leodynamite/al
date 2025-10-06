from __future__ import annotations

from typing import Dict, List, Tuple

from .models import Script, ScriptQuestion, LeadAnswer, LeadStatus


HOT_THRESHOLD = 70
WARM_THRESHOLD_LOW = 40
WARM_THRESHOLD_HIGH = 69


def compute_lead_score(script: Script, answers: List[LeadAnswer]) -> Tuple[int, LeadStatus]:
    total_score = 0
    # Индекс вопросов по id
    q_by_id: Dict[str, ScriptQuestion] = {q.id: q for q in script.questions}
    for ans in answers:
        q = q_by_id.get(ans.question_id)
        if not q:
            continue
        # Совпадение по hot_values для choice/text/number/date
        if q.hot_values:
            value_norm = (ans.value or "").strip().lower()
            if any(value_norm == hv.strip().lower() for hv in q.hot_values):
                total_score += max(0, q.weight)

    status = LeadStatus.new
    if total_score >= HOT_THRESHOLD:
        status = LeadStatus.hot
    elif WARM_THRESHOLD_LOW <= total_score <= WARM_THRESHOLD_HIGH:
        status = LeadStatus.qualified
    else:
        status = LeadStatus.new

    return total_score, status




