from enum import Enum

class MemoryCategory(str, Enum):
    IDENTITY = "identity_memory"
    PROJECT = "project_memory"
    GOAL = "goal_memory"
    CONVERSATION = "conversation_memory"
    PREFERENCE = "preference_memory"
    KNOWLEDGE = "knowledge_memory"
    DEVICE = "device_memory"
    RELATIONSHIP = "relationship_memory"

class ImportanceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
