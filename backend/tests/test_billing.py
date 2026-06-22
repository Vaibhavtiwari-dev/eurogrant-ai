"""Tests for Stripe billing webhooks and subscription-status enforcement (Wave 3).

Signature verification is exercised separately; the lifecycle tests patch
``StripeBillingService.construct_event`` so they assert event handling and DB
state without real Stripe signature crypto.
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import models
from app.main import app
from app.services.stripe_service import BillingProviderError

client = TestClient(app)

CONSTRUCT_EVENT_PATH = "app.routers.billing.StripeBillingService.construct_event"
CELERY_DELAY_PATH = "app.routers.proposals.generate_proposal_task.delay"


def _make_org(db_session, **overrides):
    unique = str(uuid.uuid4())[:8]
    org = models.Organization(
        name=f"Billing Org {unique}",
        subscription_tier="growth",
        stripe_customer_id=f"cus_{unique}",
        stripe_subscription_id=f"sub_{unique}",
        **overrides,
    )
    db_session.add(org)
    db_session.commit()
    db_session.refresh(org)
    return org


def _post_event(event: dict):
    return client.post(
        "/api/v1/billing/webhook",
        content=b"{}",
        headers={"stripe-signature": "test-sig"},
    ), event


# ---------------------------------------------------------------------------
# Webhook signature / validation
# ---------------------------------------------------------------------------


def test_webhook_rejects_invalid_signature(db_session):
    with patch(CONSTRUCT_EVENT_PATH, side_effect=BillingProviderError("bad sig")):
        response = client.post(
            "/api/v1/billing/webhook",
            content=b"{}",
            headers={"stripe-signature": "wrong"},
        )
    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "INVALID_WEBHOOK_SIGNATURE"


# ---------------------------------------------------------------------------
# Invoice lifecycle (dunning) — grace-window policy
# ---------------------------------------------------------------------------


def test_invoice_payment_failed_sets_past_due(db_session):
    org = _make_org(db_session, subscription_status=models.SubscriptionStatus.ACTIVE)
    event = {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "subscription": org.stripe_subscription_id,
                "customer": org.stripe_customer_id,
            }
        },
    }
    with patch(CONSTRUCT_EVENT_PATH, return_value=event):
        response, _ = _post_event(event)

    assert response.status_code == 200
    db_session.expire_all()
    refreshed = db_session.get(models.Organization, org.id)
    assert refreshed.subscription_status == models.SubscriptionStatus.PAST_DUE


def test_invoice_paid_restores_active(db_session):
    org = _make_org(db_session, subscription_status=models.SubscriptionStatus.PAST_DUE)
    event = {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": "invoice.paid",
        "data": {
            "object": {
                "subscription": org.stripe_subscription_id,
                "customer": org.stripe_customer_id,
            }
        },
    }
    with patch(CONSTRUCT_EVENT_PATH, return_value=event):
        response, _ = _post_event(event)

    assert response.status_code == 200
    db_session.expire_all()
    refreshed = db_session.get(models.Organization, org.id)
    assert refreshed.subscription_status == models.SubscriptionStatus.ACTIVE


def test_subscription_deleted_cancels_and_clears_subscription(db_session):
    org = _make_org(db_session, subscription_status=models.SubscriptionStatus.ACTIVE)
    event = {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": org.stripe_subscription_id,
                "customer": org.stripe_customer_id,
                "status": "canceled",
                "metadata": {"organization_id": str(org.id)},
            }
        },
    }
    with patch(CONSTRUCT_EVENT_PATH, return_value=event):
        response, _ = _post_event(event)

    assert response.status_code == 200
    db_session.expire_all()
    refreshed = db_session.get(models.Organization, org.id)
    assert refreshed.subscription_status == models.SubscriptionStatus.CANCELED
    assert refreshed.stripe_subscription_id is None


def test_webhook_is_idempotent_on_replay(db_session):
    """A replayed event id is a no-op — the second delivery must not re-apply."""
    org = _make_org(db_session, subscription_status=models.SubscriptionStatus.ACTIVE)
    event = {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": "invoice.payment_failed",
        "data": {
            "object": {
                "subscription": org.stripe_subscription_id,
                "customer": org.stripe_customer_id,
            }
        },
    }
    with patch(CONSTRUCT_EVENT_PATH, return_value=event):
        first, _ = _post_event(event)
        assert first.status_code == 200

        # Simulate a later, unrelated change, then replay the SAME event id.
        db_session.expire_all()
        org_reloaded = db_session.get(models.Organization, org.id)
        org_reloaded.subscription_status = models.SubscriptionStatus.ACTIVE
        db_session.commit()

        second, _ = _post_event(event)
        assert second.status_code == 200

    db_session.expire_all()
    refreshed = db_session.get(models.Organization, org.id)
    # Replay was ignored, so the manual ACTIVE state survives.
    assert refreshed.subscription_status == models.SubscriptionStatus.ACTIVE
    events = (
        db_session.query(models.BillingWebhookEvent)
        .filter(models.BillingWebhookEvent.stripe_event_id == event["id"])
        .count()
    )
    assert events == 1


# ---------------------------------------------------------------------------
# Subscription-status enforcement on proposal creation
# ---------------------------------------------------------------------------


def _grant(db_session):
    grant = models.Grant(
        external_id=f"BILL-{uuid.uuid4().hex[:8]}",
        title="Billing Enforcement Grant",
        description="Test grant for billing enforcement.",
        deadline=datetime(2026, 12, 31, 17, 0, tzinfo=UTC),
    )
    db_session.add(grant)
    db_session.commit()
    db_session.refresh(grant)
    return grant


def test_canceled_subscription_blocks_proposal(db_session, authenticated_client, test_user):
    grant = _grant(db_session)
    org = db_session.get(models.Organization, test_user.organization_id)
    org.subscription_status = models.SubscriptionStatus.CANCELED
    db_session.commit()

    response = authenticated_client.post("/api/v1/proposals/", json={"grant_id": grant.id})
    assert response.status_code == 402
    assert response.json()["detail"]["error"]["code"] == "BILLING_INACTIVE"


def test_past_due_subscription_allows_proposal(db_session, authenticated_client, test_user):
    """Grace window: a past_due org can still generate while Stripe retries."""
    grant = _grant(db_session)
    org = db_session.get(models.Organization, test_user.organization_id)
    org.subscription_status = models.SubscriptionStatus.PAST_DUE
    db_session.commit()

    # Disable the shared rate limiter so this test does not consume the
    # cross-test 5/min /proposals budget (mirrors tests/test_routers.py).
    from app.limiter import limiter

    was_enabled = limiter.enabled
    limiter.enabled = False
    try:
        with patch(CELERY_DELAY_PATH) as mock_delay:
            response = authenticated_client.post("/api/v1/proposals/", json={"grant_id": grant.id})
    finally:
        limiter.enabled = was_enabled

    assert response.status_code == 202
    mock_delay.assert_called_once()


def test_canceled_subscription_blocks_regeneration(db_session, authenticated_client, test_user):
    """A lapsed org cannot burn LLM compute via section regeneration either."""
    grant = _grant(db_session)
    proposal = models.Proposal(
        organization_id=test_user.organization_id,
        grant_id=grant.id,
        status=models.ProposalStatus.COMPLETED,
    )
    db_session.add(proposal)
    db_session.commit()
    section = models.ProposalSection(
        proposal_id=proposal.id,
        section_key="summary",
        name="Executive Summary",
        content_json={"type": "doc", "content": []},
        order=0,
        status=models.SectionStatus.COMPLETED,
        version=1,
    )
    db_session.add(section)
    org = db_session.get(models.Organization, test_user.organization_id)
    org.subscription_status = models.SubscriptionStatus.CANCELED
    db_session.commit()

    from app.limiter import limiter

    was_enabled = limiter.enabled
    limiter.enabled = False
    try:
        with patch("app.routers.proposals.regenerate_proposal_section_task.delay") as mock_delay:
            response = authenticated_client.post(
                f"/api/v1/proposals/{proposal.id}/sections/{section.id}/regenerate",
                json={"expected_version": 1},
            )
    finally:
        limiter.enabled = was_enabled

    assert response.status_code == 402
    assert response.json()["detail"]["error"]["code"] == "BILLING_INACTIVE"
    mock_delay.assert_not_called()


def test_invoice_paid_does_not_override_non_past_due(db_session):
    """invoice.paid only heals past_due; it must not stomp e.g. a trialing org."""
    org = _make_org(db_session, subscription_status=models.SubscriptionStatus.TRIALING)
    event = {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": "invoice.paid",
        "data": {
            "object": {
                "subscription": org.stripe_subscription_id,
                "customer": org.stripe_customer_id,
            }
        },
    }
    with patch(CONSTRUCT_EVENT_PATH, return_value=event):
        response, _ = _post_event(event)

    assert response.status_code == 200
    db_session.expire_all()
    refreshed = db_session.get(models.Organization, org.id)
    assert refreshed.subscription_status == models.SubscriptionStatus.TRIALING
