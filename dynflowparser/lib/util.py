import datetime
import re
import subprocess
import sys

import pytz


class Util:

    def __init__(self, debuglevel) -> None:
        self.debuglevel = debuglevel
        self.valid_date_formats = [
            "%Y-%m-%d",
            "%Y-%m-%d %H",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            ]

    def date_from_string(self, d):
        valid = self.valid_date_formats
        for v in valid:
            try:
                return datetime.datetime.strptime(d, v)
            except ValueError:
                continue
        self.debug('E', f"not a valid date: {d!r}. Valid formats: {str(valid)}")
        sys.exit(1)

    def debug(self, sev, msg):
        levels = {'D': 0,
                  'I': 1,
                  'W': 2,
                  'E': 3
                  }
        if levels[sev] >= levels[self.debuglevel]:
            print(f"[{sev}] {str(msg)}\n")
        if sev == 'E':
            sys.exit(1)

    def exec_command(self, cmd):
        self.debug("D", "execcommand: " + cmd)
        p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        stdout = str(stdout.decode("utf-8"))
        stderr = str(stderr.decode("utf-8"))
        if stderr != "":
            print(cmd + "\n" + stderr)
            sys.exit(1)
        return stdout

    def seconds_to_str(self, seconds):
        m = str(round(seconds / 60)) + "m"
        s = str(round(seconds % 60)) + "s"
        return m + s

    def to_timezone(self, tz, d):
        if d is None:
            return d
        to_zone = pytz.timezone(tz)
        from_zone = datetime.timezone.utc
        newd = d.replace(tzinfo=from_zone)
        dlocal = newd.astimezone(to_zone).replace(tzinfo=None)
        return dlocal

    def change_timezone(self, tz, d):
        d = re.sub(r'\.[0-9]+', '', d)
        if d is not None and d != "":
            return self.to_timezone(
                tz, self.date_from_string(d))
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
        """Return number of lines of the input file and set

        all initial parameters for printing progress bar computed from

        the number of all /processed lines of a file.
        """
        try:
            with open(log_file_name, 'r') as file:
                self.all_entries = max(i for i, line in enumerate(file)) + 1
        except Exception as file_exception:
            print(file_exception)

        self.start_time = datetime.datetime.now()
        return self.all_entries

    def set_number_of_entries(self, number: int):
        self.all_entries = number
        self.start_time = datetime.datetime.now()

    def print_bar(self, done_lines: int):
        """If the progress bar should be rewritten (there is something new)

        it is rewritten.
        """
        if self.all_entries == 0:
            return
        tenth_of_percentage = int(1000 * (done_lines / self.all_entries))
        if self.last_printed_tenth_of_percentage >= tenth_of_percentage:
            return
        half_percentage = int((tenth_of_percentage/1000) * (30 + 1))
        new_bar = chr(9608) * half_percentage + " " * (30 - half_percentage)
        now = datetime.datetime.now()
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
