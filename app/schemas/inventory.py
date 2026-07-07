"""
Admin Inventory Schemas
"""
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class InventoryUpdateRequest(BaseModel):
    """
    Partial update for a branch_inventory row.

    Only the provided fields are changed; at least one must be present.
    """

    stock_quantity: Optional[int] = Field(None, ge=0, description="Units on hand")
    reserved_quantity: Optional[int] = Field(None, ge=0, description="Units reserved by orders")
    low_stock_threshold: Optional[int] = Field(None, ge=0, description="Low-stock alert threshold")

    @model_validator(mode="after")
    def _at_least_one(self) -> "InventoryUpdateRequest":
        if (
            self.stock_quantity is None
            and self.reserved_quantity is None
            and self.low_stock_threshold is None
        ):
            raise ValueError("Provide at least one field to update.")
        return self
