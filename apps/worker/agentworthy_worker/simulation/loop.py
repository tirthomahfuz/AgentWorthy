"""Agent simulation loop — Playwright + Claude Sonnet tool use."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

from agentworthy_worker.llm.client import LLMClient
from agentworthy_worker.llm.config import SONNET_MODEL
from agentworthy_worker.simulation.actions import ActionError, check_payment_gate, execute_action
from agentworthy_worker.simulation.a11y_tree import build_tree_from_page
from agentworthy_worker.simulation.storage import LocalStorage

logger = logging.getLogger(__name__)

SIM_UA = "AgentworthyBot/1.0 (+https://agentworthy.example/bot)"
MAX_STEPS = 25
WALL_CLOCK_SEC = 240
HISTORY_KEEP = 10

TOOLS = [
    {"name": "click", "description": "Click element by ref", "input_schema": {"type": "object", "properties": {"ref": {"type": "string"}}, "required": ["ref"]}},
    {"name": "type", "description": "Type into element", "input_schema": {"type": "object", "properties": {"ref": {"type": "string"}, "text": {"type": "string"}}, "required": ["ref", "text"]}},
    {"name": "select", "description": "Select option", "input_schema": {"type": "object", "properties": {"ref": {"type": "string"}, "value": {"type": "string"}}, "required": ["ref", "value"]}},
    {"name": "navigate", "description": "Navigate to URL", "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
    {"name": "scroll", "description": "Scroll page", "input_schema": {"type": "object", "properties": {"direction": {"type": "string", "enum": ["up", "down"]}}, "required": ["direction"]}},
    {"name": "extract", "description": "Task complete — provide answer", "input_schema": {"type": "object", "properties": {"answer": {"type": "string"}}, "required": ["answer"]}},
    {"name": "give_up", "description": "Cannot complete task", "input_schema": {"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"]}},
]


def _summarize_history(steps: list[dict[str, Any]]) -> str:
    if len(steps) <= HISTORY_KEEP:
        return json.dumps(steps[-HISTORY_KEEP:])
    older = steps[:-HISTORY_KEEP]
    summary = "; ".join(f"step{s['index']}: {s['action']}" for s in older)
    return summary + "\n" + json.dumps(steps[-HISTORY_KEEP:])


def run_simulation(
    scan_id: str,
    sim_id: str,
    root_url: str,
    task_description: str,
    llm: LLMClient | None = None,
    token_budget: int | None = None,
    tokens_used: list[int] | None = None,
) -> dict[str, Any]:
    """Run one simulation; returns outcome dict for DB."""
    client = llm or LLMClient(scan_id=scan_id)
    storage = LocalStorage()
    root_domain = urlparse(root_url).hostname or ""
    page_origin = f"{urlparse(root_url).scheme}://{root_domain}"
    steps: list[dict[str, Any]] = []
    start = time.monotonic()
    outcome = "fail"
    failure_point: str | None = "unknown"
    failure_reason: str | None = None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800}, user_agent=SIM_UA)
        page = context.new_page()
        page.goto(root_url, wait_until="domcontentloaded", timeout=30_000)

        for step_idx in range(MAX_STEPS):
            if time.monotonic() - start > WALL_CLOCK_SEC:
                failure_point = "timeout"
                failure_reason = "Wall clock limit exceeded"
                break

            if check_payment_gate(page):
                outcome = "success"
                failure_point = "payment_gate_reached"
                failure_reason = "Reached payment form — simulation stopped before entering card data"
                break

            tree = build_tree_from_page(page)
            screenshot = page.screenshot()
            shot_path = storage.save_bytes(scan_id, sim_id, step_idx, screenshot)

            prompt = {
                "task": task_description,
                "url": page.url,
                "history": _summarize_history(steps),
                "a11y_tree": tree,
            }
            system = (
                "You are an AI agent testing website usability. Use exactly one tool per turn. "
                "Refs come from the a11y_tree only. Call extract when done or give_up if stuck."
            )
            t0 = time.monotonic()
            try:
                response = client.client.messages.create(
                    model=SONNET_MODEL,
                    max_tokens=512,
                    system=system,
                    tools=TOOLS,
                    messages=[{"role": "user", "content": json.dumps(prompt)}],
                )
                if tokens_used is not None:
                    tokens_used[0] += response.usage.input_tokens + response.usage.output_tokens
                if token_budget and tokens_used and tokens_used[0] > token_budget:
                    failure_point = "budget_exceeded"
                    failure_reason = "LLM token budget exceeded"
                    break
                client._log_usage(SONNET_MODEL, response.usage.input_tokens, response.usage.output_tokens)
            except Exception as e:
                failure_point = "llm_error"
                failure_reason = str(e)
                break

            tool_use = next((b for b in response.content if b.type == "tool_use"), None)
            if not tool_use:
                failure_point = "no_action"
                failure_reason = "Model returned no tool call"
                break

            action_name = tool_use.name
            action_input = tool_use.input
            reasoning = next((b.text for b in response.content if hasattr(b, "text")), "")

            if action_name == "extract":
                outcome = "success"
                failure_point = None
                steps.append({
                    "index": step_idx,
                    "action": "extract",
                    "ref_or_url": action_input.get("answer", ""),
                    "agent_reasoning": reasoning,
                    "screenshot_path": shot_path,
                    "duration_ms": int((time.monotonic() - t0) * 1000),
                    "url_after": page.url,
                })
                break
            if action_name == "give_up":
                failure_point = "agent_gave_up"
                failure_reason = action_input.get("reason", "Agent gave up")
                steps.append({
                    "index": step_idx,
                    "action": "give_up",
                    "ref_or_url": failure_reason,
                    "agent_reasoning": reasoning,
                    "screenshot_path": shot_path,
                    "duration_ms": int((time.monotonic() - t0) * 1000),
                    "url_after": page.url,
                })
                break

            action = {"action": action_name, **action_input}
            try:
                executed, note = execute_action(page, tree, action, task_description, root_domain, page_origin)
                if note == "blocked_off_domain":
                    failure_point = "off_domain_blocked"
                    failure_reason = f"Navigation to {action_input.get('url')} blocked"
                    break
                if note == "blocked_destructive":
                    steps.append({
                        "index": step_idx,
                        "action": "refused_destructive",
                        "ref_or_url": action_input.get("ref", ""),
                        "agent_reasoning": reasoning,
                        "screenshot_path": shot_path,
                        "duration_ms": int((time.monotonic() - t0) * 1000),
                        "url_after": page.url,
                    })
                    continue
                if note == "checkout_allowlist":
                    outcome = "success"
                    failure_point = "checkout_reached"
                    break
            except ActionError as e:
                steps.append({
                    "index": step_idx,
                    "action": f"error:{action_name}",
                    "ref_or_url": str(e),
                    "agent_reasoning": reasoning,
                    "screenshot_path": shot_path,
                    "duration_ms": int((time.monotonic() - t0) * 1000),
                    "url_after": page.url,
                })
                continue

            steps.append({
                "index": step_idx,
                "action": action_name,
                "ref_or_url": action_input.get("ref") or action_input.get("url", ""),
                "agent_reasoning": reasoning,
                "screenshot_path": shot_path,
                "duration_ms": int((time.monotonic() - t0) * 1000),
                "url_after": page.url,
            })

        else:
            failure_point = "step_limit"
            failure_reason = f"Exceeded {MAX_STEPS} steps"

        browser.close()

    return {
        "outcome": outcome,
        "steps": steps,
        "failure_point": failure_point,
        "failure_reason": failure_reason,
    }
