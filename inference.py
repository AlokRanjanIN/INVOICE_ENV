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
async def main():
    # Import AFTER server is running — client connects to ENV_URL
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
    asyncio.run(main())