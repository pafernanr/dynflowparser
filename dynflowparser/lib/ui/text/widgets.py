"""Custom Textual widgets for Dynflow TUI."""
import json
from rich.table import Table
from rich.text import Text
from textual.containers import VerticalScroll
from textual.widgets import DataTable
from textual.widgets import Static

from dynflowparser.lib.ui.common import ActionHierarchy


class HeaderSeparator(Static):
    """Orange separator line below header."""

    def __init__(self, version: str = "0", **kwargs):
        """Initialize header separator.

        Args:
            version: Version string
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.version = version.strip() if version else "0"

    def render(self) -> Text:
        """Render the separator line with version on the right.

        Returns:
            Text: Orange horizontal line with version
        """
        # Get terminal width, subtract padding (2 chars for 0 1 padding)
        try:
            width = self.app.size.width - 2 if hasattr(self, 'app') else 118
        except:
            width = 118

        # Build: ─────── {version} ──
        # Format: dashes + space + version + space + 2 end dashes
        version_text = f" {self.version} "
        end_dashes = "──"
        remaining = width - len(version_text) - len(end_dashes)
        if remaining < 0:
            remaining = 0

        text = Text()
        text.append("─" * remaining, style="bold #EE7D42")
        text.append(version_text, style="dim #EE7D42")  # Lighter color
        text.append(end_dashes, style="bold #EE7D42")
        return text


class HostDetailsHeader(Static):
    """Display host details header similar to HTML output."""

    def __init__(self, sos_info):
        """Initialize host details header.

        Args:
            sos_info: Dictionary with system information
        """
        super().__init__()
        self.sos_info = sos_info

    def render(self) -> str:
        """Render the host information.

        Returns:
            str: Formatted host information
        """
        hostname = self.sos_info.get('hostname', 'N/A')
        satversion = self.sos_info.get('satversion', 'N/A')
        timezone = self.sos_info.get('timezone', 'N/A')
        tuning = self.sos_info.get('tuning', 'N/A').strip()
        cpu = self.sos_info.get('cpu', 'N/A')
        ram = self.sos_info.get('ram', 'N/A')

        return (
            f"[cyan]Host:[/] {hostname} | "
            f"[cyan]Ver:[/] {satversion} | "
            f"[cyan]TZ:[/] {timezone} | "
            f"[cyan]Tuning:[/] {tuning} | "
            f"[cyan]CPU:[/] {cpu} | "
            f"[cyan]RAM:[/] {ram}"
        )


class StatsPanel(Static):
    """Panel showing Top Dynflow Steps and Top Pulp Tasks."""

    def __init__(self, db, conf, **kwargs):
        """Initialize stats panel.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.db = db
        self.conf = conf

    def on_mount(self) -> None:
        """Load and display stats when mounted."""
        self.update_stats()

    def update_stats(self) -> None:
        """Update the stats display."""
        from rich.console import Group
        from dynflowparser.lib.util import Util

        util = Util('W')

        # Get top Dynflow steps
        dynflow_query = """
            SELECT SUM(execution_time), COUNT(s.id), s.action_class
            FROM steps s
            GROUP BY s.action_class
            ORDER BY SUM(execution_time) DESC
            LIMIT 5
        """
        dynflow_stats = self.db.query(dynflow_query)

        # Create Rich table for Dynflow
        dynflow_table = Table(
            title="[bold]Top Dynflow[/]",
            show_header=True,
            header_style="bold cyan",
            expand=False,
            box=None
        )
        dynflow_table.add_column("Exectime", justify="right", style="cyan", no_wrap=True)
        dynflow_table.add_column("Steps", justify="right", no_wrap=True)
        dynflow_table.add_column("Label", style="dim", no_wrap=True, overflow="ellipsis")

        for row in dynflow_stats:
            exec_time = f"{float(row[0]):.0f}" if row[0] else "0"
            steps = str(row[1]) if row[1] else "0"
            label = str(row[2]) if row[2] else "N/A"
            dynflow_table.add_row(exec_time, steps, label)

        # Get Pulp data from all action outputs
        pulp_stats = {}
        actions_query = "SELECT a.output FROM actions a"
        actions = self.db.query(actions_query)

        for action in actions:
            output = action[0]
            if output:
                try:
                    data = json.loads(output)
                    if 'pulp_tasks' in data:
                        for task in data['pulp_tasks']:
                            task_name = task.get('name', 'Unknown')
                            finished = util.date_from_string(task['finished_at'])
                            created = util.date_from_string(task['pulp_created'])
                            exec_time = (finished - created).total_seconds()

                            if task_name not in pulp_stats:
                                pulp_stats[task_name] = [0, 0]
                            pulp_stats[task_name][0] += exec_time
                            pulp_stats[task_name][1] += 1
                except Exception:
                    pass

        # Create Pulp table
        pulp_table = Table(
            title="[bold]Top Pulp[/]",
            show_header=True,
            header_style="bold cyan",
            expand=False,
            box=None
        )
        pulp_table.add_column("Exectime", justify="right", style="cyan", no_wrap=True)
        pulp_table.add_column("Count", justify="right", no_wrap=True)
        pulp_table.add_column("Name", style="dim", no_wrap=True, overflow="ellipsis")

        # Sort and show top 5 Pulp tasks
        if pulp_stats:
            sorted_pulp = sorted(
                pulp_stats.items(),
                key=lambda x: x[1][0],
                reverse=True
            )[:5]

            for task_name, (exec_time, count) in sorted_pulp:
                pulp_table.add_row(
                    f"{exec_time:.0f}",
                    str(count),
                    task_name
                )
        else:
            pulp_table.add_row("-", "-", "No Pulp data")

        # Combine both tables
        group = Group(dynflow_table, "", pulp_table)
        self.update(group)


