### dynflowparser
Reads the dynflow files from a [sosreport](https://github.com/sosreport/sos) and generates user friendly html pages for Tasks, Plans, Actions and Steps

- Only unsuccessful Tasks are parsed by default. (Use '-a' to parse all).
- Failed Actions & Steps are automatically expanded on the Plan page for easy error location.
- Indented Actions & Steps json fields.
- Useful data on header: Hostname, Timezone, Satellite version, RAM, CPU, Tuning.
- Dynflow UTC dates are automatically converted to honor sosreport timezone according to "/sos_commands/systemd/timedatectl".
- Automatically opens output on default browser.
- Lynx friendly.

| Tasks list | Task details | Lynx |
| --- | --- | --- |
| ![](https://raw.githubusercontent.com/pafernanr/dynflowparser/refs/heads/main/docs/files/_screenshot1.png) | ![](https://raw.githubusercontent.com/pafernanr/dynflowparser/refs/heads/main/docs/files/_screenshot2.png) | ![](https://raw.githubusercontent.com/pafernanr/dynflowparser/refs/heads/main/docs/files/_screenshot3.png) |

#### Dependencies
Required python libraries:
- python3-dateutil
- python3-jinja2

#### Usage 
~~~
usage: dynflowparser [-h] [-a] [-d {D,I,W,E}] [-f DATEFROM] [-t DATETO] [-n] [-q] [sosreport_path] [output_path]

Get sosreport dynflow files and generates user friendly html pages for tasks, plans, actions and steps

positional arguments:
  sosreport_path        Path to sos report folder. Default is current path.
  output_path           Output path. Default is './dynflowparser/'.

optional arguments:
  -h, --help            show this help message and exit
  -a, --all             Parse all. By default only unsuccess plans are parsed.
  -d {D,I,W,E}, --debug {D,I,W,E}
                        Debug level. Default 'W'
  -f DATEFROM, --from DATEFROM
                        Parse only Plans that were running from this datetime.
  -t DATETO, --to DATETO
                        Parse only Plans that were running up to this datetime.
  -n, --nosql           Reuse existent sqlite file. (Useful for development).
  -q, --quiet           Quiet. Don't show progress bar.
~~~ 

#### Limitations
- sosreport by default requests last 14 days.
- sosreport truncates output files at 100M, hence some records could be missing.
- Only Dynflow schema version 24 is supported. (v20 is not CSV compliant)

#### How to accurately export tasks.
Included `dynflowparser-export-tasks` can be used to overcome sosreport size limitations and get an accurate tasks export tarball. Just execute it as follows.
~~~
Usage: export-tasks.sh DAYS RESULT
  DAYS: Number of days to export.
  RESULT: Filter exported tasks by result: [all cancelled error pending warning].
Example: ./export-tasks.sh 3 all
~~~


