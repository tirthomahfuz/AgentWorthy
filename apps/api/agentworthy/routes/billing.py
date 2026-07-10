"""Stripe billing routes."""

from __future__ import annotations

import logging
import os
import uuid

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from agentworthy.auth import get_current_user
from agentworthy.database import get_db
from agentworthy.models import Plan, StripeEvent, User
from agentworthy.plan_limits import PLAN_LIMITS

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")


@router.get("/plans")
def list_plans() -> list[dict]:
    return [
        {
            "id": k,
            "name": v.name,
            "price_usd": v.price_usd,
            "max_sites": v.max_sites,
            "pages_per_scan": v.pages_per_scan,
            "simulations_per_scan": v.simulations_per_scan,
            "scan_frequency": v.scan_frequency,
            "api_access": v.api_access,
            "max_seats": v.max_seats,
        }
        for k, v in PLAN_LIMITS.items()
        if k != "free"
    ]


@router.post("/checkout")
def create_checkout(
    plan: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not stripe.api_key:
        raise HTTPException(503, "Stripe not configured")
    price_map = {
        "starter": os.environ.get("STRIPE_PRICE_STARTER"),
        "pro": os.environ.get("STRIPE_PRICE_PRO"),
        "agency": os.environ.get("STRIPE_PRICE_AGENCY"),
    }
    price_id = price_map.get(plan)
    if not price_id:
        raise HTTPException(400, f"Unknown plan or missing price id: {plan}")

    if not user.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email, metadata={"user_id": str(user.id)})
        user.stripe_customer_id = customer.id
        db.commit()

    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=f"{os.environ.get('NEXTAUTH_URL', 'http://localhost:3000')}/settings?checkout=success",
        cancel_url=f"{os.environ.get('NEXTAUTH_URL', 'http://localhost:3000')}/pricing?checkout=cancel",
        metadata={"user_id": str(user.id), "plan": plan},
    )
    return {"checkout_url": session.url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)) -> dict[str, str]:
    payload = await request.body()
    sig = request.headers.get("stripe-signature", "")
    secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(503, "Webhook secret not configured")
    try:
        event = stripe.Webhook.construct_event(payload, sig, secret)
    except Exception as e:
        raise HTTPException(400, str(e)) from e

    if db.get(StripeEvent, event["id"]):
        return {"status": "duplicate"}
    db.add(StripeEvent(event_id=event["id"]))
    db.commit()

    etype = event["type"]
    data = event["data"]["object"]
    if etype == "checkout.session.completed":
        user_id = data.get("metadata", {}).get("user_id")
        plan = data.get("metadata", {}).get("plan", "starter")
        if user_id:
            user = db.get(User, uuid.UUID(user_id))
            if user:
                user.plan = Plan(plan)
                db.commit()
    elif etype in ("customer.subscription.updated", "customer.subscription.deleted"):
        customer_id = data.get("customer")
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            if etype.endswith("deleted") or data.get("status") == "canceled":
                user.plan = Plan.FREE
            else:
                # map price to plan via metadata if present
                pass
            db.commit()
    return {"status": "ok"}


@router.post("/portal")
def customer_portal(user: User = Depends(get_current_user)) -> dict[str, str]:
    if not stripe.api_key or not user.stripe_customer_id:
        raise HTTPException(400, "No billing account")
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{os.environ.get('NEXTAUTH_URL', 'http://localhost:3000')}/settings",
    )
    return {"portal_url": session.url}
