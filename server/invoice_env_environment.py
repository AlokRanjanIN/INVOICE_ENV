# # Copyright (c) Meta Platforms, Inc. and affiliates.
# # All rights reserved.
# #
# # This source code is licensed under the BSD-style license found in the
# # LICENSE file in the root directory of this source tree.

# """
# Invoice Env Environment Implementation.

# A simple test environment that echoes back messages sent to it.
# Perfect for testing HTTP server infrastructure.
# """

# # from uuid import uuid4

# # from openenv.core.env_server.interfaces import Environment
# # from openenv.core.env_server.types import State

# # try:
# #     from ..models import InvoiceAction, InvoiceObservation
# # except ImportError:
# #     from models import InvoiceAction, InvoiceObservation


# # class InvoiceEnvironment(Environment):
# #     """
# #     A simple echo environment that echoes back messages.

# #     This environment is designed for testing the HTTP server infrastructure.
# #     It maintains minimal state and simply echoes back whatever message it receives.

# #     Example:
# #         >>> env = InvoiceEnvironment()
# #         >>> obs = env.reset()
# #         >>> print(obs.echoed_message)  # "Invoice Env environment ready!"
# #         >>>
# #         >>> obs = env.step(InvoiceAction(message="Hello"))
# #         >>> print(obs.echoed_message)  # "Hello"
# #         >>> print(obs.message_length)  # 5
# #     """

# #     # Enable concurrent WebSocket sessions.
# #     # Set to True if your environment isolates state between instances.
# #     # When True, multiple WebSocket clients can connect simultaneously, each
# #     # getting their own environment instance (when using factory mode in app.py).
# #     SUPPORTS_CONCURRENT_SESSIONS: bool = True

# #     def __init__(self):
# #         """Initialize the invoice_env environment."""
# #         self._state = State(episode_id=str(uuid4()), step_count=0)
# #         self._reset_count = 0

# #     def reset(self) -> InvoiceObservation:
# #         """
# #         Reset the environment.

# #         Returns:
# #             InvoiceObservation with a ready message
# #         """
# #         self._state = State(episode_id=str(uuid4()), step_count=0)
# #         self._reset_count += 1

# #         return InvoiceObservation(
# #             echoed_message="Invoice Env environment ready!",
# #             message_length=0,
# #             done=False,
# #             reward=0.0,
# #         )

# #     def step(self, action: InvoiceAction) -> InvoiceObservation:  # type: ignore[override]
# #         """
# #         Execute a step in the environment by echoing the message.

# #         Args:
# #             action: InvoiceAction containing the message to echo

# #         Returns:
# #             InvoiceObservation with the echoed message and its length
# #         """
# #         self._state.step_count += 1

# #         message = action.message
# #         length = len(message)

# #         # Simple reward: longer messages get higher rewards
# #         reward = length * 0.1

# #         return InvoiceObservation(
# #             echoed_message=message,
# #             message_length=length,
# #             done=False,
# #             reward=reward,
# #             metadata={"original_message": message, "step": self._state.step_count},
# #         )

# #     @property
# #     def state(self) -> State:
# #         """
# #         Get the current environment state.

# #         Returns:
# #             Current State with episode_id and step_count
# #         """
# #         return self._state



# import re
# import uuid
# from typing import Optional

# try:
#     from ..models import InvoiceAction, InvoiceObservation
# except ImportError:
#     from models import InvoiceAction, InvoiceObservation

# from openenv.core.env_server.interfaces import Environment
# from openenv.core.env_server.types import State


# # ─── TASK DEFINITIONS ────────────────────────────────────────────────────────

# TASKS = {
#     "easy": {
#         "name": "easy",
#         "description": "Extract vendor name and total amount from a simple invoice.",
#         "fields_to_extract": ["vendor_name", "total_amount", "currency"],
#         "invoice_text": """
# INVOICE
# =======
# Vendor: Acme Supplies Ltd.
# Invoice Number: INV-2024-001
# Date: 2024-03-15
# Bill To: TechCorp Inc.

# Description            Qty    Unit Price    Total
# -------------------------------------------------
# Office Chairs           5      $120.00      $600.00
# Desk Lamps             10       $45.00      $450.00

#                               Subtotal:  $1,050.00
#                               Tax (10%):   $105.00
#                               TOTAL DUE: $1,155.00

# Currency: USD
# Payment due within 30 days.
# """,
#         "ground_truth": {
#             "vendor_name": "acme supplies ltd",
#             "total_amount": 1155.00,
#             "currency": "usd",
#         },
#     },

