#!/bin/bash
# Author: Pablo Fernández Rodríguez
# Web: https://github.com/pafernanr/dynflowparser
# Licence: GPLv3 https://www.gnu.org/licenses/gpl-3.0.en.html

result=(all cancelled error pending warning)

help () {
    echo "Usage: export-tasks.sh DAYS RESULT"
    echo "  DAYS: Number of days to export."
    echo "  RESULT: Filter exported tasks by result: [${result[@]}]."
    echo "Example: ./export-tasks.sh 3 all"
    echo
    exit 1
}

# Get parameters
if [ "$#" -ne 2 ]; then
    help
elif ! [[ ${result[*]} =~ "$2" ]]; then
    echo -e "ERROR: Unknown result '$2'.\n"
    help
else
    interval="'$1 days'"
    if [[ "$2" != "all" ]]; then
        filter="AND foreman_tasks_tasks.result='${2}'"
    fi
fi

# create output folder
outdir="task-export$(date +%Y%m%d-%H%M%S)"
mkdir /tmp/${outdir}
cd /tmp/${outdir}

# Define output files and queries
declare -A queries
queries[dynflow_schema_info]="select dynflow_schema_info.* from dynflow_schema_info"
queries[foreman_tasks_tasks]="select foreman_tasks_tasks.* from foreman_tasks_tasks 
    where started_at > NOW() - interval ${interval} ${filter}
    order by started_at asc"
queries[dynflow_execution_plans]="select dynflow_execution_plans.* 
    from foreman_tasks_tasks 
    join dynflow_execution_plans on (foreman_tasks_tasks.external_id = dynflow_execution_plans.uuid::varchar) 
    where foreman_tasks_tasks.started_at > NOW() - interval ${interval} ${filter}
    order by foreman_tasks_tasks.started_at asc"
queries[dynflow_actions]="select dynflow_actions.* from foreman_tasks_tasks 
    join dynflow_actions on (foreman_tasks_tasks.external_id = dynflow_actions.execution_plan_uuid::varchar) 
    where foreman_tasks_tasks.started_at > NOW() - interval ${interval} ${filter}
    order by foreman_tasks_tasks.started_at asc"
queries[dynflow_steps]="select dynflow_steps.* from foreman_tasks_tasks 
    join dynflow_steps on (foreman_tasks_tasks.external_id = dynflow_steps.execution_plan_uuid::varchar) 
    where foreman_tasks_tasks.started_at > NOW() - interval ${interval} ${filter}
    order by foreman_tasks_tasks.started_at asc"

# create required output folders
mkdir -p sos_commands/{systemd,foreman,processor}
mkdir -p etc/foreman-installer/scenarios.d

# get basic sosreport details
timedatectl &> sos_commands/systemd/timedatectl
hostname &> hostname
free &> free
lscpu &> sos_commands/processor/lscpu
cp /etc/foreman-installer/scenarios.d/satellite.yaml etc/foreman-installer/scenarios.d/satellite.yaml
rpm -q satellite &> installed-rpms

# execute queries
password=$(grep password /etc/foreman/database.yml | awk '{ print $2 }' | sed 's/"//g')
tmp=$(grep host /etc/foreman/database.yml | awk '{ print $2 }' | sed 's/"//g')
[ -n "$test" ] && dbhost=$tmp || dbhost="localhost"
for file in "${!queries[@]}"; do
    query=${queries[${file}]}
    binary="psql"
    if [[ $file != 'dynflow_schema_info' ]]; then
        binary=/usr/libexec/psql-msgpack-decode
        query="COPY (${query}) TO STDOUT WITH (FORMAT \"csv\", DELIMITER \",\", HEADER)"
    fi
    PGPASSWORD=$password ${binary} --no-password -h $dbhost -p 5432 -U foreman -d foreman -c "${query}" &> sos_commands/foreman/${file}
done
cd /tmp
tar -zcf ${outdir}.tgz ${outdir} && rm -rf ${outdir}
echo "Last ${interval} $3 Tasks exported to /tmp/${outdir}.tgz"
