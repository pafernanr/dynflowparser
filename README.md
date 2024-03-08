### dynflowparser
Get [sosreport](https://github.com/sosreport/sos) dynflow files and generates user friendly html pages for Tasks, Plans, Actions and Steps

- Only unsuccessful Tasks are parsed by default. (Use '-a' to parse all).
- Failed Actions & Steps are automatically expanded on the Plan page for easy error location.
- Indented Actions & Steps json fields.
- Useful data on header: Hostname, Timezone, Satellite version, RAM, CPU, Tuning.
- Dynflow UTC dates are automatically converted to honor sosreport timezone according to "/sos_commands/systemd/timedatectl".
- Automatically opens output on default browser.
- Lynx friendly.

#### Dependencies
Required python libraries:
- python3-dateutil
- python3-jinja2

#### Usage 
~~~
Usage: dynflowparser.py [Options] [INPUTDIR] [OUTPUTDIR]
  Options:
    [-a|--all]: Show all Plans. By default only unsuccess are parsed.
    [-d|--debug]: Debug level [D,I,W,E].
    [-h|--help]: Show help.
    [-n|--nosql]: Reuse existent sqlite file. (Probably only useful for self debuging purposes)
    [-q|--quiet]: Quiet. Don't show progress bar.
  Arguments:
    [INPUTDIR]: Default './'.
    [OUTPUTDIR]: Default './dynflowparser/'.
~~~ 

#### Limitations
- sosreport by default requests last 14 days.
- sosreport truncates output files at 100M, hence some records could be missing.
- Only Dynflow schema version 24 is supported. (v20 is not CSV compliant)
