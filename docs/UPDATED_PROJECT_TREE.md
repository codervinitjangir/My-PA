# UPDATED PROJECT TREE (Milestone Beta)

```text
Jarvis/
├── app/
│   ├── services/
│   │   ├── brain_service.py      [DEPRECATED]
│   │   ├── chat_service.py       [LEGACY]
│   │   ├── groq_service.py       [ACTIVE] (Will be refactored as LLM Parser)
│   │   ├── realtime_service.py   [ACTIVE]
│   │   ├── task_executor.py      [LEGACY]
│   │   ├── task_manager.py       [LEGACY]
│   │   └── vision_service.py     [LEGACY]
│   └── main.py
├── jarvis_os/
│   ├── awareness/                [ACTIVE]
│   ├── brain/                    [DEPRECATED]
│   ├── capability_registry.py    [ACTIVE]
│   ├── cognitive/                [DEPRECATED]
│   ├── computer/                 [ACTIVE]
│   ├── context/                  [DEPRECATED]
│   ├── core/                     [ACTIVE - NEW]
│   │   ├── interfaces.py
│   │   ├── state_manager.py
│   │   └── README.md
│   ├── decision/                 [DEPRECATED]
│   ├── desktop_action/           [ACTIVE]
│   ├── executor/                 [DEPRECATED]
│   ├── identity/                 [ACTIVE]
│   ├── integration/              [DEPRECATED]
│   ├── memory/                   [ACTIVE]
│   ├── operator/                 [ACTIVE]
│   ├── planner/                  [DEPRECATED]
│   ├── recommendation/           [ACTIVE]
│   ├── runtime/                  [DEPRECATED]
│   ├── security/                 [ACTIVE]
│   ├── session/                  [ACTIVE]
│   ├── tests/                    [ACTIVE]
│   └── verifier/                 [DEPRECATED]
```
