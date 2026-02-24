# Shamalgan Working Process (Live Task Protocol)

This is the default process we use while executing tasks in this repository.

## 1) Task Start (alignment)
- Restate the request in one sentence.
- State immediate constraints (for example: "do not run scenario now", "low-spec PC", "avoid long jobs").
- Define first action (read files, inspect config, or run lightweight check).

## 2) Lightweight Discovery
- Read only the minimum files needed.
- Prefer fast searches and targeted inspection.
- Identify unknowns before running heavy commands.

## 3) Plan Before Changes
- Write a short execution plan:
  - files to edit
  - commands to run
  - validation criteria
- Keep commands scoped and stop quickly on failure.

## 4) Safe Execution Rules
- Start with compile/sanity checks before full run.
- Avoid parallel heavy jobs on this machine.
- Use bounded runs and monitor logs; stop if behavior looks stuck.
- Archive old outputs to reduce IDE pressure.

## 5) Implementation
- Apply minimal, targeted edits.
- Keep assumptions explicit (for example PT assumptions: speed, dwell time, headway).
- Record any synthetic/default parameters and why they were chosen.

## 6) Validation
- Verify at three levels:
  - config validity
  - build/compile success
  - runtime completion and key outputs present
- Classify warnings:
  - blocking (must fix now)
  - non-blocking (document and continue)

## 7) Handoff After Each Task
- Report:
  - what changed
  - files touched
  - commands executed
  - outcome and remaining risks
- Propose the next 1-3 concrete steps.

## 8) Live Update Format (during work)
- Short update every major action:
  - "I am checking X because Y."
  - "I found Z; next I will do W."
  - "I am editing A/B and then validating with C."

## 9) Scope Guardrails
- If data is weak, keep model assumptions simple and explicit.
- Prefer reproducible scripts over manual one-off edits.
- Do not treat guessed PT/network values as final calibration.
