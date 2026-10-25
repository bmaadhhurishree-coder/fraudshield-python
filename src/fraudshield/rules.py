"""Deterministic, explainable demo rules; NOT a production fraud model."""
from .models import Decision, RiskResult, TransactionCreate

RULE_VERSION = "rules-v1"


def score_transaction(tx: TransactionCreate) -> RiskResult:
    score = 0
    reasons: list[str] = []
    if tx.amount >= 2000:
        score += 35
        reasons.append("high_amount")
    elif tx.amount >= 500:
        score += 15
        reasons.append("elevated_amount")
    if tx.country != tx.home_country:
        score += 25
        reasons.append("cross_border")
    if not tx.known_device:
        score += 20
        reasons.append("new_device")
    if tx.transactions_last_hour >= 10:
        score += 30
        reasons.append("high_velocity")
    elif tx.transactions_last_hour >= 5:
        score += 15
        reasons.append("elevated_velocity")
    score = min(score, 100)
    if score >= 90:
        decision = Decision.DECLINE
    elif score >= 50:
        decision = Decision.REVIEW
    else:
        decision = Decision.ALLOW
    return RiskResult(score=score, decision=decision, reasons=reasons, rule_version=RULE_VERSION)