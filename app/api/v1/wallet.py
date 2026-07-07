"""
Wallet & Cashback API Endpoints

    GET /api/v1/wallet               - current balance, currency, cashback rate
    GET /api/v1/wallet/transactions  - paginated earned/spent history

Prefix "/wallet" is applied by app/api/v1/router.py.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.database import get_db
from app.config.settings import settings
from app.core.dependencies import get_current_user
from app.schemas.wallet import (
    WalletBalanceResponse,
    WalletTransactionResponse,
    WalletTransactionsPage,
    WalletTransactionsResponse,
)
from app.services.wallet_service import WalletService

router = APIRouter(tags=["Wallet"])


@router.get("", response_model=WalletBalanceResponse)
async def get_wallet(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WalletBalanceResponse:
    """Get the authenticated user's wallet balance, currency and cashback rate."""
    try:
        balance = await WalletService.get_balance(db, current_user.user_id)
        return WalletBalanceResponse(
            balance=float(balance),
            currency=settings.wallet_currency,
            cashback_rate=settings.cashback_rate,
        )
    except Exception as e:
        logger.error(f"Error fetching wallet: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch wallet",
        )


@router.get("/transactions", response_model=WalletTransactionsResponse)
async def get_wallet_transactions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: Optional[str] = Query(
        None,
        description="Filter by transaction type: 'earned', 'spent' or 'refund'",
    ),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
) -> WalletTransactionsResponse:
    """Get a paginated list of the user's wallet transactions (newest first)."""
    try:
        transactions, total = await WalletService.get_transactions(
            db,
            user_id=current_user.user_id,
            page=page,
            page_size=page_size,
            tx_type=type,
        )

        items = [
            WalletTransactionResponse(
                transaction_id=str(tx.transaction_id),
                type=tx.type,
                title=tx.title,
                amount=float(tx.amount),
                balance_after=float(tx.balance_after)
                if tx.balance_after is not None
                else None,
                order_id=str(tx.order_id) if tx.order_id else None,
                order_number=tx.order_number,
                created_at=tx.created_at,
            )
            for tx in transactions
        ]

        return WalletTransactionsResponse(
            data=WalletTransactionsPage(
                transactions=items,
                total=total,
                page=page,
                page_size=page_size,
            )
        )
    except Exception as e:
        logger.error(f"Error fetching wallet transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch wallet transactions",
        )
