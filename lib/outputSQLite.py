import datetime
import sqlite3
import time
from lib.util import Util
from lib.util import ProgressBarFromFileLines


class OutputSQLite:
    def __init__(self, Conf):
        self._conn = sqlite3.connect(Conf.dbfile)
        self._cursor = self._conn.cursor()
        self.Conf = Conf
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
        Util.debug(self.Conf, "D", query + ", " + str(values))
        self.executemany(query, values)
        self.commit()

    def insert_plans(self, values):
        query = "INSERT INTO plans VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        Util.debug(self.Conf, "D", query + " " + str(values))
        self.executemany(query, values)
        self.commit()

    def insert_actions(self, values):
        query = "INSERT INTO actions VALUES (?,?,?,?,?,?,?,?,?,?,?)"
        Util.debug(self.Conf, "D", query + " " + str(values))
        self.executemany(query, values)
        self.commit()

    def insert_steps(self, values):
        query = "INSERT INTO steps VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        Util.debug(self.Conf, "D", query + " " + str(values))
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
        self.execute("CREATE INDEX actions_execution_plan_id ON actions(execution_plan_uuid)")  # noqa E501
        self.execute("CREATE INDEX actions_id ON actions(id)")  # noqa E501
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
        self.execute("CREATE INDEX steps_execution_plan_uuid ON steps(execution_plan_uuid)")  # noqa E501
        self.execute("CREATE INDEX steps_action_id ON steps(action_id)")
        self.execute("CREATE INDEX steps_id ON steps(id)")
        self.commit()

    def insert_multi(self, type, rows):
        if type == "tasks":
            self.insert_tasks(rows)
        if type == "plans":
            self.insert_plans(rows)
        elif type == "actions":
            self.insert_actions(rows)
        elif type == "steps":
            self.insert_steps(rows)

    def write(self, type, csv):
        pb = ProgressBarFromFileLines()
        datefields = self.Conf.parser[type]['dates']
        jsonfields = self.Conf.parser[type]['json']
        headers = self.Conf.parser[type]['headers']
        multi = []
        pb.all_entries = len(csv)
        pb.start_time = datetime.datetime.now()
        start_time = time.time()
        for i in range(0, len(csv)):
            if type == "tasks":
                myid = csv[i][headers.index('external_id')]
            elif type == "plans":
                myid = csv[i][headers.index('uuid')]
            elif type in ["actions", "steps"]:
                myid = csv[i][headers.index('execution_plan_uuid')]

            if myid in self.Conf.parser['includedUUID']:
                Util.debug(self.Conf, "I", "outputSQLite.write "
                           + type + " " + myid)
                fields = []
                for h in range(len(headers)):
                    if headers[h] in jsonfields:
                        if csv[i][h] == "":
                            fields.append("")
                        elif csv[i][h].startswith("\\x"):
                            # posgresql bytea decoding (Work In Progress)
                            btext = bytes.fromhex(csv[i][h][2:])
                            # enc = chardet.detect(btext)['encoding']
                            fields.append(btext.decode('Latin1'))
                            # return str(codecs.decode(text[2:], "hex"))
                        else:
                            fields.append(str(csv[i][h]))
                    elif headers[h] in datefields:
                        fields.append(Util.change_timezone(self.Conf.sos['timezone'], csv[i][h]))  # noqa E501
                    else:
                        fields.append(csv[i][h])
                Util.debug(self.Conf, "I", str(fields))
                multi.append(fields)
                if i > 999 and i % 1000 == 0:  # insert every 1000 records
                    self.insert_multi(type, multi)
                    multi = []
                if not self.Conf.quiet:
                    pb.print_bar(i)

        if len(multi) > 0:
            self.insert_multi(type, multi)
            multi = []

        if not self.Conf.quiet:
            seconds = time.time() - start_time
            speed = round(i/seconds)
            print("  - Parsed " + str(i) + " " + type + " in "
                  + Util.seconds_to_str(seconds)
                  + " (" + str(speed) + " lines/second)")
