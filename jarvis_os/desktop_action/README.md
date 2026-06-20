# Desktop Action Layer

The Desktop Action Layer strictly governs the physical interactions JARVIS is permitted to have with the host OS. 

## Architectural Pipeline
`Request -> Validator -> Safety Lock -> Permission Layer -> OS Adapter -> Execute`

## Constraints
- **Allowed Actions**: `open_application`, `open_folder`, `open_file`.
- **Safety Lock**: Dynamically detects restricted paths based on OS environment variables to prevent modification of System, Program, or Application Data directories.
- **Dry Run Default**: By default, `simulate=True`. The executor evaluates the pipeline but physically does nothing.
- **NO Subprocesses**: Exclusively uses `os.startfile()` on Windows to isolate the action from any shell interpreter.