#     "medium": {
#         "name": "medium",
#         "description": (
#             "Extract vendor name, invoice number, date, total amount, tax amount, "
#             "and currency from a moderately complex invoice."
#         ),
#         "fields_to_extract": [
#             "vendor_name", "invoice_number", "invoice_date",
#             "total_amount", "tax_amount", "currency"
#         ],
#         "invoice_text": """
# ---------------------------------------------
#         GLOBALTECH SOLUTIONS PTE. LTD.
#         123 Business Park, Singapore 456789
#         GST Reg No: 201234567A
# ---------------------------------------------
# TAX INVOICE

# Invoice No  : GT-SG-2024-0892
# Invoice Date: 22 November 2024
# Due Date    : 22 December 2024

# Bill To:
#   FutureCorp Pte. Ltd.
#   88 Innovation Drive, Singapore 987654

# Item  Description                     Qty   Unit Price    Amount
# ----------------------------------------------------------------
# 001   Cloud Storage (1TB/month)         3     SGD 250.00   SGD 750.00
# 002   Support Package - Enterprise      1   SGD 1,200.00 SGD 1,200.00
# 003   Setup & Onboarding Fee            1     SGD 300.00   SGD 300.00
# ----------------------------------------------------------------
#                                       Subtotal:          SGD 2,250.00
#                                       GST (9%):            SGD 202.50
#                                       TOTAL PAYABLE:     SGD 2,452.50
# ---------------------------------------------
# Currency: SGD
# """,
#         "ground_truth": {
#             "vendor_name": "globaltech solutions pte. ltd.",
#             "invoice_number": "gt-sg-2024-0892",
#             "invoice_date": "2024-11-22",
#             "total_amount": 2452.50,
#             "tax_amount": 202.50,
#             "currency": "sgd",
#         },
#     },

#     "hard": {
#         "name": "hard",
#         "description": (
#             "Extract all fields including line items from a complex, multi-section "
#             "invoice with mixed formatting and partial ambiguity."
#         ),
#         "fields_to_extract": [
#             "vendor_name", "invoice_number", "invoice_date",
#             "total_amount", "tax_amount", "currency", "line_items"
#         ],
#         "invoice_text": """
# ***** CREATIVE DIGITAL AGENCY *****
# Reg. No: CDA-UK-778899  |  VAT: GB123456789
# 14 Soho Square, London W1D 3QG
# contact@creativedigital.agency
# ================================================
#                     SALES INVOICE
# ================================================
# Ref/Invoice #: CDA/2024/NOV/0044
# Raised On    : 14-Nov-2024
# Payment Terms: Net 45
# ================================================
# CLIENT DETAILS:
#   BrandBuilders Ltd.
#   22 Canary Wharf, London E14 5AB

# ================================================
# SERVICES RENDERED:
# ------------------------------------------------
# | # | Service                  | Hrs | Rate    | Total    |
# |---|--------------------------|-----|---------|----------|
# | 1 | Brand Strategy Workshop  |  8  | £200/hr | £1,600   |
# | 2 | Logo & Identity Design   | 12  | £175/hr | £2,100   |
# | 3 | Social Media Pack (x3)   |  -  | £450 ea | £1,350   |
# | 4 | Campaign Copywriting     |  6  | £150/hr | £900     |
# ------------------------------------------------
#                          Subtotal:          £5,950.00
#                          VAT @ 20%:         £1,190.00
# ================================================
#                          GRAND TOTAL:       £7,140.00
# ================================================
# Currency: GBP
# All amounts in British Pounds Sterling.
# """,
#         "ground_truth": {
#             "vendor_name": "creative digital agency",
#             "invoice_number": "cda/2024/nov/0044",
#             "invoice_date": "2024-11-14",
#             "total_amount": 7140.00,
#             "tax_amount": 1190.00,
#             "currency": "gbp",
#             "line_items": [
#                 {"description": "brand strategy workshop", "quantity": 8, "unit_price": 200.0, "total": 1600.0},
#                 {"description": "logo & identity design", "quantity": 12, "unit_price": 175.0, "total": 2100.0},
#                 {"description": "social media pack (x3)", "quantity": 3, "unit_price": 450.0, "total": 1350.0},
#                 {"description": "campaign copywriting", "quantity": 6, "unit_price": 150.0, "total": 900.0},
#             ],
#         },
#     },
# }

# TASK_ORDER = ["easy", "medium", "hard"]
# MAX_STEPS_PER_TASK = 5


# # ─── GRADER ──────────────────────────────────────────────────────────────────

# def _normalize_str(s: Optional[str]) -> str:
#     if s is None:
#         return ""
#     return re.sub(r"\s+", " ", str(s).strip().lower())


# def _score_field(predicted, expected) -> float:
#     """Returns 0.0–1.0 for a single field comparison."""
#     if expected is None:
#         return 1.0
#     if predicted is None:
#         return 0.0
#     if isinstance(expected, float):
#         try:
#             return 1.0 if abs(float(predicted) - expected) < 0.05 else 0.0
#         except (TypeError, ValueError):
#             return 0.0
#     return 1.0 if _normalize_str(str(predicted)) == _normalize_str(str(expected)) else 0.0


