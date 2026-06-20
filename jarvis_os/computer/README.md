# Computer Awareness Layer

This layer acts as JARVIS's raw sensory connection to the host machine. 
It strictly **OBSERVES**. It does **NOT CONTROL**.

## Capabilities
- Hardware observation (CPU, Memory, Disk, Battery, Network)
- Application awareness (Top running processes)
- OS awareness (Platform, time, environment)

## Principles
- **No AI in analysis**: The analyzer uses strict deterministic rules (e.g. CPU > 85% = `high_load`).
- **No dangerous libraries**: `subprocess`, `os.startfile`, `pyautogui`, `keyboard`, and `mouse` are completely banned from this layer to physically prevent control vectors.
- **Human Readable**: Exposes a natural language summary constructed purely via rule thresholds.
