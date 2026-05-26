# DynflowParser

## Description

DynflowParser reads Dynflow task data from a [sosreport](https://github.com/sosreport/sos) and generates user-friendly HTML pages for analyzing Foreman/Satellite task execution. It provides an intuitive interface to browse Tasks, Plans, Actions, and Steps with automatic error highlighting and timezone conversion.

The companion command `dynflowparser-export-tasks` overcomes sosreport file size limitations by exporting tasks directly from the Foreman database.

| Tasks List | Task Details | Lynx Support |
| --- | --- | --- |
| ![](https://raw.githubusercontent.com/pafernanr/dynflowparser/refs/heads/main/docs/files/_screenshot1.png) | ![](https://raw.githubusercontent.com/pafernanr/dynflowparser/refs/heads/main/docs/files/_screenshot2.png) | ![](https://raw.githubusercontent.com/pafernanr/dynflowparser/refs/heads/main/docs/files/_screenshot3.png) |

## Main Features

- **Smart Filtering**: Only unsuccessful tasks parsed by default (use `-a` for all tasks)
- **Error Navigation**: Failed Actions & Steps automatically expanded for quick troubleshooting
- **System Context**: Header displays Hostname, Timezone, Satellite version, RAM, CPU, and Tuning profile
- **Timezone Support**: UTC dates automatically converted to sosreport timezone
- **Formatting**: Indented and readable JSON fields for Actions & Steps
- **HTTP Server**: Built-in web server with `--httpd-server` and `--ssh-tunnel` options
- **Browser Integration**: Automatically opens output in default browser
- **CLI Friendly**: Lynx-compatible for terminal-based browsing

## Requirements

- Python 3.6+
- Required libraries:
  - Jinja2
  - pandas
  - pytz

## Installation

**Using pip:**
```bash
pip install dynflowparser
```

**Using prebuilt packages:**

Download from [Latest Release](https://github.com/pafernanr/dynflowparser/releases/latest)

## Usage

### dynflowparser

```bash
dynflowparser [-h] [-a] [-d {D,I,W,E}] [-f DATE_FROM] [-t DATE_TO] 
              [-l LAST_N_DAYS] [-n] [-q] [-o OUTPUT_PATH] 
              [--httpd-server | --ssh-tunnel] [sosreport_path]
```

**Positional arguments:**
- `sosreport_path`: Path to sosreport folder (default: current directory)

**Optional arguments:**
- `-a, --all`: Parse all tasks (default: only unsuccessful)
- `-d, --debug {D,I,W,E}`: Debug level (default: W)
- `-f, --from DATE_FROM`: Parse tasks running from this datetime
- `-t, --to DATE_TO`: Parse tasks running up to this datetime
- `-l, --last LAST_N_DAYS`: Parse only last N days (overrides `--from` and `--to`)
- `-n, --nosql`: Reuse existing SQLite file (useful for development)
- `-q, --quiet`: Quiet mode, no progress bar
- `-o, --output_path OUTPUT_PATH`: Write output to this path (default: `./dynflowparserng/`)
- `--httpd-server`: Start HTTP server to serve generated pages
- `--ssh-tunnel`: Start HTTP server with SSH tunnel instructions (localhost binding)

**Examples:**
```bash
# Parse sosreport in current directory
dynflowparser

# Parse all tasks from specific sosreport
dynflowparser -a /path/to/sosreport

# Parse last 7 days with HTTP server
dynflowparser -l 7 --httpd-server /path/to/sosreport

# Parse with SSH tunnel for remote access
dynflowparser --ssh-tunnel /path/to/sosreport
```

### dynflowparser-export-tasks

This command must be executed on the Foreman/Satellite server.

```bash
dynflowparser-export-tasks [-h] [-d DAYS] [-f FILTER] 
                           [-r {cancelled,error,pending,success,warning}]
                           [-s {paused,planning,pending,running,scheduled,stopped}]
```

**Optional arguments:**
- `-d, --days DAYS`: Number of days to export (default: 14)
- `-f, --filter FILTER`: Custom filter query (e.g., `label LIKE '%Manifest%'`)
- `-r, --result`: Filter by task result
- `-s, --state`: Filter by task state

**Examples:**
```bash
# Export last 14 days (default)
dynflowparser-export-tasks

# Export last 30 days of failed tasks
dynflowparser-export-tasks -d 30 -r error

# Export tasks matching specific label
dynflowparser-export-tasks -f "label LIKE '%Repository%'"
```

## Limitations

- Sosreport requests last 14 days by default
- Sosreport truncates output files at 100MB, potentially missing records
- Supported Dynflow schema versions: 24 (Satellite 6.11), 25 (Satellite 6.19+)
- For larger datasets, use `dynflowparser-export-tasks` on the Foreman server

---

**Project**: https://github.com/pafernanr/dynflowparser  
**License**: GPLv3
