# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.
from typing import Optional, List
from pydantic import Field
from openenv.core.env_server.types import Action, Observation


class InvoiceAction(Action):
    """Action taken by the agent: submit extracted invoice fields."""
    vendor_name: Optional[str] = Field(None, description="Name of the vendor/supplier")
    invoice_date: Optional[str] = Field(None, description="Invoice date in YYYY-MM-DD format")
    invoice_number: Optional[str] = Field(None, description="Invoice/reference number")
    total_amount: Optional[float] = Field(None, description="Total amount due")
    tax_amount: Optional[float] = Field(None, description="Tax/VAT amount")
    currency: Optional[str] = Field(None, description="Currency code e.g. USD, EUR, INR")
    line_items: Optional[List[dict]] = Field(
        default_factory=list,
        description='List of line items: [{"description": str, "quantity": float, "unit_price": float, "total": float}]'
    )


class InvoiceObservation(Observation):
    """Observation returned to the agent after each step."""
    invoice_text: str = Field(..., description="Raw invoice text the agent must parse")
    task_name: str = Field(..., description="Current task name: easy, medium, or hard")
    task_description: str = Field(..., description="What the agent is expected to extract")
    fields_to_extract: List[str] = Field(..., description="List of field names agent must fill")
    feedback: Optional[str] = Field(None, description="Feedback from grader on last submission")
    score: Optional[float] = Field(None, description="Score from last submission (0.0-1.0)")
    step_count: int = Field(0, description="Current step count")