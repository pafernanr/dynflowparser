import argparse
from datetime import datetime
import os


class Conf:

    def __init__(self):
        self.cwd = os.getcwd()
        sufix = datetime.now().strftime('%Y%m%d-%H%M%S')
        self.sosdir = f"dynflowparser-task-export-{sufix}"
        self.workdir = "/tmp"
        self.outdir = f"{self.workdir}/{self.sosdir}"

        self.parser = argparse.ArgumentParser(
            description="Create a Foreman task-export compressed file."
            )
        self.parser.add_argument(
            '-d',
            '--days',
            help='Number of days to export. By default last 14 days.',
            default=14,
            type=self.check_positive
            )
        self.parser.add_argument(
            '-f',
            '--filter',
            help="Filter query. E.g: label LIKE '%%Manifest%%'."
            )
        self.parser.add_argument(
            '-r',
            '--result',
            help="Filter by Task Result.",
            choices=[
                'cancelled',
                'error',
                'pending',
                'success',
                'warning',
                ]
            )
        self.parser.add_argument(
            '-s',
            '--state',
            help="Filter by Task State.",
            choices=[
                'paused',
                'planning',
                'pending',
                'running',
                'scheduled',
                'stopped',
                ]
            )
        self.args = self.parser.parse_args()

        # create required output folders
        os.makedirs(self.outdir)
        os.makedirs(f"{self.outdir}/sos_commands/foreman")
        os.makedirs(f"{self.outdir}/sos_commands/processor")
        os.makedirs(f"{self.outdir}/sos_commands/systemd")
        os.makedirs(f"{self.outdir}/etc/foreman-installer/scenarios.d")
        # shutil.rmtree(self.outdir)

    def check_positive(self, value):
        ivalue = int(value)
        if ivalue <= 0:
            raise argparse.ArgumentTypeError(
                f"{value} is not a positive int value")
        return ivalue
