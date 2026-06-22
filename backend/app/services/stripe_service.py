from __future__ import annotations

from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

import stripe
from stripe import StripeClient

from ..config import settings
from ..models import Organization, SubscriptionStatus


class BillingConfigurationError(RuntimeError):
    pass


class BillingProviderError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def get_stripe_client() -> StripeClient:
    if not settings.STRIPE_SECRET_KEY:
        raise BillingConfigurationError("Stripe billing is not configured")
    return StripeClient(settings.STRIPE_SECRET_KEY, max_network_retries=2)


def _price_ids() -> dict[str, str | None]:
    return {
        "growth": settings.STRIPE_GROWTH_PRICE_ID,
        "scale": settings.STRIPE_SCALE_PRICE_ID,
        "agency": settings.STRIPE_AGENCY_PRICE_ID,
    }


def price_id_for_tier(tier: str) -> str:
    price_id = _price_ids().get(tier)
    if not price_id:
        raise BillingConfigurationError(f"Stripe price is not configured for tier: {tier}")
    return price_id


def tier_for_price_id(price_id: str | None) -> str | None:
    if not price_id:
        return None
    return next((tier for tier, configured in _price_ids().items() if configured == price_id), None)


class StripeBillingService:
    def create_checkout_session(self, organization: Organization, tier: str) -> str:
        client = get_stripe_client()
        customer_id = organization.stripe_customer_id
        try:
            if not customer_id:
                customer = client.v1.customers.create(
                    {
                        "name": organization.name,
                        "metadata": {"organization_id": str(organization.id)},
                    }
                )
                customer_id = customer.id
                organization.stripe_customer_id = customer_id

            session = client.v1.checkout.sessions.create(
                {
                    "mode": "subscription",
                    "customer": customer_id,
                    "line_items": [{"price": price_id_for_tier(tier), "quantity": 1}],
                    "success_url": (
                        f"{settings.APP_BASE_URL.rstrip('/')}/settings?billing=success"
                        "&session_id={CHECKOUT_SESSION_ID}"
                    ),
                    "cancel_url": f"{settings.APP_BASE_URL.rstrip('/')}/settings?billing=canceled",
                    "allow_promotion_codes": True,
                    "client_reference_id": str(organization.id),
                    "metadata": {
                        "organization_id": str(organization.id),
                        "tier": tier,
                    },
                    "subscription_data": {
                        "metadata": {
                            "organization_id": str(organization.id),
                            "tier": tier,
                        }
                    },
                }
            )
        except stripe.StripeError as exc:
            raise BillingProviderError("Stripe checkout could not be created") from exc
        if not session.url:
            raise BillingProviderError("Stripe checkout returned no redirect URL")
        return session.url

    def create_portal_session(self, organization: Organization) -> str:
        if not organization.stripe_customer_id:
            raise BillingConfigurationError("No Stripe customer exists for this organization")
        try:
            session = get_stripe_client().v1.billing_portal.sessions.create(
                {
                    "customer": organization.stripe_customer_id,
                    "return_url": f"{settings.APP_BASE_URL.rstrip('/')}/settings",
                }
            )
        except stripe.StripeError as exc:
            raise BillingProviderError("Stripe customer portal could not be created") from exc
        return session.url

    @staticmethod
    def construct_event(payload: bytes, signature: str | None) -> Any:
        if not settings.STRIPE_WEBHOOK_SECRET:
            raise BillingConfigurationError("Stripe webhook verification is not configured")
        if not signature:
            raise BillingProviderError("Missing Stripe signature")
        try:
            return stripe.Webhook.construct_event(
                payload,
                signature,
                settings.STRIPE_WEBHOOK_SECRET,
            )
        except (ValueError, stripe.SignatureVerificationError) as exc:
            raise BillingProviderError("Invalid Stripe webhook signature") from exc


def apply_subscription_event(organization: Organization, subscription: Any) -> None:
    organization.stripe_subscription_id = _object_value(subscription, "id")
    customer_id = _object_value(subscription, "customer")
    if isinstance(customer_id, str):
        organization.stripe_customer_id = customer_id

    raw_status = _object_value(subscription, "status")
    try:
        organization.subscription_status = SubscriptionStatus(raw_status)
    except (TypeError, ValueError):
        organization.subscription_status = SubscriptionStatus.INACTIVE

    metadata = _object_value(subscription, "metadata") or {}
    tier = metadata.get("tier") if hasattr(metadata, "get") else None
    price_id = _subscription_price_id(subscription)
    resolved_tier = tier if tier in _price_ids() else tier_for_price_id(price_id)
    if resolved_tier:
        organization.subscription_tier = resolved_tier

    period_end = _object_value(subscription, "current_period_end")
    if isinstance(period_end, (int, float)):
        organization.subscription_current_period_end = datetime.fromtimestamp(period_end, tz=UTC)
    if organization.subscription_status == SubscriptionStatus.CANCELED:
        organization.stripe_subscription_id = None


def apply_invoice_event(organization: Organization, event_type: str) -> None:
    """Update subscription status from invoice lifecycle (dunning) events.

    Grace-window policy: a failed payment moves the org to ``past_due`` (Stripe
    keeps retrying and access is preserved); a successful payment restores
    ``active``. Definitive lapse (``unpaid``/``canceled``) arrives via the
    ``customer.subscription.*`` events, not here.
    """
    if event_type == "invoice.payment_failed":
        organization.subscription_status = SubscriptionStatus.PAST_DUE
    elif (
        # Only heal a previously-failed payment; authoritative status for every
        # other state arrives via customer.subscription.* events, so a paid
        # invoice must not stomp e.g. a trialing or canceled subscription.
        event_type == "invoice.paid"
        and organization.subscription_status == SubscriptionStatus.PAST_DUE
    ):
        organization.subscription_status = SubscriptionStatus.ACTIVE


def _subscription_price_id(subscription: Any) -> str | None:
    items = _object_value(subscription, "items")
    data = _object_value(items, "data") if items is not None else None
    if not data:
        return None
    price = _object_value(data[0], "price")
    value = _object_value(price, "id")
    return value if isinstance(value, str) else None


def _object_value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)
