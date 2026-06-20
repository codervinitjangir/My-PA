# Identity Engine

## Purpose
The Identity Engine is responsible for loading, parsing, and caching the user's global identity from the `profiles/` directory.

## Responsibilities
* Load identity JSON files.
* Validate identity schemas via Pydantic.
* Provide a unified `get_identity_context()` function for the Brain.
* Act as the single source of truth for "Who is the Boss".

## Current State (Week 1 Part 2)
Foundation built. It loads the JSON templates but is not yet connected to the main FastAPI stream.
