# Code adapted from https://github.com/pmoravec/foreman-tasks-load-stats
from datetime import datetime
from os.path import isfile
from os.path import join
import re

from dynflowparser.lib.util import ProgressBarFromFileLines
from dynflowparser.lib.util import Util


class DynflowPolling:

    def __init__(self, conf):
        self.stats = {}
        self.conf = conf
        self.util = Util(conf.args.debug)
        self.pb = ProgressBarFromFileLines()

        # parse foreman_settings_table line like:
        #  18 | foreman_tasks_polling_multiplier      | --- 5 ..
        self.REGEXP_POLLING_MULTIPLIER = re.compile(
            r".* foreman_tasks_polling_multiplier.*--- (\d+)")
        # extract timestamp and task id from log entries
        self.REGEXP_GET_PULPTASK = re.compile(
            r".*\[(.*)\] \"GET /pulp/api/v3/tasks/(.*)/ .*")
        # timestamp format in input data
        self.TS_FORMAT = '%d/%b/%Y:%H:%M:%S'
        self.multiplier = 1
        self.add_rounding_error = 2

    def main(self):
        input_files = []
        for logfile in ['var/log/httpd/foreman-ssl_access_ssl.log',
                        'var/log/messages',
                        'sos_commands/logs/journalctl_--no-pager',
                        ]:
            fullpath = join(self.conf.args.sosreport_path, logfile)
            if isfile(fullpath):
                input_files.append(fullpath)
        # read foreman_tasks_polling_multiplier
        settings_file = join(self.conf.args.sosreport_path,
                             'sos_commands/foreman/foreman_settings_table')
        if isfile(settings_file):
            for line in open(settings_file, 'r', encoding="utf8").readlines():
                match = self.REGEXP_POLLING_MULTIPLIER.match(line)
                if match:
                    self.multiplier = int(match.group(1))
                    break

        maxdelay = 16 * self.multiplier + self.add_rounding_error
        for _file in input_files:
            print(f"Processing file {_file}..")
            # last_seen: when polling status of a pulp task was last seen?
            # key: task UUID, value: datetime
            last_seen = dict()
            for line in open(_file, encoding="utf-8", errors="replace").readlines():  # noqa E501
                match = self.REGEXP_GET_PULPTASK.match(line)
                if match:
                    timestamp = match.group(1)[:20]
                    task_id = match.group(2)
                    now = datetime.strptime(timestamp, self.TS_FORMAT)
                    prev = last_seen.get(task_id, now)
                    diff = (now-prev).seconds
                    if diff > maxdelay:
                        self.stats[task_id] = diff
                        self.util.debug("W", (
                            f"Task '{task_id}' polled at "
                            f"'{prev.strftime(self.TS_FORMAT)}' and then at "
                            f"'{now.strftime(self.TS_FORMAT)}', delay {diff}s "
                            f"is bigger than maximum {maxdelay}s.")
                            )
                    last_seen[task_id] = now
