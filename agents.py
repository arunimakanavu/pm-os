import os
import json
from datetime import datetime
from typing import List, Dict, Optional

import database as db
import rag

# ---------------------------------------------------------------------------
# HuggingFace local LLM
# ---------------------------------------------------------------------------

MODEL_ID = os.environ.get("PM_OS_MODEL", "microsoft/Phi-3-mini-4k-instruct")

_pipeline = None

def get_pipeline():
    global _pipeline
    if _pipeline is None:
        from transformers import pipeline, AutoTokenizer, AutoModelForCausalLM
        import torch
        print(f"[PM OS] Loading model: {MODEL_ID} ...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _pipeline = pipeline(
            "text-generation",
            model=MODEL_ID,
            tokenizer=MODEL_ID,
            torch_dtype=torch.float32,
            device_map="auto",
            trust_remote_code=True,
        )
        print(f"[PM OS] Model loaded on {device}.")
    return _pipeline

def llm(system: str, user: str, history: List[Dict] = None, max_tokens: int = 512) -> str:
    pipe = get_pipeline()

    # Build chat messages in standard format
    messages = [{"role": "system", "content": system}]
    if history:
        for h in history[-4:]:  # keep context window tight for small models
            messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user})

    # Use chat template if available, else flatten manually
    try:
        output = pipe(
            messages,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=pipe.tokenizer.eos_token_id,
            return_full_text=False,
        )
        return output[0]["generated_text"].strip()
    except Exception as e:
        return f"[Model error: {e}]"

# ---------------------------------------------------------------------------
# RAG context builder
# ---------------------------------------------------------------------------

def build_rag_context(query: str, n: int = 4) -> str:
    chunks = rag.retrieve(query, n_results=n)
    if not chunks:
        return ""
    lines = ["### Relevant context from your uploaded docs:\n"]
    for c in chunks:
        fname = c["metadata"].get("filename", "doc")
        lines.append(f"**[{fname}]**: {c['text']}\n")
    return "\n".join(lines)

# ---------------------------------------------------------------------------
# Roadmap Agent
# ---------------------------------------------------------------------------

ROADMAP_SYSTEM = """You are the Roadmap Agent in an AI PM OS. 
You help manage product features: adding, updating, prioritizing, and analyzing the roadmap.
When asked to add or update features, respond with a JSON block inside <action> tags.
Actions: add_feature, update_feature, delete_feature, summarize_roadmap.

For add_feature: <action>{"type":"add_feature","title":"...","description":"...","status":"backlog|in_progress|done","priority":"low|medium|high|critical","owner":"...","quarter":"..."}</action>
For update_feature: <action>{"type":"update_feature","id":N,"field":"...","value":"..."}</action>
For delete_feature: <action>{"type":"delete_feature","id":N}</action>

Always explain what you're doing in plain English before the action tag.
Use the provided roadmap data and doc context to give grounded, specific advice."""

def roadmap_agent(user_message: str, chat_history: List[Dict] = None) -> str:
    features = db.get_features()
    summary = db.get_roadmap_summary()
    rag_context = build_rag_context(user_message)

    roadmap_str = json.dumps(features, indent=2) if features else "No features yet."
    summary_str = json.dumps(summary)

    system = ROADMAP_SYSTEM
    context = f"""Current roadmap ({summary_str}):
{roadmap_str}

{rag_context}"""

    full_user = f"{context}\n\nUser request: {user_message}"
    response = llm(system, full_user, chat_history)

    # Parse and execute actions
    import re
    actions = re.findall(r'<action>(.*?)</action>', response, re.DOTALL)
    results = []
    for action_str in actions:
        try:
            action = json.loads(action_str.strip())
            result = execute_roadmap_action(action)
            results.append(result)
        except Exception as e:
            results.append(f"Action error: {e}")

    # Clean response of action tags for display
    clean = re.sub(r'<action>.*?</action>', '', response, flags=re.DOTALL).strip()
    if results:
        clean += "\n\n✅ " + " | ".join(str(r) for r in results)
    return clean

