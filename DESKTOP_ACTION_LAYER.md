# Desktop Action Layer

The Desktop Action Layer (`jarvis_os/desktop_action/`) represents JARVIS's first physical capability. It has been meticulously constrained to ensure complete transparency, safety, and human control.

## Architectural Pipeline
The execution of any local command must traverse the following flow:
1. **Request**: The user approves an action recommended by the OS.
2. **Validator**: Validates the schema.
3. **Safety Lock**: Verifies the action is on the strict whitelist (`open_application`, `open_folder`, `open_file`) and that the target is not empty.
4. **Security Manager**: The path is checked against the global blacklist (System/Program folders).
5. **Permission Layer**: Evaluates if the user explicitly approved this specific execution.
6. **OS Adapter**: Binds the request to the target operating system (Windows via `os.startfile()`).
7. **Execute**: The file or application is safely opened. Default behavior is **Dry Run** (`simulate=True`).

## Cross-Platform Status
- **Windows**: `os.startfile()` implemented successfully.
- **Linux**: Pending implementation. Requires safe alternative to `subprocess.run(["xdg-open"])`.
- **macOS**: Pending implementation. Requires safe alternative to `subprocess.run(["open"])`.
