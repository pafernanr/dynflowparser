# Code adapted from https://github.com/pmoravec/foreman-tasks-load-stats
from copy import deepcopy
from datetime import datetime
import json
import os

from dynflowparser.lib.outputsqlite import OutputSQLite
from dynflowparser.lib.util import ProgressBarFromFileLines
from dynflowparser.lib.util import Util


class BlameTaskExecution:

    def __init__(self, conf):
        self.conf = conf
        self.util = Util(conf.args.debug)
        self.pb = ProgressBarFromFileLines()
        self.now = datetime.now().timestamp()

        self.metric = "relative-blame"
        # What metric to use for blaming.
        # 'absolute': Sum of absolute values regardless of
        #   concurrency. 'sidewait' can be negative as it is
        #   realtime subsctracted by other possibly concurrent
        #   values.
        # 'absolute-blame': Summarize blame times regardless
        #   of concurrency. I.e. when two dynflow steps run
        #   concurrently, count them both.
        # 'relative-blame': Relativize blame times per
        #   concurrency. I.e. when two dynflow steps run
        #   concurrently, count half of each blame time from
        #   both.
        # 'all': Show all three metrics.

        # absolute / cumulative times, not respecting concurrency
        self.zero_blame_times = {
            'sidewait': 0.0,
            'sideexec': 0.0,
            'pulpwait': 0.0,
            'pulpexec': 0.0,
            'candlewait': 0.0,
            'candleexec': 0.0
        }
        # track all timestamps in a set
        self.timestamps = set()
        # for each dynflow step, keep start and finish timestamps and sidekiq's
        # execution time - index them per action_id which is a sufficient
        # common id for both action and step (for us)
        self.steps_times = {}
        # for each dynflow action, keep list of intervals "we started to wait
        # on (pulp|candlepin) task at .. for time .."
        self.action_intervals = {}
        # even once we have action_intervals complete, we can distribute
        # sidekiq execution time evenly to these "not sidekiq responsibility"
        # intervals and to the remaining "sidekiq responsibility" intervals
        # & store within blame_periods
        self.blame_periods = set()  # of start_time, duration, who-to-blame, weight  # noqa E501
        # cumul_blame_intervals are cumulative blame_periods grouped into
        # individual intervals from `timestamps`. Format:
        # key=start_time, value={duration, zero_blame_times, concurrency) where
        # concurrency is the number of concurrent steps
        # (to split the blame evenly)
        self.cumul_blame_intervals = {}
        self.absolute_times = deepcopy(self.zero_blame_times)
        self.relative_blame_intervals = deepcopy(self.zero_blame_times)
        self.absolute_blame_intervals = deepcopy(self.zero_blame_times)

        self.foreman_uuid = None
        self.dynflow_uuid = None
        self.fdir = f"{self.conf.args.sosreport_path}/sos_commands/foreman/"
        self.foreman_tasks_fname = os.path.join(self.fdir, "foreman_tasks_tasks")  # noqa E501
        self.dynflow_steps_fname = os.path.join(self.fdir, "dynflow_steps")
        self.dynflow_actions_fname = os.path.join(self.fdir, "dynflow_actions")

    def _convert_datetime_to_seconds(self, ts):
        ts = self.util.date_from_string(ts)
        return ts.timestamp()

    # for an external task, add times from "task created/started/finished" to
    # internal structures
    def process_external_task(self, step_id, who, created, started, finished):
        try:
            created = self._convert_datetime_to_seconds(created)
            started = self._convert_datetime_to_seconds(started)
            finished = self._convert_datetime_to_seconds(finished)
        except (KeyError, TypeError):
            return

        self.timestamps.add(created)
        self.timestamps.add(started)
        self.timestamps.add(finished)
        self.action_intervals[step_id].append(
            (created, started-created, f'{who}wait'))
        self.action_intervals[step_id].append(
            (started, finished-started, f'{who}exec'))
        self.absolute_times['sidewait'] -= finished-created
        self.absolute_times[f'{who}wait'] += started-created
        self.absolute_times[f'{who}exec'] += finished-started

    def reset(self):
        self.timestamps = set()
        self.steps_times = {}
        self.action_intervals = {}
        self.blame_periods = set()  # start_time, duration, who-to-blame, weight  # noqa E501
        self.cumul_blame_intervals = {}
        self.absolute_times = deepcopy(self.zero_blame_times)
        self.absolute_blame_intervals = deepcopy(self.zero_blame_times)
        self.relative_blame_intervals = deepcopy(self.zero_blame_times)

    def main(self):
        sqlite = OutputSQLite(self.conf)
        multi = []

        rtasks = sqlite.query("SELECT t.id, t.external_id FROM tasks t \
                              LEFT JOIN actions a \
                              ON t.external_id = a.execution_plan_uuid \
                              WHERE a.output LIKE '%pulp_tasks%' \
                              GROUP BY t.id")
        # rtasks = sqlite.query("select * from tasks  \
        #                       where id='be3ab34d-61de-4967-a237-dfb9a27a7d1e'")  # noqa E501
        i = 0
        for rt in rtasks:
            i = i + 1
            self.reset()
            self.foreman_uuid = rt[0]
            self.dynflow_uuid = rt[1]
            rsteps = sqlite.query(
                f"SELECT action_id, started_at, ended_at, real_time, \
                  execution_time FROM steps WHERE execution_plan_uuid \
                  = '{self.dynflow_uuid}'")
            for rs in rsteps:
                step_id = rs[0]  # in fact it is action_id, not step_id
                started_at = rs[1]
                ended_at = rs[2]
                realtime = rs[3]
                exectime = rs[4]
                # ignore incomplete data - neither length can be zero
                if (started_at == 0 or ended_at == 0
                        or realtime == 0 or exectime == 0):
                    continue

                try:
                    started_at = self._convert_datetime_to_seconds(started_at)
                    ended_at = self._convert_datetime_to_seconds(ended_at)
                except ValueError as v:  # noqa F841
                    continue

                self.timestamps.add(started_at)
                self.timestamps.add(ended_at)
                if step_id not in self.steps_times.keys():
                    self.steps_times[step_id] = []
                    self.action_intervals[step_id] = []
                self.steps_times[step_id].append((started_at, ended_at,
                                                  realtime, exectime))
                self.absolute_times['sidewait'] += realtime-exectime
                self.absolute_times['sideexec'] += exectime

            ractions = sqlite.query(
                f"select id, output from actions where \
                    execution_plan_uuid = '{self.dynflow_uuid}'")
            for ra in ractions:
                if "pulp_tasks" not in ra[1]:
                    continue
                try:
                    data = json.loads(ra[1])
                except json.decoder.JSONDecodeError:
                    continue
                step_id = ra[0]  # in fact it is action_id, not step_id
                # if dynflow_steps are truncated, we might not know the
                # [real/exec]time then skip further calculation
                if step_id not in self.steps_times.keys():
                    continue
                # pulp tasks
                if 'pulp_tasks' in data:
                    for task in data['pulp_tasks']:
                        if task == "task":
                            continue
                        if task.keys() >= {"pulp_created", "started_at", "finished_at"}:  # noqa E501
                            self.process_external_task(
                                step_id, 'pulp',
                                task['pulp_created'][:23],
                                task['started_at'][:23],
                                task['finished_at'][:23])
                # pulp task groups
                if 'task_groups' in data and data['task_groups']:
                    for group in data['task_groups']:
                        for task in group["tasks"]:
                            if task.keys() >= {"pulp_created", "started_at", "finished_at"}:  # noqa
                                self.process_external_task(
                                    step_id, 'pulp',
                                    task['pulp_created'][:23],
                                    task['started_at'][:23],
                                    task['finished_at'][:23])
                # candlepin tasks
                if 'task' in data:
                    task = data['task']
                    # time format is '2024-10-02T12:18:04+0000' so strip the
                    # trailing timezone
                    if task.keys() >= {'created', 'startTime', 'endTime'}:
                        self.process_external_task(
                            step_id, 'candle',
                            task['created'].split('+')[0],
                            task['startTime'].split('+')[0],
                            task['endTime'].split('+')[0])

            # for each action_intervals[step_id], distribute the execution
            # time among partial intervals and store the final value in final
            # intervals. Then sort action_intervals per time, to traverse it
            # linearly in time to feed blame_periods
            for step_id, item in self.action_intervals.items():
                # insert dummy record to prevent "is there a record .." tests
                self.action_intervals[step_id].append(
                    (self.now, 0, 'pulpexec'))
                self.action_intervals[step_id].sort(key=lambda x: x[0])
            for step_id, item in self.steps_times.items():
                for started_at, ended_at, realtime, exectime in self.steps_times[step_id]:  # noqa E501
                    # if whole interval was spent by sidekiq execution, skip
                    # finding any external action, there won't be
                    if realtime == exectime:
                        self.blame_periods.add(
                            (started_at, ended_at-started_at, 'sideexec', 1))
                        continue
                    exec2real = exectime/realtime
                    # while there is an action within this sidekiq interval..
                    if isinstance(self.action_intervals[step_id][0][0], list):
                        while ended_at > self.action_intervals[step_id][0][0]:
                            # blame sidekiq for period prior the external action
                            if started_at < self.action_intervals[step_id][0][0]:
                                duration = self.action_intervals[step_id][0][0]-started_at  # noqa E501
                                self.blame_periods.add(
                                    (started_at, duration, 'sidewait', 1-exec2real))  # noqa E501
                                self.blame_periods.add(
                                    (started_at, duration, 'sideexec', exec2real))
                            # now blame pulp/candlepin and sideexec - nowadays, we
                            # treat both them fully concurrently, not interfering
                            # each other "blame" or weight. This approach alone
                            # could mean simplier code but the current code is
                            # prepared for a variant "blame them with proper
                            # "weights" (sideexec might affect pulp/candlepin..?)
                            self.blame_periods.add(
                                (self.action_intervals[step_id][0][0],
                                 self.action_intervals[step_id][0][1],
                                 self.action_intervals[step_id][0][2], 1))
                            self.blame_periods.add(
                                (self.action_intervals[step_id][0][0],
                                 self.action_intervals[step_id][0][1],
                                 'sideexec', exec2real))
                            # move in time beyond the action
                            started_at = self.action_intervals[step_id][0][0] + \
                                self.action_intervals[step_id][0][1]
                            self.action_intervals[step_id].pop(0)
                    # else:
                    #    print(f"ERROR: not a List: {self.foreman_uuid} \
                    #           {self.action_intervals[step_id][0][0]}")
                    # if there is a trailing time spent by sidekiq, blame for it  # noqa E501
                    if started_at < ended_at:
                        duration = ended_at-started_at
                        self.blame_periods.add(
                            (started_at, duration, 'sidewait', 1-exec2real))
                        self.blame_periods.add(
                            (started_at, duration, 'sideexec', exec2real))

            # transform blame_periods into cumul_blame_intervals
            # first initialise cumul_blame_intervals
            next_ts = max(self.timestamps)
            for ts in sorted(self.timestamps, reverse=True):
                self.cumul_blame_intervals[ts] = [next_ts-ts, deepcopy(
                    self.zero_blame_times), 0]
                next_ts = ts
            self.cumul_blame_intervals = dict(
                sorted(self.cumul_blame_intervals.items()))
            # now, add each of blame_periods into corresponding cumul_blame_intervals  # noqa E501
            for ts, duration, who, weight in self.blame_periods:
                while duration > 0:
                    interval = self.cumul_blame_intervals[ts]
                    interval[1][who] += weight
                    interval[2] += 1
                    duration -= interval[0]
                    ts += interval[0]

            # summarize cumul_blame_intervals over time (absolute_blame_intervals) and  # noqa E501
            # also concurrency (relative_blame_intervals)
            whos = self.absolute_blame_intervals.keys()
            for duration, blame_times, concurrency in self.cumul_blame_intervals.values():  # noqa E501
                if concurrency == 0:
                    continue
                for who in whos:
                    self.absolute_blame_intervals[who] += duration*blame_times[who]  # noqa E501
                    self.relative_blame_intervals[who] += duration*blame_times[who]/concurrency  # noqa E501

            for (metric, description, argvalue) in (
                    (self.absolute_times, "absolute times", "absolute"),
                    (self.absolute_blame_intervals, "abs.blame times", "absolute-blame"),  # noqa E501
                    (self.relative_blame_intervals, "relative blame times", "relative-blame")):  # noqa E501
                fields = [
                    self.dynflow_uuid,
                    description,
                    sum(metric.values())] + list(metric.values())

                multi.append(fields)
                if i > 999 and i % 1000 == 0:  # insert every 1000 records
                    sqlite.insert_multi("blametaskexecution", multi)
                    multi = []
            if len(multi) > 0:
                sqlite.insert_multi("blametaskexecution", multi)
                multi = []