def execute_roadmap_action(action: Dict) -> str:
    t = action.get("type")
    if t == "add_feature":
        db.add_feature(
            title=action.get("title", "Untitled"),
            description=action.get("description", ""),
            status=action.get("status", "backlog"),
            priority=action.get("priority", "medium"),
            owner=action.get("owner", ""),
            quarter=action.get("quarter", ""),
            tags=action.get("tags", "")
        )
        return f"Feature '{action.get('title')}' added to roadmap"
    elif t == "update_feature":
        db.update_feature(action["id"], **{action["field"]: action["value"]})
        return f"Feature #{action['id']} updated"
    elif t == "delete_feature":
        db.delete_feature(action["id"])
        return f"Feature #{action['id']} deleted"
    return "Action executed"

# ---------------------------------------------------------------------------
# Standup Agent
# ---------------------------------------------------------------------------

STANDUP_SYSTEM = """You are the Standup Agent in an AI PM OS.
Parse raw standup notes into three clear sections: Done, Doing, Blocked.
Also identify any blockers that need escalation and link them to roadmap items if possible.
Return a JSON block inside <standup> tags:
<standup>{"done": ["..."], "doing": ["..."], "blocked": ["..."], "blockers_summary": "..."}</standup>
Then give a brief human-friendly summary."""

def standup_agent(raw_notes: str, chat_history: List[Dict] = None) -> str:
    features = db.get_features(status="in_progress")
    rag_context = build_rag_context(raw_notes, n=3)
    features_str = json.dumps([f["title"] for f in features])

    user = f"""Raw standup notes:
{raw_notes}

Active roadmap items: {features_str}
{rag_context}

Parse these into done/doing/blocked and identify any blockers."""

    response = llm(STANDUP_SYSTEM, user, chat_history)

    import re
    match = re.search(r'<standup>(.*?)</standup>', response, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1).strip())
            today = datetime.now().strftime("%Y-%m-%d")
            db.save_standup(
                date=today,
                raw_notes=raw_notes,
                done="\n".join(parsed.get("done", [])),
                doing="\n".join(parsed.get("doing", [])),
                blocked="\n".join(parsed.get("blocked", []))
            )
        except Exception:
            pass

    clean = re.sub(r'<standup>.*?</standup>', '', response, flags=re.DOTALL).strip()
    return clean

# ---------------------------------------------------------------------------
# PRD Agent
# ---------------------------------------------------------------------------

PRD_SYSTEM = """You are the PRD Agent in an AI PM OS.
You generate professional Product Requirement Documents.
Use context from the user's uploaded docs to match their team's style and reference prior decisions.
Structure every PRD with these sections:
## Problem Statement
## Goals & Success Metrics  
## User Stories
## Functional Requirements
## Edge Cases & Constraints
## Open Questions

Be specific, opinionated, and concise. Reference relevant prior PRDs or research if context is provided."""

def prd_agent(feature_description: str, feature_title: str = "", chat_history: List[Dict] = None) -> str:
    rag_context = build_rag_context(f"PRD {feature_title} {feature_description}", n=5)
    features = db.get_features()
    features_str = json.dumps([{"title": f["title"], "status": f["status"]} for f in features])

    user = f"""Generate a PRD for the following feature:

Title: {feature_title or 'New Feature'}
Description: {feature_description}

Existing roadmap context: {features_str}

{rag_context}

Write a complete, production-quality PRD."""

    response = llm(PRD_SYSTEM, user, chat_history, max_tokens=3000)

    # Save to DB
    db.save_prd(
        title=feature_title or feature_description[:60],
        full_draft=response
    )
    return response

# ---------------------------------------------------------------------------
# Orchestrator Agent
# ---------------------------------------------------------------------------

