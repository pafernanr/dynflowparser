# Dynflow Database Schema

This document describes the database schema used by dynflowparser to store and query Dynflow execution data.

## Tables

### tasks
Represents Dynflow tasks that users initiate.

**Key fields:**
- `id` - Task ID (primary identifier)
- `external_id` - Links to plan UUID (1:1 relationship)
- `parent_task_id` - Parent task ID (for child tasks)
- `action` - Task action name
- `label` - Task description
- `state` - Current state (running, stopped, paused)
- `result` - Execution result (success, error, warning)

### plans
Represents execution plans that orchestrate actions.

**Key fields:**
- `uuid` - Plan UUID (primary identifier)
- `label` - Plan description
- `state` - Current state
- `result` - Execution result
- `started_at`, `ended_at` - Timestamps
- `execution_time`, `real_time` - Performance metrics

### actions
Represents individual actions within an execution plan.

**Key fields:**
- `execution_plan_uuid` - Links to parent plan
- `id` - Action ID within the plan
- `caller_action_id` - Parent action ID (for action hierarchy)
- `run_step_id` - Step ID displayed in UI (e.g., 29, 19)
- `class` - Action class name
- `data`, `input`, `output` - Action payloads (JSON)

### steps
Represents execution steps within actions.

**Key fields:**
- `execution_plan_uuid` - Links to parent plan
- `action_id` - Links to parent action
- `id` - Step ID within the action
- `action_class` - Step class name
- `state` - Execution state (success, error, skipped, etc.)
- `started_at`, `ended_at` - Timestamps
- `execution_time`, `real_time` - Performance metrics
- `error`, `queue`, `children` - Step details (JSON)

## Hierarchy Relationships

### Task → Plan (1:1)
```
Task
  └─ Plan (via tasks.external_id = plans.uuid)
```

Every task is mapped to exactly one plan. There are no 1:N relationships.

**Example:**
```
Task ID: 803663b2-308c-49be-b0b5-4f4043587d83
  └─ Plan UUID: 82512462-a441-4fae-857c-91fd1832587c
```

### Plan → Actions (1:N)
```
Plan
  └─ Action 1 (root: caller_action_id = NULL/0)
  └─ Action 2 (root: caller_action_id = NULL/0)
  └─ Action N (root: caller_action_id = NULL/0)
```

Root actions have `caller_action_id` = NULL, empty, or 0.

### Action → Child Actions (1:N, recursive)
```
Action 1
  ├─ Action 2 (caller_action_id = 1)
  │   ├─ Action 3 (caller_action_id = 2)
  │   └─ Action 4 (caller_action_id = 2)
  └─ Action 5 (caller_action_id = 1)
```

Actions can have child actions via `caller_action_id` pointing to the parent action's ID.

**Important:** `caller_action_id` may reference an action ID that doesn't exist in the current plan (external reference). Such actions are treated as roots.

### Action → Steps (1:N)
```
Action 29
  ├─ Step 29.1 (action_id = 29, id = 1)
  ├─ Step 29.29 (action_id = 29, id = 29)
  └─ Step 29.30 (action_id = 29, id = 30)
```

Steps belong to their parent action via `action_id`.

## Complete Hierarchy Example

```
Task: 803663b2-308c-49be-b0b5-4f4043587d83
  └─ Plan: 82512462-a441-4fae-857c-91fd1832587c
      └─ Action 1 (run_step_id=29)
          ├─ Step 1.1
          ├─ Step 1.29
          ├─ Step 1.30
          └─ Action 2 (run_step_id=19, caller_action_id=1)
              ├─ Step 2.2
              ├─ Step 2.19
              ├─ Action 3 (run_step_id=4, caller_action_id=2)
              │   ├─ Step 3.3
              │   └─ Step 3.4
              └─ Action 4 (run_step_id=6, caller_action_id=2)
                  ├─ Step 4.5
                  ├─ Step 4.6
                  └─ Step 4.7
```

## Special Cases

### Auto-expansion of Non-success States

**Problem:** An action may show `state=success` but contain child actions or steps with non-success states (error, warning, skipped, pending, suspended).

**Solution:** The UI auto-expands actions where:
1. Any step has a non-success state, OR
2. Any descendant action (recursively) has non-success states

Additionally, the entire parent chain from root to the problematic action is expanded, making issues immediately visible without manual navigation.

**Example:**
```
Action 1 (success) - EXPANDED
  └─ Action 2 (success) - EXPANDED
      └─ Action 4 (skipped) - EXPANDED
          └─ Step 4.6 (skipped) ← Non-success state detected
```

Even though Actions 1 and 2 show success, they are auto-expanded because Action 4 → Step 4.6 has a skipped state.

**Note:** This behavior ensures users can quickly identify problems in deeply nested hierarchies without manually expanding every action.

### Circular References in Action Hierarchy

**Problem:** In rare cases, two actions may have mutual parent-child references, creating a circular relationship (A→B and B→A).

**Solution:** The hierarchy building logic detects circular references and resolves them deterministically:
1. The action with the **lower ID** becomes the root
2. The action with the **higher ID** becomes its child
3. A `processed_circular` set prevents duplicate processing

**Example:**
```
Action 1: caller_action_id = 2 (points to Action 2 as parent)
Action 2: caller_action_id = 1 (points to Action 1 as parent)

Resolved hierarchy:
Action 1 (root - lower ID)
  └─ Action 2 (child - higher ID)
```

**Implementation:** Both HTML and terminal UIs use shared code from `lib/ui/shared/data.py`:
- `ActionHierarchy.build_hierarchy()` detects and resolves circular references
- Cycle detection using `visited` sets prevents infinite recursion during rendering
- Jinja2 templates include additional cycle detection in recursive macros

**Note:** Circular references should not occur in normal Dynflow execution but are handled defensively to prevent UI crashes.
