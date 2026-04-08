# """
# Inference Script Example
# ===================================
# MANDATORY
# - Before submitting, ensure the following variables are defined in your environment configuration:
#     API_BASE_URL   The API endpoint for the LLM.
#     MODEL_NAME     The model identifier to use for inference.
#     HF_TOKEN       Your Hugging Face / API key.
#     LOCAL_IMAGE_NAME The name of the local image to use for the environment if you are using from_docker_image()
#                      method

# - Defaults are set only for API_BASE_URL and MODEL_NAME 
#     (and should reflect your active inference setup):
#     API_BASE_URL = os.getenv("API_BASE_URL", "<your-active-endpoint>")
#     MODEL_NAME = os.getenv("MODEL_NAME", "<your-active-model>")
    
# - The inference script must be named `inference.py` and placed in the root directory of the project
# - Participants must use OpenAI Client for all LLM calls using above variables

# STDOUT FORMAT
# - The script must emit exactly three line types to stdout, in this order:

#     [START] task=<task_name> env=<benchmark> model=<model_name>
#     [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
#     [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>

#   Rules:
#     - One [START] line at episode begin.
#     - One [STEP] line per step, immediately after env.step() returns.
#     - One [END] line after env.close(), always emitted (even on exception).
#     - reward and rewards are formatted to 2 decimal places.
#     - done and success are lowercase booleans: true or false.
#     - error is the raw last_action_error string, or null if none.
#     - All fields on a single line with no newlines within a line.
#     - Each tasks should return score in [0, 1]

#   Example:
#     [START] task=click-test env=miniwob model=Qwen3-VL-30B
#     [STEP] step=1 action=click('123') reward=0.00 done=false error=null
#     [STEP] step=2 action=fill('456','text') reward=0.00 done=false error=null
#     [STEP] step=3 action=click('789') reward=1.00 done=true error=null
#     [END] success=true steps=3 score=1.00 rewards=0.00,0.00,1.00
# """

# import asyncio
# import os
# import textwrap
# from typing import List, Optional

# from openai import OpenAI
# from dotenv import load_dotenv
# load_dotenv()

# # from my_env_v4 import MyEnvV4Action, MyEnvV4Env
# from client import TryEnv
# from models import TryAction, TryObservation
# IMAGE_NAME = os.getenv("IMAGE_NAME", "my-default-image")
# API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
# MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
# TASK_NAME = os.getenv("TRY_TASK", "echo")
# BENCHMARK = os.getenv("TRY_BENCHMARK", "my_env_v4")
# MAX_STEPS = 8
# TEMPERATURE = 0.7
# MAX_TOKENS = 150
# SUCCESS_SCORE_THRESHOLD = 0.1  # normalized score in [0, 1]

# # Max possible reward: each token contributes 0.1, across all steps
# _MAX_REWARD_PER_STEP = MAX_TOKENS * 0.1
# MAX_TOTAL_REWARD = MAX_STEPS * _MAX_REWARD_PER_STEP

# SYSTEM_PROMPT = textwrap.dedent(
#     """
#     You are interacting with a simple echo environment.
#     Each turn you must send a message. The environment will echo it back.
#     Reward is proportional to message length: reward = len(message) * 0.1
#     Your goal is to maximize total reward by sending meaningful, substantive messages.
#     Reply with exactly one message string — no quotes, no prefixes, just the message text.
#     """
# ).strip()


# def log_start(task: str, env: str, model: str) -> None:
#     print(f"[START] task={task} env={env} model={model}", flush=True)


# def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
#     error_val = error if error else "null"
#     done_val = str(done).lower()
#     print(
#         f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
#         flush=True,
#     )


# def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
#     rewards_str = ",".join(f"{r:.2f}" for r in rewards)
#     print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


# def build_user_prompt(step: int, last_echoed: str, last_reward: float, history: List[str]) -> str:
#     history_block = "\n".join(history[-4:]) if history else "None"
#     return textwrap.dedent(
#         f"""
#         Step: {step}
#         Last echoed message: {last_echoed!r}
#         Last reward: {last_reward:.2f}
#         Previous steps:
#         {history_block}
#         Send your next message.
#         """
#     ).strip()


