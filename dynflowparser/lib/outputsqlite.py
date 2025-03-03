import datetime
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

    def create_tables(self):
        self.execute("""SELECT name FROM sqlite_master
                     WHERE type='table' AND name='tasks';""")
        if not self.fetchone():
            self.create_tasks()
        self.execute("""SELECT name FROM sqlite_master
                     WHERE type='table' AND name='plans';""")
        if not self.fetchone():
            self.create_plans()
        self.execute("""SELECT name FROM sqlite_master
                     WHERE type='table' AND name='actions';""")
        if not self.fetchone():
            self.create_actions()
        self.execute("""SELECT name FROM sqlite_master
                     WHERE type='table' AND name='steps';""")
        if not self.fetchone():
            self.create_steps()

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

    def insert_multi(self, dtype, rows):
        if dtype == "tasks":
            self.insert_tasks(rows)
        if dtype == "plans":
            self.insert_plans(rows)
        elif dtype == "actions":
            self.insert_actions(rows)
        elif dtype == "steps":
            self.insert_steps(rows)

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
                            fields.append(str(lcsv[h]))
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
