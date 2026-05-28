import datetime
import time
import webbrowser

from dynflowparser.lib.configuration import Conf
from dynflowparser.lib.httpserver import HttpServer
from dynflowparser.lib.inputdynflow import InputDynflow
from dynflowparser.lib.outputsqlite import OutputSQLite
from dynflowparser.lib.util import Util


class DynflowParser:

    def __init__(self):
        self.conf = Conf()
        self.util = Util(self.conf.args.debug)
        self.input_dynflow = InputDynflow(self.conf)

    def main(self):
        start_time = time.time()
        sqlite = OutputSQLite(self.conf)
        headers = self.conf.dynflowdata['tasks']['headers']
        dynflow = self.input_dynflow.read_dynflow('tasks')
        if self.conf.args.last_n_days:
            dto = self.util.date_from_string(self.conf.sos['localtime'])
            dfrom = dto - datetime.timedelta(days=self.conf.args.last_n_days)
            self.conf.args.date_from = dfrom
            self.conf.args.date_to = dto
        else:
            dfrom = self.conf.args.date_from
            dto = self.conf.args.date_to
        # workaround for disordered fields on some csv files
        if " " not in dynflow[2][13]:
            self.conf.dynflowdata['tasks']['headers'] = [
                'id', 'dtype', 'label', 'started_at', 'ended_at',
                'state', 'result', 'external_id', 'parent_task_id',
                'start_at', 'start_before', 'action',
                'state_updated_at', 'user_id']
        # end workaround
        for i, dline in enumerate(dynflow):
            # exclude task if not between arguments dfrom and dto
            starts = "1974-04-10"
            ends = "2999-01-01"
            if 'started_at' in headers:
                istarts = headers.index('started_at')
                iends = headers.index('ended_at')
                if dline[istarts] != "":
                    starts = dline[istarts]
                if dline[iends] != "":
                    ends = dline[iends]
            starts = self.util.change_timezone(
                self.conf.sos['timezone'],
                starts)
            ends = self.util.change_timezone(
                self.conf.sos['timezone'],
                ends)
            if (dfrom <= starts <= dto) or (dfrom <= ends <= dto):
                if not self.conf.args.showall:
                    if dline[headers.index('result')] != 'success':
                        self.conf.dynflowdata['includedUUID'].append(
                            dline[headers.index('external_id')]
                        )
                else:
                    self.conf.dynflowdata['includedUUID'].append(
                        dline[headers.index('external_id')]
                        )
        # Write Tasks to SQLite
        if self.conf.writesql:
            for d in ['tasks', 'plans', 'actions', 'steps']:
                dynflow = self.input_dynflow.read_dynflow(d)
                sqlite.write(d, dynflow)
            # Create indexes after all data is inserted for better performance
            sqlite.create_indexes()

        # Route to appropriate UI based on --text flag
        if self.conf.args.text_ui:
            # Text UI mode - launch interactive Textual TUI
            from dynflowparser.lib.ui.text.output import TextOutput
            output = TextOutput(self.conf)
            output.write()  # Blocking call - runs until user quits
        else:
            # HTML mode - generate HTML files
            from dynflowparser.lib.ui.html.output import HtmlOutput
            html = HtmlOutput(self.conf)
            html.write()

            indexpath = f"{self.conf.args.output_path}/index.html"
            if not self.conf.args.quiet:
                print("\nUTC dates converted to: " + self.conf.sos['timezone'])
                print("TotalTime: "
                      + self.util.seconds_to_str(time.time() - start_time) + "\n")
                print(f"OutputFile: {indexpath}"
                      .replace('//', '/')
                      .replace('/./', '/'))

            if self.conf.args.httpd_server:
                # Start HTTP server
                server = HttpServer(self.conf.args.output_path,
                                    self.conf.args.quiet)
                server.start()
                try:
                    # Keep server running until Ctrl+C
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    if not self.conf.args.quiet:
                        print("\nShutting down HTTP server...")
                    try:
                        server.stop()
                    except KeyboardInterrupt:
                        # Suppress second Ctrl+C during shutdown
                        pass
            else:
                webbrowser.open_new_tab(f"file:///{indexpath}")
