"""
Wallet & Cashback Pydantic Schemas
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

# ============================================================================
# Response Schemas
# ============================================================================

class WalletBalanceResponse(BaseModel):
    """GET /wallet — current balance, currency and cashback rate."""
    balance: float
    currency: str = "LKR"
    cashback_rate: float


class WalletTransactionResponse(BaseModel):
    """A single wallet ledger entry."""
    transaction_id: str
    type: str  # 'earned' | 'spent' | 'refund'
    title: str
    amount: float
    balance_after: Optional[float] = None
    order_id: Optional[str] = None
    order_number: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WalletTransactionsPage(BaseModel):
    """Paginated wallet transaction list."""
    transactions: List[WalletTransactionResponse]
    total: int
    page: int
    page_size: int


class WalletTransactionsResponse(BaseModel):
    """Standard wrapper for the transactions list."""
    success: bool = True
    data: WalletTransactionsPage
