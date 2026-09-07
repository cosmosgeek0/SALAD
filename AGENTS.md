# bandwidth reel

This project is for bandwidth.

## Attack every claim

Every claim by a Fable, Codex, or any other model about a limit, a floor, a ceiling, "the fastest", "the best", or "cannot be done" is presumed wrong until it is measured on the actual system or read in full from a dated source. That covers its own claims, the critic's, and the previous chat's. Before stating any number, label it measured, published, or guessed, and say what it was measured against. When the owner disputes a limit, do not defend it: run parallel research agents, read the sources, measure again, and report what was found, including exactly where the earlier claim was wrong. Keep attacking each claim until no faster or better form is left to find, then build that one. A wrong limit stated with confidence is the worst defect in this project: it ends the search and the owner nearly builds on it.

## Do the narrow thing

The owner's last instruction is the whole task. Do exactly that and stop. A good result is not permission for the next step: not the next capability, not deployment, not a live command. When the owner says "just look" or "simulate", keep the work observational or simulated; do not add or execute live actions. Every mistake of this kind is recorded here with its date so the next worker does not repeat it.

Do not invent gates, ceremonies, or bloat for other agents to obey.

The work is rewarded for exactly three things. A simple, clear, lightning-fast implementation with nothing standing in the middle. Live proof — your own dry read, then the authorized real run, nothing between. The owner's word followed without your own biases added. Code written once that works beats code edited twenty times; every shortcut becomes work for the next worker.

Build it vertically, one complete working capability at a time. Long-term directions are not permission to build ahead.

The owner gives the current capability and execution path in chat. Do not ask the owner for what this file or the current chat already answers.

## Project

- Start and work inside the current project. Use external locations only when the owner names them or the current task requires them.
- Ordinary frontend work changes only the frontend; review or deploy backend and service files only when the task changes their behavior.
- Read, review, or change authentication and access files only when the current task requires work on that boundary.
- Use existing configured access. Never expose, print, log, or copy credentials into project files or chat.
- Use the owner's connected browser session when the task requires it; do not open another login.
- Deploy only the finished files required by the current capability.
- Only one worker edits the repository at a time. A new worker starts from this file, the complete code required by the current chat, and the last live output; no handover documents.
- Unrelated repositories, parent folders, external files, memories, state files, handovers, evidence, Git history, and old instructions are not project context unless the owner names an exact item.
- The current chat instruction is the only task. Do not invent or search for additional context.

## Work style

- Prefer the smallest clear implementation that fully works. Working bloat is rejected.
- Before editing, also quote the AGENTS.md lines that govern the change.
- Judge simplicity by the complete flow: direct steps, plain names, few moving parts, and no repeated behavior.
- The code is lightning fast and stays that way: direct calls and the best available tools, plainly used.
- Before adding anything, ask whether it makes the code slower or the flow longer. If it does, it is the defect; gates, ceremonies, and invented process are always defects.
- If the repository is empty, start with one working Python file. Otherwise extend the current working program.
- Build vertically. Do not create separate pieces and hope to connect them later.
- Every added line must serve the current capability or a failure observed in a real run.
- Do not add future features, imagined failures, speculative safety, dormant options, or architecture for style.
- Do not invent approval gates or add ceremonies, pipelines, or background runners outside the owner's requested scope.
- Prefer changing or deleting existing code over adding wrappers, parallel paths, second implementations, or new architecture.
- When new code replaces old behavior, delete the old behavior. "It still works" and "it is harmless" are not reasons to keep it.
- When a section has rotted, rewrite it fresh from what it must do. Do not repair it patch by patch, and do not paste blocks from old code.
- Keep one implementation for each behavior and one definition for each measured value.
- Extract shared code only after real repetition exists and only when the complete flow becomes simpler.
- Do not split one readable sequence into many helpers, classes, files, or layers merely to make it look structured.
- Use ordinary names that describe the real action. Do not invent project vocabulary, decorative architecture names, banner comments, boxed separators, slogans, or stylistic structure.
- If the owner says to delete something, delete it. Do not preserve, archive, disable, rename, or argue that it may be useful later.

