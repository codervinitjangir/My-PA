# Permanent Core Rules

To prevent JARVIS from regressing into an unmaintainable "split-brain" state, the following engineering directives are now immutable:

1. **No duplicate brains.** There is exactly one orchestrator (Operator) and one parser (LLM). Never build parallel intelligence loops.
2. **No duplicate memory systems.** All state must be managed by the active capability modules (Session, Awareness) and aggregated by the Operator.
3. **No new folders without justification.** Less code is vastly superior to more code.
4. **Every sprint must create a demoable ability.** Architecture without physical implementation is wasted effort.
5. **Every sprint must solve a real user problem.** Do not build modules that sound impressive but lack practical daily utility.
6. **Architecture cannot exceed 20% of work.** The majority of time must be spent engineering the actual pipeline, testing edges, and handling errors.
7. **Every new ability must pass through Operator.** If an ability is not registered in the `CapabilityRegistry` and routed by the Operator, it does not exist.
8. **Every physical action must pass Security.** All executions, without exception, must traverse the immutable append-only audit trail and whitelist block-chain.
