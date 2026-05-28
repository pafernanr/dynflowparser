"""HTML output implementation for dynflowparser."""
import datetime
import html
import json
import os
import re
import time

from jinja2 import Environment
from jinja2 import FileSystemLoader

from dynflowparser.lib.outputsqlite import OutputSQLite
from dynflowparser.lib.ui.base import BaseOutput
from dynflowparser.lib.ui.common import ActionHierarchy
from dynflowparser.lib.util import ProgressBarFromFileLines
from dynflowparser.lib.util import Util


class HtmlOutput(BaseOutput):
    """HTML output generator using Jinja2 templates."""

    def __init__(self, conf):
        """Initialize HTML output.

        Args:
            conf: Configuration object with args and settings
        """
        super().__init__(conf)
        self.db = OutputSQLite(conf)
        self.pb = ProgressBarFromFileLines()
        self.util = Util(conf.args.debug)
        self.pulp_plans_exectime = {}
        self.pulp_total_exectime = {}
        self.pulp_total_rel_exectime = {}
        self.dynflow_plans_exectime = {}

        # Initialize Jinja2 Environment with new template path
        template_dir = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "templates"
        )
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=True  # Enable autoescape for security
        )

    def write(self):
        """Generate all HTML output files.

        Actions must be written first to compute execution time statistics
        that are used in the tasks overview.
        """
        self.write_actions()
        self.write_tasks()

    def dynflow_total_exectime(self):
        """Get top 5 Dynflow action classes by total execution time.

        Returns:
            list: Query results with (sum_time, count, action_class)
        """
        return self.db.query(
            """SELECT SUM(execution_time), COUNT(s.id), s.action_class
            FROM steps s
            GROUP BY s.action_class
            ORDER BY SUM(execution_time) DESC
            LIMIT 5
            """
        )

    def write_tasks(self):
        """Generate the main tasks overview HTML file (index.html)."""
        self.util.debug("I", "write_tasks")

        # Determine filter for successful vs all tasks
        where = "" if self.conf.args.showall else " AND t.result != 'success'"

        # Fetch parent tasks
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

        # Fetch child tasks
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

        # Flatten to list
        rows = []
        for vs in rowsdict.values():
            if vs:
                for v in vs:
                    rows.append(v)

        # Generate HTML
        outputfile = self.conf.args.output_path + "/index.html"
        context = {
            "rows": rows,
            "dynflow_total_exectime": self.dynflow_total_exectime(),
            "pulp_total_exectime": sorted(
                self.pulp_total_exectime.items(),
                key=lambda item: item[1],
                reverse=True
            )[:5]
        }
        self.write_report(context, "tasks.html", outputfile)

    def get_pulp_uuid(self, txt):
        """Extract UUID from Pulp task text.

        Args:
            txt: Text containing UUID

        Returns:
            str: Extracted UUID
        """
        uuid = re.search(
            r"[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+", txt
        )
        return uuid.group()

    def sum_pulp_total_exectime(self, name, started_at, finished_at, exectime):
        """Aggregate Pulp task execution times across all plans.

        Args:
            name: Pulp task name
            started_at: Task start datetime
            finished_at: Task finish datetime
            exectime: Execution time in seconds
        """
        try:
            self.pulp_total_exectime[name][0] += exectime
            self.pulp_total_exectime[name][1] += 1
            self.pulp_total_exectime[name][2] = finished_at
        except Exception:
            self.pulp_total_exectime[name] = [
                exectime,
                1,
                started_at,
                finished_at
            ]

    def sum_pulp_plans_exectime(self, puid, txt):
        """Parse and aggregate Pulp task times for a specific plan.

        Args:
            puid: Plan UUID
            txt: JSON text containing pulp_tasks data
        """
        if puid not in self.pulp_plans_exectime:
            self.pulp_plans_exectime[puid] = {}

        try:
            j = json.loads(txt)
            for task in j["pulp_tasks"]:
                finished_at = self.util.date_from_string(task['finished_at'])
                pulp_created = self.util.date_from_string(task['pulp_created'])
                pulp_exectime = (finished_at - pulp_created).total_seconds()

                self.sum_pulp_total_exectime(
                    task['name'], pulp_created, finished_at, pulp_exectime
                )
                self.sum_pulp_relative_exectime(
                    task['name'], pulp_created, finished_at, pulp_exectime
                )

                try:
                    self.pulp_plans_exectime[puid][task['name']][0] += pulp_exectime
                    self.pulp_plans_exectime[puid][task['name']][1] += 1
                except Exception:
                    self.pulp_plans_exectime[puid][task['name']] = [
                        pulp_exectime,
                        1
                    ]
        except Exception:
            return

    def sum_pulp_relative_exectime(self, name, started_at, finished_at, exectime):
        """Calculate relative execution time for Pulp tasks (deprecated).

        Args:
            name: Task name
            started_at: Start datetime
            finished_at: Finish datetime
            exectime: Execution time in seconds
        """
        try:
            if (finished_at > self.pulp_total_rel_exectime[name][3]
                    and started_at < self.pulp_total_rel_exectime[name][3]):
                self.pulp_total_rel_exectime[name][0] += (
                    (finished_at - self.pulp_total_rel_exectime[name][3]).total_seconds()
                )
                self.pulp_total_rel_exectime[name][1] += 1
                self.pulp_total_rel_exectime[name][2] = finished_at
            elif (started_at > self.pulp_total_rel_exectime[name][2]
                    and finished_at < self.pulp_total_rel_exectime[name][3]):
                self.pulp_total_rel_exectime[name][0] += exectime
                self.pulp_total_rel_exectime[name][1] += 1
            elif (started_at < self.pulp_total_rel_exectime[name][2]
                    and finished_at > self.pulp_total_rel_exectime[name][2]):
                self.pulp_total_rel_exectime[name][0] += (
                    (self.pulp_total_rel_exectime[name][2] - started_at).total_seconds()
                )
                self.pulp_total_rel_exectime[name][1] += 1
                self.pulp_total_rel_exectime[name][2] = started_at
            else:
                self.pulp_total_rel_exectime[name][1] += 1
        except Exception:
            self.pulp_total_rel_exectime[name] = [
                exectime,
                1,
                started_at,
                finished_at
            ]

    def sum_dynflow_plans_exectime(self, puid, action_class, exectime):
        """Aggregate Dynflow action execution times per plan.

        Args:
            puid: Plan UUID
            action_class: Action class name
            exectime: Execution time in seconds
        """
        if puid not in self.dynflow_plans_exectime:
            self.dynflow_plans_exectime[puid] = {}

        try:
            self.dynflow_plans_exectime[puid][action_class][0] += exectime
            self.dynflow_plans_exectime[puid][action_class][1] += 1
        except Exception:
            self.dynflow_plans_exectime[puid][action_class] = [exectime, 1]

    def write_actions(self):
        """Generate individual action detail HTML files for each execution plan."""
        self.util.debug("I", "writeActionTree")
        c = 0

        # Enable query-only mode for better read performance
        self.db.execute("PRAGMA query_only = ON")

        # Fetch steps with optimized query
        steps = {}
        if self.conf.dynflowdata['includedUUID']:
            uuid_placeholders = ','.join('?' * len(self.conf.dynflowdata['includedUUID']))
            sql = f"SELECT * FROM steps WHERE execution_plan_uuid IN ({uuid_placeholders}) ORDER BY id"
            rows = self.db.query(sql, tuple(self.conf.dynflowdata['includedUUID']))
        else:
            sql = "SELECT * FROM steps ORDER BY id"
            rows = self.db.query(sql)

        for r in rows:
            if not self.conf.args.showall and r[8] == "success":
                continue

            r = list(r)
            # Format JSON fields
            r[12] = self.show_json(r[12])  # queue
            r[13] = self.show_json(r[13])  # error
            r[14] = self.show_json(r[14])  # children
            r[15] = self.show_json(r[15])  # data

            if r[0] in steps.keys():
                if r[2] in steps[r[0]].keys():
                    steps[r[0]][r[2]].append(r)
                else:
                    steps[r[0]][r[2]] = [r]
            else:
                steps[r[0]] = {r[2]: [r]}

        # Fetch actions
        actions = {}
        sql = (
            "SELECT s.action_id, p.uuid, a.caller_action_id,"
            + " a.run_step_id, s.action_class, a.data, a.input, a.output,"
            + " p.result, p.label, MIN(s.state),"
            + " a.caller_execution_plan_id, MAX(t.action), MAX(t.id),"
            + " MAX(t.parent_task_id), s.execution_time,"
            + " MIN(s.started_at), MAX(s.ended_at),"
            + " SUM(s.real_time), SUM(s.execution_time)"
            + " FROM steps s"
            + " LEFT JOIN tasks t ON s.execution_plan_uuid = t.external_id"
            + " LEFT JOIN plans p ON s.execution_plan_uuid = p.uuid"
            + " LEFT JOIN actions a ON s.execution_plan_uuid = a.execution_plan_uuid"
            + " AND s.action_id = a.id"
            + " GROUP BY s.execution_plan_uuid, s.action_id"
        )
        rows = self.db.query(sql)
        self.pb.all_entries = len(rows)
        self.pb.start_time = datetime.datetime.now()
        start_time = time.time()

        for r in rows:
            if not self.conf.args.showall and r[8] == "success":
                continue

            self.sum_pulp_plans_exectime(r[1], r[7])
            self.sum_dynflow_plans_exectime(r[1], r[4], r[19])

            r = list(r)
            # Remove old single execution_time field, keep aggregated fields
            del r[15]

            # Format JSON fields
            r[5] = self.show_json(r[5])  # data
            r[6] = self.show_json(r[6])  # input
            r[7] = self.show_json(r[7])  # output

            # Attach steps to this action
            if r[1] in steps.keys() and r[0] in steps[r[1]].keys():
                r.append(steps[r[1]][r[0]])
            else:
                r.append([])

            if r[1] in actions.keys():
                actions[r[1]].append(r)
            else:
                actions[r[1]] = [r]

        # Write output files
        for execution_plan_uuid, data in actions.items():
            c = c + 1
            outputfile = (
                self.conf.args.output_path
                + "/actions/"
                + execution_plan_uuid
                + ".html"
            )

            # Build action hierarchy using shared code
            root_actions, child_actions, actions_by_id = (
                ActionHierarchy.build_hierarchy(data)
            )

            context = {
                "root_actions": root_actions,
                "child_actions": child_actions,
                "label": data[0][9],
                "execution_plan_uuid": execution_plan_uuid,
                "caller_execution_plan_id": data[0][11],
                "pulp_exectime": sorted(
                    self.pulp_plans_exectime[execution_plan_uuid].items(),
                    key=lambda item: item[1],
                    reverse=True
                )[:5],
                "dynflow_exectime": sorted(
                    self.dynflow_plans_exectime[execution_plan_uuid].items(),
                    key=lambda item: item[1],
                    reverse=True
                )[:5],
                "sos": self.conf.sos,
            }
            self.write_report(context, "actions.html", outputfile)

            # Update progress bar less frequently (every 100 iterations)
            if not self.conf.args.quiet and c % 100 == 0:
                self.pb.print_bar(c)

        # Write CSV export
        self.write_report(
            {'actions': actions},
            "tasks.csv",
            self.conf.args.output_path + "/dynflowparserng.csv"
        )

        # Disable query-only mode
        self.db.execute("PRAGMA query_only = OFF")

        seconds = time.time() - start_time
        speed = round(c / seconds) if c > 0 else 0

        if not self.conf.args.quiet:
            print(
                "  - Written " + str(c) + " output plans in "
                + self.util.seconds_to_str(seconds)
                + " (" + str(speed) + " lines/second)"
            )

    def show_json(self, txt):
        """Format JSON text with indentation and HTML escaping.

        Args:
            txt: JSON text to format

        Returns:
            str: Formatted and HTML-escaped JSON, or original text if not valid JSON
        """
        try:
            # Check if it's JSON (backtrace check is kept for compatibility)
            if '"backtrace":' in txt[0:30]:
                return html.escape(json.dumps(json.loads(txt), indent=4))
            else:
                return html.escape(json.dumps(json.loads(txt), indent=4))
        except Exception:
            return txt

    def write_report(self, context, templatefile, outputfile):
        """Render a Jinja2 template and write to file.

        Args:
            context: Template context dictionary
            templatefile: Template filename (in templates/ directory)
            outputfile: Output file path
        """
        # Add system info to context
        context.update({'sos': self.conf.sos})

        self.util.debug("D", "write_report " + outputfile)

        # Render template
        template = self.jinja_env.get_template(templatefile)

        # Write output file
        with open(outputfile, mode="w", encoding="utf-8") as results:
            results.write(template.render(context))
