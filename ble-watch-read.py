import os, sys, time, struct
import ConfigParser as configparser
from datetime import datetime, timedelta, date
from base import MiBand2
from constants import ALERT_TYPES, UUIDS
from influxdb import InfluxDBClient
from StringIO import StringIO
import re
import dateutil

basepath = os.path.abspath(os.path.dirname(sys.argv[0])) + "/"
config = configparser.ConfigParser()
config.read(basepath + 'default.config')

try:
        f = open(basepath + sys.argv[2]+".time", 'r')
        timestamp = int(float(f.read()))
        prev_time = datetime.fromtimestamp(timestamp)
        f.close()
        diff = datetime.now() - prev_time
        if diff.seconds/60 < int(config.get('DEFAULT','check_frequency')):
                sys.exit(0)
except Exception, e:
        print "File read error?"


print "\nRunning for", sys.argv[1], "-", sys.argv[2]
print "Time:", datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

try:
        band = MiBand2(sys.argv[1], debug=False)
        band.setSecurityLevel(level="medium")
except Exception, e:
        print "Connection failed?"
        #print e
        sys.exit(0)

heartrates = []

client = InfluxDBClient(config.get('DEFAULT','influx_host'), config.get('DEFAULT','influx_port'), config.get('DEFAULT','influx_user'), config.get('DEFAULT','influx_pass'), config.get('DEFAULT','influx_db'))

hist_ins_dst = sys.argv[2]+"_activity"

tq = client.query("select last(steps) from " + hist_ins_dst)
timeindb = list(tq.get_points())
if len(timeindb) == 0:
    timeindb = [{"time": "1970-01-01T00:00:00Z"}]

def get_heartrate():
        band.start_heart_rate_realtime(heart_measure_callback=read_hr)
        json_body = [
                {
                        "measurement": sys.argv[2],
                        "tags": {
                                "sensor": "heartrate"
                        },
                        "time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "fields": {
                                "value": int(round(float(sum(heartrates))/len(heartrates)))
                        }
                }
        ]
        print "Heart rate:", int(round(float(sum(heartrates))/len(heartrates)))
        client.write_points(json_body)


def read_hr(rate):
        heartrates.append(rate)


def get_steps():
        steps_data = band.get_steps()
        json_body = [
                {
                        "measurement": sys.argv[2],
                        "tags": {
                                "sensor": "steps"
                        },
                        "time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "fields": {
                                "value": steps_data['steps']
                        }
                }
        ]
        print "Steps:", steps_data['steps']
        client.write_points(json_body)


def get_distance():
        steps_data = band.get_steps()
        distance_meters = 0
        if steps_data['meters']:
                distance_meters = steps_data['meters']

        json_body = [
                {
                        "measurement": sys.argv[2],
                        "tags": {
                                "sensor": "distance"
                        },
                        "time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "fields": {
                                "value": distance_meters
                        }
                }
        ]
        print "Meters:", distance_meters
        client.write_points(json_body)


def get_battery():
        batt_data = band.get_battery_info()
        json_body = [
                {
                        "measurement": sys.argv[2],
                        "tags": {
                                "sensor": "batt_level"
                        },
                        "time": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "fields": {
                                "value": batt_data['level']
                        }
                }
        ]
        print "Battery:", batt_data['level']
        client.write_points(json_body)

class Capturing(list):
        def __enter__(self):
            self._stdout = sys.stdout
            sys.stdout = self._stringio = StringIO()
            return self
        def __exit__(self, *args):
            self.extend(self._stringio.getvalue().splitlines())
            del self._stringio
            sys.stdout = self._stdout

def get_historical_data():
        band._auth_previews_data_notif(True)
        start_time = (datetime.now() - timedelta(hours=int(config.get('DEFAULT','prev_hours'))))
        band.start_get_previews_data(start_time)
        with Capturing() as output:
            while band.active:
                band.waitForNotifications(0.1)
        
        for i in range(1,len(output)):
            line = (re.split('[.:;\s]',output[i].strip()))
            if line[1] == "12" and date.today().strftime('%m') == "01":
                datayear = (datetime.now() + dateutil.relativedelta.relativedelta(years=-1)).strftime('%Y')
                tupledate = (datayear,"-",line[1],"-",line[0]," ",line[3],":",line[4])
                strdate = ''.join(tupledate)
                datatimestamp = time.mktime(datetime.strptime(strdate, "%Y-%m-%d %H:%M").timetuple())
                findate = datetime.utcfromtimestamp(datatimestamp).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                tupledate = (date.today().strftime('%Y'),"-",line[1],"-",line[0]," ",line[3],":",line[4])
                strdate = ''.join(tupledate)
                datatimestamp = time.mktime(datetime.strptime(strdate, "%Y-%m-%d %H:%M").timetuple())
                findate = datetime.utcfromtimestamp(datatimestamp).strftime("%Y-%m-%dT%H:%M:%SZ")

            if line[18] == "255" or line[18] == "0":
                fields_data = [{"fields": {"category": line[8], "acceleration": line[11], "steps": line[14]}, "time": findate, "measurement": hist_ins_dst}]
            else:
                fields_data = [{"fields": {"category": line[8], "acceleration": line[11], "steps": line[14], "heart_rate": line[18]}, "time": findate, "measurement": hist_ins_dst}]

            if findate > timeindb[0]['time']:
                client.write_points(fields_data)

def set_time():
        now = datetime.now()
        band.set_current_time(now)

def write_time_to_file():
        f = open(basepath + sys.argv[2]+".time", 'w')
        f.write(str(time.time()))
        f.close()


try:
        band.authenticate()
        set_time()
        get_historical_data()
        get_steps()
        get_distance()
        #get_heartrate()
        get_battery()
        band.disconnect()
        write_time_to_file()
        sys.exit(0)
except Exception, e:
        print e
        band.disconnect()
        sys.exit(0)
