import getopt
import os
import shutil
import sys
from pathlib import Path
from lib.util import Util


class Conf:
    # Default Values
    parser = {
        'version': "0",
        'plans': {'times': 0},
        'steps': {'times': 0},
        'actions': {'times': 0},
        'includedUUID': [],
        }
    inputdir = "."
    outputdir = "./"
    unsuccess = True
    writesql = True
    sos = {}
    quiet = False
    dto = "2999-01-01"
    dfrom = "1974-10-04"
    debug = "W"  # [D, I, W, E]

    def show_help(errmsg=""):
        print("Usage: dynflowparser.py"
              + " [Options] [INPUTDIR] [OUTPUTDIR]"
              "\n  Options:"
              "\n    [-a|--all]: Parse all Plans. By default only unsuccess are parsed."  # noqa E501
              "\n    [-d|--debug]: Debug level [D,I,W,E]. Default Warning."  # noqa E501
              "\n    [-f|--from]: Filter events running from this datetime."
              "\n    [-h|--help]: Show help."
              "\n    [-n|--nosql]: Reuse existent sqlite file. (Useful for self debuging)"  # noqa E501
              "\n    [-t|--to]: Filter events running up to this datetime."
              "\n    [-q|--quiet]: Quiet. Don't show progress bar."
              "\n  Arguments:"
              "\n    [INPUTDIR]: Default is current path."
              "\n    [OUTPUTDIR]: Default is current path plus '/dynflowparser/'.")  # noqa E501
        if errmsg != "":
            print("\nERROR: " + errmsg)
            sys.exit(1)
        else:
            sys.exit(0)

    def set_sos_details():
        Conf.sos['timezone'] = Util.exec_command(Conf, "grep 'Time zone:' " + Conf.inputdir + "/sos_commands/systemd/timedatectl |  awk '{print $3}'").strip()  # noqa E501
        Conf.sos['hostname'] = Util.exec_command(Conf, "cat  " + Conf.inputdir + "/hostname").strip()  # noqa E501
        Conf.sos['ram'] = Util.exec_command(Conf, "cat  " + Conf.inputdir + "/free")  # noqa E501
        Conf.sos['cpu'] = Util.exec_command(Conf, "grep -e '^CPU(s)'  " + Conf.inputdir + "/sos_commands/processor/lscpu | awk '{print $2}'").strip()  # noqa E501
        Conf.sos['tuning'] = Util.exec_command(Conf, 'grep tuning  ' + Conf.inputdir + '/etc/foreman-installer/scenarios.d/satellite.yaml | cut -d ":" -f2')  # noqa E501
        Conf.sos['satversion'] = Util.exec_command(Conf, "grep -E 'satellite-6' "  # noqa E501
                                                   + " " + Conf.inputdir + "/installed-rpms | cut -d ' ' -f1").strip()  # noqa E501
        Conf.parser['version'] = Util.exec_command(Conf, "tail -n3 " + Conf.inputdir + "/sos_commands/foreman/dynflow_schema_info | head -1 | sed 's/ *//'").strip()  # noqa E501
        Conf.sos['sosname'] = os.path.basename(os.path.normpath(Conf.inputdir))  # noqa E501
        if Conf.sos['sosname'] == ".":
            Conf.sos['sosname'] = ""

    def get_opts():
        try:
            options, remainder = getopt.getopt(
                sys.argv[1:], 'adf:hnt:q', ['all', 'debug=', 'from=', 'help',
                                           'nosql', 'to=', 'quiet'])
            for opt, arg in options:
                if opt == '-a' or opt == '--all':
                    Conf.unsuccess = False
                elif opt == '-d' or opt == '--debug':
                    Conf.debug = arg
                elif opt == '-f' or opt == '--from':
                    Conf.dfrom = arg
                elif opt == '-h' or opt == '--help':
                    Conf.show_help()
                elif opt == '-n' or opt == '--nosql':
                    Conf.writesql = False
                elif opt == '-t' or opt == '--to':
                    Conf.dto = arg
                elif opt == '-q' or opt == '--quiet':
                    Conf.quiet = True
            if len(remainder) > 0:
                if remainder[0].endswith("/"):
                    remainder[0] = remainder[0][:-1]
                Conf.inputdir = remainder[0]
                if not Path(Conf.inputdir).is_dir():
                    Conf.show_help("provided sosreport '" + Conf.inputdir
                                   + "' is not a folder")
                if len(remainder) == 2:
                    Conf.outputdir = remainder[1]
                    if not Path(Conf.outputdir).is_dir():
                        Conf.show_help("provided outputdir "
                                       + Conf.outputdir
                                       + " is not a folder or doesn't exists")
                elif len(remainder) > 2:
                    Conf.show_help("Wrong parameters count")

            if not os.path.exists(Conf.inputdir + "/sos_commands"):
                Conf.show_help("'" + Conf.inputdir + "' doesn't look a valid sosreport folder")  # noqa E501

            Conf.set_sos_details()
            Conf.outputdir = str(Conf.outputdir + "/dynflowparser/"
                                 + Conf.sos['sosname'] + "/").replace('//', '/')  # noqa E501

            if os.path.exists(Conf.outputdir):
                if Conf.writesql:
                    shutil.rmtree(Conf.outputdir)
                else:
                    for d in ["/actions", "/html"]:
                        shutil.rmtree(Conf.outputdir + d)

            os.makedirs(Conf.outputdir + "/actions")
            shutil.copytree(os.path.dirname(
                        os.path.realpath(__file__)) + "/../html",
                        Conf.outputdir + "/html")

            Conf.dbfile = Conf.outputdir + "dynflowparser.db"

        except Exception as e:
            print(e)
