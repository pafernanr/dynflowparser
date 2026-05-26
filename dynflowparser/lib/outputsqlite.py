import datetime
import json
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

        # Apply PRAGMA optimizations for better write performance
        self.execute("PRAGMA synchronous = OFF")
        self.execute("PRAGMA journal_mode = WAL")
        self.execute("PRAGMA cache_size = -64000")  # 64MB cache
        self.execute("PRAGMA temp_store = MEMORY")
        # Note: EXCLUSIVE locking mode removed to allow multiple connections

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
        # Commit removed - now handled by caller in write()

    def insert_plans(self, values):
        query = "INSERT INTO plans VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        self.util.debug("D", query + " " + str(values))
        self.executemany(query, values)
        # Commit removed - now handled by caller in write()

    def insert_actions(self, values):
        query = "INSERT INTO actions VALUES (?,?,?,?,?,?,?,?,?,?,?)"
        self.util.debug("D", query + " " + str(values))
        self.executemany(query, values)
        # Commit removed - now handled by caller in write()

    def insert_steps(self, values):
        query = "INSERT INTO steps VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        self.util.debug("D", query + " " + str(values))
        self.executemany(query, values)
        # Commit removed - now handled by caller in write()

    def create_tables(self):
        self.execute("""SELECT name FROM sqlite_master
                     WHERE type='table' AND name='tasks';""")
        if not self.fetchone():
            self.create_tasks()
            self.create_plans()
            self.create_actions()
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
        # Index creation moved to create_indexes()
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
        # Index creation moved to create_indexes()
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
        # Index creation moved to create_indexes()
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
        # Index creation moved to create_indexes()
        self.commit()

    def create_indexes(self):
        """Create indexes after data insertion for better performance."""
        if not self.conf.args.quiet:
            print("Creating database indexes...")

        # Tasks indexes
        self.execute("CREATE INDEX IF NOT EXISTS tasks_id ON tasks(id)")
        self.execute(
            "CREATE INDEX IF NOT EXISTS tasks_external_id "
            "ON tasks(external_id)")

        # Plans indexes
        self.execute("CREATE INDEX IF NOT EXISTS plans_uuid ON plans(uuid)")

        # Actions indexes
        self.execute(
            "CREATE INDEX IF NOT EXISTS actions_execution_plan_id "
            "ON actions(execution_plan_uuid)")
        self.execute("CREATE INDEX IF NOT EXISTS actions_id ON actions(id)")

        # Steps indexes
        self.execute(
            "CREATE INDEX IF NOT EXISTS steps_execution_plan_uuid "
            "ON steps(execution_plan_uuid)")
        self.execute(
            "CREATE INDEX IF NOT EXISTS steps_action_id "
            "ON steps(action_id)")
        self.execute("CREATE INDEX IF NOT EXISTS steps_id ON steps(id)")

        # Compound indexes for better JOIN performance
        self.execute(
            "CREATE INDEX IF NOT EXISTS idx_steps_plan_action "
            "ON steps(execution_plan_uuid, action_id)")

        self.commit()

        if not self.conf.args.quiet:
            print("Indexes created successfully.")

    def insert_multi(self, dtype, rows):
        if dtype == "tasks":
            self.insert_tasks(rows)
        elif dtype == "plans":
            self.insert_plans(rows)
        elif dtype == "actions":
            self.insert_actions(rows)
        elif dtype == "steps":
            self.insert_steps(rows)
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
        batch_size = 5000  # Increased from 1000 for better performance
        progress_update_freq = 1000  # Update progress bar every 1000 rows
        last_index = 0

        # Begin single transaction for entire write
        self.execute("BEGIN TRANSACTION")

        for i, lcsv in enumerate(csv):
            last_index = i
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
                            if header == "output":
                                value = self.parse_action_output(myid, value)
                            fields.append(value)
                    elif headers[h] in datefields:
                        fields.append(self.util.change_timezone(
                            self.conf.sos['timezone'], lcsv[h]))
                    else:
                        fields.append(lcsv[h])
                self.util.debug("I", str(fields))
                multi.append(fields)

                # Insert in larger batches
                if len(multi) >= batch_size:
                    self.insert_multi(dtype, multi)
                    multi = []

                # Update progress bar less frequently
                if not self.conf.args.quiet and i % progress_update_freq == 0:
                    pb.print_bar(i)

        # Insert remaining records
        if len(multi) > 0:
            self.insert_multi(dtype, multi)
            multi = []

        # Commit the transaction
        self.commit()

        if not self.conf.args.quiet:
            seconds = time.time() - start_time
            if last_index > 0:
                speed = round(last_index/seconds)
            else:
                speed = 0
            print("  - Parsed " + str(last_index) + " " + dtype + " in "
                  + self.util.seconds_to_str(seconds)
                  + " (" + str(speed) + " lines/second)")

    def parse_action_output(self, execution_plan_uuid, txt):
        txt = txt.replace("\\r", "").replace("\\n", "\n")
        try:
            json_v = json.loads(txt)
            for i, p in enumerate(json_v['pulp_tasks']):
                finished_at = (
                    self.util.change_timezone(
                        self.conf.sos['timezone'],
                        p["finished_at"].replace("Z", "000Z")))
                started_at = (
                    self.util.change_timezone(
                        self.conf.sos['timezone'],
                        p["started_at"].replace("Z", "000Z")))
                pulp_created = (
                    self.util.change_timezone(
                        self.conf.sos['timezone'],
                        p["pulp_created"].replace("Z", "000Z")))
                pulp_last_updated = (
                    self.util.change_timezone(
                        self.conf.sos['timezone'],
                        p["pulp_last_updated"].replace("Z", "000Z")))
                unblocked_at = (
                    self.util.change_timezone(
                        self.conf.sos['timezone'],
                        p["unblocked_at"].replace("Z", "000Z")))
                json_v['pulp_tasks'][i]["finished_at"] = str(finished_at)
                json_v['pulp_tasks'][i]["started_at"] = str(started_at)
                json_v['pulp_tasks'][i]["pulp_created"] = str(pulp_created)
                json_v['pulp_tasks'][i]["pulp_last_updated"] = str(
                    pulp_last_updated)
                json_v['pulp_tasks'][i]["unblocked_at"] = str(unblocked_at)
            return json.dumps(json_v, indent=None)
        except Exception as e:  # noqa F841
            # if str(e) != "'pulp_tasks'":
            #    self.util.debug("E", f"{str(e)}:\n{txt}")
            return txt
