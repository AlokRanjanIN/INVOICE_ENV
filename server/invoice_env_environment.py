# # Copyright (c) Meta Platforms, Inc. and affiliates.
# # All rights reserved.
# #
# # This source code is licensed under the BSD-style license found in the
# # LICENSE file in the root directory of this source tree.

# """
# Invoice Env Environment Implementation.
# """

import re
import uuid
from typing import Optional

try:
    from ..models import InvoiceAction, InvoiceObservation
except ImportError:
    from models import InvoiceAction, InvoiceObservation

from openenv.core.env_server.interfaces import Environment
from openenv.core.env_server.types import State


# ─── INVOICE CORPUS ──────────────────────────────────────────────────────────

TASKS = {
    "easy": {
        "name": "easy",
        "description": (
            "Extract the vendor name, total amount, and currency from this invoice. "
            "The invoice is simple and clearly formatted."
        ),
        "fields_to_extract": ["vendor_name", "total_amount", "currency"],
        "invoice_text": """\
INVOICE
=======
Vendor: Acme Supplies Ltd.
Invoice Number: INV-2024-001
Date: 2024-03-15
Bill To: TechCorp Inc.

Description            Qty    Unit Price    Total
-------------------------------------------------
Office Chairs           5      $120.00      $600.00
Desk Lamps             10       $45.00      $450.00

                              Subtotal:  $1,050.00
                              Tax (10%):   $105.00
                              TOTAL DUE: $1,155.00

Currency: USD
Payment due within 30 days.
""",
        "ground_truth": {
            "vendor_name": "acme supplies ltd",
            "total_amount": 1155.00,
            "currency": "usd",
        },
    },

    "medium": {
        "name": "medium",
        "description": (
            "Extract vendor name, invoice number, invoice date (YYYY-MM-DD), "
            "total amount, tax amount, and currency from this invoice."
        ),
        "fields_to_extract": [
            "vendor_name", "invoice_number", "invoice_date",
            "total_amount", "tax_amount", "currency",
        ],
        "invoice_text": """\
---------------------------------------------
        GLOBALTECH SOLUTIONS PTE. LTD.
        123 Business Park, Singapore 456789
        GST Reg No: 201234567A
---------------------------------------------
TAX INVOICE

Invoice No  : GT-SG-2024-0892
Invoice Date: 22 November 2024
Due Date    : 22 December 2024

Bill To:
  FutureCorp Pte. Ltd.
  88 Innovation Drive, Singapore 987654

Item  Description                     Qty   Unit Price    Amount
----------------------------------------------------------------
001   Cloud Storage (1TB/month)         3     SGD 250.00   SGD 750.00
002   Support Package - Enterprise      1   SGD 1,200.00 SGD 1,200.00
003   Setup & Onboarding Fee            1     SGD 300.00   SGD 300.00
----------------------------------------------------------------
                                      Subtotal:          SGD 2,250.00
                                      GST (9%):            SGD 202.50
                                      TOTAL PAYABLE:     SGD 2,452.50
---------------------------------------------
Currency: SGD
""",
        "ground_truth": {
            "vendor_name": "globaltech solutions pte. ltd.",
            "invoice_number": "gt-sg-2024-0892",
            "invoice_date": "2024-11-22",
            "total_amount": 2452.50,
            "tax_amount": 202.50,
            "currency": "sgd",
        },
    },

    "hard": {
        "name": "hard",
        "description": (
            "Extract all fields including line items from this complex invoice "
            "with mixed formatting. Line items need description, quantity, "
            "unit_price, and total."
        ),
        "fields_to_extract": [
            "vendor_name", "invoice_number", "invoice_date",
            "total_amount", "tax_amount", "currency", "line_items",
        ],
        "invoice_text": """\
***** CREATIVE DIGITAL AGENCY *****
Reg. No: CDA-UK-778899  |  VAT: GB123456789
14 Soho Square, London W1D 3QG
================================================
                    SALES INVOICE
================================================
Ref/Invoice #: CDA/2024/NOV/0044
Raised On    : 14-Nov-2024
Payment Terms: Net 45
================================================
CLIENT: BrandBuilders Ltd., 22 Canary Wharf, London E14 5AB

SERVICES RENDERED:
| # | Service                  | Hrs | Rate    | Total    |
|---|--------------------------|-----|---------|----------|
| 1 | Brand Strategy Workshop  |  8  | £200/hr | £1,600   |
| 2 | Logo & Identity Design   | 12  | £175/hr | £2,100   |
| 3 | Social Media Pack (x3)   |  -  | £450 ea | £1,350   |
| 4 | Campaign Copywriting     |  6  | £150/hr | £900     |
                         Subtotal:          £5,950.00
                         VAT @ 20%:         £1,190.00
================================================
                         GRAND TOTAL:       £7,140.00
================================================
Currency: GBP
""",
        "ground_truth": {
            "vendor_name": "creative digital agency",
            "invoice_number": "cda/2024/nov/0044",
            "invoice_date": "2024-11-14",
            "total_amount": 7140.00,
            "tax_amount": 1190.00,
            "currency": "gbp",
            "line_items": [
                {"description": "brand strategy workshop", "quantity": 8, "unit_price": 200.0, "total": 1600.0},
                {"description": "logo & identity design",  "quantity": 12, "unit_price": 175.0, "total": 2100.0},
                {"description": "social media pack (x3)", "quantity": 3,  "unit_price": 450.0, "total": 1350.0},
                {"description": "campaign copywriting",   "quantity": 6,  "unit_price": 150.0, "total": 900.0},
            ],
        },
    },
}

