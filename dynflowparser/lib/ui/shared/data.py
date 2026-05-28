"""Shared data handling and hierarchy building for UI implementations."""


class ActionHierarchy:
    """Build and manage action hierarchy based on caller_action_id."""

    @staticmethod
    def build_hierarchy(actions):
        """Build hierarchical action structure from flat list.

        Args:
            actions: List of action tuples/dicts with action data
                    Expected fields: id (index 0), caller_action_id (index 2)

        Returns:
            tuple: (root_actions, child_actions_map, actions_by_id)
                - root_actions: List of root action records
                - child_actions_map: Dict mapping parent_id -> [child actions]
                - actions_by_id: Dict mapping action_id -> action record
        """
        # First pass: index all actions by ID
        actions_by_id = {}
        for action in actions:
            action_id = action[0]  # action_id is at index 0
            actions_by_id[action_id] = action

        # Second pass: build parent-child relationships
        child_actions = {}  # Map parent_action_id -> [child_actions]
        root_actions = []
        processed_circular = set()

        for action in actions:
            action_id = action[0]
            caller_action_id = action[2]  # caller_action_id at index 2

            # Check if this is a root action
            if (caller_action_id is None or caller_action_id == '' or
                    caller_action_id == 0):
                # Explicit root (no caller)
                root_actions.append(action)
            elif caller_action_id not in actions_by_id:
                # Orphaned reference - caller doesn't exist in this plan
                root_actions.append(action)
            else:
                # Check for mutual reference (shouldn't happen per schema)
                caller_action = actions_by_id[caller_action_id]
                caller_of_caller = caller_action[2]

                if caller_of_caller == action_id:
                    # Mutual reference: A→B and B→A
                    # Lower ID wins as root, higher becomes its child
                    pair = tuple(sorted([action_id, caller_action_id]))
                    if pair not in processed_circular:
                        processed_circular.add(pair)
                        # Lower ID to roots regardless which encountered
                        lower_id, higher_id = pair
                        lower_action = actions_by_id[lower_id]
                        higher_action = actions_by_id[higher_id]

                        root_actions.append(lower_action)
                        if lower_id not in child_actions:
                            child_actions[lower_id] = []
                        child_actions[lower_id].append(higher_action)
                else:
                    # Normal parent-child relationship
                    if caller_action_id not in child_actions:
                        child_actions[caller_action_id] = []
                    child_actions[caller_action_id].append(action)

        return root_actions, child_actions, actions_by_id

    @staticmethod
    def flatten_with_depth(root_actions, child_actions):
        """Flatten hierarchical actions into list with depth information.

        Args:
            root_actions: List of root action records
            child_actions: Dict mapping parent_id -> [child actions]

        Returns:
            list: Actions in hierarchical order with depth appended
        """
        hierarchical = []
        visited = set()  # Track visited actions to prevent infinite recursion

        def add_action_tree(action, depth=0):
            """Recursively add action and its children."""
            action_id = action[0]

            # Prevent infinite recursion from circular references
            if action_id in visited:
                return
            visited.add(action_id)

            # Add depth info to action (append as new field)
            action_with_depth = list(action) + [depth]
            hierarchical.append(action_with_depth)

            # Add children recursively
            if action_id in child_actions:
                for child in child_actions[action_id]:
                    add_action_tree(child, depth + 1)

        # Add all root actions and their trees
        for root in root_actions:
            add_action_tree(root)

        return hierarchical


class DataProvider:
    """Common data queries for UI implementations."""

    def __init__(self, db):
        """Initialize data provider.

        Args:
            db: OutputSQLite database instance
        """
        self.db = db

    def get_actions_for_plan(self, plan_uuid):
        """Query all actions for a specific plan.

        Args:
            plan_uuid: The execution plan UUID

        Returns:
            list: Action records with hierarchy fields
        """
        query = """
            SELECT a.id, a.execution_plan_uuid, a.caller_action_id,
                   a.run_step_id, a.class, a.data, a.input, a.output,
                   p.result, p.label,
                   a.caller_execution_plan_id
            FROM actions a
            LEFT JOIN plans p ON a.execution_plan_uuid = p.uuid
            WHERE a.execution_plan_uuid = ?
            ORDER BY a.id
        """
        return self.db.query(query, (plan_uuid,))

    def get_steps_for_plan(self, plan_uuid):
        """Query all steps for a specific plan.

        Args:
            plan_uuid: The execution plan UUID

        Returns:
            dict: Steps grouped by action_id
        """
        query = """
            SELECT * FROM steps
            WHERE execution_plan_uuid = ?
            ORDER BY action_id, id
        """
        all_steps = self.db.query(query, (plan_uuid,))

        # Group by action_id
        steps_by_action = {}
        for step in all_steps:
            action_id = step[2]  # action_id at index 2
            if action_id not in steps_by_action:
                steps_by_action[action_id] = []
            steps_by_action[action_id].append(step)

        return steps_by_action
