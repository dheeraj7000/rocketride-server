# guardrails

A RocketRide filter node that screens questions before they reach the LLM and answers before they reach your users.

## What it does

Sits in the pipeline as a guard filter, evaluating questions on the way in and answers on the way out. On the input side it catches prompt injection, enforces topic rules (blocked and allowed keyword lists), and caps input length or estimated token count. On the output side it checks answers for hallucination (keyword grounding against source documents), flags harmful content, detects PII leaks (emails, phones, SSNs, credit cards, IP addresses), and validates the output format.

All checks are pure stdlib and regex: the node has no external dependencies, no model calls, and adds no network latency.

How it reacts is controlled by the `policy_mode` field: `block` drops the offending question or answer and never forwards it, `warn` logs the violation and forwards anyway, and `log` records the violation silently. The default profile runs in `warn` mode, so a freshly added node never blocks traffic until you opt in.

Text that is empty or whitespace-only is forwarded without checks.

---

## Lanes

| Lane in | Lane out | Description |
|---|---|---|
| `questions` | `questions` | Input checks run before the question is forwarded to the LLM |
| `answers` | `answers` | Output checks run after the LLM responds |
| `documents` | `documents` | Forwarded unchanged; content is collected as ground-truth context for the hallucination check |

Question text is assembled from both the question objects and any attached context before evaluation. Collected document content resets per pipeline object.

## Profiles

Default: **Basic: Prompt injection + PII detection** (`basic`).

Start with `basic` to observe violations without interrupting a pipeline, or `strict` when rejected content must not continue. Choose `custom` when the checks need to be selected individually.

| Profile | Behaviour |
|---|---|
| `basic` **(default)** | Prompt injection + PII detection, `warn` mode. Nonce fencing off. Only `policy_mode` is configurable in the UI. |
| `strict` | All checks enabled, `block` on violation, `max_input_length` 50000, and `max_tokens_estimate` 4096. Nonce fencing is off by default; enable it explicitly after confirming downstream consumers accept fenced question text. |
| `custom` | All checks enabled, nonce fencing off, `warn` mode. Exposes every individual check, limit, topic, format, and policy control. |

## Configuration

The generated schema is the field reference. Use the checks below to select what to enforce, then choose the policy mode that determines whether an observed violation should stop the pipeline.

### Input checks

Run on the `questions` lane before the question is forwarded:

Enable prompt-injection checking for untrusted questions. Use an allowed-topic list to constrain a focused workflow, or a blocked-topic list for specific unacceptable terms; both are case-insensitive substring checks, not semantic classification. Set one or both size limits when unusually large questions should be stopped before later nodes consume them.

- **Prompt injection** (rule `prompt_injection`, critical severity): regex patterns covering instruction-override attempts, system-prompt extraction, role-play jailbreaks, delimiter/token injection, and encoding-evasion commands; plus weighted keyword scoring.
- **Topic restriction** (rule `topic_restriction`): blocked-keyword matches are high severity; failing to match any allowed keyword is medium severity. Matching is case-insensitive substring.
- **Input length** (rule `input_length`, medium severity): only runs when a limit is set. Tokens are estimated as word count times 1.3.

### Nonce fencing

When `enable_nonce_fencing` is true, questions that pass the input checks are mutated before forwarding:

1. One cryptographically secure nonce is selected per execution cycle.
2. Each question text and context string is wrapped between nonce-delimited markers.
3. A `Security Directive` instruction is appended using the same nonce markers.

Caller-supplied `Question.instructions` are rejected while nonce fencing is enabled. This prevents untrusted caller instructions from bypassing the fencing boundary; the guardrails-generated directive is the only instruction added by this path.

The nonce is selected so it is absent from all question and context text before fencing. If a collision cannot be resolved, the question is blocked. Nonce fencing is disabled by default in every profile to preserve existing downstream consumers; enable it only where the next node treats fenced question text as data.

### Output checks

Run on the `answers` lane before the answer is forwarded:

Enable hallucination checking only when relevant documents arrive on the `documents` lane before the answer. It is a lexical grounding test, so use it to flag potentially unsupported output rather than as a factual verifier. Select an expected format only when a downstream consumer requires that shape.

- **Hallucination** (rule `hallucination`, high severity): sentence-level grounding against source documents; skipped when no documents have been received.
- **Content safety** (rule `content_safety`, critical severity): regex patterns across self-harm, violence, and illegal-activity categories.
- **PII leak** (rule `pii_leak`, high severity): matches emails, US phones, SSNs, credit cards, and IP addresses.
- **Format compliance** (rule `format_compliance`, medium severity): validates configured JSON, Markdown, bullet-list, or numbered-list output.

### Nonce length (bytes)

`nonce_length` defaults to 16 bytes and accepts whole-byte values from 16 through 128. Larger values increase marker size without improving ordinary operation; values outside this range are clamped by the runtime validator.

### Policy modes

When any enabled check fails, `policy_mode` decides the outcome:

| Mode | Effect |
|---|---|
| `block` | Each violation is logged as a warning and the question or answer is dropped. |
| `warn` | Each violation is logged as a warning; the item is forwarded anyway. |
| `log` | The item is forwarded with no warnings emitted. |

Blocking happens silently from the pipeline's point of view: downstream nodes simply never receive the item. Check the engine logs to see what was rejected.

---

<!-- ROCKETRIDE:GENERATED:PARAMS START -->
<!-- Generated by nodes:docs-generate. Do not edit by hand. -->

## Schema

| Field | Type | Description | Default |
|---|---|---|---|
| `allowed_topics` | `array` | **Allowed topics**<br/>If set, input must contain at least one of these keywords |  |
| `blocked_topics` | `array` | **Blocked topics**<br/>Keywords for topics that should be rejected |  |
| `enable_content_safety` | `boolean` | **Enable content safety check** | `true` |
| `enable_hallucination_check` | `boolean` | **Enable hallucination check** | `false` |
| `enable_pii_detection` | `boolean` | **Enable PII detection** | `true` |
| `enable_prompt_injection` | `boolean` | **Enable prompt injection detection** | `true` |
| `expected_format` | `string` | **Expected output format** | `""` |
| `guardrails.profile` | `string` | **Profile** | `"basic"` |
| `max_input_length` | `number` | **Max input length (chars)** | `0` |
| `max_tokens_estimate` | `number` | **Max tokens (estimate)** | `0` |
| `policy_mode` | `string` | **Policy mode** | `"warn"` |

## Source

[View source](https://github.com/rocketride-org/rocketride-server/tree/develop/nodes/src/nodes/guardrails)
<!-- ROCKETRIDE:GENERATED:PARAMS END -->
