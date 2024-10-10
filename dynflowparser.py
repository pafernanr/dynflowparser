#!/usr/bin/python3
'''
Author: Pablo Fernández Rodríguez
Web: https://github.com/pafernanr/dynflowparser
Licence: GPLv3 https://www.gnu.org/licenses/gpl-3.0.en.html
'''
import csv
import operator
import os
import re
import sys
import time
import webbrowser

from lib.configuration import Conf
from lib.outputHtml import OutputHtml
from lib.outputSQLite import OutputSQLite
from lib.util import Util

# increase csv field limit
MAXINT = sys.maxsize
while True:
    try:
        csv.field_size_limit(MAXINT)
        break
    except OverflowError:
        MAXINT = int(MAXINT/10)


def read_dynflow(dtype):
    inputfile = Conf.inputdir + Conf.parser[dtype]['inputfile']
    if os.path.islink(inputfile):
        Util.debug(Conf, "W",
                   f"read_dynflow: {Conf.parser[dtype]['inputfile']} "
                   f"was truncated by sosreport. Some {dtype} may be missing.")
    sort = Conf.parser[dtype]['headers'].index(Conf.parser[dtype]['sortby'])
    reverse = Conf.parser[dtype]['reverse']
    # Workaround for old sosreport versions (Sat 6.11 RHEL7?)
    # probably this workaround should be deprecated
    with open(inputfile, "r+", encoding="utf-8") as csv_file:
        tmpfile = "/tmp/foreman_tasks_tasks"
        if dtype == "tasks" and "|" in csv_file.readlines()[0]:
            Util.debug(Conf, "W",
                       f"File {Conf.parser[dtype]['inputfile']} "
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
        # sreader = sorted(reader, key=lambda row: sort, reverse=True) # is it faster?  # noqa E501
        sreader = sorted(reader, key=operator.itemgetter(sort),
                         reverse=reverse)

    csv_file.close()
    return sreader


def get_dynflow_schema():
    if Conf.parser['version'] == "24":  # Satellite 6.11 and upper
        Conf.parser['tasks'] = {
            'inputfile': "/sos_commands/foreman/foreman_tasks_tasks",
            'sortby': 'started_at',  # sort by
            'reverse': True,  # sort order
            'dates': ['started_at', 'ended_at', 'state_updated_at'],
            'json': [],
            'headers': ['id', 'dtype', 'label', 'started_at', 'ended_at',
                        'state', 'result', 'external_id', 'parent_task_id',
                        'start_at', 'start_before', 'action,user_id',
                        'state_updated_at']
        }
        Conf.parser['plans'] = {
            'inputfile': "/sos_commands/foreman/dynflow_execution_plans",
            'sortby': 'started_at',  # sort by
            'reverse': True,  # sort order
            'dates': ['started_at', 'ended_at'],
            'json': ['run_flow', 'finalize_flow',
                     'execution_history', 'step_ids'],
            'headers': ['uuid', 'state', 'result', 'started_at', 'ended_at',
                        'real_time', 'execution_time', 'label', 'class',
                        'root_plan_step_id', 'run_flow', 'finalize_flow',
                        'execution_history', 'step_ids', 'data']
        }
        Conf.parser['actions'] = {
            'inputfile': "/sos_commands/foreman/dynflow_actions",  # noqa E501
            'sortby': 'caller_action_id',  # sort by
            'reverse': False,  # sort order
            'json': ['input', 'output'],
            'dates': [],
            'headers': ['execution_plan_uuid', 'id',
                        'caller_execution_plan_id', 'caller_action_id',
                        'class', 'plan_step_id', 'run_step_id',
                        'finalize_step_id', 'data', 'input', 'output']
        }
        Conf.parser['steps'] = {
            'inputfile': "/sos_commands/foreman/dynflow_steps",
            'sortby': 'started_at',  # sort by
            'reverse': True,  # sort order
            'json': ['children', 'error'],
            'dates': ['started_at', 'ended_at'],
            'headers': ['execution_plan_uuid', 'id', 'action_id', 'state',
                        'started_at', 'ended_at', 'real_time',
                        'execution_time', 'progress_done', 'progress_weight',
                        'class', 'action_class', 'queue', 'error',
                        'children', 'data']
        }
    else:
        print("ERROR: Dynflow schema version "
              + f"{Conf.parser['version']} is not supported. "
              + "Please refer to README.")
        sys.exit(1)


if __name__ == "__main__":
    start_time = time.time()
    Conf.get_opts()
    get_dynflow_schema()
    sqlite = OutputSQLite(Conf)
    html = OutputHtml(Conf)
    # Search for Tasks that should to include
    headers = Conf.parser['tasks']['headers']
    dynflow = read_dynflow('tasks')
    # begin workaround for mysteriously disordered fields on some task files
    if " " not in dynflow[2][13]:
        Conf.parser['tasks']['headers'] = [
            'id', 'dtype', 'label', 'started_at', 'ended_at', 'state',
            'result', 'external_id', 'parent_task_id', 'start_at',
            'start_before', 'action', 'state_updated_at', 'user_id']
    # end workaround
    for i, dline in enumerate(dynflow):
        # exclude task is not between dfrom and dto
        STARTS = "1974-04-10"
        ENDS = "2999-01-01"
        if 'started_at' in headers:
            iSTARTS = headers.index('started_at')
            iENDS = headers.index('ended_at')
            if dline[iSTARTS] != "":
                STARTS = dline[iSTARTS]
            if dline[iENDS] != "":
                ENDS = dline[iENDS]
        dfrom = Util.date_from_string(Conf.dfrom)
        dto = Util.date_from_string(Conf.dto)
        STARTS = Util.change_timezone(Conf.sos['timezone'], STARTS)
        ENDS = Util.change_timezone(Conf.sos['timezone'], ENDS)
        if (dfrom <= STARTS <= dto) or (dfrom <= ENDS <= dto):
            # include only success tasks or all
            if Conf.unsuccess:
                if dline[headers.index('result')] != 'success':
                    Conf.parser['includedUUID'].append(
                        dline[headers.index('external_id')]
                    )
            else:
                Conf.parser['includedUUID'].append(
                    dline[headers.index('external_id')]
                    )
    # Write Tasks to SQLite
    if Conf.writesql:
        for d in ['tasks', 'plans', 'actions', 'steps']:
            dynflow = read_dynflow(d)
            sqlite.write(d, dynflow)
    html.write()

    if not Conf.quiet:
        print("\nUTC dates converted to: " + Conf.sos['timezone'])
        print("TotalTime: "
              + Util.seconds_to_str(time.time() - start_time) + "\n")
        print(f"OutputFile: {os.getcwd()}/{Conf.outputdir}/index.html"
              .replace('//', '/')
              .replace('/./', '/'))

    webbrowser.open(Conf.outputdir + "/index.html", 0, True)
