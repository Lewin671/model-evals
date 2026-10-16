"""CLI-specific protocols; model and effort are part of every variant's identity."""
import json
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Variant:
    harness: str
    model: str
    effort: str

    def __post_init__(self):
        if self.harness not in ("command-code","codex"):
            raise ValueError("unknown harness: " + self.harness)
        if not self.model or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/._-" for c in self.model):
            raise ValueError("invalid model ID")
        if self.effort not in ("off","low","medium","high","xhigh","max"):
            raise ValueError("explicit supported reasoning effort required")

    @property
    def id(self):
        return f"{self.harness}:{self.model}@{self.effort}"

    def record(self):
        return dict(asdict(self),id=self.id)


def codex_command(variant):
    # Ignore personal config, docs and discovered integrations. No constrained
    # output schema: both CLIs must follow the same plain JSON instruction.
    args=["codex","--no-daemon","-a","never","exec","--json","--ephemeral",
          "--ignore-user-config","--ignore-rules","--skip-git-repo-check",
          "--sandbox","read-only","--model",variant.model,
          "-c",f'model_reasoning_effort="{variant.effort}"',
          "-c","project_doc_max_bytes=0","-c",'web_search="disabled"']
    for feature in ("shell_tool","apps","plugins","browser_use","computer_use","in_app_browser",
                    "image_generation","view_image","skill_search","hooks","memories"):
        args += ["-c",f"features.{feature}=false"]
    args += ["-c","features.skip_host_skill_discovery=true","-"]
    return args


def frames(raw):
    result=[]
    for line in raw.splitlines():
        try: item=json.loads(line)
        except ValueError: continue
        if isinstance(item,dict): result.append(item)
    return result


def parse_codex(raw):
    events=frames(raw)
    completed=[e for e in events if e.get("type")=="turn.completed"]
    if len(completed)!=1 or any(e.get("type")=="turn.failed" for e in events):
        raise ValueError("expected exactly one completed Codex turn")
    messages=[e["item"]["text"] for e in events if e.get("type")=="item.completed"
              and isinstance(e.get("item"),dict) and e["item"].get("type")=="agent_message"
              and isinstance(e["item"].get("text"),str)]
    if not messages: raise ValueError("missing final Codex message")
    tools={e["item"].get("id",str(i)) for i,e in enumerate(events) if e.get("type","").startswith("item.")
           and isinstance(e.get("item"),dict) and e["item"].get("type") not in ("agent_message","reasoning","error")}
    raw_usage=completed[0].get("usage",{})
    mapping={"input_tokens":"inputTokens","output_tokens":"outputTokens",
             "cached_input_tokens":"cacheReadTokens","reasoning_output_tokens":"reasoningTokens"}
    usage={v:raw_usage[k] for k,v in mapping.items() if k in raw_usage}
    return {"subtype":"success","finalText":messages[-1],"usage":usage,
            "observed_models":[],"observed_efforts":[],"identity_source":"invocation (not exposed in Codex JSONL)"},len(tools)
