'''
Author: Pablo Fernández Rodríguez
Web: https://github.com/pafernanr/dynflowparser
Licence: GPLv3 https://www.gnu.org/licenses/gpl-3.0.en.html
'''
import os
import json
import html
import datetime
import time
from jinja2 import Environment, FileSystemLoader
from lib.outputSQLite import OutputSQLite
from lib.util import ProgressBarFromFileLines
from lib.util import Util


class OutputHtml:

    def __init__(self, Conf):
        self.Conf = Conf
        self.db = OutputSQLite(Conf)
        self.pb = ProgressBarFromFileLines()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

    def write(self):
        self.write_tasks()
        self.write_actions()

    def write_tasks(self):
        Util.debug(self.Conf, "I", "write_tasks")
        if self.Conf.unsuccess:
            where = " AND t.result != 'success'"
        else:
            where = ""

        tmp = self.db.query("SELECT t.parent_task_id, t.id, t.external_id,"
                            + " t.label, t.state, t.result, t.started_at,"
                            + " t.ended_at, t.action"
                            + " FROM tasks t"
                            + " INNER JOIN plans p"
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
                            + " INNER JOIN plans p"
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

        outputfile = self.Conf.outputdir + "/index.html"
        outputcsv = self.Conf.outputdir + "/tasks.csv"
        context = {
            "rows": rows
        }
        self.write_report(context, "tasks.html", outputfile)
        self.write_report(context, "tasks.csv", outputcsv)

    def write_actions(self):
        Util.debug(self.Conf, "I", "writeActionTree")
        c = 0
        # fetch steps
        steps = {}
        sql = ("SELECT * FROM steps ORDER BY id")
        rows = self.db.query(sql)
        for r in rows:
            if self.Conf.unsuccess and r[8] == "success":
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
               + " a.caller_execution_plan_id, MAX(t.action), MAX(t.id)"
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
            if self.Conf.unsuccess and r[8] == "success":
                continue
            r = list(r)
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
            outputfile = self.Conf.outputdir + "/actions/" + execution_plan_uuid + ".html"  # noqa E501
            context = {
                "actions": data,
                "label": data[0][9],
                "execution_plan_uuid": execution_plan_uuid,
                "caller_execution_plan_id": data[0][11]
            }
            self.write_report(context, "actions.html", outputfile)  # noqa E501
            if not self.Conf.quiet:
                self.pb.print_bar(c)
        seconds = time.time() - start_time
        speed = round(c/seconds)
        if not self.Conf.quiet:
            print("  - Written " + str(c) + " output plans in "
                  + Util.seconds_to_str(seconds)
                  + " (" + str(speed) + " lines/second)")

    def show_json(self, txt):
        try:
            return (html.escape(json.dumps(json.loads(txt), indent=4))
                    .replace("\\r", "")
                    .replace("\\n", "\n")
                    .replace("\n", "<br>")
                    .replace(" ", "&nbsp;"))
        except Exception as e:  # noqa F841
            return txt

    def write_report(self, context, templatefile, outputfile):
        context.update({
            'sos': self.Conf.sos
            })
        Util.debug(self.Conf, "D", "write_report " + outputfile)
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
