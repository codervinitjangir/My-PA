# Memory Engine

## Responsibilities
The Memory Engine acts as the hippocampus of Jarvis OS. It categorizes incoming information, scores its importance, and stores it in an easily retrievable format. 

## Inputs
* **Raw Content**: Text, timestamps, and source origin.
* **Categories**: Specific memory buckets (e.g., `goal_memory`, `project_memory`).

## Outputs
* **Structured Memory Items**: Data stored with UUIDs, Importance levels (Low, Medium, High, Critical), tags, and timestamps.
* **Retrieval Methods**: `get_recent_memories()` and category-based retrieval.

## Future Usage
Currently, importance classification relies on basic keyword rules. In the future, it will use an LLM-driven classification loop to dynamically assess the importance of a memory based on the user's active goals. The `MemoryStore` will be connected to FAISS (and potentially a Graph Database like Neo4j) to map relationships between memories, rather than just acting as a flat list.
