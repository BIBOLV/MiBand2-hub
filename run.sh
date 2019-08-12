#!/bin/bash
#cron job for reading fitness watch data to InfluxDB

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

hciconfig hci0 reset
sleep 2
python $DIR/ble-watch-read.py <<WATCH_BLE_ADDRESS>> <<WATCH_FRIENDLY_NAME>>
