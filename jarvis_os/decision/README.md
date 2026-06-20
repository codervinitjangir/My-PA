# Decision Engine

## Purpose
The Decision Engine represents the "free will" loop of Jarvis OS. Instead of passively waiting for a user command, it actively evaluates the state of the user's world and decides *what should happen next*. 

## Components
* **DecisionManager**: The orchestrator of the entire engine.
* **DecisionEvaluator**: Analyzes inputs against rules to generate `DecisionCandidate`s.
* **DecisionSelector**: Picks the absolute best decision from the candidates.
* **DecisionRules**: The deterministic logic module.
* **DecisionHistory**: Records what was decided and why, enabling future ML feedback loops.

## Current State (Week 2 Part 3)
The engine is purely rules-based and deterministic. It does not actually execute or trigger anything yet. It exists to prove that Jarvis can evaluate context and independently state "I should wait" or "I should plan an active goal."
