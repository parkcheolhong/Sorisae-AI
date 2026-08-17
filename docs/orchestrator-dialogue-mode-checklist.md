# Orchestrator Dialogue Mode Single Checklist

## Goal

Make the orchestrator default to free dialogue, keep execution explicit, and carry a durable reciprocal-question session that can surface structured questions, technology proposals, risks, costs, and alternatives.

## Applied design checklist

- [x] Separate dialogue and execution.
  - Enter submits chat only.
  - Execution starts through `/run` or explicit action buttons.
  - Stage pass/fix/fail is handled by buttons, not casual chat text.
- [x] Wire reverse-question mode end-to-end.
  - UI sends `reverse_question_mode`.
  - Backend promotes selected reverse-question mode to `conversation_mode="reverse_question"`.
  - Prompt policy and reciprocal-question post-processing use the same mode.
- [x] Persist dialogue by `session_id`.
  - Backend stores a session snapshot keyed by `session_id`.
  - Snapshot includes conversation, project memory, open questions, technology recommendations, and next actions.
  - Frontend keeps the same session id and conversation after reload.
- [x] Introduce structured response fields.
  - Response includes `technology_recommendations`.
  - Existing question/proposal/action fields are rendered as cards.
- [x] Make technology recommendations context-grounded.
  - Recommendations are derived from LLM reply text and web-grounding results when available.
  - Each recommendation includes adoption risk, implementation difficulty, operating cost, and alternative.
- [x] Remove prompt contradiction.
  - Free mode stays natural.
  - Reverse-question mode explicitly requires exactly one useful follow-up question.
- [x] Add regression tests.
  - Tests verify that selected reverse-question mode produces an automatic reciprocal question.
  - Tests verify that `session_id` restores prior conversation context.

## Remaining expansion points

- Replace the current lightweight recommendation extractor with a strict LLM JSON schema parser once the runtime model endpoint is stable.
- Move the file session store to the existing database layer if multi-replica production deployment requires shared storage.
- Add Playwright coverage for marketplace structured cards after CI backend mocking is stabilized.
