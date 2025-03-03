### dynflowparser
Reads the dynflow files from a [sosreport](https://github.com/sosreport/sos) and generates user friendly html pages for Tasks, Plans, Actions and Steps.
Companion command `dynflowparser-export-tasks` helps to overcome `sosreport` file size limitations. (Read [Limitations](#limitations) below)

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
- Jinja2>=3.1.3
- python_dateutil>=2.8.2

#### Installation
~~~
pip install dynflowparser
~~~

#### `dynflowparser` Usage
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

#### `dynflowparser-export-tasks` Usage
This command must be executed on the `Foreman` server.
~~~
usage: dynflowparser-export-tasks [-h] [-d DAYS] [-f FILTER] [-r {cancelled,error,pending,success,warning}] [-s {paused,planning,pending,running,scheduled,stopped}]

Create a Foreman task-export compressed file.

options:
  -h, --help            show this help message and exit
  -d DAYS, --days DAYS  Number of days to export. By default last 14 days.
  -f FILTER, --filter FILTER
                        Filter query. E.g: label LIKE '%Manifest%'.
  -r {cancelled,error,pending,success,warning}, --result {cancelled,error,pending,success,warning}
                        Filter by Task Result.
  -s {paused,planning,pending,running,scheduled,stopped}, --state {paused,planning,pending,running,scheduled,stopped}
                        Filter by Task State.
~~~

#### Limitations
- sosreport by default requests last 14 days.
- sosreport truncates output files at 100M, hence some records could be missing.
- Only Dynflow schema version 24 is supported. (v20 is not CSV compliant)
