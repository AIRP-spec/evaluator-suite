"""CPU stand-in for a vLLM OpenAI-compatible server, for the self-hosted dry-run only.

Serves POST /v1/chat/completions and GET /version with a tiny HF model through
transformers (greedy-free sampling, CPU). Honors chat_template_kwargs like vLLM.

  python tools/tiny_openai_server.py --model HuggingFaceTB/SmolLM2-135M-Instruct \
      --revision 12fd25f77366fa6b3b4b768ec3050bf629380bac --port 8765
"""
import argparse
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

LOCK = threading.Lock()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--revision", required=True)
    ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args()
    tok = AutoTokenizer.from_pretrained(a.model, revision=a.revision)
    model = AutoModelForCausalLM.from_pretrained(a.model, revision=a.revision, torch_dtype=torch.float32)
    model.eval()

    class H(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def _send(self, code, obj):
            b = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            if self.path == "/version":
                return self._send(200, {"version": "tiny-cpu-transformers-" + __import__("transformers").__version__})
            if self.path == "/v1/models":
                return self._send(200, {"data": [{"id": a.model}]})
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/v1/chat/completions":
                return self._send(404, {"error": "not found"})
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            ctk = body.get("chat_template_kwargs") or {}
            ids = tok.apply_chat_template(body["messages"], add_generation_prompt=True, return_tensors="pt", **ctk)
            with LOCK, torch.no_grad():
                out = model.generate(ids, max_new_tokens=min(int(body.get("max_tokens", 32)), 48), do_sample=True,
                                     temperature=float(body.get("temperature", 0.7)), pad_token_id=tok.eos_token_id)
            gen = out[0, ids.shape[1]:]
            text = tok.decode(gen, skip_special_tokens=True)
            fin = "length" if len(gen) >= min(int(body.get("max_tokens", 32)), 48) else "stop"
            self._send(200, {"id": "chatcmpl-" + uuid.uuid4().hex[:12], "created": int(time.time()), "model": body.get("model"),
                             "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": fin}],
                             "usage": {"prompt_tokens": int(ids.shape[1]), "completion_tokens": int(len(gen)),
                                       "total_tokens": int(ids.shape[1] + len(gen))}})

    ThreadingHTTPServer(("127.0.0.1", a.port), H).serve_forever()


if __name__ == "__main__":
    main()
