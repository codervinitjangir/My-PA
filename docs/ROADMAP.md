# Roadmap

* **Phase 1: Foundation (Current)**
  - Decouple existing monolithic architecture.
  - Establish OS-level folder structure (`brain/`, `memory/`, `planner/`, etc.).
  - Set up Identity and Config schemas.
  - Document the transition path.

* **Phase 2: Memory**
  - Migrate from simple local text files to structured knowledge representation.
  - Build ingestion pipelines for JSON schemas (profiles).

* **Phase 3: Planner**
  - Replace the rule-based brain routing with a dynamic Planning agent.
  - Implement task breakdown and dependency graphing.

* **Phase 4: Agents**
  - Implement specialized agent roles (Coder, Researcher, Editor).
  - Connect the agents to the planner to allow multi-step workflows.

* **Phase 5: Device Control**
  - Build secure interface layers to control local OS functions.
  - Implement true browser automation (e.g., Playwright/Puppeteer).

* **Phase 6: Hardware**
  - Extend the ecosystem to external APIs (Smart Home, IoT).

* **Phase 7: Autonomy**
  - Introduce asynchronous background processing loops.
  - Allow J.A.R.V.I.S to wake up, execute scheduled complex tasks, and report back natively.
