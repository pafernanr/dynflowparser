import os
import re

from dynflowparser.lib.outputsqlite import OutputSQLite
from dynflowparser.lib.util import Util


class PulpCore:

    def __init__(self, conf):
        self.conf = conf
        self.util = Util(self.conf.args.debug)
        self.get_pulpcore_schema()
        self.schema_version = self.get_schema_version()

    def get_pulpcore_schema(self):
        self.conf.pulpcoredata['core_task'] = {
            'inputfile': "/sos_commands/pulpcore/core_task",
            'sortby': 'started_at',
            'reverse': True,
            'dates': ['started_at', 'finished_at', 'pulp_created',
                      'pulp_last_updated'],
            'json': [],
            'headers': [
                'pulp_id', 'pulp_created', 'pulp_last_updated', 'state',
                'name', 'started_at', 'finished_at', 'error', 'worker_id',
                'parent_task_id', 'task_group_id', 'logging_cid',
                'reserved_resources_record', 'pulp_domain_id', 'versions',
                'unblocked_at']
        }
        self.conf.pulpcoredata['core_taskgroup'] = {
            'inputfile': "/sos_commands/pulpcore/core_taskgroup",
            'sortby': 'pulp_created',
            'reverse': True,
            'dates': ['pulp_created', 'pulp_last_updated'],
            'json': [],
            'headers': [
                'pulp_id', 'pulp_created', 'pulp_last_updated', 'description',
                'all_tasks_dispatched', 'pulp_domain_id']
        }
        self.conf.pulpcoredata['core_progressreport'] = {
            'inputfile': "/sos_commands/pulpcore/core_progressreport",
            'sortby': 'pulp_created',
            'reverse': True,
            'dates': ['pulp_created', 'pulp_last_updated'],
            'json': [],
            'headers': [
                'pulp_id', 'pulp_created', 'pulp_last_updated', 'message',
                'state', 'total', 'done', 'suffix', 'task_id', 'code']
        }
        self.conf.pulpcoredata['core_groupprogressreport'] = {
            'inputfile': "/sos_commands/pulpcore/core_groupprogressreport",
            'sortby': 'pulp_created',
            'reverse': True,
            'dates': ['pulp_created', 'pulp_last_updated'],
            'json': [],
            'headers': [
                'pulp_id', 'pulp_created', 'pulp_last_updated', 'message',
                'code', 'total', 'done', 'suffix', 'task_group_id']
        }

    def get_schema_version(self):
        v = 0
        with open(f"{self.conf.args.sosreport_path}/installed-rpms",
                  "r", encoding="utf-8") as f:
            v = re.search(
                r'python.*-pulpcore-([0-9]\.[0-9]{2})\.',  # noqa: E501
                f.read()).group(1)
        return float(v)

    def read_pulp(self, dtype):
        inputfile = (self.conf.args.sosreport_path
                     + self.conf.pulpcoredata[dtype]['inputfile'])
        if os.path.islink(inputfile):
            self.util.debug(
                "W",
                f"read_pulp: {self.conf.pulpcoredata[dtype]['inputfile']} "
                f"was truncated by sosreport. Some {dtype} may be missing.")
        with open(inputfile, "r+", encoding="utf-8") as f:
            fields = []
            lines = f.readlines()
            for line in lines[2:len(lines)-2]:
                row = []
                for field in line.strip().split("|"):
                    row.append(field.strip())
                if dtype == "core_task" and self.schema_version < 3.49:
                    row.append("")
                fields.append(row)
            return fields

    def main(self):
        sqlite = OutputSQLite(self.conf)
        for d in ['core_task', 'core_taskgroup', 'core_progressreport',
                  'core_groupprogressreport']:
            pulp = self.read_pulp(d)
            sqlite.insert_multi(d, pulp)
