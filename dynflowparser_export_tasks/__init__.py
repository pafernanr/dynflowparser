import csv
import os
import sys

from dynflowparser.lib.util import Util
from dynflowparser_export_tasks.lib.configuration import Conf


class DynflowParserExportTasks:

    def __init__(self):
        self.conf = Conf()
        self.util = Util("W")
        # increase csv field limit
        maxint = sys.maxsize
        while True:
            try:
                csv.field_size_limit(maxint)
                break
            except OverflowError:
                maxint = int(maxint/10)
        # Define output files and queries
        filter = (
            f"AND foreman_tasks_tasks.{self.conf.args.filter}"
            if self.conf.args.filter else "")
        filter_result = (
            f"AND foreman_tasks_tasks.result='{self.conf.args.result}'"
            if self.conf.args.result else "")
        filter_state = (
            f"AND foreman_tasks_tasks.state='{self.conf.args.state}'"
            if self.conf.args.state else "")
        self.queries = {
            "dynflow_schema_info": (
                """select dynflow_schema_info.* from dynflow_schema_info"""),
            "foreman_tasks_tasks": (
                f"""select foreman_tasks_tasks.* from foreman_tasks_tasks
                where
                  started_at > NOW() - interval '{self.conf.args.days} days'
                  {filter} {filter_result} {filter_state}
                order by started_at asc"""),
            "dynflow_execution_plans": (
                f"""select dynflow_execution_plans.* from foreman_tasks_tasks
                join dynflow_execution_plans on
                (foreman_tasks_tasks.external_id = dynflow_execution_plans.uuid::varchar)
                where
                  foreman_tasks_tasks.started_at > NOW() - interval '{self.conf.args.days} days'
                  {filter} {filter_result} {filter_state}
                order by foreman_tasks_tasks.started_at asc"""),
            "dynflow_actions": (
                f"""select dynflow_actions.* from foreman_tasks_tasks
                join dynflow_actions on
                (foreman_tasks_tasks.external_id = dynflow_actions.execution_plan_uuid::varchar)
                where
                  foreman_tasks_tasks.started_at > NOW() - interval '{self.conf.args.days} days'
                  {filter} {filter_result} {filter_state}
                order by foreman_tasks_tasks.started_at asc"""),
            "dynflow_steps": (
                f"""select dynflow_steps.* from foreman_tasks_tasks
                join dynflow_steps on
                (foreman_tasks_tasks.external_id = dynflow_steps.execution_plan_uuid::varchar)
                where
                  foreman_tasks_tasks.started_at > NOW() - interval '{self.conf.args.days} days'
                  {filter} {filter_result} {filter_state}
                order by foreman_tasks_tasks.started_at asc"""),
        }

    def main(self):
        # get basic sosreport details
        self.util.exec_command(f"timedatectl &> {self.conf.outdir}/sos_commands/systemd/timedatectl")  # noqa E501
        self.util.exec_command(f"hostname &> {self.conf.outdir}/hostname")
        self.util.exec_command(f"free &> {self.conf.outdir}/free")
        self.util.exec_command(f"lscpu &> {self.conf.outdir}/sos_commands/processor/lscpu")
        self.util.exec_command(f"cp /etc/foreman-installer/scenarios.d/satellite.yaml {self.conf.outdir}/etc/foreman-installer/scenarios.d/satellite.yaml")  # noqa E501
        self.util.exec_command(f"rpm -q satellite &> {self.conf.outdir}/installed-rpms")  # noqa E501

        # execute queries
        password = self.util.exec_command("""grep password /etc/foreman/database.yml | awk '{ print $2 }' | sed 's/"//g'""").rstrip()  # noqa E501
        tmp = self.util.exec_command("""grep host /etc/foreman/database.yml | awk '{ print $2 }' | sed 's/"//g'""")  # noqa E501
        # [ -n "$test" ] && dbhost=$tmp || dbhost="localhost"
        dbhost = tmp if tmp != "" else "localhost"
        for file, query in self.queries.items():
            binary = "psql"
            if file != 'dynflow_schema_info':
                binary = "/usr/libexec/psql-msgpack-decode"
                query = f"COPY ({query}) TO STDOUT WITH (FORMAT 'csv', DELIMITER ',', HEADER)"  # noqa E501
            export = f"""PGPASSWORD={password} {binary} --no-password -h {dbhost} -p 5432 -U foreman -d foreman -c "{query}" &> {self.conf.outdir}/sos_commands/foreman/{file}"""  # noqa E501
            self.util.exec_command(export)

        os.chdir(self.conf.workdir)
        self.util.exec_command(f"tar -zcf {self.conf.sosdir}.tgz {self.conf.sosdir} && rm -rf {self.conf.outdir}")  # noqa E501
        print(f"Last {self.conf.args.days} days Tasks exported to {self.conf.outdir}.tgz")  # noqa E501