# 🛡️ Agent Red-Team & Safety Eval Harness

Attack AI agents on purpose — prompt injection, jailbreaks, tool-misuse — and score how well they hold up.
Built to be pointed at **any** agent, not just a demo. Attack library based on the **OWASP LLM Top 10**.

> Built and shipped an open-source agent red-teaming CLI based on the OWASP LLM Top 10; used by external developers to test their own agents, surfacing real vulnerabilities.

---

## Why this exists

Safety is now a board-level concern in AI, and almost nobody builds the *adversarial* side of AI systems for
their portfolio. Most safety projects test against a private demo and stop there. This one is designed to be
run by strangers, against their own agents — that's the difference between "I wrote a report" and
"I shipped something used by other engineers."

## Everything here is free to run

| Component | Free option used |
|---|---|
| LLM to attack | Local **Ollama** model, or a free-tier **Groq** API key |
| Web form hosting | **Streamlit Community Cloud** (share.streamlit.io) |
| Sandbox isolation | **Docker Desktop** (local, no cloud bill) |
| Attack reference | **OWASP LLM Top 10** (public, free) |
| Distribution | Reddit / Discord / your dev community |

No credit card required anywhere in this stack.

## Quickstart (free, zero API keys required)

```bash
git clone <your-repo-url>
cd agent-redteam
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install fastapi uvicorn slowapi pydantic

# 1. Start the sandboxed demo target agent (runs in free offline "mock" mode
#    by default — no API key needed to try the tool)
uvicorn demo_target.app:app --reload --port 8000

# 2. In a new terminal, attack it with the full OWASP-based attack library
python -m harness.runner \
  --target-url http://localhost:8000/chat \
  --target-type http_custom \
  --target-label "my-first-run" \
  --user-label "your-name"

# 3. See the aggregated trust report
python -m harness.report
```

## Point it at YOUR agent instead

This is the part that matters: the harness never hardcodes a target.

```bash
# Local Ollama model (100% free, no API key, no rate limits)
python -m harness.runner \
  --target-url http://localhost:11434/v1 \
  --target-type openai_compatible \
  --model llama3.1 \
  --target-label "my-ollama-agent"

# Groq free-tier endpoint
export GROQ_API_KEY=your_key_here
python -m harness.runner \
  --target-url https://api.groq.com/openai/v1 \
  --target-type openai_compatible \
  --model llama-3.1-8b-instant \
  --api-key-env GROQ_API_KEY \
  --target-label "my-groq-agent"

# Any custom HTTP agent that accepts {"input": "..."} and returns {"output": "..."}
python -m harness.runner \
  --target-url https://your-agent.example.com/chat \
  --target-type http_custom \
  --target-label "my-custom-agent"
```

## Web form (no repo clone needed)

```bash
streamlit run webapp/streamlit_app.py
```

Deploy this for free on [Streamlit Community Cloud](https://share.streamlit.io) so anyone can attack their
own agent from a browser, and see the public aggregated **Trust Report** dashboard tab.

## Architecture

```
Attack Library (OWASP LLM Top 10, attacks/attack_library.yaml)
        │
        ▼
Attack Runner (harness/runner.py) ──► Target Agent (variable: yours, or any user-supplied endpoint)
        │
        ▼
Response Classifier (harness/classifier.py) → blocked / partial / succeeded
        │
        ▼
Trust Report (harness/report.py + webapp dashboard)
```

The `Target Agent` box is a variable, not a constant — the same attack runner works whether it's pointed at
your own sandboxed demo or a stranger's endpoint.

## Sandboxing the demo target (important before you invite strangers)

```bash
docker build -f demo_target/Dockerfile -t redteam-demo-target .
docker run -p 8000:8000 --rm redteam-demo-target
```

Safety properties of `demo_target/app.py`:
- No real destructive tool actions exist (delete/email tools are stubs that only log).
- No real secrets in context — only a decoy value used to test exfiltration attempts.
- Rate-limited per IP (10 req/min) so strangers can't burn your free-tier quota.
- Runs offline in mock mode with zero API cost unless you opt in to a real model.

## Attack library

10 starter attacks across OWASP LLM01 (direct + indirect prompt injection, jailbreak templates),
LLM03 (supply chain / tool poisoning), LLM06 (sensitive info disclosure), and LLM08 (excessive agency /
tool misuse). See `attacks/attack_library.yaml` — add your own entries in the same format to grow the library.

## Trust Report metrics tracked

- External users who ran the tool
- Distinct agents tested
- Total attack attempts logged
- Vulnerabilities found
- Most common failure category

## Roadmap / extra credit

- [ ] Public trust-report dashboard link
- [ ] Write-up of the most interesting vulnerability found
- [ ] Screenshots of the community thread that got people testing it
- [ ] LLM-as-judge second pass for ambiguous verdicts (`harness/classifier.py:llm_judge_classify`)
- [ ] MITRE ATLAS attacks alongside OWASP LLM Top 10

## Tech stack

Python CLI · Streamlit web form · OWASP LLM Top 10 · Docker sandboxing
