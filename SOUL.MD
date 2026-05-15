# Project Guidelines (CLAUDE.md)

## Architecture & Coding Principles

### 1. No Dummy Data
- Strictly prohibited from using fake (dummy) data, placeholders, or hardcoded variables for simulation.
- Use real data source integrations or define complete data interfaces based on the actual database/API schema.
- If data is not yet available, implement functional data-fetching logic rather than simple mock returns.

### 2. Respect Data Flow
- Strictly adhere to unidirectional data flow.
- Maintain consistent state management: data must flow from the single source of truth to components without mid-stream mutations.
- Do not bypass established data paths within the application architecture.

### 3. No Fallback Logic
- Do not implement fallback logic or default values to mask data failures.
- The system must reflect its actual state; if data is empty or fails, do not display alternative UIs that hide the condition unless explicitly instructed.
- Focus on the flawless execution of the happy path.

### 4. No Error Handling (Root Cause Fix)
- Prohibited from wrapping code in `try-catch` blocks, `if (error)` checks, or other passive error-handling mechanisms to tolerate failure.
- If an error occurs, the primary focus is to identify the root cause and fix it permanently so the code executes successfully without gaps.
- The ultimate goal is "Zero-Error Code" through logical integrity, not through failure management.

### 5. Must Clean Code
- **Zero Dead Code:** Every line of code must be functional and actively used. Immediately remove unused variables, functions, imports, or unreachable logic.
- **No Redundancy (DRY):** Adhere strictly to the "Don't Repeat Yourself" principle. Eliminate logic duplication through proper abstraction.
- **Self-Documenting Code:** Prohibited from using comments or docstrings. Code intent must be crystal clear through precise naming of variables, functions, and classes.
- **Utility-Driven:** Every implementation must serve a direct purpose. Do not over-engineer or add "just-in-case" features.