# Recommendation Layer

The Recommendation Layer is the safety bridge between Intelligence (Awareness/Computer State) and Execution (Abilities). It transforms JARVIS from a purely reactive assistant into a proactive assistant that asks for permission *before* enacting control.

## Components
- `recommendation_builder.py`: A strict deterministic rules-engine evaluating the global state against actionable triggers.
- `recommendation_prioritizer.py`: Filters and ranks outputs to prevent overwhelming the user.
- `recommendation_history.py`: A debounce tracker to prevent spamming the same suggestion repeatedly.
- `recommendation_manager.py`: The entry point that ties the pipeline together and exposes the "Ask Layer" (`build_action_request()`).

## Safety Principles
This module executes **nothing**. It strictly outputs a string request ("I recommend doing X. Proceed?"). It fully complies with the core directive: "Would I trust Jarvis to do this unsupervised?" (Yes, because it cannot act unsupervised).
