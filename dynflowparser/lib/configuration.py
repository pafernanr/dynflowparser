import argparse
import os
import shutil

from dynflowparser.lib.util import Util


class Conf:

    def __init__(self):
        self.cwd = os.getcwd()
        self.util = Util("W")
        self.dynflowdata = {
            'version': "0",
            'plans': {'times': 0},
            'steps': {'times': 0},
            'actions': {'times': 0},
            'includedUUID': [],
            }
        self.pulpcoredata = {
            'version': "0",
            'core_task': {'times': 0},
            'core_taskgroup': {'times': 0},
            'core_progressreport': {'times': 0},
            'core_groupprogressreport': {'times': 0}
            }
        self.writesql = True
        self.sos = {}
        self.dbfile = ""

        self.parser = argparse.ArgumentParser(
            description="Get sosreport dynflow files and generates user"
            + " friendly html pages for tasks, plans, actions and steps"
            )
        self.parser.add_argument(
            '-a',
            '--all',
            dest='showall',
            help='Parse all. By default only unsuccess plans are parsed.',
            default=False,
            action='store_true'
            )
        self.parser.add_argument(
            '-d',
            '--debug',
            help="Debug level. Default 'W'",
            default="W",
            choices=['D', 'I', 'W', 'E']
            )
        self.parser.add_argument(
            '-f',
            '--from',
            dest='date_from',
            help='Parse only Plans that were running from this datetime.',
            default='1974-04-10',
            type=self.valid_date
            )
        self.parser.add_argument(
            '-t',
            '--to',
            dest='date_to',
            help='Parse only Plans that were running up to this datetime.',
            default='2999-01-01',
            type=self.valid_date
            )
        self.parser.add_argument(
            '-l',
            '--last',
            dest='last_n_days',
            help='Parse only last N days. Overrides `--from` and `--to`.',
            type=int
            )
        self.parser.add_argument(
            '-n',
            '--nosql',
            help='Reuse existent sqlite file. (Useful for development).',
            default=False,
            action='store_true'
            )
        self.parser.add_argument(
            '-q',
            '--quiet',
            help="Quiet. Don't show progress bar.",
            default=False,
            action='store_true'
            )
        self.parser.add_argument(
            '-o',
            '--output_path',
            help="Write output to this path. Default is './dynflowparser/'.",
            default=self.cwd,
            type=self.valid_output_path
            )
        self.parser.add_argument(
            'sosreport_path',
            help='Path to sos report folder. Default is current path.',
            default=self.cwd,
            type=self.valid_sosreport_path,
            nargs='?'
            )
        self.args = self.parser.parse_args()

        self.set_sos_details()
        self.args.output_path = (
            f"{self.args.output_path}/dynflowparser/{self.sos['sosname']}"
            .replace('//', '/')
            )
        if os.path.exists(self.args.output_path):
            if self.writesql:
                shutil.rmtree(self.args.output_path)
            else:
                for d in ["/actions", "/html"]:
                    shutil.rmtree(self.args.output_path + d)
        os.makedirs(self.args.output_path + "/actions")
        shutil.copytree(os.path.dirname(
                    os.path.realpath(__file__)) + "/../html",
                    self.args.output_path + "/html")
        self.dbfile = self.args.output_path + "/dynflowparser.db"

    def valid_output_path(self, path):
        if path[:1] == "/":
            fullpath = path
        else:
            fullpath = f"{self.cwd}/{path}"
        if os.path.exists(fullpath):
            return fullpath
        else:
            raise argparse.ArgumentTypeError(
                f"{fullpath!r} is not a valid path.")

    def valid_sosreport_path(self, path):
        p = path + "/sos_commands/foreman/dynflow_schema_info"
        if os.path.exists(p):
            return path
        else:
            raise argparse.ArgumentTypeError(
                f"{p!r} doesn't exist.")

    def valid_date(self, d):
        valid = Util("W").valid_date_formats
        for v in valid:
            try:
                return self.util.date_from_string(d)
            except ValueError:
                pass
        raise argparse.ArgumentTypeError(
            f"not a valid date: {d!r}. Valid formats: {str(valid)}")

    def set_sos_details(self):
        self.sos['timezone'] = self.util.exec_command(
            f"grep 'Time zone:' {self.args.sosreport_path}/sos_commands/systemd/timedatectl"  # noqa E501
            + " | awk '{print $3}'").strip()
        self.sos['localtime'] = self.util.exec_command(
            f"grep 'Local time:' {self.args.sosreport_path}/sos_commands/systemd/timedatectl"  # noqa E501
            + " | awk '{print $4\" 23:59:59\"}'").strip()
        self.sos['hostname'] = self.util.exec_command(
            f"cat  {self.args.sosreport_path}/hostname").strip()
        self.sos['ram'] = self.util.exec_command(
            f"cat  {self.args.sosreport_path}/free")
        self.sos['cpu'] = self.util.exec_command(
            f"grep -e '^CPU(s)'  {self.args.sosreport_path}/sos_commands/processor/lscpu "  # noqa E501
            + " | awk '{print $2}'").strip()
        self.sos['tuning'] = self.util.exec_command(
            f"grep tuning  {self.args.sosreport_path}/etc/foreman-installer/scenarios.d/satellite.yaml | cut -d ':' -f2")  # noqa E501
        self.sos['satversion'] = self.util.exec_command(
            f"grep -E 'satellite-6' {self.args.sosreport_path}/installed-rpms | cut -d ' ' -f1").strip()  # noqa E501
        self.dynflowdata['version'] = self.util.exec_command(
            f"tail -n3 {self.args.sosreport_path}/sos_commands/foreman/dynflow_schema_info | head -1 | sed 's/ *//'").strip()  # noqa E501
        self.sos['sosname'] = os.path.basename(
            os.path.normpath(self.args.sosreport_path))
        if self.sos['sosname'] == ".":
            self.sos['sosname'] = ""
