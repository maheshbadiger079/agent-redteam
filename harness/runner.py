"""
Attack Runner CLI
------------------
Usage examples (all free-tier friendly):

  # Attack a local Ollama model (fully free, no API key needed)
  python -m harness.runner \
      --target-url http://localhost:11434/v1 \
      --target-type openai_compatible \
      --model llama3.1 \
      --target-label "my-local-llama"

  # Attack a Groq free-tier endpoint
  python -m harness.runner \
      --target-url https://api.groq.com/openai/v1 \
      --target-type openai_compatible \
      --model llama-3.1-8b-instant \
      --api-key-env GROQ_API_KEY \
      --target-label "groq-llama-8b"

  # Attack a custom HTTP agent (your own FastAPI demo target)
  python -m harness.runner \
      --target-url http://localhost:8000/chat \
      --target-type http_custom \
      --target-label "my-demo-agent"
"""

import argparse
import uuid
import yaml
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.target_adapter import TargetAgent
from harness.classifier import heuristic_classify
from harness import storage


def load_attacks(path: str = None) -> list:
    candidates = []
    if path:
        candidates.append(path)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates.append(os.path.join(base_dir, "attacks", "attack_library.yaml"))
    candidates.append("attacks/attack_library.yaml")

    for p in candidates:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)

    raise FileNotFoundError("Could not locate attack_library.yaml file.")


def run(args):
    attacks = load_attacks(args.attack_file)
    
    if args.api_key:
        os.environ["_CLI_TEMP_API_KEY"] = args.api_key
        api_key_env = "_CLI_TEMP_API_KEY"
    else:
        api_key_env = args.api_key_env

    target = TargetAgent(
        base_url=args.target_url,
        api_key_env=api_key_env,
        model=args.model,
        target_type=args.target_type,
        request_field=args.request_field,
        response_field=args.response_field,
        api_key_header=args.api_key_header,
    )

    run_id = str(uuid.uuid4())[:8]
    print(f"\n=== Agent Red-Team Run [{run_id}] target='{args.target_label}' ===\n")

    counts = {"blocked": 0, "partial": 0, "succeeded": 0}

    for attack in attacks:
        print(f"[{attack['id']}] {attack['name']} ({attack['category']}) ... ", end="", flush=True)
        response_text = target.send(attack["payload"])
        verdict = heuristic_classify(attack, response_text)
        counts[verdict.verdict] += 1
        storage.save_result(run_id, args.target_label, attack, verdict)

        tag = {"blocked": "SAFE", "partial": "WARN", "succeeded": "VULN"}[verdict.verdict]
        print(f"{tag} ({verdict.verdict})")

    if args.user_label:
        storage.log_external_user(args.user_label, args.target_label, run_id)

    print("\n--- Summary ---")
    print(f"Blocked:   {counts['blocked']}")
    print(f"Partial:   {counts['partial']}")
    print(f"Succeeded: {counts['succeeded']}  <-- vulnerabilities")
    print(f"\nRun ID: {run_id} (saved to {storage.DB_PATH})")
    print("Run 'redteam-report' or 'python -m harness.report' to see the aggregated trust report.\n")


def main():
    parser = argparse.ArgumentParser(description="Agent Red-Team & Safety Eval Harness")
    parser.add_argument("--target-url", required=True, help="Base URL of the agent to attack")
    parser.add_argument("--target-type", default="openai_compatible",
                         choices=["openai_compatible", "http_custom"])
    parser.add_argument("--model", default=None, help="Model name, if applicable")
    parser.add_argument("--api-key-env", default=None,
                         help="Name of the environment variable holding your API key")
    parser.add_argument("--api-key", default=None, help="Direct API key value (alternative to --api-key-env)")
    parser.add_argument("--api-key-header", default="Authorization",
                         help="Header name for API key authentication (e.g. Authorization or X-API-Key)")
    parser.add_argument("--request-field", default="input", help="Request field name for http_custom (default: input)")
    parser.add_argument("--response-field", default="output", help="Response field name for http_custom (default: output)")
    parser.add_argument("--target-label", required=True, help="Human label for this target, e.g. 'my-agent-v1'")
    parser.add_argument("--user-label", default=None, help="Your name/handle, for the external-users trust metric")
    parser.add_argument("--attack-file", default=None, help="Path to custom attack library YAML file")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    main()