## Build and verify

- When the chat names several capabilities, build them strictly in the named order. Complete, live-test, review, and correct one before writing the next.
- Before each capability, reread `AGENTS.md` and the complete current code for that capability.
- Before editing, state the capability, files, functions, why each change is needed, and the rough net line change.
- Stop before writing if the solution is unexpectedly large or needs an additional permanent file, class, dependency, abstraction, or parallel implementation.
- After writing, reread the complete changed flow.
- Remove unused imports, unused variables, duplicate logic, unnecessary helpers, speculative branches, commented-out old code, decorative comments, and temporary files.
- Do not create test files by default. Run only quick syntax, import, and exact-arithmetic checks when needed.
- Test the complete current program on the actual system using only the owner-authorized scope and execution path.
- After each live run, compare every printed action, number, and label with the actual system. Inaccurate or misleading output means the capability has not passed; correct it and rerun before continuing.
- Failure is allowed. Stop at the first real failure.
- Report the exact step, exact error, completed actions, and current system state.
- Make only the smallest change required by that failure, then run the whole program again.
- Do not add handling for similar failures that have not happened.
- Do not commit experiments or small edits. Commit only after the capability works live and the owner asks.

## Review

- After each capability passes live, and before any claim reaches the owner, run one independent Astra GPT-6 critic at max or ultra reasoning.
- Run the critic locally: `codex exec -m gpt-6-astra -c 'model_reasoning_effort="ultra"' -c 'service_tier="priority"' -s read-only --skip-git-repo-check` with the complete packet on stdin (`max` is the other allowed effort). Never use a Claude sub-agent as the critic. Trust the verdict only after the printed session header confirms model gpt-6-astra with max or ultra reasoning. Verified 2026-09-06: the names gpt-6, gpt-6-astra-max and gpt-6-astra-ultracore are refused by codex.
- The critic reads `AGENTS.md`, every active file the change touches and the files they import, excluding authentication and access files unless the current task changes them, plus the exact change and live output.
- The packet is one self-contained text: this file verbatim, the owner's task verbatim, every file in that set in full, the exact change with before and after code, all live output including failed runs, and prior rounds' adjudicated results. Never include the builder's own review or conclusions.
- The critic does not edit code and does not propose speculative features, architecture, style preferences, or general hardening.
- Every finding must name the exact location, concrete wrong behavior, supporting code or live fact, consequence, and smallest correction.
- The critic's verdict also answers: is this the smallest, fastest form of the capability? Structure beyond that is a concrete defect, not a style preference.
- The builder verifies every finding against the code and actual system. Confirmed findings earn the smallest fix and a full live rerun. Unsupported findings are rejected.
- Repeat fix, full live rerun with the capability's authorized inputs and execution path, and critic until it answers "no concrete defect found", then freeze the capability.
- A finding refuted by a critic round and accepted by the builder, or rejected by the owner, stays closed. Reopen only on a new live failure or an owner instruction.
- No other reviewer model is used unless the owner explicitly changes it.
- UI review adds `claude -p --model opus --effort xhigh` as a second critic, run in parallel on the same packet.

## Finish

- Stop after the last capability named in the current chat works.
- Do not harden, generalize, restructure, refactor, polish, or start the next capability.
- Compare the result with the simplest direct implementation. Use the smaller version when it stays equally clear and complete.
- Before returning, inspect everything created or changed during the task and remove anything the working program does not need.
- Remove task-only residue created during this run, including scratch scripts, temporary tests, hidden agent folders, plans, generated reports, traces, notes, caches, .codex, and .claude artifacts.
- Of the files created or changed during this task, leave only what the working capability needs. Do not delete unrelated pre-existing project files.
- Return the live result, files changed, line count before and after, each function added or changed in plain words, every real failure and its exact fix, and what was deliberately not added.
- The owner must be able to understand the complete active flow line by line.
