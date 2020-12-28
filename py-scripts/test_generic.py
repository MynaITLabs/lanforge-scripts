#!/usr/bin/env python3
import pprint
import sys
import os

if sys.version_info[0] != 3:
    print("This script requires Python 3")
    exit(1)

if 'py-json' not in sys.path:
    sys.path.append(os.path.join(os.path.abspath('..'), 'py-json'))

import argparse
from LANforge.lfcli_base import LFCliBase
from LANforge import LFUtils
import realm
import time
import datetime
import json

class GenTest(LFCliBase):
    def __init__(self, ssid, security, passwd, sta_list, client, name_prefix, upstream, host="localhost", port=8080,
                 number_template="000", test_duration="5m", type="lfping", dest=None, cmd =None,
                 interval=1, radio=None, speedtest_min_up=None, speedtest_min_dl=None, speedtest_max_ping=None,
                 _debug_on=False,
                 _exit_on_error=False,
                 _exit_on_fail=False,):
        super().__init__(host, port, _local_realm=realm.Realm(host,port), _debug=_debug_on, _halt_on_error=_exit_on_error, _exit_on_fail=_exit_on_fail)
        self.ssid = ssid
        self.radio = radio
        self.upstream = upstream
        self.sta_list = sta_list
        self.security = security
        self.passwd = passwd
        self.number_template = number_template
        self.name_prefix = name_prefix
        self.test_duration = test_duration
        if (speedtest_min_up is not None):
            self.speedtest_min_up = float(speedtest_min_up)
        if (speedtest_min_dl is not None):
            self.speedtest_min_dl = float(speedtest_min_dl)
        if (speedtest_max_ping is not None):
            self.speedtest_max_ping = float(speedtest_max_ping)
        self.debug = _debug_on
        if (client is not None):
            self.client_name = client
        self.station_profile = self.local_realm.new_station_profile()
        self.generic_endps_profile = self.local_realm.new_generic_endp_profile()

        self.station_profile.lfclient_url = self.lfclient_url
        self.station_profile.ssid = self.ssid
        self.station_profile.ssid_pass = self.passwd,
        self.station_profile.security = self.security
        self.station_profile.number_template_ = self.number_template
        self.station_profile.mode = 0

        self.generic_endps_profile.name = name_prefix
        self.generic_endps_profile.type = type
        self.generic_endps_profile.dest = dest
        self.generic_endps_profile.cmd = cmd
        self.generic_endps_profile.interval = interval

    def choose_ping_command(self):
        gen_results = self.json_get("generic/list?fields=name,last+results", debug_=self.debug)
        if self.debug:
            print(gen_results)
        if gen_results['endpoints'] is not None:
            for name in gen_results['endpoints']:
                for k, v in name.items():
                    if v['name'] in self.generic_endps_profile.created_endp and not v['name'].endswith('1'):
                        if v['last results'] != "" and "Unreachable" not in v['last results']:
                            return True, v['name']
                        else:
                            return False, v['name']

    def choose_lfcurl_command(self):
        return False, ''

    def choose_iperf3_command(self):
        gen_results = self.json_get("generic/list?fields=name,last+results", debug_=self.debug)
        if gen_results['endpoints'] is not None:
            pprint.pprint(gen_results['endpoints'])
            #for name in gen_results['endpoints']:
               # pprint.pprint(name.items)
                #for k,v in name.items():
        exit(1)


    def choose_speedtest_command(self):
        gen_results = self.json_get("generic/list?fields=name,last+results", debug_=self.debug)
        if gen_results['endpoints'] is not None:
            for name in gen_results['endpoints']:
                for k, v in name.items():
                    if v['last results'] is not None and v['name'] in self.generic_endps_profile.created_endp and v['last results'] != '':
                        last_results = json.loads(v['last results'])
                        if last_results['download'] is None and last_results['upload'] is None and last_results['ping'] is None:
                            return False, v['name']
                        elif last_results['download'] >= self.speedtest_min_dl and \
                             last_results['upload'] >= self.speedtest_min_up and \
                             last_results['ping'] <= self.speedtest_max_ping:
                            return True, v['name']

    def choose_generic_command(self):
        gen_results = self.json_get("generic/list?fields=name,last+results", debug_=self.debug)
        if (gen_results['endpoints'] is not None):
            for name in gen_results['endpoints']:
                for k, v in name.items():
                    if v['name'] in self.generic_endps_profile.created_endp and not v['name'].endswith('1'):
                        if v['last results'] != "" and "not known" not in v['last results']:
                            return True, v['name']
                        else:
                            return False, v['name']

    def start(self, print_pass=False, print_fail=False):
        self.station_profile.admin_up()
        temp_stas = []
        for station in self.sta_list.copy():
            temp_stas.append(self.local_realm.name_to_eid(station)[2])
        if self.debug:
            pprint.pprint(self.station_profile.station_names)
        LFUtils.wait_until_ports_admin_up(base_url=self.lfclient_url, port_list=self.station_profile.station_names)
        if self.local_realm.wait_for_ip(temp_stas):
            self._pass("All stations got IPs")
        else:
            self._fail("Stations failed to get IPs")
            self.exit_fail()
        cur_time = datetime.datetime.now()
        passes = 0
        expected_passes = 0
        self.generic_endps_profile.start_cx()
        time.sleep(15)
        end_time = self.local_realm.parse_time("30s") + cur_time
        print("Starting Test...")
        result = False
        while cur_time < end_time:
            cur_time = datetime.datetime.now()
            if self.generic_endps_profile.type == "lfping":
                result = self.choose_ping_command()
            elif self.generic_endps_profile.type == "generic":
                result = self.choose_generic_command()
            elif self.generic_endps_profile.type == "lfcurl":
                result = self.choose_lfcurl_command()
            elif self.generic_endps_profile.type == "speedtest":
                result = self.choose_speedtest_command()
            elif self.generic_endps_profile.type == "iperf3":
                result = self.choose_iperf3_command()
            else:
                continue
            expected_passes += 1
            if result is not None:
                if result[0]:
                    passes += 1
                else:
                    self._fail("%s Failed to ping %s " % (result[1], self.generic_endps_profile.dest))
                    break
            time.sleep(1)

        if passes == expected_passes:
            self._pass("PASS: All tests passed")

    def stop(self):
        print("Stopping Test...")
        self.generic_endps_profile.stop_cx()
        self.station_profile.admin_down()

    def build(self):
        self.station_profile.use_security(self.security, self.ssid, self.passwd)
        self.station_profile.set_number_template(self.number_template)
        print("Creating stations")
        self.station_profile.set_command_flag("add_sta", "create_admin_down", 1)
        self.station_profile.set_command_param("set_port", "report_timer", 1500)
        self.station_profile.set_command_flag("set_port", "rpt_timer", 1)

        self.station_profile.create(radio=self.radio, sta_names_=self.sta_list, debug=self.debug)

        self.generic_endps_profile.create(ports=self.station_profile.station_names, sleep_time=.5)
        self._pass("PASS: Station build finished")

    def cleanup(self, sta_list):
        self.generic_endps_profile.cleanup()
        self.station_profile.cleanup(sta_list)
        LFUtils.wait_until_ports_disappear(base_url=self.lfclient_url, port_list=sta_list, debug=self.debug)