TASK_ORDER = ["easy", "medium", "hard"]
MAX_STEPS_PER_TASK = 5


# ─── GRADER ──────────────────────────────────────────────────────────────────

def _norm(s) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s).strip().lower())


def _score_field(predicted, expected) -> float:
    if expected is None:
        return 1.0
    if predicted is None:
        return 0.0
    if isinstance(expected, float):
        try:
            return 1.0 if abs(float(predicted) - expected) < 0.05 else 0.0
        except (TypeError, ValueError):
            return 0.0
    return 1.0 if _norm(predicted) == _norm(expected) else 0.0


def _score_line_items(predicted, expected) -> float:
    if not expected:
        return 1.0
    if not predicted:
        return 0.0
    total_fields = len(expected) * 3
    matched = 0.0
    for exp in expected:
        best = 0.0
        for pred in predicted:
            s = (
                _score_field(pred.get("description"), exp.get("description")) +
                _score_field(pred.get("unit_price"), exp.get("unit_price")) +
                _score_field(pred.get("total"), exp.get("total"))
            )
            best = max(best, s)
        matched += best
    return round(matched / total_fields, 4)


def grade(action: InvoiceAction, task: dict) -> tuple[float, str]:
    gt = task["ground_truth"]
    fields = task["fields_to_extract"]
    scores = []
    issues = []

    for field in [f for f in fields if f != "line_items"]:
        expected = gt.get(field)
        predicted = getattr(action, field, None)
        s = _score_field(predicted, expected)
        scores.append(s)
        if s < 1.0:
            issues.append(f"'{field}': expected='{expected}' got='{predicted}'")

    if "line_items" in fields:
        s = _score_line_items(action.line_items or [], gt.get("line_items", []))
        scores.append(s)
        if s < 1.0:
            issues.append(f"'line_items' score={s:.2f} (partial credit given)")

    final = round(sum(scores) / len(scores), 4) if scores else 0.0
    feedback = "Perfect extraction!" if not issues else "Issues found: " + " | ".join(issues)
    return final, feedback


# ─── ENVIRONMENT ─────────────────────────────────────────────────────────────

class InvoiceEnvironment(Environment):
    """
    Invoice Data Extraction RL Environment.

    The agent receives raw invoice text and must extract structured fields.
    Episodes contain 3 sequential tasks (easy → medium → hard).
    Reward is per-field accuracy (0.0–1.0) at every step.
    """

    allow_concurrent_sessions = True

    def __init__(self):
        super().__init__()
        self._episode_id = str(uuid.uuid4())
        self._step_count = 0
        self._task_index = 0
        self._steps_in_task = 0
        self._done = False

    def _task(self) -> dict:
        return TASKS[TASK_ORDER[self._task_index]]

    def _make_obs(self, feedback=None, score=None, done=False, reward=0.0) -> InvoiceObservation:
        t = self._task()
        return InvoiceObservation(
            invoice_text=t["invoice_text"],
            task_name=t["name"],
            task_description=t["description"],
            fields_to_extract=t["fields_to_extract"],
            feedback=feedback,
            score=score,
            step_count=self._step_count,
            done=done,
            reward=reward,
        )

    def reset(self) -> InvoiceObservation:
        self._episode_id = str(uuid.uuid4())
        self._step_count = 0
        self._task_index = 0
        self._steps_in_task = 0
        self._done = False
        return self._make_obs(
            feedback="New episode started. Read the invoice and extract the requested fields.",
            score=None,
            done=False,
            reward=0.0,
        )

    def step(self, action: InvoiceAction) -> InvoiceObservation:
        if self._done:
            return self._make_obs(
                feedback="Episode is done. Call reset() to start a new episode.",
                score=0.0,
                done=True,
                reward=0.0,
            )

        self._step_count += 1
        self._steps_in_task += 1

        score, feedback = grade(action, self._task())

        # Advance task if agent scores well OR runs out of attempts
        if score >= 0.8 or self._steps_in_task >= MAX_STEPS_PER_TASK:
            self._task_index += 1
            self._steps_in_task = 0

        done = self._task_index >= len(TASK_ORDER)
        self._done = done

        # If not done, snap to the new task; if done, keep showing last task
        if done:
            self._task_index = len(TASK_ORDER) - 1  # clamp for obs generation

        return self._make_obs(
            feedback=feedback,
            score=score,
            done=done,
            reward=score,
        )

    def state(self) -> State:
        return State(episode_id=self._episode_id, step_count=self._step_count)