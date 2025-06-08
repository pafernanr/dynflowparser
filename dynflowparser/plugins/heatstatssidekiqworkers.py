# Code adapted from https://github.com/pmoravec/foreman-tasks-load-stats
from datetime import datetime

from dynflowparser.lib.outputsqlite import OutputSQLite
from dynflowparser.lib.util import Util


class HeatStatsSidekiqWorkers:

    def __init__(self, conf):
        self.conf = conf
        self.util = Util(conf.args.debug)

        self.intervals = []
        self.timestamps = set()
        self.now = datetime.now().timestamp()
        self.items_limit = 5
        self.show_graph = False
        self.from_ts = 0
        self.to_ts = self.now

    def _convert_datetime_to_seconds(self, ts):
        ts = self.util.date_from_string(ts)
        return ts.timestamp()

    def main(self):
        sqlite = OutputSQLite(self.conf)
        rsteps = sqlite.query("SELECT started_at, ended_at, \
                              execution_time, action_class from steps")
        for rs in rsteps:
            start = rs[0]
            finish = rs[1]
            exectime = rs[2]
            label = rs[3]
            if exectime == 0:
                continue
            try:
                start = self._convert_datetime_to_seconds(start)
            except ValueError:
                continue
            if len(finish) == 0:
                finish = self.now
            else:
                try:
                    finish = self._convert_datetime_to_seconds(finish)
                except ValueError:
                    continue
            try:
                exectime = float(exectime)
            except Exception:
                continue
            # truncate steps starting before --from
            # and adjust exectime accordingly
            if start < self.from_ts:
                exectime *= (finish-self.from_ts) / (finish-start)
                start = self.from_ts
            # truncate steps ending after --to and adjust exectime accordingly
            if finish > self.to_ts:
                exectime *= (self.to_ts-start) / (finish-start)
                finish = self.to_ts
            self.intervals.append((start, finish, exectime, label))
            self.timestamps.add(start)
            self.timestamps.add(finish)

        # TODO(progress bar): add progress bar e.g. from
        # https://github.com/pavlinamv/rails-load-stats-py/blob/main/progress_bar.py

        # sorted list of timestamps for "get me next timestamp/interval" search
        timestamps_sorted = list(sorted(self.timestamps))
        # output data structure to keep info like
        # start_interval - end_interval: #dynflow_steps, avg_exec_load
        # where start_interval is key to the dict
        heat_intervals = dict()
        # labels: dict with key of dynflow step label and values:
        #   'count': count of the label in input data
        #   'exectime': sum of execution times of steps with this label
        labels = dict()
        ts_prev = 0
        for ts in timestamps_sorted:
            heat_intervals[ts] = {'end': self.now, 'steps': 0, 'load': 0.0}
            if ts_prev > 0:
                heat_intervals[ts_prev]['end'] = ts
            ts_prev = ts

        for start, finish, exectime, label in self.intervals:
            if label not in labels.keys():
                labels[label] = {'count': 0, 'exectime': 0.0}
            labels[label]['count'] += 1
            labels[label]['exectime'] += exectime
            try:
                load = exectime / (finish-start)
            except ZeroDivisionError:
                load = 0
            ts = start
            while finish > heat_intervals[ts]['end']:
                heat_intervals[ts]['steps'] += 1
                heat_intervals[ts]['load'] += load
                ts = heat_intervals[ts]['end']  # skip to the next interval

        labels_list = [(label[1]['count'], label[1]['exectime'], label[0])
                       for label in labels.items()]

        # Top {self.items_limit} dynflow step labels per execution time:"
        execdata = []
        labels_list.sort(key=lambda x: x[1], reverse=True)
        for steps, exectime, label in labels_list[0:self.items_limit]:
            execdata.append([steps, exectime, label])

        # "Top {self.items_limit} dynflow step labels per count:
        countdata = []
        labels_list.sort(key=lambda x: x[0], reverse=True)
        for steps, exectime, label in labels_list[0:self.items_limit]:
            countdata.append([steps, exectime, label])

        # Intervals with distinct sidekiq load
        intervals = []
        # start;duration;concur.steps;avg.exec.load
        for ts in heat_intervals.keys():
            ts_out = datetime.fromtimestamp(ts)
            intervals.append([
                ts_out.isoformat('T', 'microseconds'),
                heat_intervals[ts]['end']-ts,
                heat_intervals[ts]['steps'],
                heat_intervals[ts]['load']
                ])

        return ({
            "execdata": execdata,
            "countdata": countdata,
            "intervals": intervals
            })
