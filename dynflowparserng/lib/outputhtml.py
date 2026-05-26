import datetime
import html
import json
import os
import re
import time

from jinja2 import Environment
from jinja2 import FileSystemLoader

from dynflowparserng.lib.outputsqlite import OutputSQLite
from dynflowparserng.lib.util import ProgressBarFromFileLines
from dynflowparserng.lib.util import Util


class OutputHtml:

    def __init__(self, conf):
        self.conf = conf
        self.db = OutputSQLite(conf)
        self.pb = ProgressBarFromFileLines()
        self.util = Util(conf.args.debug)
        self.pulp_plans_exectime = {}
        self.pulp_total_exectime = {}
        self.pulp_total_rel_exectime = {}
        self.dynflow_plans_exectime = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

    def write(self):
        # actions must be in first place in order to make some maths
        self.write_actions()
        self.write_tasks()

    def dynflow_total_exectime(self):
        return self.db.query(
            """SELECT SUM(execution_time), COUNT(s.id), s.action_class
            FROM steps s
            GROUP BY s.action_class
            ORDER BY SUM(execution_time) DESC
            LIMIT 5
            """)

    def write_tasks(self):
        self.util.debug("I", "write_tasks")
        if self.conf.args.showall:
            where = ""
        else:
            where = " AND t.result != 'success'"

        tmp = self.db.query("SELECT t.parent_task_id, t.id, t.external_id,"
                            + " t.label, t.state, t.result, t.started_at,"
                            + " t.ended_at, t.action, p.state, p.result"
                            + " FROM tasks t"
                            + " LEFT JOIN plans p"
                            + " ON t.external_id=p.uuid"
                            + " WHERE t.parent_task_id=''"
                            + where
                            + " GROUP BY t.id"
                            + " ORDER BY t.started_at DESC")
        rowsdict = {}
        for t in tmp:
            rowsdict[t[1]] = [t]

        tmp = self.db.query("SELECT t.parent_task_id, t.id, t.external_id,"
                            + " t.label, t.state, t.result, t.started_at,"
                            + " t.ended_at, t.action"
                            + " FROM tasks t"
                            + " LEFT JOIN plans p"
                            + " ON t.external_id=p.uuid"
                            + " WHERE t.parent_task_id!=''"
                            + where
                            + " ORDER BY t.started_at ASC")
        for t in tmp:
            if t[0] in rowsdict.keys():
                rowsdict[t[0]].append(t)

        rows = []
        for vs in rowsdict.values():
            if vs:
                for v in vs:
                    rows.append(v)

        outputfile = self.conf.args.output_path + "/index.html"
        context = {
            "rows": rows,
            "dynflow_total_exectime": self.dynflow_total_exectime(),
            "pulp_total_exectime": sorted(
                self.pulp_total_exectime.items(),
                key=lambda item: item[1],
                reverse=True)[:5]
        }
        self.write_report(context, "tasks.html", outputfile)

    def get_pulp_uuid(self, txt):
        uuid = re.search(
            r"[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+-[a-z0-9]+", txt)
        return uuid.group()

    def sum_pulp_total_exectime(self, name, started_at, finished_at, exectime):
        try:
            self.pulp_total_exectime[name][0] += exectime
            self.pulp_total_exectime[name][1] += 1
            self.pulp_total_exectime[name][2] = finished_at
        except Exception as e:  # noqa F841
            self.pulp_total_exectime[name] = [exectime,
                                              1,
                                              started_at,
                                              finished_at]

    def sum_pulp_plans_exectime(self, puid, txt):
        if puid not in self.pulp_plans_exectime:
            self.pulp_plans_exectime[puid] = {}
        try:
            j = json.loads(txt)
            for task in j["pulp_tasks"]:
                finished_at = self.util.date_from_string(task['finished_at'])
                pulp_created = self.util.date_from_string(task['pulp_created'])
                pulp_exectime = (finished_at - pulp_created).total_seconds()
                self.sum_pulp_total_exectime(
                    task['name'], pulp_created, finished_at, pulp_exectime)
                self.sum_pulp_relative_exectime(
                    task['name'], pulp_created, finished_at, pulp_exectime)
                try:
                    self.pulp_plans_exectime[puid][task['name']][0] += pulp_exectime  # noqa E501
                    self.pulp_plans_exectime[puid][task['name']][1] += 1
                except Exception as e:  # noqa F9841
                    self.pulp_plans_exectime[puid][task['name']] = [
                        pulp_exectime,
                        1]
        except Exception as e:  # noqa F841
            return

    # deprecated
    def sum_pulp_relative_exectime(self, name, started_at, finished_at,
                                   exectime):
        try:
            if (finished_at > self.pulp_total_rel_exectime[name][3]
                    and started_at < self.pulp_total_rel_exectime[name][3]):
                self.pulp_total_rel_exectime[name][0] += (
                    (finished_at
                     - self.pulp_total_rel_exectime[name][3]
                     ).total_seconds())
                self.pulp_total_rel_exectime[name][1] += 1
                self.pulp_total_rel_exectime[name][2] = finished_at
            elif (started_at > self.pulp_total_rel_exectime[name][2]
                    and finished_at < self.pulp_total_rel_exectime[name][3]):
                self.pulp_total_rel_exectime[name][0] += exectime
                self.pulp_total_rel_exectime[name][1] += 1
            elif (started_at < self.pulp_total_rel_exectime[name][2]
                    and finished_at > self.pulp_total_rel_exectime[name][2]):
                self.pulp_total_rel_exectime[name][0] += (
                    (self.pulp_total_rel_exectime[name][2]
                     - started_at).total_seconds())
                self.pulp_total_rel_exectime[name][1] += 1
                self.pulp_total_rel_exectime[name][2] = started_at
            else:
                self.pulp_total_rel_exectime[name][1] += 1
        except Exception as e:  # noqa F841
            self.pulp_total_rel_exectime[name] = [exectime,
                                                  1,
                                                  started_at,
                                                  finished_at]

    def sum_dynflow_plans_exectime(self, puid, action_class, exectime):
        if puid not in self.dynflow_plans_exectime:
            self.dynflow_plans_exectime[puid] = {}
        try:
            self.dynflow_plans_exectime[puid][action_class][0] += exectime  # noqa E501
            self.dynflow_plans_exectime[puid][action_class][1] += 1
        except Exception as e:  # noqa F9841
            self.dynflow_plans_exectime[puid][action_class] = [exectime,
                                                               1]

    def write_actions(self):
        self.util.debug("I", "writeActionTree")
        c = 0
        # fetch steps
        steps = {}
        sql = "SELECT * FROM steps ORDER BY id"
        rows = self.db.query(sql)
        for r in rows:
            if not self.conf.args.showall and r[8] == "success":
                continue
            r = list(r)
            r[12] = self.show_json(r[12])
            r[13] = self.show_json(r[13])
            r[14] = self.show_json(r[14])
            r[15] = self.show_json(r[15])
            if r[0] in steps.keys():
                if r[2] in steps[r[0]].keys():
                    steps[r[0]][r[2]].append(r)
                else:
                    steps[r[0]][r[2]] = [r]
            else:
                steps[r[0]] = {r[2]: [r]}

        # fetch actions
        actions = {}
        sql = ("SELECT s.action_id, p.uuid, a.caller_action_id,"
               + " a.run_step_id, s.action_class, a.data, a.input, a.output,"
               + " p.result, p.label, MIN(s.state),"
               + " a.caller_execution_plan_id, MAX(t.action), MAX(t.id),"
               + " MAX(t.parent_task_id), s.execution_time"
               + " FROM steps s"
               + " LEFT JOIN tasks t ON s.execution_plan_uuid = t.external_id"
               + " LEFT JOIN plans p ON s.execution_plan_uuid = p.uuid"
               + " LEFT JOIN actions a ON s.execution_plan_uuid = a.execution_plan_uuid"  # noqa E501
               + " AND s.action_id = a.id"
               + " GROUP BY s.execution_plan_uuid, s.action_id")
        rows = self.db.query(sql)
        self.pb.all_entries = len(rows)
        self.pb.start_time = datetime.datetime.now()
        start_time = time.time()
        for r in rows:
            if not self.conf.args.showall and r[8] == "success":
                continue
            self.sum_pulp_plans_exectime(r[1], r[7])
            self.sum_dynflow_plans_exectime(r[1], r[4], r[15])
            r = list(r[:-1])
            r[5] = self.show_json(r[5])
            r[6] = self.show_json(r[6])
            r[7] = self.show_json(r[7])
            if r[1] in steps.keys() and r[0] in steps[r[1]].keys():
                r.append(steps[r[1]][r[0]])
            else:
                r.append([])
            if r[1] in actions.keys():
                actions[r[1]].append(r)
            else:
                actions[r[1]] = [r]

        # write output
        for execution_plan_uuid, data in actions.items():
            c = c + 1
            outputfile = self.conf.args.output_path + "/actions/" + execution_plan_uuid + ".html"  # noqa E501
            context = {
                "actions": data,
                "label": data[0][9],
                "execution_plan_uuid": execution_plan_uuid,
                "caller_execution_plan_id": data[0][11],
                "pulp_exectime": sorted(
                    self.pulp_plans_exectime[execution_plan_uuid].items(),
                    key=lambda item: item[1],
                    reverse=True)[:5],
                "dynflow_exectime": sorted(
                    self.dynflow_plans_exectime[execution_plan_uuid].items(),
                    key=lambda item: item[1],
                    reverse=True)[:5],
            }
            self.write_report(context, "actions.html", outputfile)  # noqa E501
            if not self.conf.args.quiet:
                self.pb.print_bar(c)
        self.write_report({'actions': actions}, "tasks.csv",
                          self.conf.args.output_path + "/dynflowparserng.csv")
        seconds = time.time() - start_time
        speed = round(c/seconds)
        if not self.conf.args.quiet:
            print("  - Written " + str(c) + " output plans in "
                  + self.util.seconds_to_str(seconds)
                  + " (" + str(speed) + " lines/second)")

    def show_json(self, txt):
        try:
            if '"backtrace":' in txt[0:30]:
                return html.escape(json.dumps(json.loads(txt), indent=4))
            else:
                return html.escape(json.dumps(json.loads(txt), indent=4))
        except Exception as e:  # noqa F841
            return txt

    def write_report(self, context, templatefile, outputfile):
        context.update({
            'sos': self.conf.sos
            })
        self.util.debug("D", "write_report " + outputfile)
        # Load template
        parent = os.path.dirname(os.path.realpath(__file__)) + "/../templates/"
        environment = Environment(loader=FileSystemLoader(parent))
        template = environment.get_template(templatefile)
        # ##### could be useful in the future
        # ##### it can make functions available on jinja2 space
        # # func_dict = {
        # #     "show_json": self.show_json
        # # }
        # # template.globals.update(func_dict)
        # Write output csv file
        with open(outputfile, mode="w", encoding="utf-8") as results:
            results.write(template.render(context))
