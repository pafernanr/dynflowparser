import datetime
import re
import sqlite3
import time

from dynflowparser.lib.util import ProgressBarFromFileLines
from dynflowparser.lib.util import Util


class OutputSQLite:
    def __init__(self, conf):
        self.conf = conf
        self.util = Util(conf.args.debug)
        self._conn = sqlite3.connect(conf.dbfile)
        self._cursor = self._conn.cursor()
        self.create_tables()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    @property
    def connection(self):
        return self._conn

    @property
    def cursor(self):
        return self._cursor

    def commit(self):
        self.connection.commit()

    def close(self, commit=True):
        if commit:
            self.commit()
        self.connection.close()

    def execute(self, sql, params=None):
        self.cursor.execute(sql, params or ())

    def executemany(self, sql, params=None):
        self.cursor.executemany(sql, params or ())

    def fetchall(self):
        return self.cursor.fetchall()

    def fetchone(self):
        return self.cursor.fetchone()

    def query(self, sql, params=None):
        self.cursor.execute(sql, params or ())
        return self.fetchall()

    def insert_tasks(self, values):
        query = "INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        self.util.debug("D", query + ", " + str(values))
        self.executemany(query, values)
        self.commit()

    def insert_plans(self, values):
        query = "INSERT INTO plans VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        self.util.debug("D", query + " " + str(values))
        self.executemany(query, values)
        self.commit()

    def insert_actions(self, values):
        query = "INSERT INTO actions VALUES (?,?,?,?,?,?,?,?,?,?,?)"
        self.util.debug("D", query + " " + str(values))
        self.executemany(query, values)
        self.commit()

    def insert_steps(self, values):
        query = "INSERT INTO steps VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        self.util.debug("D", query + " " + str(values))
        self.executemany(query, values)
        self.commit()

    def insert_blametaskexecution(self, values):
        query = "INSERT INTO blametaskexecution VALUES (?,?,?,?,?,?,?,?,?)"
        self.util.debug("D", query + " " + str(values))
        self.executemany(query, values)
        self.commit()

    def create_tables(self):
        self.execute("""SELECT name FROM sqlite_master
                     WHERE type='table' AND name='tasks';""")
        if not self.fetchone():
            self.create_tasks()
            self.create_plans()
            self.create_actions()
            self.create_steps()
            self.create_blametaskexecution()
            self.create_core_task()
            self.create_core_taskgroup()
            self.create_core_progressreport()
            self.create_core_groupprogressreport()

    def create_tasks(self):
        self.execute("""CREATE TABLE IF NOT EXISTS tasks (
        id TEXT,
        type TEXT,
        label TEXT,
        started_at INTEGER,
        ended_at INTEGER,
        state TEXT,
        result TEXT,
        external_id TEXT,
        parent_task_id TEXT,
        start_at TEXT,
        start_before TEXT,
        action TEXT,
        user_id INTEGER,
        state_updated_at INTEGER
        )""")
        self.execute("CREATE INDEX tasks_id ON tasks(id)")
        self.commit()

    def create_plans(self):
        self.execute("""CREATE TABLE IF NOT EXISTS plans (
        uuid TEXT,
        state TEXT,
        result TEXT,
        started_at INTEGER,
        ended_at INTEGER,
        real_time REAL,
        execution_time REAL,
        label TEXT,
        class TEXT,
        root_plan_step_id INTEGER,
        run_flow TEXT,
        finalize_flow INTEGER,
        execution_history TEXT,
        step_ids TEXT,
        data TEXT
        )""")
        self.execute("CREATE INDEX plans_uuid ON plans(uuid)")
        self.commit()

    def create_actions(self):
        self.execute("""CREATE TABLE IF NOT EXISTS actions (
        execution_plan_uuid TEXT,
        id INTEGER,
        caller_execution_plan_id INTEGER,
        caller_action_id INTEGER,
        class TEXT,
        plan_step_id INTEGER,
        run_step_id INTEGER,
        finalize_step_id INTEGER,
        data TEXT,
        input TEXT,
        output TEXT
        )""")
        self.execute("""CREATE INDEX actions_execution_plan_id
                     ON actions(execution_plan_uuid)""")
        self.execute("CREATE INDEX actions_id ON actions(id)")
        self.commit()

    def create_steps(self):
        self.execute("""CREATE TABLE IF NOT EXISTS steps (
        execution_plan_uuid TEXT,
        id INTEGER,
        action_id INTEGER,
        state TEXT,
        started_at INTEGER,
        ended_at INTEGER,
        real_time REAL,
        execution_time REAL,
        progress_done INTEGER,
        progress_weight INTEGER,
        class TEXT,
        action_class TEXT,
        queue TEXT,
        error TEXT,
        children TEXT,
        data TEXT
        )""")
        self.execute("""CREATE INDEX steps_execution_plan_uuid
                     ON steps(execution_plan_uuid)""")
        self.execute("CREATE INDEX steps_action_id ON steps(action_id)")
        self.execute("CREATE INDEX steps_id ON steps(id)")
        self.commit()

    def create_blametaskexecution(self):
        self.execute("""CREATE TABLE IF NOT EXISTS blametaskexecution (
        execution_plan_uuid TEXT,
        type TEXT,
        total FLOAT,
        sidewait FLOAT,
        sideexec FLOAT,
        pulpwait FLOAT,
        pulpexec FLOAT,
        candlewait FLOAT,
        candleexec FLOAT
        )""")
        self.execute("CREATE INDEX blametaskexecution_execution_plan_id "
                     "ON blametaskexecution(execution_plan_uuid)")
        self.execute("CREATE INDEX blametaskexecution_type "
                     "ON blametaskexecution(type)")
        self.commit()

    def insert_multi(self, dtype, rows):
        if dtype == "tasks":
            self.insert_tasks(rows)
        elif dtype == "plans":
            self.insert_plans(rows)
        elif dtype == "actions":
            self.insert_actions(rows)
        elif dtype == "steps":
            self.insert_steps(rows)
        elif dtype == "blametaskexecution":
            self.insert_blametaskexecution(rows)
        elif dtype == "core_task":
            self.insert_core_task(rows)
        elif dtype == "core_taskgroup":
            self.insert_core_taskgroup(rows)
        elif dtype == "core_progressreport":
            self.insert_core_progressreport(rows)
        elif dtype == "core_groupprogressreport":
            self.insert_core_groupprogressreport(rows)
        else:
            print(f"ERROR: Unknown table '{dtype}'")

    def write(self, dtype, csv):
        pb = ProgressBarFromFileLines()
        datefields = self.conf.dynflowdata[dtype]['dates']
        jsonfields = self.conf.dynflowdata[dtype]['json']
        headers = self.conf.dynflowdata[dtype]['headers']
        multi = []
        pb.all_entries = len(csv)
        pb.start_time = datetime.datetime.now()
        start_time = time.time()
        myid = False
        for i, lcsv in enumerate(csv):
            if dtype == "tasks":
                myid = lcsv[headers.index('external_id')]
            elif dtype == "plans":
                myid = lcsv[headers.index('uuid')]
            elif dtype in ["actions", "steps"]:
                myid = lcsv[headers.index('execution_plan_uuid')]

            if myid in self.conf.dynflowdata['includedUUID']:
                self.util.debug(
                    "I", f"outputSQLite.write {dtype} {myid}")
                fields = []
                for h, header in enumerate(headers):
                    if header in jsonfields:
                        if lcsv[h] == "":
                            fields.append("")
                        elif lcsv[h].startswith("\\x"):
                            # posgresql bytea decoding (Work In Progress)
                            btext = bytes.fromhex(lcsv[h][2:])
                            # enc = chardet.detect(btext)['encoding']
                            fields.append(btext.decode('Latin1'))
                            # return str(codecs.decode(text[2:], "hex"))
                        else:
                            value = str(lcsv[h])
                            # pulp output timezone change
                            if '"pulp_created":' in value:
                                dates = re.findall(
                                    r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+\+\d{2}:\d{2}',  # noqa E501
                                    value)
                                for d in dates:
                                    value = value.replace(
                                        d, str(self.util.change_timezone(
                                            self.conf.sos['timezone'], d))
                                        )
                            fields.append(value)
                    elif headers[h] in datefields:
                        fields.append(self.util.change_timezone(
                            self.conf.sos['timezone'], lcsv[h]))
                    else:
                        fields.append(lcsv[h])
                self.util.debug("I", str(fields))
                multi.append(fields)
                if i > 999 and i % 1000 == 0:  # insert every 1000 records
                    self.insert_multi(dtype, multi)
                    multi = []
                if not self.conf.args.quiet:
                    pb.print_bar(i)

        if len(multi) > 0:
            self.insert_multi(dtype, multi)
            multi = []

        if not self.conf.args.quiet:
            seconds = time.time() - start_time
            speed = round(i/seconds)
            print("  - Parsed " + str(i) + " " + dtype + " in "
                  + self.util.seconds_to_str(seconds)
                  + " (" + str(speed) + " lines/second)")

    # pulpcore methods
    def create_core_task(self):
        self.execute("""CREATE TABLE IF NOT EXISTS core_task (
        pulp_id TEXT,
        pulp_created INTEGER,
        pulp_last_updated INTEGER,
        state TEXT,
        name TEXT,
        started_at INTEGER,
        finished_at INTEGER,
        error TEXT,
        worker_id TEXT,
        parent_task_id TEXT,
        task_group_id TEXT,
        logging_cid TEXT,
        reserved_resources_record TEXT,
        pulp_domain_id TEXT,
        versions TEXT,
        unblocked_at TEXT
        )""")
        self.execute("CREATE INDEX core_task_pulp_id ON core_task(pulp_id)")
        self.commit()

    def create_core_taskgroup(self):
        self.execute("""CREATE TABLE IF NOT EXISTS core_taskgroup (
        pulp_id TEXT,
        pulp_created INTEGER,
        pulp_last_updated INTEGER,
        description TEXT,
        all_tasks_dispatched TEXT,
        pulp_domain_id TEXT
        )""")
        self.execute("CREATE INDEX core_taskgroup_pulp_id \
                     ON core_taskgroup(pulp_id)")
        self.commit()

    def create_core_progressreport(self):
        self.execute("""CREATE TABLE IF NOT EXISTS core_progressreport (
        pulp_id TEXT,
        pulp_created INTEGER,
        pulp_last_updated INTEGER,
        message TEXT,
        state TEXT,
        total TEXT,
        done TEXT,
        suffix TEXT,
        task_id TEXT,
        code TEXT
        )""")
        self.execute("CREATE INDEX core_progressreport_pulp_id \
                     ON core_progressreport(pulp_id)")
        self.commit()

    def create_core_groupprogressreport(self):
        self.execute("""CREATE TABLE IF NOT EXISTS core_groupprogressreport (
        pulp_id TEXT,
        pulp_created INtEGER,
        pulp_last_updated INTEGER,
        message TEXT,
        code TEXT,
        total TEXT,
        done TEXT,
        suffix TEXT,
        task_group_id TEXT
        )""")
        self.execute("CREATE INDEX core_groupprogressreport_pulp_id \
                     ON core_groupprogressreport(pulp_id)")
        self.commit()

    def insert_core_task(self, values):
        query = "INSERT INTO core_task VALUES \
            (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        self.util.debug("D", query + ", " + str(values))
        self.executemany(query, values)
        self.commit()

    def insert_core_taskgroup(self, values):
        query = "INSERT INTO core_taskgroup VALUES \
            (?,?,?,?,?,?)"
        self.util.debug("D", query + ", " + str(values))
        self.executemany(query, values)
        self.commit()

    def insert_core_progressreport(self, values):
        query = "INSERT INTO core_progressreport VALUES \
            (?,?,?,?,?,?,?,?,?,?)"
        self.util.debug("D", query + ", " + str(values))
        self.executemany(query, values)
        self.commit()

    def insert_core_groupprogressreport(self, values):
        query = "INSERT INTO core_groupprogressreport VALUES \
            (?,?,?,?,?,?,?,?,?)"
        self.util.debug("D", query + ", " + str(values))
        self.executemany(query, values)
        self.commit()