def main():
    parser = LFCliBase.create_basic_argparse(
        prog='test_generic.py',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''Create generic endpoints and test for their ability to execute chosen commands\n''',
        description='''test_generic.py
--------------------
Generic command example:
python3 ./test_generic.py 
    --mgr localhost (optional)
    --mgr_port 4122 (optional)
    --upstream_port eth1 (optional)
    --radio wiphy0 (required)
    --num_stations 3 (optional)
    --security {open|wep|wpa|wpa2|wpa3} (required)
    --ssid netgear (required)
    --passwd admin123 (required)
    --type lfping  {generic|lfping|iperf3-client | speedtest | lf_curl} (required)
    --dest 10.40.0.1 (required - also target for iperf3)
    --test_duration 2m 
    --interval 1s 
    --debug 


    Example commands: 
    LFPING:
    ./test_generic.py --mgr localhost --mgr_port 4122 --radio wiphy0 --num_stations 7 --ssid jedway-wpa2-x2048-4-1 --passwd jedway-wpa2-x2048-4-1 --type lfping --dest 10.40.0.1 --security wpa2
    LFCURL (under construction):
    ./test_generic.py --mgr localhost --mgr_port 4122 --radio wiphy1  --num_stations 26 --ssid jedway-wpa2-x2048-4-1 --passwd jedway-wpa2-x2048-4-1 --security wpa2 --type lfcurl --dest 10.40.0.1
    GENERIC: 
    ./test_generic.py --mgr localhost--mgr_port 4122 --radio wiphy1  --num_stations 2 --ssid jedway-wpa2-x2048-4-1 --passwd jedway-wpa2-x2048-4-1 --security wpa2 --type generic
    SPEEDTEST:
  ./test_generic.py --mgr localhost --mgr_port 4122 --radio wiphy2 --num_stations 13 --ssid jedway-wpa2-x2048-4-1 --passwd jedway-wpa2-x2048-4-1 --type speedtest --speedtest_min_up 20 
    --speedtest_min_dl 20 --speedtest_max_ping 150 --security wpa2
    IPERF3 (under construction):
   ./test_generic.py --mgr localhost --mgr_port 4122 --radio wiphy1 --num_stations 3 --ssid jedway-wpa2-x2048-4-1 --passwd jedway-wpa2-x2048-4-1 --security wpa2 --type iperf3 
''')

    parser.add_argument('--type', help='type of command to run: generic, lfping, iperf3-client, iperf3-server, lfcurl', default="lfping")
    parser.add_argument('--cmd', help='specifies command to be run by generic type endp', default='')
    parser.add_argument('--dest', help='destination IP for command', default="10.40.0.1")
    parser.add_argument('--test_duration', help='duration of the test eg: 30s, 2m, 4h', default="2m")
    parser.add_argument('--interval', help='interval to use when running lfping (1s, 1m)', default=1)
    parser.add_argument('--speedtest_min_up', help='sets the minimum upload threshold for the speedtest type', default=None)
    parser.add_argument('--speedtest_min_dl', help='sets the minimum download threshold for the speedtest type', default=None)
    parser.add_argument('--speedtest_max_ping', help='sets the minimum ping threshold for the speedtest type', default=None)
    parser.add_argument('--client', help='client to the iperf3 server',default=None)

    args = parser.parse_args()
    num_sta = 2
    if (args.num_stations is not None) and (int(args.num_stations) > 0):
        num_stations_converted = int(args.num_stations)
        num_sta = num_stations_converted

    station_list = LFUtils.portNameSeries(radio=args.radio,
                                          prefix_="sta",
                                          start_id_=0,
                                          end_id_=num_sta-1,
                                          padding_number_=100)

    generic_test = GenTest(host=args.mgr, port=args.mgr_port,
                           number_template="00",
                           radio=args.radio,
                           sta_list=station_list,
                           name_prefix="GT",
                           type=args.type,
                           dest=args.dest,
                           cmd=args.cmd,
                           interval=1,
                           ssid=args.ssid,
                           upstream=args.upstream_port,
                           passwd=args.passwd,
                           security=args.security,
                           test_duration=args.test_duration,
                           speedtest_min_up=args.speedtest_min_up,
                           speedtest_min_dl=args.speedtest_min_dl,
                           speedtest_max_ping=args.speedtest_max_ping,
                           client=args.client,
                           _debug_on=args.debug)

    generic_test.cleanup(station_list)
    generic_test.build()
    if not generic_test.passes():
        print(generic_test.get_fail_message())
        generic_test.exit_fail()        
    generic_test.start()
    if not generic_test.passes():
        print(generic_test.get_fail_message())
        generic_test.exit_fail()
    generic_test.stop()
    time.sleep(30)
    generic_test.cleanup(station_list)
    if generic_test.passes():
        generic_test.exit_success()



if __name__ == "__main__":
    main()