# def get_model_message(client: OpenAI, step: int, last_echoed: str, last_reward: float, history: List[str]) -> str:
#     user_prompt = build_user_prompt(step, last_echoed, last_reward, history)
#     try:
#         completion = client.chat.completions.create(
#             model=MODEL_NAME,
#             messages=[
#                 {"role": "system", "content": SYSTEM_PROMPT},
#                 {"role": "user", "content": user_prompt},
#             ],
#             temperature=TEMPERATURE,
#             max_tokens=MAX_TOKENS,
#             stream=False,
#         )
#         text = (completion.choices[0].message.content or "").strip()
#         return text if text else "hello"
#     except Exception as exc:
#         print(f"[DEBUG] Model request failed: {exc}", flush=True)
#         return "hello"


# async def main() -> None:
#     client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

#     env = await TryEnv.from_docker_image(IMAGE_NAME)

#     history: List[str] = []
#     rewards: List[float] = []
#     steps_taken = 0
#     score = 0.0
#     success = False

#     log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)

#     try:
#         result = await env.reset() # OpenENV.reset()
#         last_echoed = result.observation.echoed_message
#         last_reward = 0.0

#         for step in range(1, MAX_STEPS + 1):
#             if result.done:
#                 break

#             message = get_model_message(client, step, last_echoed, last_reward, history)

#             result = await env.step(TryAction(message=message))
#             obs = result.observation

#             reward = result.reward or 0.0
#             done = result.done
#             error = None

#             rewards.append(reward)
#             steps_taken = step
#             last_echoed = obs.echoed_message
#             last_reward = reward

#             log_step(step=step, action=message, reward=reward, done=done, error=error)

#             history.append(f"Step {step}: {message!r} -> reward {reward:+.2f}")

#             if done:
#                 break

#         score = sum(rewards) / MAX_TOTAL_REWARD if MAX_TOTAL_REWARD > 0 else 0.0
#         score = min(max(score, 0.0), 1.0)  # clamp to [0, 1]
#         success = score >= SUCCESS_SCORE_THRESHOLD

#     finally:
#         try:
#             await env.close()
#         except Exception as e:
#             print(f"[DEBUG] env.close() error (container cleanup): {e}", flush=True)
#         log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


# if __name__ == "__main__":
#     asyncio.run(main())



# """
# Invoice Data Extraction Agent — Baseline Inference Script
# Follows the exact [START] / [STEP] / [END] log format required by the hackathon.
# """

# import asyncio
# import json
# import os
# import sys
# from typing import List

# from openai import OpenAI

# from dotenv import load_dotenv
# load_dotenv()

# # ─── CONFIG ───────────────────────────────────────────────────────────────────
# API_BASE_URL = os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
# API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
# MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
# ENV_URL = os.environ.get("ENV_URL", "http://localhost:8000")

# BENCHMARK = "invoice_env"
# MAX_STEPS = 15
# MAX_TOTAL_REWARD = 3.0   # 3 tasks × max reward 1.0 each
# SUCCESS_SCORE_THRESHOLD = 0.7



"""
Invoice Data Extraction — Baseline Inference Script
Hackathon-compliant [START] / [STEP] / [END] logging.
"""

import asyncio
import json
import os
from typing import List

from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# ── CONFIG ────────────────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME = os.environ.get("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_URL       = os.environ.get("ENV_URL",        "http://localhost:8000")

BENCHMARK              = "invoice_env"
MAX_STEPS              = 15
MAX_TOTAL_REWARD       = 3.0   # 3 tasks × 1.0 each
SUCCESS_THRESHOLD      = 0.7

# ── REQUIRED LOG FORMAT ───────────────────────────────────────────────────────
def log_start(task, env, model):
    print(json.dumps({"type": "START", "task": task, "env": env, "model": model}), flush=True)

def log_step(step, action, reward, done, error=None):
    print(json.dumps({
        "type": "STEP", "step": step,
        "action": action, "reward": reward,
        "done": done, "error": str(error) if error else None,
    }), flush=True)

def log_end(success, steps, score, rewards):
    print(json.dumps({
        "type": "END", "success": success,
        "steps": steps, "score": score, "rewards": rewards,
    }), flush=True)

