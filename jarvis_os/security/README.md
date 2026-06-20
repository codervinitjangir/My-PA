# Security Foundation

The Security Foundation is the absolute, un-bypassable firewall for JARVIS OS. All future abilities (Desktop, Browser, Phone, Hardware) must validate their execution vectors through this centralized manager.

## Core Mandates
- **Append-Only Audits**: The `security_audit.py` component strictly appends to logs. Past execution history cannot be erased.
- **Dynamic Blacklists**: Paths are generated via OS environment variables (e.g., `%SystemRoot%`), not hardcoded strings.
