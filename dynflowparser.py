#!/usr/bin/python3
'''
Author: Pablo Fernández Rodríguez
Web: https://github.com/pafernanr/dynflowparser
Licence: GPLv3 https://www.gnu.org/licenses/gpl-3.0.en.html
'''
from lib.configuration import Conf
from lib.outputSQLite import OutputSQLite
from lib.outputHtml import OutputHtml
from lib.util import Util
import csv
import operator
import os
import re
import sys
import time
import webbrowser


# increase csv field limit
maxInt = sys.maxsize
while True:
    try:
        csv.field_size_limit(maxInt)
        break
    except OverflowError:
        maxInt = int(maxInt/10)


def read_dynflow(type):
    inputfile = Conf.inputdir + Conf.parser[type]['inputfile']
    if os.path.islink(inputfile):
        Util.debug(Conf, "W", 
                   f"read_dynflow: {Conf.parser[type]['inputfile']} "
                   f"was truncated by sosreport. Some {type} may be missing.")
    sort = Conf.parser[type]['headers'].index(Conf.parser[type]['sortby'])
    reverse = Conf.parser[type]['reverse']
    # Workaround for old sosreport versions (Sat 6.11 RHEL7?)
    # probably this workaround should be deprecated
    with open(inputfile, "r+", encoding="utf-8") as csv_file:
        tmpfile = "/tmp/foreman_tasks_tasks"
        if type == "tasks" and "|" in csv_file.readlines()[0]:
            Util.debug(Conf, "W",
                       f"File {Conf.parser[type]['inputfile']} "
                       "is not in CSV format. "
                       f"Trying to convert it to ({tmpfile}).")
            csv_file.seek(0)
            tmp = csv_file.read()
            tmp = re.sub(r' *\| *', ',', tmp)
            tmp = re.sub(r'\n\-.*\n', '\n', tmp)
            tmp = re.sub(r'\n\([0-9]+ rows\)\n+', '', tmp)
            tmp = re.sub(r'\n +', '\n', tmp)
            tmp = re.sub(r'^ +', '', tmp)
            f = open(tmpfile, "w")
            f.write(tmp)
            f.close
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
            'headers': 'id,type,label,started_at,ended_at,state,result,external_id,parent_task_id,start_at,start_before,action,user_id,state_updated_at'.split(",")  # noqa E501
        }
        Conf.parser['plans'] = {
            'inputfile': "/sos_commands/foreman/dynflow_execution_plans",  # noqa E501
            'sortby': 'started_at',  # sort by
            'reverse': True,  # sort order
            'dates': ['started_at', 'ended_at'],
            'json': ['run_flow', 'finalize_flow', 'execution_history', 'step_ids'],   # noqa E501
            'headers': 'uuid,state,result,started_at,ended_at,real_time,execution_time,label,class,root_plan_step_id,run_flow,finalize_flow,execution_history,step_ids,data'.split(",")  # noqa 501
        }
        Conf.parser['actions'] = {
            'inputfile': "/sos_commands/foreman/dynflow_actions",  # noqa E501
            'sortby': 'caller_action_id',  # sort by
            'reverse': False,  # sort order
            'json': ['input', 'output'],
            'dates': [],
            'headers': 'execution_plan_uuid,id,caller_execution_plan_id,caller_action_id,class,plan_step_id,run_step_id,finalize_step_id,data,input,output'.split(",")  # noqa E501
        }
        Conf.parser['steps'] = {
            'inputfile': "/sos_commands/foreman/dynflow_steps",
            'sortby': 'started_at',  # sort by
            'reverse': True,  # sort order
            'json': ['children', 'error'],
            'dates': ['started_at', 'ended_at'],
            'headers': 'execution_plan_uuid,id,action_id,state,started_at,ended_at,real_time,execution_time,progress_done,progress_weight,class,action_class,queue,error,children,data'.split(",")  # noqa E501
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
        Conf.parser['tasks']['headers'] = 'id,type,label,started_at,ended_at,state,result,external_id,parent_task_id,start_at,start_before,action,state_updated_at,user_id'.split(",")  # noqa E501
    # end workaround
    for i, dline in enumerate(dynflow):
        # exclude task is not between dfrom and dto
        starts = "1974-04-10"
        ends = "2999-01-01"
        if 'started_at' in headers:
            istarts = headers.index('started_at')
            iends = headers.index('ended_at')
            if dline[istarts] != "":
                starts = dline[istarts]
            if dline[iends] != "":
                ends = dline[iends]
        dfrom = Util.date_from_string(Conf.dfrom)
        dto = Util.date_from_string(Conf.dto)
        starts = Util.change_timezone(Conf.sos['timezone'], starts)
        ends = Util.change_timezone(Conf.sos['timezone'], ends)
        if (dfrom <= starts <= dto) or (dfrom <= ends <= dto):
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