class TasksDataTable(DataTable):
    """DataTable widget for displaying tasks with parent/child hierarchy."""

    def __init__(self, db, conf, **kwargs):
        """Initialize tasks data table.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            **kwargs: Additional keyword arguments for DataTable
        """
        super().__init__(**kwargs)
        self.db = db
        self.conf = conf
        self.cursor_type = "row"
        self.zebra_stripes = True
        # Store mapping of row keys to plan UUIDs for navigation
        self.row_to_plan = {}
        # Store ordered list of row keys
        self.row_keys = []
        # Track expanded parent tasks
        self.expanded_parents = set()
        # Store all parent and child task data
        self.parent_tasks = []
        self.children_by_parent = {}

    def on_mount(self) -> None:
        """Load and display tasks data when widget is mounted."""
        # Add columns matching HTML interface order
        self.add_column("Task Label", key="label", width=50)
        self.add_column("Task ID", key="task_id", width=38)
        self.add_column("Started At", key="started", width=20)
        self.add_column("Ended At", key="ended", width=20)
        self.add_column("State", key="state", width=12)
        self.add_column("Result", key="result", width=12)

        # Load task data
        self._load_tasks()

    def _load_tasks(self) -> None:
        """Load tasks from database."""
        # Fetch tasks data
        where = "" if self.conf.args.showall else " AND t.result != 'success'"

        # Fetch parent tasks
        parent_query = (
            "SELECT t.parent_task_id, t.id, t.external_id,"
            " t.label, t.state, t.result, t.started_at,"
            " t.ended_at, t.action, p.state, p.result"
            " FROM tasks t"
            " LEFT JOIN plans p ON t.external_id=p.uuid"
            " WHERE t.parent_task_id=''"
            + where
            + " GROUP BY t.id"
            " ORDER BY t.started_at DESC"
        )
        self.parent_tasks = self.db.query(parent_query)

        # Fetch child tasks
        child_query = (
            "SELECT t.parent_task_id, t.id, t.external_id,"
            " t.label, t.state, t.result, t.started_at,"
            " t.ended_at, t.action"
            " FROM tasks t"
            " LEFT JOIN plans p ON t.external_id=p.uuid"
            " WHERE t.parent_task_id!=''"
            + where
            + " ORDER BY t.started_at ASC"
        )
        child_tasks_raw = self.db.query(child_query)

        # Group children by parent task ID (convert to string for consistency)
        for child in child_tasks_raw:
            parent_id = str(child[0]) if child[0] else ""
            if parent_id and parent_id not in self.children_by_parent:
                self.children_by_parent[parent_id] = []
            if parent_id:
                self.children_by_parent[parent_id].append(child)

        # Initially expand all parents (default behavior)
        for parent in self.parent_tasks:
            parent_id = str(parent[1]) if parent[1] else ""
            if parent_id in self.children_by_parent:
                self.expanded_parents.add(parent_id)

        # Render the table
        self._render_table()

    def _render_table(self) -> None:
        """Render all tasks based on expanded state."""
        # Clear current rows
        self.clear()
        self.row_keys.clear()
        self.row_to_plan.clear()

        # Add rows: parents and their children if expanded
        for parent in self.parent_tasks:
            parent_id = str(parent[1]) if parent[1] else ""
            has_children = parent_id in self.children_by_parent

            # Add parent task
            self._add_task_row(parent, is_child=False, has_children=has_children)

            # Add child tasks if expanded
            if parent_id in self.expanded_parents and has_children:
                for child in self.children_by_parent[parent_id]:
                    self._add_task_row(child, is_child=True)

    def _add_task_row(self, row, is_child=False, has_children=False):
        """Add a task row to the table.

        Args:
            row: Database row with task data
            is_child: If True, indent to show as child task
            has_children: If True, show expand/collapse indicator
        """
        task_id = str(row[1]) if row[1] else ""
        plan_uuid = str(row[2])[:36] if row[2] else ""
        label = str(row[3]) if row[3] else ""
        state = str(row[4]) if row[4] else ""
        result = str(row[5]) if row[5] else ""
        started = str(row[6])[:-7] if row[6] and len(str(row[6])) > 7 else str(row[6])
        ended = str(row[7])[:-7] if row[7] and len(str(row[7])) > 7 else str(row[7])
        action = str(row[8]) if row[8] else ""

        # Format label column (just the label)
        if is_child:
            label_text = Text()
            label_text.append("  └─ ", style="dim")
            label_text.append(label if label else "")
        else:
            label_text = Text()
            # Add expand/collapse indicator for parents with children
            if has_children:
                if task_id in self.expanded_parents:
                    label_text.append("▼ ", style="dim")
                else:
                    label_text.append("▶ ", style="dim")
            label_text.append(label if label else "", style="bold")

        # Format task ID column (just the task ID)
        task_id_text = Text(task_id, style="cyan")

        # Format timestamps (remove microseconds)
        started_text = started if started else ""
        ended_text = ended if ended else ""

        # Color-code state
        if state == "stopped":
            state_text = Text(state, style="red")
        elif state == "running":
            state_text = Text(state, style="cyan")
        elif state == "paused":
            state_text = Text(state, style="yellow")
        else:
            state_text = Text(state)

        # Color-code result
        if result == "error":
            result_text = Text(result, style="bold red")
        elif result == "warning":
            result_text = Text(result, style="bold yellow")
        elif result == "success":
            result_text = Text(result, style="bold green")
        else:
            result_text = Text(result)

        # Add row
        row_key = f"task_{task_id}"
        self.add_row(
            label_text,
            task_id_text,
            started_text,
            ended_text,
            state_text,
            result_text,
            key=row_key
        )

        # Store row key in ordered list
        self.row_keys.append(row_key)

        # Store plan UUID for navigation (for both parent and child tasks)
        # Every task has actions, so all should be navigable
        if plan_uuid:
            self.row_to_plan[row_key] = plan_uuid

        # Store task_id for parent tasks (for expand/collapse)
        if not is_child:
            if not hasattr(self, 'row_to_task_id'):
                self.row_to_task_id = {}
            self.row_to_task_id[row_key] = task_id

    def expand_task(self) -> None:
        """Expand current parent task to show children."""
        if self.cursor_row is None or self.cursor_row >= len(self.row_keys):
            return

        row_key = self.row_keys[self.cursor_row]

        # Only expand parent tasks
        if not hasattr(self, 'row_to_task_id') or row_key not in self.row_to_task_id:
            return

        task_id = self.row_to_task_id[row_key]

        # Check if this task has children
        if task_id not in self.children_by_parent:
            return

        # Save cursor position
        saved_cursor = self.cursor_row

        # Expand the parent
        self.expanded_parents.add(task_id)

        # Re-render table
        self._render_table()

        # Restore cursor position
        if saved_cursor < len(self.row_keys):
            self.move_cursor(row=saved_cursor, column=0)

    def collapse_task(self) -> None:
        """Collapse current parent task to hide children."""
        if self.cursor_row is None or self.cursor_row >= len(self.row_keys):
            return

        row_key = self.row_keys[self.cursor_row]

        # Only collapse parent tasks
        if not hasattr(self, 'row_to_task_id') or row_key not in self.row_to_task_id:
            return

        task_id = self.row_to_task_id[row_key]

        # Check if this task has children
        if task_id not in self.children_by_parent:
            return

        # Save cursor position
        saved_cursor = self.cursor_row

        # Collapse the parent
        self.expanded_parents.discard(task_id)

        # Re-render table
        self._render_table()

        # Restore cursor position
        if saved_cursor < len(self.row_keys):
            self.move_cursor(row=saved_cursor, column=0)


