# Daily Brief Module

The Daily Brief module provides a proactive summary of the user's day, calculating an Energy Score and Today Mode without using an LLM.

## Performance Requirements
- **NO LLM CALLS**: All summarization and logic MUST be purely programmatic rules.
- **SPEED**: Must return the full JSON payload in `<50ms`.
- **DATA**: Sourced exclusively from `GlobalStateManager`.