ORCHESTRATOR_SYSTEM = """You are the Orchestrator of an AI PM OS. You route user requests to the right agent.

Agents available:
- roadmap: Add/update/prioritize/query features on the roadmap
- standup: Parse standup notes into done/doing/blocked
- prd: Generate a PRD for a feature
- query: Answer general PM questions using uploaded docs as context
- digest: Summarize the current state of the roadmap and recent standups

Respond ONLY with a JSON object:
{"agent": "roadmap|standup|prd|query|digest", "confidence": 0.0-1.0, "reason": "..."}"""

def orchestrate(user_message: str) -> str:
    """Decide which agent to call using keyword heuristics + local LLM fallback."""
    import re
    msg = user_message.lower()

    # Fast keyword heuristics — no LLM call for obvious cases
    if any(w in msg for w in ["prd", "product requirement", "write a spec", "draft a spec"]):
        return "prd"
    if any(w in msg for w in ["standup", "done:", "doing:", "blocked:", "yesterday i", "today i"]):
        return "standup"
    if any(w in msg for w in ["add feature", "add to roadmap", "update feature", "roadmap", "priority", "backlog", "in progress", "quarter"]):
        return "roadmap"
    if any(w in msg for w in ["digest", "weekly summary", "weekly report", "what shipped", "velocity"]):
        return "digest"

    # LLM fallback for ambiguous messages
    try:
        raw = llm(ORCHESTRATOR_SYSTEM, user_message, max_tokens=80)
        raw = re.sub(r'```json\s*|\s*```', '', raw).strip()
        match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if match:
            result = json.loads(match.group())
            return result.get("agent", "query")
    except Exception:
        pass

    return "query"

# ---------------------------------------------------------------------------
# Query / General Agent
# ---------------------------------------------------------------------------

QUERY_SYSTEM = """You are a helpful PM assistant with access to the user's product docs and roadmap.
Answer questions, give advice, and help think through PM problems.
Ground your answers in the provided context. Be direct and specific."""

def query_agent(user_message: str, chat_history: List[Dict] = None) -> str:
    rag_context = build_rag_context(user_message)
    features = db.get_features()
    summary = db.get_roadmap_summary()
    recent_standups = db.get_standups(limit=3)

    context = f"""Roadmap summary: {json.dumps(summary)}
Recent standups: {json.dumps([{k: v for k, v in s.items() if k in ['date','done','doing','blocked']} for s in recent_standups])}
{rag_context}"""

    full_user = f"{context}\n\nQuestion: {user_message}"
    return llm(QUERY_SYSTEM, full_user, chat_history)

# ---------------------------------------------------------------------------
# Digest Agent
# ---------------------------------------------------------------------------

DIGEST_SYSTEM = """You are the Digest Agent. Generate a crisp weekly PM digest.
Cover: what shipped, what's in progress, what's blocked, risks, and what's coming next.
Format it as a clean, scannable brief. Be specific, not generic."""

def digest_agent() -> str:
    features = db.get_features()
    standups = db.get_standups(limit=5)
    prds = db.get_prds(limit=3)

    user = f"""Generate a weekly PM digest from this data:

ROADMAP:
{json.dumps(features, indent=2)}

RECENT STANDUPS:
{json.dumps(standups, indent=2)}

RECENT PRDs:
{json.dumps([{"title": p["title"], "created_at": p["created_at"]} for p in prds], indent=2)}"""

    return llm(DIGEST_SYSTEM, user, max_tokens=1500)

# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------

def process_message(user_message: str, chat_history: List[Dict] = None, force_agent: str = None) -> tuple[str, str]:
    """Returns (response, agent_used)."""
    agent = force_agent or orchestrate(user_message)

    if agent == "standup":
        return standup_agent(user_message, chat_history), "standup"
    elif agent == "prd":
        return prd_agent(user_message, chat_history=chat_history), "prd"
    elif agent == "roadmap":
        return roadmap_agent(user_message, chat_history), "roadmap"
    elif agent == "digest":
        return digest_agent(), "digest"
    else:
        return query_agent(user_message, chat_history), "query"
