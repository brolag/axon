# Environment

Recorded for reproducibility. The quantization level matters: Q4_K_M is the
aggressive quant some community reports use — and the harness sustains loops on it.

## Model
- Name: `gemma4:26b` (Ollama)
- Family: gemma4
- Parameters: 25.8B
- Quantization: **Q4_K_M**

## Runtime
- Ollama: 0.24.0
- Endpoint: http://localhost:11434 (HTTP, stdlib urllib — no client library)
- Python: 3.11.14
- axon: 0.1.0 (PyYAML only runtime dependency)

## Hardware
- Machine: Mac16,7 (Apple Silicon, M4-class)
- RAM: 48 GB
- Inference: on-device (Metal)

## Cost
- API cost: $0 (fully local)
- Compute cost: GPU/CPU seconds on-device. Per-task latency recorded in `results/*/runs.jsonl`.

## Baseline model (secondary)
- `qwen3.6:35b` available locally on the same machine for the same-harness comparison.

## Notes
- Smoke results (n=1/task): see `results/gemma4_26b_temp0.0_harness/` and `results/_d2_check/`.
- To regenerate the task set: `python eval/_build_tasks.py`.