# ── LLM PROMPT ────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are an expert invoice data extraction agent.
Read the invoice text carefully and extract ONLY the fields listed.
Respond with a single valid JSON object. No markdown, no explanation, no code fences.

Schema (use null for any field not present or not requested):
{
  "vendor_name": string or null,
  "invoice_date": "YYYY-MM-DD" or null,
  "invoice_number": string or null,
  "total_amount": number or null,
  "tax_amount": number or null,
  "currency": "USD"/"GBP"/"SGD"/"EUR" etc. or null,
  "line_items": [{"description": str, "quantity": number, "unit_price": number, "total": number}] or []
}

Rules:
- Dates MUST be YYYY-MM-DD.
- Amounts are plain numbers (no £, $, SGD symbols).
- vendor_name: full legal name exactly as printed.
- currency: 3-letter ISO code only.
"""

def call_llm(client: OpenAI, obs_dict: dict, feedback: str, step: int) -> dict:
    user_content = f"""Task: {obs_dict.get('task_name', '').upper()} — {obs_dict.get('task_description', '')}
Fields to extract: {', '.join(obs_dict.get('fields_to_extract', []))}

=== INVOICE ===
{obs_dict.get('invoice_text', '')}
=== END ===
"""
    if feedback and step > 1:
        user_content += f"\nPrevious attempt feedback: {feedback}\nFix your extraction accordingly."

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ],
        temperature=0.0,
        max_tokens=800,
    )
    raw = resp.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}

# ── MAIN LOOP ─────────────────────────────────────────────────────────────────
async def run():
    # Import AFTER server is running — client connects to ENV_URL
    # from invoice_env import InvoiceEnv, InvoiceAction
    from client import InvoiceEnv
    from models import InvoiceAction, InvoiceObservation

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    all_results = {}

    for task_label in ["easy", "medium", "hard"]:
        print(f"\n{'='*52}", flush=True)
        print(f"[INFO] Starting task: {task_label}", flush=True)

        rewards: List[float] = []
        steps_taken = 0
        score = 0.0
        success = False
        last_feedback = ""

        log_start(task=task_label, env=BENCHMARK, model=MODEL_NAME)

        try:
            async with InvoiceEnv(base_url=ENV_URL) as env:
                result = await env.reset()

                for step in range(1, MAX_STEPS + 1):
                    if result.done:
                        break

                    obs = result.observation
                    # Grab the dict representation for prompt building
                    obs_dict = {
                        "task_name":        obs.task_name,
                        "task_description": obs.task_description,
                        "fields_to_extract": obs.fields_to_extract,
                        "invoice_text":     obs.invoice_text,
                    }

                    extracted = call_llm(client, obs_dict, last_feedback, step)

                    action = InvoiceAction(
                        vendor_name=extracted.get("vendor_name"),
                        invoice_date=extracted.get("invoice_date"),
                        invoice_number=extracted.get("invoice_number"),
                        total_amount=extracted.get("total_amount"),
                        tax_amount=extracted.get("tax_amount"),
                        currency=extracted.get("currency"),
                        line_items=extracted.get("line_items", []),
                    )

                    result      = await env.step(action)
                    reward      = result.reward or 0.0
                    done        = result.done
                    last_feedback = result.observation.feedback or ""

                    rewards.append(reward)
                    steps_taken = step

                    log_step(step=step, action=extracted, reward=reward, done=done)

                    if done:
                        break

            score   = min(max(sum(rewards) / MAX_TOTAL_REWARD, 0.0), 1.0)
            success = score >= SUCCESS_THRESHOLD

        except Exception as e:
            log_step(step=steps_taken + 1, action={}, reward=0.0, done=True, error=e)

        finally:
            log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

        all_results[task_label] = {"success": success, "steps": steps_taken, "score": score}

    print(f"\n{'='*52}", flush=True)
    print("[SUMMARY]", flush=True)
    for task, r in all_results.items():
        print(f"  {task:8s} | score={r['score']:.3f} | success={r['success']} | steps={r['steps']}", flush=True)
    overall = sum(r["score"] for r in all_results.values()) / len(all_results)
    print(f"  OVERALL  | avg_score={overall:.3f}", flush=True)


if __name__ == "__main__":
    asyncio.run(run())