# MIGRATION CHECKLIST

- [ ] Update `jarvis_os/session/session_tracker.py` to inherit from `CapabilityInterface`.
- [ ] Update `jarvis_os/awareness/awareness_manager.py` to inherit from `CapabilityInterface`.
- [ ] Update `jarvis_os/computer/computer_manager.py` to inherit from `CapabilityInterface`.
- [ ] Update `jarvis_os/desktop_action/desktop_action_manager.py` to inherit from `CapabilityInterface`.
- [ ] Map the `execute()` payload of the `desktop_action` Capability directly to `os.startfile()`.
- [ ] Refactor `main.py` FastAPI routes to point to `OperatorManager` instead of `BrainService`.
- [ ] Quarantine `app/services/task_executor.py` into a `.legacy` folder or explicitly mark as unused.
- [ ] Inject `GlobalStateManager.build_global_state()` into the primary context payload sent to Groq.