# def _score_line_items(predicted_items, expected_items) -> float:
#     """Score line items with partial credit."""
#     if not expected_items:
#         return 1.0
#     if not predicted_items:
#         return 0.0
#     total_fields = len(expected_items) * 3  # description, unit_price, total
#     matched = 0
#     for exp in expected_items:
#         best = 0.0
#         for pred in predicted_items:
#             s = (
#                 _score_field(pred.get("description"), exp.get("description")) +
#                 _score_field(pred.get("unit_price"), exp.get("unit_price")) +
#                 _score_field(pred.get("total"), exp.get("total"))
#             )
#             best = max(best, s)
#         matched += best
#     return round(matched / total_fields, 4)


# def grade_action(action: InvoiceAction, task: dict) -> tuple[float, str]:
#     """Grade the agent's action against ground truth. Returns (score, feedback)."""
#     gt = task["ground_truth"]
#     fields = task["fields_to_extract"]
#     scores = []
#     feedback_parts = []

#     scalar_fields = [f for f in fields if f != "line_items"]
#     for field in scalar_fields:
#         expected = gt.get(field)
#         predicted = getattr(action, field, None)
#         s = _score_field(predicted, expected)
#         scores.append(s)
#         if s < 1.0:
#             feedback_parts.append(f"'{field}': expected '{expected}', got '{predicted}'")

#     if "line_items" in fields:
#         s = _score_line_items(
#             [item for item in (action.line_items or [])],
#             gt.get("line_items", [])
#         )
#         scores.append(s)
#         if s < 1.0:
#             feedback_parts.append(f"'line_items' partial score: {s:.2f}")

#     final_score = round(sum(scores) / len(scores), 4) if scores else 0.0
#     feedback = "All fields correct!" if not feedback_parts else "Issues: " + "; ".join(feedback_parts)
#     return final_score, feedback


# # ─── ENVIRONMENT ─────────────────────────────────────────────────────────────

# class InvoiceEnvironment(Environment):
#     """
#     Invoice Data Extraction Environment.
#     The agent reads raw invoice text and extracts structured fields.
#     3 tasks: easy → medium → hard.
#     """

#     allow_concurrent_sessions = True

#     def __init__(self):
#         super().__init__()
#         self._state = State(episode_id=str(uuid.uuid4()), step_count=0)
#         self._task_index: int = 0
#         self._steps_in_task: int = 0
#         self._last_score: float = 0.0
#         self._last_feedback: str = ""
#         self._done: bool = False

#     def _current_task(self) -> dict:
#         return TASKS[TASK_ORDER[self._task_index]]

#     def reset(self) -> InvoiceObservation:
#         self._state = State(episode_id=str(uuid.uuid4()), step_count=0)
#         self._task_index = 0
#         self._steps_in_task = 0
#         self._last_score = 0.0
#         self._last_feedback = ""
#         self._done = False
#         task = self._current_task()
#         return InvoiceObservation(
#             invoice_text=task["invoice_text"],
#             task_name=task["name"],
#             task_description=task["description"],
#             fields_to_extract=task["fields_to_extract"],
#             feedback=None,
#             score=None,
#             step_count=0,
#             done=False,
#             reward=0.0,
#         )

#     def step(self, action: InvoiceAction) -> InvoiceObservation:
#         if self._done:
#             task = self._current_task()
#             return InvoiceObservation(
#                 invoice_text=task["invoice_text"],
#                 task_name=task["name"],
#                 task_description=task["description"],
#                 fields_to_extract=task["fields_to_extract"],
#                 feedback="Episode already done.",
#                 score=self._last_score,
#                 step_count=self._state.step_count,
#                 done=True,
#                 reward=0.0,
#             )

#         self._state.step_count += 1
#         self._steps_in_task += 1

#         task = self._current_task()
#         score, feedback = grade_action(action, task)
#         self._last_score = score
#         self._last_feedback = feedback

#         # Advance to next task if agent scores well OR exhausts attempts
#         advance = score >= 0.8 or self._steps_in_task >= MAX_STEPS_PER_TASK

#         if advance:
#             self._task_index += 1
#             self._steps_in_task = 0

#         done = self._task_index >= len(TASK_ORDER)
#         self._done = done

#         if done:
#             next_task = task  # stay on last task observation
#         else:
#             next_task = self._current_task()

#         return InvoiceObservation(
#             invoice_text=next_task["invoice_text"],
#             task_name=next_task["name"],
#             task_description=next_task["description"],
#             fields_to_extract=next_task["fields_to_extract"],
#             feedback=feedback,
#             score=score,
#             step_count=self._state.step_count,
#             done=done,
#             reward=score,
#         )

#     def state(self) -> State:
#         return self._state





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