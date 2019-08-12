#!/bin/bash
#cron job for reading fitness watch data to InfluxDB

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

sudo hciconfig hci0 reset
sleep 2
python $DIR/ble-watch-read.py 00:00:00:00:00:00 hr_watch_mom
