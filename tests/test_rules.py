from uuid import uuid4

from fraudshield.models import Decision, TransactionCreate
from fraudshield.rules import score_transaction


def tx(**changes):
    values = dict(transaction_id=uuid4(), account_id="demo", amount="90.00", country="US",
                  home_country="US", device_id="device-1", known_device=True,
                  transactions_last_hour=1)
    return TransactionCreate(**(values | changes))


def test_low_risk_is_allowed():
    assert score_transaction(tx()).decision == Decision.ALLOW


def test_moderate_risk_goes_to_review():
    result = score_transaction(tx(amount="800", country="GB", known_device=False))
    assert result.decision == Decision.REVIEW
    assert result.score == 60


def test_high_risk_is_declined():
    result = score_transaction(tx(amount="4800", country="GB", known_device=False,
                                  transactions_last_hour=12))
    assert result.decision == Decision.DECLINE
    assert result.score == 100
    assert len(result.reasons) == 4