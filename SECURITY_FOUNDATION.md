# Global Security Foundation

The Security Foundation (`jarvis_os/security/`) operates as the un-bypassable firewall across the entire OS. By separating security constraints from individual abilities (like Desktop Actions or Browser Automation), we ensure a unified, absolute threat mitigation strategy.

## Current Protections
1. **Append-Only Auditing**: Every attempt, success, or rejection is immutably logged to `security_audit.jsonl`.
2. **Dynamic Path Blacklists**: System directories (`SystemRoot`, `ProgramFiles`, `ProgramData`) are calculated at runtime using standard OS environment variables, guaranteeing they adapt to the host machine without hardcoding paths.
3. **Decoupled Validation**: Before an execution request even reaches a sub-module's executor, it must pass the `SecurityManager` validation rules.

## Future Protections
As JARVIS expands to Browser Automation or Phone integrations, new rule sets will be injected into `security_rules.py` (e.g., URL domain blacklists, restricted phone numbers). The manager will effortlessly scale to accommodate these new vectors.

## Threat Model & Boundaries
- **Threat**: Subprocess escape via string concatenation.
  - **Boundary**: Strict banning of `subprocess` imports. Use of OS-native bindings (like `os.startfile()`).
- **Threat**: Accidental system corruption.
  - **Boundary**: Broad-stroke `startswith()` path rejection for all vital system folders.
- **Threat**: Audit tampering.
  - **Boundary**: Logs are strictly opened in `a` (append) mode. No `w` (write/overwrite) operations are permitted.
