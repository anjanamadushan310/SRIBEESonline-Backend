"""
Payment API Endpoints
"""
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.core.dependencies import get_current_admin, get_current_user
from app.schemas.order import PaymentStatusEnum
from app.schemas.payment import (
    ConfirmPaymentRequest,
    CreatePaymentIntentRequest,
    PaymentHistoryResponse,
    RefundRequest,
    SaveCardRequest,
    SavedCardResponse,
    SavedCardsListResponse,
)
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService

# Prefix "/payments" is applied by app/api/v1/router.py — do not repeat it here.
router = APIRouter(tags=["Payments"])

# ============================================================================
# Payment Methods (Module 13.1) — mounted separately at "/payment-methods".
#
# MVP: external card/gateway is on hold, so we expose a static list of the two
# supported methods (Cash on Delivery + internal Wallet). Kept as a constant so
# it can later be swapped for a DB-backed PaymentMethod table without changing
# the endpoint contract.
# ============================================================================
methods_router = APIRouter(tags=["Payment Methods"])

_SUPPORTED_PAYMENT_METHODS = [
    {
        "id": "cod",
        "code": "COD",
        "name": "Cash on Delivery",
        "type": "OFFLINE",
        "is_active": True,
    },
    {
        "id": "wallet",
        "code": "WALLET",
        "name": "SRIBEES Wallet",
        "type": "WALLET",
        "is_active": True,
    },
]


@methods_router.get("", response_model=dict, summary="List supported payment methods")
async def list_payment_methods(
    current_user=Depends(get_current_user),
):
    """
    Return the active payment methods available at checkout.

    For the MVP this is Cash on Delivery and the internal SRIBEES Wallet.
    """
    active = [m for m in _SUPPORTED_PAYMENT_METHODS if m["is_active"]]
    return {"success": True, "data": {"methods": active}}


# ============================================================================
# Payment Endpoints
# ============================================================================

@router.post("/create-intent", response_model=dict)
async def create_payment_intent(
    data: CreatePaymentIntentRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Create a payment intent for an order.
    """
    try:
        # Get order
        order = await OrderService.get_by_id(
            db,
            UUID(data.order_id),
            current_user.user_id
        )

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        if order.payment_status == "paid":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order is already paid"
            )

        # Create payment intent
        intent = await PaymentService.create_payment_intent(
            amount=order.total_amount,
            currency="inr",
            order_id=str(order.order_id)
        )

        return {
            "success": True,
            "data": intent
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment intent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment intent"
        )


@router.post("/confirm", response_model=dict)
async def confirm_payment(
    data: ConfirmPaymentRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """
    Confirm a payment.
    """
    try:
        # Confirm with payment provider
        result = await PaymentService.confirm_payment(
            data.payment_intent_id,
            data.payment_method_id
        )

        if result["status"] == "succeeded":
            # Update order payment status
            # Note: In production, get order_id from payment intent metadata
            return {
                "success": True,
                "data": result,
                "message": "Payment successful"
            }
        else:
            return {
                "success": False,
                "data": result,
                "message": "Payment requires additional action"
            }
    except Exception as e:
        logger.error(f"Error confirming payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm payment"
        )


@router.get("/status/{payment_intent_id}", response_model=dict)
async def get_payment_status(
    payment_intent_id: str,
    current_user = Depends(get_current_user)
):
    """
    Get payment intent status.
    """
    try:
        result = await PaymentService.retrieve_payment_intent(payment_intent_id)

        return {
            "success": True,
            "data": result
        }
    except Exception as e:
        logger.error(f"Error getting payment status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get payment status"
        )


# ============================================================================
# Admin Endpoints
# ============================================================================

@router.post("/refund", response_model=dict)
async def create_refund(
    data: RefundRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin)
):
    """
    Create a refund for an order. (Admin only)
    """
    try:
        # Get order
        order = await OrderService.get_by_id(db, UUID(data.order_id))

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Order not found"
            )

        if order.payment_status != "paid":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order has not been paid"
            )

        if not order.payment_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No payment ID found for this order"
            )

        # Create refund
        refund_amount = Decimal(str(data.amount)) if data.amount else order.total_amount

        result = await PaymentService.create_refund(
            payment_intent_id=order.payment_id,
            amount=refund_amount,
            reason=data.reason
        )

        # Update order status
        await OrderService.update_payment_status(
            db, order, PaymentStatusEnum.REFUNDED
        )

        return {
            "success": True,
            "data": {
                "refund_id": result["refund_id"],
                "amount": float(refund_amount),
                "status": result["status"]
            },
            "message": "Refund processed successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating refund: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create refund"
        )


# ============================================================================
# Saved Cards Endpoints
# ============================================================================

@router.get("/cards", response_model=SavedCardsListResponse)
async def get_saved_cards(
    current_user = Depends(get_current_user)
):
    """
    Get user's saved payment methods (cards).
    """
    try:
        cards = await PaymentService.get_saved_cards(str(current_user.user_id))

        return SavedCardsListResponse(
            success=True,
            cards=[SavedCardResponse(**card) for card in cards]
        )
    except Exception as e:
        logger.error(f"Error getting saved cards: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get saved cards"
        )


@router.post("/cards", response_model=dict)
async def save_card(
    data: SaveCardRequest,
    current_user = Depends(get_current_user)
):
    """
    Save a new payment method (card).
    """
    try:
        card = await PaymentService.save_card(
            user_id=str(current_user.user_id),
            payment_method_id=data.payment_method_id,
            set_default=data.set_default
        )

        return {
            "success": True,
            "data": card,
            "message": "Card saved successfully"
        }
    except Exception as e:
        logger.error(f"Error saving card: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save card"
        )


@router.delete("/cards/{card_id}", response_model=dict)
async def delete_saved_card(
    card_id: str,
    current_user = Depends(get_current_user)
):
    """
    Delete a saved payment method.
    """
    try:
        await PaymentService.delete_saved_card(
            user_id=str(current_user.user_id),
            card_id=card_id
        )

        return {
            "success": True,
            "message": "Card deleted successfully"
        }
    except Exception as e:
        logger.error(f"Error deleting card: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete card"
        )


@router.get("/history", response_model=PaymentHistoryResponse)
async def get_payment_history(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's payment history.
    """
    try:
        payments = await PaymentService.get_payment_history(
            str(current_user.user_id), db
        )

        return PaymentHistoryResponse(
            success=True,
            payments=payments,
            total=len(payments)
        )
    except Exception as e:
        logger.error(f"Error getting payment history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get payment history"
        )


# ============================================================================
# Webhook Endpoint
# ============================================================================

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Handle Stripe webhook events.
    """
    try:
        payload = await request.body()
        signature = request.headers.get("stripe-signature", "")

        result = await PaymentService.handle_webhook(payload, signature)

        # Handle different event types
        event_type = result.get("event_type")

        if event_type == "payment_intent.succeeded":
            # Update order payment status
            logger.info("Payment succeeded webhook received")
            # Extract order_id from event metadata and update
            pass

        elif event_type == "payment_intent.payment_failed":
            logger.info("Payment failed webhook received")
            pass

        elif event_type == "charge.refunded":
            logger.info("Refund webhook received")
            pass

        return {"received": True}

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed"
        )
