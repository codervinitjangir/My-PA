# Memory Engine

## Purpose
The Memory Engine manages how Jarvis remembers things. Unlike the V1 flat-file RAG system, this engine structures memories by category and importance.

## Responsibilities
* Classify memory importance using rules (and later AI).
* Store structured memory items.
* Retrieve memories based on context and need.

## Current State (Week 1 Part 2)
Foundation built. It defines the categories, structure, and rules-based classifier, but has not yet replaced the existing FAISS integration.