class ActionsDataTable(DataTable):
    """DataTable widget for displaying actions for a specific plan."""

    def __init__(self, db, conf, plan_uuid=None, **kwargs):
        """Initialize actions data table.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            plan_uuid: Optional plan UUID to filter actions
            **kwargs: Additional keyword arguments for DataTable
        """
        super().__init__(**kwargs)
        self.db = db
        self.conf = conf
        self.plan_uuid = plan_uuid
        self.cursor_type = "row"
        self.zebra_stripes = True

    def on_mount(self) -> None:
        """Load and display actions data when widget is mounted."""
        # Add columns
        self.add_column("Action ID", key="action_id", width=10)
        self.add_column("Action Class", key="action_class", width=60)
        self.add_column("Result", key="result", width=12)
        self.add_column("Started", key="started", width=20)
        self.add_column("Ended", key="ended", width=20)
        self.add_column("Exec Time", key="exec_time", width=12)

        # Build query based on whether we're filtering by plan UUID
        if self.plan_uuid:
            actions_query = (
                "SELECT s.action_id, s.action_class, p.result, "
                "MIN(s.started_at), MAX(s.ended_at), "
                "SUM(s.execution_time) "
                "FROM steps s "
                "LEFT JOIN plans p ON s.execution_plan_uuid = p.uuid "
                "WHERE s.execution_plan_uuid = ? "
                "GROUP BY s.action_id "
                "ORDER BY s.action_id"
            )
            rows = self.db.query(actions_query, (self.plan_uuid,))
        else:
            actions_query = (
                "SELECT s.action_id, s.action_class, p.result, "
                "MIN(s.started_at), MAX(s.ended_at), "
                "SUM(s.execution_time) "
                "FROM steps s "
                "LEFT JOIN plans p ON s.execution_plan_uuid = p.uuid "
                "GROUP BY s.execution_plan_uuid, s.action_id "
                "ORDER BY MIN(s.started_at) DESC "
                "LIMIT 1000"
            )
            rows = self.db.query(actions_query)

        # Add rows with color coding
        for row in rows:
            action_id = str(row[0])[:10] if row[0] else ""
            action_class = str(row[1])[:60] if row[1] else ""
            result = str(row[2])[:12] if row[2] else ""
            started = str(row[3])[:20] if row[3] else ""
            ended = str(row[4])[:20] if row[4] else ""
            exec_time = f"{row[5]:.2f}s" if row[5] else "0.00s"

            # Skip successful if not showing all
            if not self.conf.args.showall and result == "success":
                continue

            # Color-code result
            if result == "error":
                result_text = Text(result, style="bold red")
            elif result == "warning":
                result_text = Text(result, style="bold yellow")
            elif result == "success":
                result_text = Text(result, style="bold green")
            else:
                result_text = Text(result)

            self.add_row(
                action_id,
                action_class,
                result_text,
                started,
                ended,
                exec_time,
                key=f"action_{action_id}"
            )


