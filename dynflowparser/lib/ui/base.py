"""Base classes for UI output implementations."""
from abc import ABC, abstractmethod


class BaseOutput(ABC):
    """Abstract base class for all output implementations (HTML, Text, etc.)."""

    def __init__(self, conf):
        """Initialize with configuration.

        Args:
            conf: Configuration object containing args and settings
        """
        self.conf = conf
        self.db = None  # Will be OutputSQLite instance

    @abstractmethod
    def write(self):
        """Main entry point - generate output.

        This method should implement the complete output generation logic.
        """
        pass

    @abstractmethod
    def write_tasks(self):
        """Render tasks/plans overview.

        This method should generate the tasks view specific to the output format.
        """
        pass

    @abstractmethod
    def write_actions(self):
        """Render actions and steps details.

        This method should generate the actions/steps view specific to the output format.
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        if self.db:
            self.db.close()


class BaseDataProvider:
    """Shared data access layer for all output implementations.

    This class encapsulates all database queries and data aggregation logic
    that is common across different output formats (HTML, Text, etc.).
    """

    def __init__(self, db, conf):
        """Initialize data provider.

        Args:
            db: OutputSQLite database instance
            conf: Configuration object
        """
        self.db = db
        self.conf = conf
        self.pulp_plans_exectime = {}
        self.pulp_total_exectime = {}
        self.pulp_total_rel_exectime = {}
        self.dynflow_plans_exectime = {}

    def get_tasks_data(self, show_all=False):
        """Fetch tasks data with parent/child relationships.

        Args:
            show_all: If True, include successful tasks. Otherwise only errors.

        Returns:
            dict: Dictionary mapping task IDs to lists of task rows
        """
        where = "" if show_all else " AND t.result != 'success'"

        # Get parent tasks
        parent_tasks = self.db.query(
            "SELECT t.parent_task_id, t.id, t.external_id,"
            + " t.label, t.state, t.result, t.started_at,"
            + " t.ended_at, t.action, p.state, p.result"
            + " FROM tasks t"
            + " LEFT JOIN plans p"
            + " ON t.external_id=p.uuid"
            + " WHERE t.parent_task_id=''"
            + where
            + " GROUP BY t.id"
            + " ORDER BY t.started_at DESC"
        )

        rowsdict = {}
        for t in parent_tasks:
            rowsdict[t[1]] = [t]

        # Get child tasks
        child_tasks = self.db.query(
            "SELECT t.parent_task_id, t.id, t.external_id,"
            + " t.label, t.state, t.result, t.started_at,"
            + " t.ended_at, t.action"
            + " FROM tasks t"
            + " LEFT JOIN plans p"
            + " ON t.external_id=p.uuid"
            + " WHERE t.parent_task_id!=''"
            + where
            + " ORDER BY t.started_at ASC"
        )

        for t in child_tasks:
            if t[0] in rowsdict.keys():
                rowsdict[t[0]].append(t)

        return rowsdict

    def get_tasks_flat_list(self, show_all=False):
        """Get flat list of tasks from hierarchical data.

        Args:
            show_all: If True, include successful tasks

        Returns:
            list: Flat list of task rows
        """
        rowsdict = self.get_tasks_data(show_all)
        rows = []
        for vs in rowsdict.values():
            if vs:
                for v in vs:
                    rows.append(v)
        return rows

    def get_dynflow_total_exectime(self):
        """Get top Dynflow steps by execution time.

        Returns:
            list: Query results with (sum_exec_time, count, action_class)
        """
        return self.db.query(
            """SELECT SUM(execution_time), COUNT(s.id), s.action_class
            FROM steps s
            GROUP BY s.action_class
            ORDER BY SUM(execution_time) DESC
            LIMIT 5
            """
        )

    def get_pulp_total_exectime_sorted(self):
        """Get top Pulp tasks by execution time.

        Returns:
            list: Sorted list of (task_name, exec_time_data) tuples
        """
        return sorted(
            self.pulp_total_exectime.items(),
            key=lambda item: item[1],
            reverse=True
        )[:5]

    def get_dynflow_plans_exectime(self, plan_uuid):
        """Get Dynflow execution times for a specific plan.

        Args:
            plan_uuid: Execution plan UUID

        Returns:
            list: Top 5 Dynflow actions for this plan
        """
        if plan_uuid not in self.dynflow_plans_exectime:
            return []

        return sorted(
            self.dynflow_plans_exectime[plan_uuid].items(),
            key=lambda item: item[1],
            reverse=True
        )[:5]

    def get_pulp_plans_exectime(self, plan_uuid):
        """Get Pulp execution times for a specific plan.

        Args:
            plan_uuid: Execution plan UUID

        Returns:
            list: Top 5 Pulp tasks for this plan
        """
        if plan_uuid not in self.pulp_plans_exectime:
            return []

        return sorted(
            self.pulp_plans_exectime[plan_uuid].items(),
            key=lambda item: item[1][0],
            reverse=True
        )[:5]
