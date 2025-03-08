import csv
import operator
import os
import re
import sys
import time
import webbrowser

from dynflowparser.lib.configuration import Conf
from dynflowparser.lib.outputhtml import OutputHtml
from dynflowparser.lib.outputsqlite import OutputSQLite
from dynflowparser.lib.util import Util


class DynflowParser:

    def __init__(self):
        self.conf = Conf()
        self.util = Util(self.conf.args.debug)
        self.get_dynflow_schema()
        # increase csv field limit
        maxint = sys.maxsize
        while True:
            try:
                csv.field_size_limit(maxint)
                break
            except OverflowError:
                maxint = int(maxint/10)

    def read_dynflow(self, dtype):
        inputfile = (self.conf.args.sosreport_path
                     + self.conf.dynflowdata[dtype]['inputfile'])
        if os.path.islink(inputfile):
            self.util.debug(
                "W",
                f"read_dynflow: {self.conf.dynflowdata[dtype]['inputfile']} "
                f"was truncated by sosreport. Some {dtype} may be missing.")
        sort = (self.conf.dynflowdata[dtype]['headers']
                .index(self.conf.dynflowdata[dtype]['sortby']))
        reverse = self.conf.dynflowdata[dtype]['reverse']
        # Workaround for old sosreport versions (Sat 6.11 RHEL7?)
        # probably this workaround should be deprecated
        with open(inputfile, "r+", encoding="utf-8") as csv_file:
            tmpfile = "/tmp/foreman_tasks_tasks"
            if dtype == "tasks" and "|" in csv_file.readlines()[0]:
                self.util.debug(
                    "W",
                    f"File {self.conf.dynflowdata[dtype]['inputfile']} "
                    "is not in CSV format. "
                    f"Trying to convert it to ({tmpfile}).")
                csv_file.seek(0)
                tmp = csv_file.read()
                tmp = re.sub(r' *\| *', ',', tmp)
                tmp = re.sub(r'\n\-.*\n', '\n', tmp)
                tmp = re.sub(r'\n\([0-9]+ rows\)\n+', '', tmp)
                tmp = re.sub(r'\n +', '\n', tmp)
                tmp = re.sub(r'^ +', '', tmp)
                with open(tmpfile, 'w', encoding="utf-8") as f:
                    f.write(tmp)
                inputfile = tmpfile

        with open(inputfile, "r+", encoding="utf-8") as csv_file:
            reader = csv.reader(csv_file, delimiter=",")
            next(reader)  # discard header line (or truncated first line)
            sreader = sorted(reader, key=operator.itemgetter(sort),
                             reverse=reverse)
        csv_file.close()
        return sreader

    def get_dynflow_schema(self):
        if self.conf.dynflowdata['version'] == "24":  # from Satellite 6.11
            self.conf.dynflowdata['tasks'] = {
                'inputfile': "/sos_commands/foreman/foreman_tasks_tasks",
                'sortby': 'started_at',
                'reverse': True,
                'dates': ['started_at', 'ended_at', 'state_updated_at'],
                'json': [],
                'headers': ['id', 'dtype', 'label', 'started_at', 'ended_at',
                            'state', 'result', 'external_id', 'parent_task_id',
                            'start_at', 'start_before', 'action', 'user_id',
                            'state_updated_at']
            }
            self.conf.dynflowdata['plans'] = {
                'inputfile': "/sos_commands/foreman/dynflow_execution_plans",
                'sortby': 'started_at',
                'reverse': True,
                'dates': [
                    'started_at',
                    'ended_at'],
                'json': [
                    'run_flow', 'finalize_flow',
                    'execution_history', 'step_ids'],
                'headers': [
                    'uuid', 'state', 'result', 'started_at', 'ended_at',
                    'real_time', 'execution_time', 'label', 'class',
                    'root_plan_step_id', 'run_flow', 'finalize_flow',
                    'execution_history', 'step_ids', 'data']
            }
            self.conf.dynflowdata['actions'] = {
                'inputfile': "/sos_commands/foreman/dynflow_actions",
                'sortby': 'caller_action_id',
                'reverse': False,
                'json': ['input', 'output'],
                'dates': [],
                'headers': [
                    'execution_plan_uuid', 'id',
                    'caller_execution_plan_id', 'caller_action_id',
                    'class', 'plan_step_id', 'run_step_id',
                    'finalize_step_id', 'data', 'input', 'output']
            }
            self.conf.dynflowdata['steps'] = {
                'inputfile': "/sos_commands/foreman/dynflow_steps",
                'sortby': 'started_at',
                'reverse': True,
                'json': ['children', 'error'],
                'dates': ['started_at', 'ended_at'],
                'headers': [
                    'execution_plan_uuid', 'id', 'action_id', 'state',
                    'started_at', 'ended_at', 'real_time',
                    'execution_time', 'progress_done', 'progress_weight',
                    'class', 'action_class', 'queue', 'error',
                    'children', 'data']
            }
        else:
            print("ERROR: Dynflow schema version "
                  + f"{self.conf.dynflowdata['version']} is not supported. "
                  + "Please refer to README.")
            sys.exit(1)

    def main(self):
        start_time = time.time()
        sqlite = OutputSQLite(self.conf)
        html = OutputHtml(self.conf)
        headers = self.conf.dynflowdata['tasks']['headers']
        dynflow = self.read_dynflow('tasks')
        dfrom = self.util.date_from_string(self.conf.args.datefrom)
        dto = self.util.date_from_string(self.conf.args.dateto)
        # workaround for mysteriously disordered fields on some csv files
        if " " not in dynflow[2][13]:
            self.conf.dynflowdata['tasks']['headers'] = [
                'id', 'dtype', 'label', 'started_at', 'ended_at', 'state',
                'result', 'external_id', 'parent_task_id', 'start_at',
                'start_before', 'action', 'state_updated_at', 'user_id']
        # end workaround
        for i, dline in enumerate(dynflow):
            # exclude task if not between arguments dfrom and dto
            starts = "1974-04-10"
            ends = "2999-01-01"
            if 'started_at' in headers:
                istarts = headers.index('started_at')
                iends = headers.index('ended_at')
                if dline[istarts] != "":
                    starts = dline[istarts]
                if dline[iends] != "":
                    ends = dline[iends]
            starts = self.util.change_timezone(
                self.conf.sos['timezone'],
                starts)
            ends = self.util.change_timezone(
                self.conf.sos['timezone'],
                ends)
            if (dfrom <= starts <= dto) or (dfrom <= ends <= dto):
                # include only success tasks or all
                if self.conf.unsuccess:
                    if dline[headers.index('result')] != 'success':
                        self.conf.dynflowdata['includedUUID'].append(
                            dline[headers.index('external_id')]
                        )
                else:
                    self.conf.dynflowdata['includedUUID'].append(
                        dline[headers.index('external_id')]
                        )
        # Write Tasks to SQLite
        if self.conf.writesql:
            for d in ['tasks', 'plans', 'actions', 'steps']:
                dynflow = self.read_dynflow(d)
                sqlite.write(d, dynflow)
        html.write()
        indexpath = f"{self.conf.args.output_path}/index.html"
        if not self.conf.args.quiet:
            print("\nUTC dates converted to: " + self.conf.sos['timezone'])
            print("TotalTime: "
                  + self.util.seconds_to_str(time.time() - start_time) + "\n")
            print(f"OutputFile: {indexpath}"
                  .replace('//', '/')
                  .replace('/./', '/'))

        webbrowser.open_new_tab(f"file:///{indexpath}")
