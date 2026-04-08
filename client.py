# # Copyright (c) Meta Platforms, Inc. and affiliates.
# # All rights reserved.
# #
# # This source code is licensed under the BSD-style license found in the
# # LICENSE file in the root directory of this source tree.

# """Invoice Env Environment Client."""

# from typing import Dict

# from openenv.core import EnvClient
# from openenv.core.client_types import StepResult
# from openenv.core.env_server.types import State

# # from .models import InvoiceAction, InvoiceObservation
# from models import InvoiceAction, InvoiceObservation


# class InvoiceEnv(
#     EnvClient[InvoiceAction, InvoiceObservation, State]
# ):
#     """
#     Client for the Invoice Env Environment.

#     This client maintains a persistent WebSocket connection to the environment server,
#     enabling efficient multi-step interactions with lower latency.
#     Each client instance has its own dedicated environment session on the server.

#     Example:
#         >>> # Connect to a running server
#         >>> with InvoiceEnv(base_url="http://localhost:8000") as client:
#         ...     result = client.reset()
#         ...     print(result.observation.echoed_message)
#         ...
#         ...     result = client.step(InvoiceAction(message="Hello!"))
#         ...     print(result.observation.echoed_message)

#     Example with Docker:
#         >>> # Automatically start container and connect
#         >>> client = InvoiceEnv.from_docker_image("invoice_env-env:latest")
#         >>> try:
#         ...     result = client.reset()
#         ...     result = client.step(InvoiceAction(message="Test"))
#         ... finally:
#         ...     client.close()
#     """

#     def _step_payload(self, action: InvoiceAction) -> Dict:
#         """
#         Convert InvoiceAction to JSON payload for step message.

#         Args:
#             action: InvoiceAction instance

#         Returns:
#             Dictionary representation suitable for JSON encoding
#         """
#         return {
#             "message": action.message,
#         }

#     def _parse_result(self, payload: Dict) -> StepResult[InvoiceObservation]:
#         """
#         Parse server response into StepResult[InvoiceObservation].

#         Args:
#             payload: JSON response data from server

#         Returns:
#             StepResult with InvoiceObservation
#         """
#         obs_data = payload.get("observation", {})
#         observation = InvoiceObservation(
#             echoed_message=obs_data.get("echoed_message", ""),
#             message_length=obs_data.get("message_length", 0),
#             done=payload.get("done", False),
#             reward=payload.get("reward"),
#             metadata=obs_data.get("metadata", {}),
#         )

#         return StepResult(
#             observation=observation,
#             reward=payload.get("reward"),
#             done=payload.get("done", False),
#         )

#     def _parse_state(self, payload: Dict) -> State:
#         """
#         Parse server response into State object.

#         Args:
#             payload: JSON response from state request

#         Returns:
#             State object with episode_id and step_count
#         """
#         return State(
#             episode_id=payload.get("episode_id"),
#             step_count=payload.get("step_count", 0),
#         )




"""Invoice Data Extraction Environment Client."""

from typing import Dict

from openenv.core import EnvClient
from openenv.core.client_types import StepResult
from openenv.core.env_server.types import State

try:
    from .models import InvoiceAction, InvoiceObservation
except ImportError:
    from models import InvoiceAction, InvoiceObservation


class InvoiceEnv(EnvClient[InvoiceAction, InvoiceObservation, State]):
    """
    Client for the Invoice Data Extraction Environment.

    Connects via WebSocket to the environment server.
    The agent receives raw invoice text and must extract structured fields.

    Example (async):
        >>> async with InvoiceEnv(base_url="http://localhost:8000") as env:
        ...     result = await env.reset()
        ...     print(result.observation.invoice_text)
        ...     action = InvoiceAction(vendor_name="Acme Ltd", total_amount=1155.0, currency="USD")
        ...     result = await env.step(action)
        ...     print(result.reward)

    Example (sync):
        >>> with InvoiceEnv(base_url="http://localhost:8000").sync() as env:
        ...     result = env.reset()
        ...     result = env.step(InvoiceAction(vendor_name="Acme Ltd", total_amount=1155.0, currency="USD"))
    """

    def _step_payload(self, action: InvoiceAction) -> Dict:
        """Convert InvoiceAction to JSON payload for the step message."""
        payload = {}
        for field in [
            "vendor_name", "invoice_date", "invoice_number",
            "total_amount", "tax_amount", "currency", "line_items",
        ]:
            value = getattr(action, field, None)
            if value is not None:
                payload[field] = value
        return payload

    def _parse_result(self, payload: Dict) -> StepResult[InvoiceObservation]:
        """Parse server response into StepResult[InvoiceObservation]."""
        obs_data = payload.get("observation", {})

        observation = InvoiceObservation(
            invoice_text=obs_data.get("invoice_text", ""),
            task_name=obs_data.get("task_name", ""),
            task_description=obs_data.get("task_description", ""),
            fields_to_extract=obs_data.get("fields_to_extract", []),
            feedback=obs_data.get("feedback"),
            score=obs_data.get("score"),
            step_count=obs_data.get("step_count", 0),
            done=payload.get("done", False),
            reward=payload.get("reward"),
            metadata=obs_data.get("metadata", {}),
        )

        return StepResult(
            observation=observation,
            reward=payload.get("reward"),
            done=payload.get("done", False),
        )

    def _parse_state(self, payload: Dict) -> State:
        """Parse server response into State object."""
        return State(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
        )