class ActionDetailsHeader(Static):
    """Display action details header (Task, Label, ID, Caller, Plan)."""

    def __init__(self, db, plan_uuid, **kwargs):
        """Initialize action details header.

        Args:
            db: OutputSQLite database instance
            plan_uuid: The execution plan UUID
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.db = db
        self.plan_uuid = plan_uuid

    def on_mount(self) -> None:
        """Load and display action details when mounted."""
        # Query to get action details
        query = """
            SELECT p.label, t.action, t.id, a.caller_execution_plan_id
            FROM plans p
            LEFT JOIN tasks t ON p.uuid = t.external_id
            LEFT JOIN actions a ON p.uuid = a.execution_plan_uuid
            WHERE p.uuid = ?
            LIMIT 1
        """
        result = self.db.query(query, (self.plan_uuid,))

        if result and len(result) > 0:
            row = result[0]
            label = str(row[0]) if row[0] else "N/A"
            task = str(row[1]) if row[1] else "N/A"
            task_id = str(row[2]) if row[2] else "N/A"
            caller = str(row[3]) if row[3] else None
        else:
            label = "N/A"
            task = "N/A"
            task_id = "N/A"
            caller = None

        # Build multi-line header using Rich Text (auto-wraps)
        header = Text()

        header.append("Task: ", style="cyan bold")
        header.append(task)
        header.append(" | ")

        header.append("Label: ", style="cyan bold")
        header.append(label)
        header.append(" | ")

        header.append("ID: ", style="cyan bold")
        header.append(str(task_id))

        if caller:
            header.append(" | ")
            header.append("Caller: ", style="cyan bold")
            header.append(caller)

        header.append(" | ")
        header.append("Plan: ", style="cyan bold")
        header.append(self.plan_uuid)

        self.update(header)


class ActionStatsPanel(Static):
    """Panel showing Top Dynflow and Pulp stats for a specific plan."""

    def __init__(self, db, conf, plan_uuid, **kwargs):
        """Initialize action stats panel.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            plan_uuid: The execution plan UUID
            **kwargs: Additional keyword arguments
        """
        super().__init__(**kwargs)
        self.db = db
        self.conf = conf
        self.plan_uuid = plan_uuid

    def on_mount(self) -> None:
        """Load and display stats when mounted."""
        self.update_stats()

    def update_stats(self) -> None:
        """Update the stats display."""
        from rich.console import Group
        from dynflowparser.lib.util import Util

        util = Util('W')

        # Get top Dynflow steps for this plan
        dynflow_query = """
            SELECT SUM(execution_time), COUNT(s.id), s.action_class
            FROM steps s
            WHERE s.execution_plan_uuid = ?
            GROUP BY s.action_class
            ORDER BY SUM(execution_time) DESC
            LIMIT 5
        """
        dynflow_stats = self.db.query(dynflow_query, (self.plan_uuid,))

        # Create Rich table for Dynflow
        dynflow_table = Table(
            title="[bold]Top Dynflow[/]",
            show_header=True,
            header_style="bold cyan",
            expand=False,
            box=None
        )
        dynflow_table.add_column("Exectime", justify="right", style="cyan", no_wrap=True)
        dynflow_table.add_column("Steps", justify="right", no_wrap=True)
        dynflow_table.add_column("Label", style="dim", no_wrap=True, overflow="ellipsis")

        for row in dynflow_stats:
            exec_time = f"{float(row[0]):.0f}" if row[0] else "0"
            steps = str(row[1]) if row[1] else "0"
            label = str(row[2]) if row[2] else "N/A"
            dynflow_table.add_row(exec_time, steps, label)

        # Get Pulp data from action outputs
        pulp_stats = {}
        actions_query = """
            SELECT a.output
            FROM actions a
            WHERE a.execution_plan_uuid = ?
        """
        actions = self.db.query(actions_query, (self.plan_uuid,))

        for action in actions:
            output = action[0]
            if output:
                try:
                    data = json.loads(output)
                    if 'pulp_tasks' in data:
                        for task in data['pulp_tasks']:
                            task_name = task.get('name', 'Unknown')
                            finished = util.date_from_string(task['finished_at'])
                            created = util.date_from_string(task['pulp_created'])
                            exec_time = (finished - created).total_seconds()

                            if task_name not in pulp_stats:
                                pulp_stats[task_name] = [0, 0]
                            pulp_stats[task_name][0] += exec_time
                            pulp_stats[task_name][1] += 1
                except Exception:
                    pass

        # Create Pulp table
        pulp_table = Table(
            title="[bold]Top Pulp[/]",
            show_header=True,
            header_style="bold cyan",
            expand=False,
            box=None
        )
        pulp_table.add_column("Exectime", justify="right", style="cyan", no_wrap=True)
        pulp_table.add_column("Count", justify="right", no_wrap=True)
        pulp_table.add_column("Name", style="dim", no_wrap=True, overflow="ellipsis")

        # Sort and show top 5 Pulp tasks
        if pulp_stats:
            sorted_pulp = sorted(
                pulp_stats.items(),
                key=lambda x: x[1][0],
                reverse=True
            )[:5]

            for task_name, (exec_time, count) in sorted_pulp:
                pulp_table.add_row(
                    f"{exec_time:.0f}",
                    str(count),
                    task_name
                )
        else:
            pulp_table.add_row("-", "-", "No Pulp data")

        # Combine both tables
        group = Group(dynflow_table, "", pulp_table)
        self.update(group)


class ActionsTreeTable(DataTable):
    """Tree-style table for displaying actions and their steps."""

    def __init__(self, db, conf, plan_uuid=None, **kwargs):
        """Initialize actions tree table.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
            plan_uuid: Plan UUID to filter actions
            **kwargs: Additional keyword arguments for DataTable
        """
        super().__init__(**kwargs)
        self.db = db
        self.conf = conf
        self.plan_uuid = plan_uuid
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.show_cursor = True
        # Track expanded rows and details
        self.row_keys = []
        self.row_data = {}  # Store full row data for detail display
        self.expanded_actions = set()  # Track which actions are expanded
        self.action_steps = {}  # Map action_id to list of step keys
        self.step_rows = {}  # Map step key to row index

    def on_mount(self) -> None:
        """Load and display actions/steps when mounted."""
        # Columns matching HTML: Action/Step, Started, Ended, Real Time,
        # Exec Time, Status
        self.add_column("Action / Step", key="action", width=60)
        self.add_column("Started At", key="started", width=20)
        self.add_column("Ended At", key="ended", width=20)
        self.add_column("Real Time", key="real_time", width=12)
        self.add_column("Exec Time", key="exec_time", width=12)
        self.add_column("Status", key="status", width=12)

        # Fetch actions with steps
        self._load_actions()

    def _render_table(self) -> None:
        """Render all actions and expanded steps in hierarchical order."""
        # Clear current rows
        self.clear()
        self.row_keys.clear()
        self.row_data.clear()

        # Render root actions recursively
        for action in self.root_actions:
            self._render_action_tree(action, depth=0)

    def _load_actions(self) -> None:
        """Load actions and steps from database."""
        # Query all actions for this plan (including caller_action_id for hierarchy)
        actions_query = """
            SELECT a.id, a.execution_plan_uuid, a.caller_action_id,
                   a.run_step_id, a.class, a.data, a.input, a.output,
                   p.result, p.label,
                   a.caller_execution_plan_id
            FROM actions a
            LEFT JOIN plans p ON a.execution_plan_uuid = p.uuid
            WHERE a.execution_plan_uuid = ?
            ORDER BY a.id
        """
        actions_raw = self.db.query(actions_query, (self.plan_uuid,))

        # Build action hierarchy using shared code
        self.root_actions, self.child_actions, self.actions_by_id = (
            ActionHierarchy.build_hierarchy(actions_raw)
        )

        # Query steps for actions
        steps_query = """
            SELECT * FROM steps
            WHERE execution_plan_uuid = ?
            ORDER BY action_id, id
        """
        all_steps = self.db.query(steps_query, (self.plan_uuid,))

        # Group steps by action_id
        self.steps_by_action = {}
        for step in all_steps:
            action_id = step[2]  # action_id is at index 2
            if action_id not in self.steps_by_action:
                self.steps_by_action[action_id] = []
            self.steps_by_action[action_id].append(step)

        # Store which actions have steps
        for action_id in self.actions_by_id:
            if action_id in self.steps_by_action:
                self.action_steps[action_id] = self.steps_by_action[action_id]

        # Auto-expand actions with non-success states
        # This includes actions where the action itself OR any descendant has issues
        self._auto_expand_non_success()

        # Render the table
        self._render_table()

    def _auto_expand_non_success(self):
        """Auto-expand actions that have non-success states.

        Simple approach:
        - If an action status is not "success": expand all parents up to root
        - If a step status is not "success": expand all parents up to root
        - Stop iterating when finding a parent that's already expanded
        """
        actions_to_expand = set()

        # Build parent map (reverse of child_actions)
        action_to_parent = {}
        for parent_id, children in self.child_actions.items():
            for child_action in children:
                child_id = child_action[0]
                action_to_parent[child_id] = parent_id

        def expand_all_parents(action_id):
            """Add action and all its parents to expansion set.

            Stops when finding a parent already in the expansion set.
            """
            current = action_id
            visited = set()
            while True:
                if current in visited:
                    break
                visited.add(current)

                # If already expanded, stop iterating
                if current in actions_to_expand:
                    break

                actions_to_expand.add(current)

                if current not in action_to_parent:
                    break
                current = action_to_parent[current]

        # 1. Find actions with non-success status
        for action_id, action in self.actions_by_id.items():
            # Action state is at index 10
            action_state = str(action[10]).lower() if action[10] else ""
            if action_state and action_state != "success":
                expand_all_parents(action_id)

        # 2. Find actions with steps that have non-success status
        for action_id, steps in self.steps_by_action.items():
            for step in steps:
                # Step state is at index 3
                step_state = str(step[3]).lower() if step[3] else ""
                if step_state and step_state != "success":
                    expand_all_parents(action_id)
                    break  # Only need one non-success step

        self.expanded_actions = actions_to_expand

    def _render_action_tree(self, action, depth=0) -> None:
        """Recursively render an action and its children/steps.

        Args:
            action: Action data tuple
            depth: Nesting depth (0 for root)
        """
        action_id = action[0]
        has_steps = action_id in self.action_steps
        has_children = action_id in self.child_actions

        # Add the action row
        self._add_action_row(action, has_steps=has_steps, has_children=has_children, depth=depth)

        # If expanded, add steps and child actions
        if action_id in self.expanded_actions:
            # Add steps first
            if has_steps:
                # Get run_step_id for step labeling
                run_step_id = action[3] if action[3] else action_id
                for step in self.action_steps[action_id]:
                    self._add_step_row(action_id, run_step_id, step, depth=depth + 1)

            # Then add child actions recursively
            if has_children:
                for child_action in self.child_actions[action_id]:
                    self._render_action_tree(child_action, depth=depth + 1)

    def _add_action_row(self, action, has_steps=False, has_children=False, depth=0) -> None:
        """Add an action row.

        Args:
            action: Action data tuple
            has_steps: Whether this action has steps
            has_children: Whether this action has child actions
            depth: Nesting depth for indentation
        """
        action_id = action[0]
        action_class = str(action[4]) if action[4] else ""
        run_step_id = action[3]  # run_step_id is at index 3

        # Get aggregated step data for this action
        started, ended, real_time, exec_time, state = self._get_action_aggregated_data(action_id)

        # Calculate indentation
        indent = "  " * depth

        # Format action text with expand indicator and ID
        action_text = Text()
        action_text.append(indent)

        # Show expand/collapse indicator if action has steps or children
        if has_steps or has_children:
            if action_id in self.expanded_actions:
                action_text.append("▼ ", style="dim")  # Expanded
            else:
                action_text.append("▶ ", style="dim")  # Collapsed

        action_text.append(f"{run_step_id}: ", style="dim")
        action_text.append(action_class, style="bold")

        # Add alert indicator if action has output data
        output = action[7] if len(action) > 7 else ""
        if output and output != "{}":
            action_text.append(" !", style="bold red")

        # Color-code status
        if state == "error":
            status_text = Text(state, style="bold red")
        elif state == "warning":
            status_text = Text(state, style="bold yellow")
        elif state == "success":
            status_text = Text(state, style="bold green")
        else:
            status_text = Text(state)

        row_key = f"action_{action_id}"
        self.add_row(
            action_text,
            started,
            ended,
            real_time.rjust(12),  # Right-align in 12-char column
            exec_time.rjust(12),  # Right-align in 12-char column
            status_text,
            key=row_key
        )
        self.row_keys.append(row_key)
        self.row_data[row_key] = {
            'type': 'action',
            'data': action,
            'action_id': action_id,
            'has_steps': has_steps,
            'has_children': has_children
        }

    def _get_action_aggregated_data(self, action_id):
        """Get aggregated step data for an action.

        Args:
            action_id: The action ID

        Returns:
            Tuple of (started, ended, real_time, exec_time, state)
        """
        if action_id not in self.steps_by_action:
            return "", "", "0.00", "0.00", ""

        steps = self.steps_by_action[action_id]

        # Aggregate data from steps
        started_times = [step[4] for step in steps if step[4]]
        ended_times = [step[5] for step in steps if step[5]]
        real_times = [step[6] for step in steps if step[6]]
        exec_times = [step[7] for step in steps if step[7]]
        states = [step[3] for step in steps if step[3]]

        started = str(min(started_times))[:-7] if started_times else ""
        ended = str(max(ended_times))[:-7] if ended_times else ""
        real_time = f"{sum(real_times):.2f}" if real_times else "0.00"
        exec_time = f"{sum(exec_times):.2f}" if exec_times else "0.00"

        # Get the "worst" state (error > warning > skipped > pending > success)
        state_priority = {'error': 0, 'warning': 1, 'skipped': 2, 'pending': 3, 'suspended': 4, 'success': 5}
        state = min(states, key=lambda s: state_priority.get(str(s).lower(), 999)) if states else ""

        return started, ended, real_time, exec_time, state

    def _add_step_row(self, action_id, run_step_id, step, depth=0) -> None:
        """Add a step row under an action.

        Args:
            action_id: Parent action ID (for row key)
            run_step_id: Run step ID to display (e.g., 29)
            step: Step data tuple
            depth: Nesting depth for indentation
        """
        step_id = step[1]
        action_class = str(step[10]) if step[10] else ""
        # Format timestamps - remove microseconds if present
        started_raw = str(step[4]) if step[4] else ""
        started = started_raw[:-7] if started_raw and len(started_raw) > 19 else started_raw
        ended_raw = str(step[5]) if step[5] else ""
        ended = ended_raw[:-7] if ended_raw and len(ended_raw) > 19 else ended_raw
        real_time = f"{step[6]:.2f}" if step[6] else "0.00"
        exec_time = f"{step[7]:.2f}" if step[7] else "0.00"
        state = str(step[3]) if step[3] else ""

        # Calculate indentation (steps are one level deeper than their action)
        indent = "  " * depth

        # Format step text (indented)
        step_text = Text()
        step_text.append(indent)
        step_text.append("  └─ ", style="dim")
        step_text.append(f"{run_step_id}.{step_id}: ", style="dim cyan")
        step_text.append(action_class)

        # Add alert indicator if step has error content
        error = step[13] if len(step) > 13 else ""
        if error:
            step_text.append(" !", style="bold red")

        # Color-code status
        if state == "error":
            status_text = Text(state, style="bold red")
        elif state == "warning":
            status_text = Text(state, style="bold yellow")
        elif state == "success":
            status_text = Text(state, style="bold green")
        else:
            status_text = Text(state)

        row_key = f"step_{action_id}_{step_id}"
        self.add_row(
            step_text,
            started,
            ended,
            real_time.rjust(12),  # Right-align in 12-char column
            exec_time.rjust(12),  # Right-align in 12-char column
            status_text,
            key=row_key
        )
        self.row_keys.append(row_key)
        self.row_data[row_key] = {
            'type': 'step',
            'data': step
        }

    def on_data_table_row_highlighted(self, event) -> None:
        """Handle row cursor changes to update bindings.

        Args:
            event: Row highlighted event
        """
        if self.cursor_row is None or self.cursor_row >= len(self.row_keys):
            # No row selected
            if hasattr(self.screen, 'update_bindings'):
                self.screen.update_bindings(None)
            return

        row_key = self.row_keys[self.cursor_row]
        if row_key in self.row_data:
            row_type = self.row_data[row_key]['type']
            # Update bindings in parent screen
            if hasattr(self.screen, 'update_bindings'):
                self.screen.update_bindings(row_type)

    def expand_action(self) -> None:
        """Expand current action to show steps and child actions."""
        if self.cursor_row is None or self.cursor_row >= len(self.row_keys):
            return

        row_key = self.row_keys[self.cursor_row]
        if row_key not in self.row_data:
            return

        row_info = self.row_data[row_key]

        # Only expand actions, not steps
        if row_info['type'] != 'action':
            return

        # Must have steps or children to expand
        if not row_info.get('has_steps') and not row_info.get('has_children'):
            return

        action_id = row_info['action_id']

        # Save cursor position
        saved_cursor = self.cursor_row

        # Expand the action
        self.expanded_actions.add(action_id)

        # Re-render entire table to show changes
        self._render_table()

        # Restore cursor position using move_cursor
        if saved_cursor < len(self.row_keys):
            self.move_cursor(row=saved_cursor, column=0)

    def collapse_action(self) -> None:
        """Collapse current action to hide steps and child actions."""
        if self.cursor_row is None or self.cursor_row >= len(self.row_keys):
            return

        row_key = self.row_keys[self.cursor_row]
        if row_key not in self.row_data:
            return

        row_info = self.row_data[row_key]

        # Only collapse actions, not steps
        if row_info['type'] != 'action':
            return

        # Must have steps or children to collapse
        if not row_info.get('has_steps') and not row_info.get('has_children'):
            return

        action_id = row_info['action_id']

        # Save cursor position
        saved_cursor = self.cursor_row

        # Collapse the action
        self.expanded_actions.discard(action_id)

        # Re-render entire table to show changes
        self._render_table()

        # Restore cursor position using move_cursor
        if saved_cursor < len(self.row_keys):
            self.move_cursor(row=saved_cursor, column=0)

    def toggle_detail(self, detail_type: str) -> None:
        """Toggle detail display for the current row.

        Args:
            detail_type: Type of detail to show (input/output/data/error)
        """
        if self.cursor_row is None or self.cursor_row >= len(self.row_keys):
            return

        row_key = self.row_keys[self.cursor_row]
        if row_key not in self.row_data:
            return

        row_info = self.row_data[row_key]
        row_type = row_info['type']
        action_data = row_info['data']

        # Get the appropriate data field based on type
        if row_type == 'action':
            # Action data indices: 0=id, 1=uuid, 2=caller_id, 3=run_step, 4=class,
            # 5=data, 6=input, 7=output, 8=result, 9=label, 10=caller_plan_id
            if detail_type == 'input':
                content = action_data[6] if len(action_data) > 6 else ""
                title = "Action Input"
            elif detail_type == 'output':
                content = action_data[7] if len(action_data) > 7 else ""
                title = "Action Output"
            elif detail_type == 'data':
                content = action_data[5] if len(action_data) > 5 else ""
                title = "Action Data"
            else:
                self.app.notify(f"{detail_type} not available for actions", severity="warning")
                return
        elif row_type == 'step':
            # Step data indices from steps table
            # 0=uuid, 1=id, 2=action_id, 3=state, 4=started, 5=ended, 6=real_time,
            # 7=exec_time, 8=progress_done, 9=progress_weight, 10=action_class,
            # 11=execution_plan_id, 12=queue, 13=error, 14=children, 15=data
            if detail_type == 'error':
                content = action_data[13] if len(action_data) > 13 else ""
                title = "Step Error"
            elif detail_type == 'queue':
                content = action_data[12] if len(action_data) > 12 else ""
                title = "Step Queue"
            elif detail_type == 'children':
                content = action_data[14] if len(action_data) > 14 else ""
                title = "Step Children"
            elif detail_type == 'data':
                content = action_data[15] if len(action_data) > 15 else ""
                title = "Step Data"
            else:
                self.app.notify(f"{detail_type} not available for steps", severity="warning")
                return
        else:
            return

        # Format the content
        if not content or content == '{}' or content == '':
            formatted_content = "[dim]No data[/dim]"
        else:
            # Try to pretty-print JSON
            import json
            try:
                parsed = json.loads(content)
                formatted_content = json.dumps(parsed, indent=2)
            except:
                formatted_content = str(content)

        # Show in modal
        from .app import DetailModal
        self.app.push_screen(DetailModal(title, formatted_content))


class DetailPanel(VerticalScroll):
    """Scrollable panel for displaying detailed information."""

    def __init__(self, **kwargs):
        """Initialize detail panel.

        Args:
            **kwargs: Additional keyword arguments for VerticalScroll
        """
        super().__init__(**kwargs)
        self.border_title = "Details"

    def display_json(self, json_data: str, title: str = "JSON Data") -> None:
        """Display formatted JSON data.

        Args:
            json_data: JSON string to display
            title: Title for the display
        """
        self.border_title = title

        try:
            # Parse and pretty-print JSON
            parsed = json.loads(json_data)
            formatted = json.dumps(parsed, indent=2)

            # Clear existing content and add new
            self.remove_children()
            self.mount(Static(formatted))

        except (json.JSONDecodeError, TypeError):
            # Display as plain text if not valid JSON
            self.remove_children()
            self.mount(Static(f"[yellow]{json_data}[/yellow]"))

    def display_text(self, text: str, title: str = "Details") -> None:
        """Display plain text.

        Args:
            text: Text to display
            title: Title for the display
        """
        self.border_title = title
        self.remove_children()
        self.mount(Static(text))

    def clear(self) -> None:
        """Clear the detail panel."""
        self.border_title = "Details"
        self.remove_children()
        self.mount(Static("[dim]Select an item to view details[/dim]"))
