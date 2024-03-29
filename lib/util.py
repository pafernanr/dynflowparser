'''
Author: Pablo Fernández Rodríguez
Web: https://github.com/pafernanr/dynflowparser
Licence: GPLv3 https://www.gnu.org/licenses/gpl-3.0.en.html
'''
from datetime import datetime as mytime
import datetime
from dateutil import tz
import re
import subprocess
import sys


class Util:
    USERS = {}

    def debug(Conf, sev, msg):
        levels = {'D': 0,
                  'I': 1,
                  'W': 2,
                  'E': 3
                  }
        if levels[sev] >= levels[Conf.debug]:
            print(f"[{sev}] {str(msg)}\n")

    def exec_command(Conf, cmd):
        Util.debug(Conf, "D", "execcommand: " + cmd)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        stdout = str(stdout.decode("utf-8"))
        stderr = str(stderr.decode("utf-8"))
        if stderr != "":
            print(cmd + "\n" + stderr)
            sys.exit(1)
        return stdout

    def seconds_to_str(seconds):
        m = str(round(seconds / 60)) + "m"
        s = str(round(seconds % 60)) + "s"
        return m + s

    def change_timezone(timezone, d):
        d = re.sub(r'\.[0-9]+', '', d)
        if d != "":
            if re.match(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}', d):
                to_zone = tz.gettz(timezone)
                from_zone = tz.gettz('UTC')
                newd = datetime.datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
                newd = newd.replace(tzinfo=from_zone)
                return str(newd.astimezone(to_zone))
            else:
                print("WARNING: date '" + d
                      + "' doesn't match %Y-%m-%d %H:%M:%S")
        return d


# adopted from https://github.com/pavlinamv/rails-load-stats-py/blob/main/progress_bar.py  # noqa E501
class ProgressBarFromFileLines:
    all_entries: int
    start_time: datetime
    last_printed_tenth_of_percentage: int

    def __init__(self) -> None:
        self.all_entries = 0
        self.last_printed_tenth_of_percentage = 0

    def set_number_of_file_lines(self, log_file_name: str):
        """ Return number of lines of the input file and set
    all initial parameters for printing progress bar computed from
    the number of all /processed lines of a file.
    """
        try:
            with open(log_file_name, 'r') as file:
                self.all_entries = max(i for i, line in enumerate(file)) + 1
        except Exception as file_exception:
            print(file_exception)

        self.start_time = mytime.now()
        return self.all_entries

    def set_number_of_entries(self, number: int):
        self.all_entries = number
        self.start_time = mytime.now()

    def print_bar(self, done_lines: int):
        """ If the progress bar should be rewritten (there is something new)
    it is rewritten.
    """
        if self.all_entries == 0:
            return
        tenth_of_percentage = int(1000 * (done_lines / self.all_entries))
        if self.last_printed_tenth_of_percentage >= tenth_of_percentage:
            return
        half_percentage = int((tenth_of_percentage/1000) * (30 + 1))
        new_bar = chr(9608) * half_percentage + " " * (30 - half_percentage)
        now = mytime.now()
        left = (self.all_entries - done_lines) * (now - self.start_time) / done_lines  # noqa E501
        # sec = int(left.total_seconds())
        text = f"\r|{new_bar}| {tenth_of_percentage/10:.1f} %  "  # +\
        #       "Estimated time left: "
        # if sec > 60:
        #    text += f"{format(int(sec / 60))} min "
        # text += f"{format(int(sec % 79)+1)} sec       "
        print(text, end="\r\r")

        # print(tenth_of_percentage)
        if tenth_of_percentage == 999:
            print(" " * 79, end="\r\r")
        self.last_printed_tenth_of_percentage = tenth_of_percentage
