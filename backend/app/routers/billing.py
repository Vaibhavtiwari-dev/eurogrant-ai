import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .. import database, models, schemas
from ..auth import get_current_user, require_role
from ..errors import error_response
from ..limiter import limiter
from ..services.stripe_service import (
    BillingConfigurationError,
    BillingProviderError,
    StripeBillingService,
    apply_invoice_event,
    apply_subscription_event,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])


def _organization_for_user(db: Session, user: models.User) -> models.Organization:
    if user.organization_id is None:
        error_response("FORBIDDEN", "You are not assigned to an organisation.", status_code=403)
    organization = db.get(models.Organization, user.organization_id)
    if organization is None:
        error_response("NOT_FOUND", "Organisation not found.", status_code=404)
    return organization


def _billing_error(exc: Exception) -> None:
    if isinstance(exc, BillingConfigurationError):
        error_response("BILLING_NOT_CONFIGURED", str(exc), status_code=503)
    logger.warning("Stripe billing provider request failed", exc_info=True)
    error_response(
        "BILLING_PROVIDER_UNAVAILABLE",
        "The billing provider is temporarily unavailable.",
        status_code=502,
    )


@router.get("/status", response_model=schemas.BillingStatusOut)
def billing_status(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(get_current_user),
) -> schemas.BillingStatusOut:
    organization = _organization_for_user(db, current_user)
    return schemas.BillingStatusOut(
        tier=organization.subscription_tier,
        status=organization.subscription_status,
        current_period_end=organization.subscription_current_period_end,
        has_customer=organization.stripe_customer_id is not None,
    )


@router.post("/checkout", response_model=schemas.BillingSessionOut)
@limiter.limit("5/minute")
def create_checkout(
    request: Request,
    payload: schemas.BillingCheckoutCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_role([models.RoleEnum.ADMIN])),
) -> schemas.BillingSessionOut:
    organization = _organization_for_user(db, current_user)
    try:
        url = StripeBillingService().create_checkout_session(organization, payload.tier.value)
        db.commit()
    except (BillingConfigurationError, BillingProviderError) as exc:
        db.rollback()
        _billing_error(exc)
    return schemas.BillingSessionOut(url=url)


@router.post("/portal", response_model=schemas.BillingSessionOut)
@limiter.limit("5/minute")
def create_portal(
    request: Request,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(require_role([models.RoleEnum.ADMIN])),
) -> schemas.BillingSessionOut:
    organization = _organization_for_user(db, current_user)
    try:
        url = StripeBillingService().create_portal_session(organization)
    except (BillingConfigurationError, BillingProviderError) as exc:
        _billing_error(exc)
    return schemas.BillingSessionOut(url=url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(database.get_db),
) -> dict[str, bool]:
    payload = await request.body()
    try:
        event = StripeBillingService.construct_event(
            payload, request.headers.get("stripe-signature")
        )
    except BillingConfigurationError as exc:
        error_response("BILLING_NOT_CONFIGURED", str(exc), status_code=503)
    except BillingProviderError:
        error_response("INVALID_WEBHOOK_SIGNATURE", "Invalid webhook signature.", status_code=400)

    event_id = _value(event, "id")
    event_type = _value(event, "type")
    if not isinstance(event_id, str) or not isinstance(event_type, str):
        error_response("INVALID_WEBHOOK_EVENT", "Malformed Stripe event.", status_code=400)
    if (
        db.query(models.BillingWebhookEvent)
        .filter(models.BillingWebhookEvent.stripe_event_id == event_id)
        .first()
    ):
        return {"received": True}

    event_object = _value(_value(event, "data"), "object")
    if event_type == "checkout.session.completed":
        _apply_checkout_completed(db, event_object)
    elif event_type in {
        "customer.subscription.created",
        "customer.subscription.updated",
        "customer.subscription.deleted",
    }:
        _apply_subscription_changed(db, event_object)
    elif event_type in {"invoice.payment_failed", "invoice.paid"}:
        _apply_invoice_event(db, event_type, event_object)

    db.add(
        models.BillingWebhookEvent(
            stripe_event_id=event_id,
            event_type=event_type,
        )
    )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
    return {"received": True}


def _apply_checkout_completed(db: Session, session: Any) -> None:
    metadata = _value(session, "metadata") or {}
    organization_id = metadata.get("organization_id") if hasattr(metadata, "get") else None
    if not organization_id or not str(organization_id).isdigit():
        logger.warning("Ignoring checkout session without valid organization metadata")
        return
    organization = db.get(models.Organization, int(organization_id))
    if organization is None:
        logger.warning("Ignoring checkout session for missing organization %s", organization_id)
        return
    customer_id = _value(session, "customer")
    subscription_id = _value(session, "subscription")
    tier = metadata.get("tier") if hasattr(metadata, "get") else None
    if isinstance(customer_id, str):
        organization.stripe_customer_id = customer_id
    if isinstance(subscription_id, str):
        organization.stripe_subscription_id = subscription_id
    if tier in {"growth", "scale", "agency"}:
        organization.subscription_tier = tier


def _apply_subscription_changed(db: Session, subscription: Any) -> None:
    metadata = _value(subscription, "metadata") or {}
    organization_id = metadata.get("organization_id") if hasattr(metadata, "get") else None
    organization = None
    if organization_id and str(organization_id).isdigit():
        organization = db.get(models.Organization, int(organization_id))
    if organization is None:
        customer_id = _value(subscription, "customer")
        if isinstance(customer_id, str):
            organization = (
                db.query(models.Organization)
                .filter(models.Organization.stripe_customer_id == customer_id)
                .first()
            )
    if organization is None:
        logger.warning("Ignoring subscription event without a matching organization")
        return
    apply_subscription_event(organization, subscription)


def _apply_invoice_event(db: Session, event_type: str, invoice: Any) -> None:
    subscription_id = _value(invoice, "subscription")
    customer_id = _value(invoice, "customer")
    organization = None
    if isinstance(subscription_id, str):
        organization = (
            db.query(models.Organization)
            .filter(models.Organization.stripe_subscription_id == subscription_id)
            .first()
        )
    if organization is None and isinstance(customer_id, str):
        organization = (
            db.query(models.Organization)
            .filter(models.Organization.stripe_customer_id == customer_id)
            .first()
        )
    if organization is None:
        logger.warning("Ignoring invoice event without a matching organization")
        return
    apply_invoice_event(organization, event_type)


def _value(value: Any, key: str) -> Any:
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)
