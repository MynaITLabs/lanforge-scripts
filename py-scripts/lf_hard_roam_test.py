"""
Note : please do not overwrite script under progress and is used for cisco
"""

import sys
import os
import importlib
import logging
import time
import datetime
from datetime import datetime
import pandas as pd
import csv

logger = logging.getLogger(__name__)
if sys.version_info[0] != 3:
    logger.critical("This script requires Python 3")
    exit(1)

sys.path.append(os.path.join(os.path.abspath(__file__ + "../../../")))
lfcli_base = importlib.import_module("py-json.LANforge.lfcli_base")
LFCliBase = lfcli_base.LFCliBase
LFUtils = importlib.import_module("py-json.LANforge.LFUtils")
realm = importlib.import_module("py-json.realm")
Realm = realm.Realm
lf_logger_config = importlib.import_module("py-scripts.lf_logger_config")
cv_test_reports = importlib.import_module("py-json.cv_test_reports")
lf_report = cv_test_reports.lanforge_reports
lf_report_pdf = importlib.import_module("py-scripts.lf_report")
lf_csv = importlib.import_module("py-scripts.lf_csv")

from lf_cleanup import lf_clean
from sta_connect2 import StaConnect2
from lf_sniff_radio import SniffRadio
from lf_pcap import LfPcap
from lf_csv import lf_csv


class HardRoam(Realm):
    def __init__(self, lanforge_ip=None,
                 lanforge_port=None,
                 lanforge_ssh_port=None,
                 c1_bssid=None,
                 c2_bssid=None,
                 fiveg_radio=None,
                 twog_radio=None,
                 sixg_radio=None,
                 band=None,
                 sniff_radio=None,
                 num_sta=None,
                 security=None,
                 security_key=None,
                 ssid=None,
                 upstream=None,
                 duration=None,
                 iteration=None,
                 channel=None,
                 option=None,
                 duration_based=None,
                 iteration_based=None,
                 dut_name=[]):
        super().__init__(lanforge_ip,
                         lanforge_port)
        self.lanforge_ip = lanforge_ip
        self.lanforge_port = lanforge_port
        self.lanforge_ssh_port = lanforge_ssh_port
        self.c1_bssid = c1_bssid
        self.c2_bssid = c2_bssid
        self.fiveg_radios = fiveg_radio
        self.twog_radios = twog_radio
        self.sixg_radios = sixg_radio
        self.band = band
        self.sniff_radio = sniff_radio
        self.num_sta = num_sta
        self.ssid_name = ssid
        self.security = security
        self.security_key = security_key
        self.upstream = upstream
        self.duration = duration
        self.iteration = iteration
        self.channel = channel
        self.option = option
        self.iteration_based = iteration_based
        self.duration_based = duration_based
        self.local_realm = realm.Realm(lfclient_host=self.lanforge_ip, lfclient_port=self.lanforge_port)
        self.staConnect = StaConnect2(self.lanforge_ip, self.lanforge_port)
        self.final_bssid = []
        self.pcap_obj = None
        self.pcap_name = None
        self.test_duration = None
        self.client_list = []
        self.dut_name = dut_name

    def get_station_list(self):
        # realm_obj = self.staConnect.localrealm
        sta = self.staConnect.station_list()
        sta_list = []
        for i in sta:
            for j in i:
                sta_list.append(j)
        return sta_list

    def create_n_clients(self, start_id=0, sta_prefix=None, num_sta=None, dut_ssid=None,
                         dut_security=None, dut_passwd=None, radio=None, type=None):

        local_realm = realm.Realm(lfclient_host=self.lanforge_ip, lfclient_port=self.lanforge_port)
        station_profile = local_realm.new_station_profile()
        if self.band == "fiveg":
            radio = self.fiveg_radios
        if self.band == "twog":
            radio = self.twog_radios
        if self.band == "sixg":
            radio = self.sixg_radios

        # pre clean
        sta_list = self.get_station_list()
        print(sta_list)
        if not sta_list:
            print("no stations on lanforge")
        else:
            station_profile.cleanup(sta_list, delay=1)
            LFUtils.wait_until_ports_disappear(base_url=local_realm.lfclient_url,
                                               port_list=sta_list,
                                               debug=True)
            time.sleep(2)
            print("pre cleanup done")

        station_list = LFUtils.portNameSeries(prefix_=sta_prefix, start_id_=start_id,
                                              end_id_=num_sta - 1, padding_number_=10000,
                                              radio=radio)

        if type == "11r-sae-802.1x":
            dut_passwd = "[BLANK]"
        station_profile.use_security(dut_security, dut_ssid, dut_passwd)
        station_profile.set_number_template("00")

        station_profile.set_command_flag("add_sta", "create_admin_down", 1)

        station_profile.set_command_param("set_port", "report_timer", 1500)

        # connect station to particular bssid
        # self.station_profile.set_command_param("add_sta", "ap", self.bssid[0])

        station_profile.set_command_flag("set_port", "rpt_timer", 1)
        if type == "11r":
            station_profile.set_command_flag("add_sta", "80211u_enable", 0)
            station_profile.set_command_flag("add_sta", "8021x_radius", 1)
            station_profile.set_command_flag("add_sta", "disable_roam", 1)
            station_profile.set_wifi_extra(key_mgmt="FT-PSK     ",
                                           pairwise="",
                                           group="",
                                           psk="",
                                           eap="",
                                           identity="",
                                           passwd="",
                                           pin=""
                                           )
        if type == "11r-sae":
            station_profile.set_command_flag("add_sta", "ieee80211w", 2)
            station_profile.set_command_flag("add_sta", "80211u_enable", 0)
            station_profile.set_command_flag("add_sta", "8021x_radius", 1)
            station_profile.set_command_flag("add_sta", "disable_roam", 1)
            station_profile.set_wifi_extra(key_mgmt="FT-SAE     ",
                                           pairwise="",
                                           group="",
                                           psk="",
                                           eap="",
                                           identity="",
                                           passwd="",
                                           pin=""
                                           )

        if type == "11r-sae-802.1x":
            station_profile.set_command_flag("set_port", "rpt_timer", 1)
            station_profile.set_command_flag("add_sta", "ieee80211w", 2)
            station_profile.set_command_flag("add_sta", "80211u_enable", 0)
            station_profile.set_command_flag("add_sta", "8021x_radius", 1)
            station_profile.set_command_flag("add_sta", "disable_roam", 1)
            # station_profile.set_command_flag("add_sta", "ap", "68:7d:b4:5f:5c:3f")
            station_profile.set_wifi_extra(key_mgmt="FT-EAP     ",
                                           pairwise="[BLANK]",
                                           group="[BLANK]",
                                           psk="[BLANK]",
                                           eap="TTLS",
                                           identity="testuser",
                                           passwd="testpasswd",
                                           pin=""
                                           )
        station_profile.create(radio=radio, sta_names_=station_list)
        local_realm.wait_until_ports_appear(sta_list=station_list)
        station_profile.admin_up()
        if local_realm.wait_for_ip(station_list):
            print("All stations got IPs")
            return True
        else:
            print("Stations failed to get IPs")
            return False

    def create_layer3(self, side_a_min_rate, side_a_max_rate, side_b_min_rate, side_b_max_rate,
                      traffic_type, sta_list, ):
        # checked
        print(sta_list)
        print(type(sta_list))
        print(self.upstream)
        cx_profile = self.local_realm.new_l3_cx_profile()
        cx_profile.host = self.lanforge_ip
        cx_profile.port = self.lanforge_port
        # layer3_cols = ['name', 'tx bytes', 'rx bytes', 'tx rate', 'rx rate']
        cx_profile.side_a_min_bps = side_a_min_rate
        cx_profile.side_a_max_bps = side_a_max_rate
        cx_profile.side_b_min_bps = side_b_min_rate
        cx_profile.side_b_max_bps = side_b_max_rate

        # create
        cx_profile.create(endp_type=traffic_type, side_a=sta_list,
                          side_b=self.upstream, sleep_time=0)
        cx_profile.start_cx()

    def get_cx_list(self):
        layer3_result = self.local_realm.cx_list()
        layer3_names = [item["name"] for item in layer3_result.values() if "_links" in item]
        print(layer3_names)
        return layer3_names

    def precleanup(self):
        obj = lf_clean(host=self.lanforge_ip,
                       port=self.lanforge_port,
                       clean_cxs=True,
                       clean_endp=True)
        obj.resource = "all"
        obj.cxs_clean()
        obj.endp_clean()

    def station_data_query(self, station_name="wlan0", query="channel"):
        url = f"/port/{1}/{1}/{station_name}?fields={query}"
        # print("url//////", url)
        response = self.local_realm.json_get(_req_url=url)
        print("response: ", response)
        if (response is None) or ("interface" not in response):
            print("station_list: incomplete response:")
            # pprint(response)
            exit(1)
        y = response["interface"][query]
        return y

    def start_sniffer(self, radio_channel=None, radio=None, test_name="sniff_radio", duration=60):
        self.pcap_name = test_name + str(datetime.now().strftime("%Y-%m-%d-%H-%M")).replace(':', '-') + ".pcap"
        self.pcap_obj = SniffRadio(lfclient_host=self.lanforge_ip, lfclient_port=self.lanforge_port, radio=radio,
                                   channel=radio_channel)
        self.pcap_obj.setup(0, 0, 0)
        time.sleep(5)
        self.pcap_obj.monitor.admin_up()
        time.sleep(5)
        self.pcap_obj.monitor.start_sniff(capname=self.pcap_name, duration_sec=duration)

    def stop_sniffer(self):
        directory = None
        directory_name = "pcap"
        if directory_name:
            directory = os.path.join("", str(directory_name))
        # if os.path.exists(directory):
        #     shutil.rmtree(directory)
        try:

            if not os.path.exists(directory):
                os.mkdir(directory)
        except Exception as x:
            print(x)

        self.pcap_obj.monitor.admin_down()
        time.sleep(2)
        self.pcap_obj.cleanup()
        lf_report.pull_reports(hostname=self.lanforge_ip, port=self.lanforge_ssh_port, username="lanforge",
                               password="lanforge",
                               report_location="/home/lanforge/" + self.pcap_name,
                               report_dir="pcap")
        time.sleep(10)

        return self.pcap_name

    def query_sniff_data(self, pcap_file, filter='wlan.fc.type_subtype==0x001'):
        obj = LfPcap()
        status = obj.get_wlan_mgt_status_code(pcap_file=pcap_file, filter=filter)
        return status

    def sniff_full_data(self, pcap_file, filter):
        obj = LfPcap()
        status = obj.get_packet_info(pcap_file=pcap_file, filter=filter)
        # allure.attach(name="pack", body=str(status))
        return status

    def generate_csv(self):
        file_name = []
        for i in range(self.num_sta):
            file = 'test_client_' + str(i) + '.csv'
            lf_csv_obj = lf_csv(_columns=['Iterations', 'bssid1', 'bssid2', "PASS/FAIL", "Pcap file Name"], _rows=[], _filename=file)
            file_name.append(file)
            lf_csv_obj.generate_csv()
        return file_name

    def open_csv_append(self, fields, name):
        # fields = ['first', 'second', 'third']
        with open(str(name), 'a') as f:
            writer = csv.writer(f)
            writer.writerow(fields)

    def run(self, file_n=None):
        # iteration = [[0,"68", "90"], [0,"45", "78"]]
        #
        # print(file_n)
        # for i,x in zip(file_n, iteration):
        #     self.open_csv_append(fields=x, name=i)
        # exit()
        test_time = datetime.now()
        test_time = test_time.strftime("%b %d %H:%M:%S")
        print("Test started at ", test_time)
        self.final_bssid.extend([self.c1_bssid, self.c2_bssid])
        print("final bssid", self.final_bssid)
        self.precleanup()

        if self.band == "twog":
            self.create_n_clients(sta_prefix="wlan1", num_sta=self.num_sta, dut_ssid=self.ssid_name,
                                  dut_security=self.security, dut_passwd=self.security_key, radio=self.twog_radios,
                                  type="11r")

        if self.band == "fiveg":
            self.create_n_clients(sta_prefix="wlan", num_sta=self.num_sta, dut_ssid=self.ssid_name,
                                  dut_security=self.security, dut_passwd=self.security_key, radio=self.fiveg_radios,
                                  type="11r")
        if self.band == "sixg":
            self.create_n_clients(sta_prefix="wlan", num_sta=self.num_sta, dut_ssid=self.ssid_name,
                                  dut_security=self.security, radio=self.sixg_radios,
                                  type="11r-sae-802.1x")

        # check if all stations have ip
        sta_list = self.get_station_list()
        print(sta_list)
        val = self.wait_for_ip(sta_list)
        self.create_layer3(side_a_min_rate=1000000, side_a_max_rate=1000000, side_b_min_rate=0, side_b_max_rate=0,
                           sta_list=sta_list, traffic_type="lf_udp")
        cx_list = self.get_cx_list()

        timeout, variable, iterable_var = None, None, None

        if self.duration_based:
            timeout = time.time() + 60 * float(self.duration)
            iteration_dur = 50000000
            iterable_var = 50000000
            variable = -1

        if self.iteration_based:
            variable = self.iteration
            iterable_var = self.iteration
        if val:

            while variable:
                print("variable", variable)
                iter = None
                if variable != -1:
                    iter = iterable_var - variable
                    variable = variable - 1

                if variable == -1:
                    # need to write duration iteration logic
                    # iter = iterable_var - iteration_dur
                    if self.duration is not None:
                        if time.time() > timeout:
                            break
                time.sleep(1)
                # define ro list per iteration
                row_list = []
                sta_list = self.get_station_list()
                print(sta_list)
                station = self.wait_for_ip(sta_list)
                if station:
                    # get bssid's of all stations connected
                    bssid_list = []
                    for sta_name in sta_list:
                        sta = sta_name.split(".")[2]
                        time.sleep(5)
                        bssid = self.station_data_query(station_name=str(sta), query="ap")
                        bssid_list.append(bssid)
                    print(bssid_list)

                    for sta_name in sta_list:
                        # local_row_list = [0, "68"]
                        local_row_list = []
                        local_row_list.append(str(iter))
                        sta = sta_name.split(".")[2]
                        time.sleep(5)
                        before_bssid = self.station_data_query(station_name=str(sta), query="ap")
                        print(before_bssid)
                        local_row_list.append(before_bssid)
                        print(local_row_list)
                        row_list.append(local_row_list)
                    print(row_list)

                    # check if all element of bssid list has same bssid's
                    result = all(element == bssid_list[0] for element in bssid_list)
                    if result:
                        print("All sstations connected to one ap")
                        #  if all bid are equal then do check to hich ap it is connected
                        formated_bssid = bssid_list[0].lower()
                        station_before = ""
                        if formated_bssid == self.c1_bssid:
                            print("station connected to chamber1 ap")
                            station_before = formated_bssid
                        elif formated_bssid == self.c2_bssid:
                            print("station connected to chamber 2 ap")
                            station_before = formated_bssid
                        print(station_before)

                        # after checking all conditions start roam and start snifffer
                        print("starting snifer")
                        self.start_sniffer(radio_channel=int(self.channel), radio=self.sniff_radio,
                                           test_name="roam_11r_" + str(self.option) + "_iteration_" + str(
                                               iter) + "_",
                                           duration=3600)
                        if station_before == self.final_bssid[0]:
                            print("connected stations bssid is same to bssid list first element")
                            for sta_name in sta_list:
                                sta = sta_name.split(".")[2]
                                print(sta)
                                wpa_cmd = "roam " + str(self.final_bssid[1])
                                wifi_cli_cmd_data1 = {
                                    "shelf": 1,
                                    "resource": 1,
                                    "port": str(sta),
                                    "wpa_cli_cmd": 'scan trigger freq 5180 5300'
                                }
                                wifi_cli_cmd_data = {
                                    "shelf": 1,
                                    "resource": 1,
                                    "port": str(sta),
                                    "wpa_cli_cmd": wpa_cmd
                                }
                                print(wifi_cli_cmd_data)
                                # cli_base = LFCliBase(_lfjson_host=self.lanforge_ip, _lfjson_port=self.lanforge_port)
                                self.local_realm.json_post("/cli-json/wifi_cli_cmd", wifi_cli_cmd_data1)
                                time.sleep(2)
                                self.local_realm.json_post("/cli-json/wifi_cli_cmd", wifi_cli_cmd_data)
                        else:
                            print("connected stations bssid is same to bssid list second  element")
                            for sta_name in sta_list:
                                sta = sta_name.split(".")[2]
                                wifi_cmd = ""
                                if self.option == "ota":
                                    wifi_cmd = "roam " + str(self.final_bssid[0])
                                if self.option == "otds":
                                    wifi_cmd = "ft_ds " + str(self.final_bssid[0])
                                print(sta)
                                wifi_cli_cmd_data1 = {
                                    "shelf": 1,
                                    "resource": 1,
                                    "port": str(sta),
                                    "wpa_cli_cmd": 'scan trigger freq 5180 5300'
                                }
                                wifi_cli_cmd_data = {
                                    "shelf": 1,
                                    "resource": 1,
                                    "port": str(sta),
                                    "wpa_cli_cmd": wifi_cmd
                                }
                                print(wifi_cli_cmd_data)
                                # cli_base = LFCliBase(_lfjson_host=self.lanforge_ip, _lfjson_port=self.lanforge_port)
                                self.local_realm.json_post("/cli-json/wifi_cli_cmd", wifi_cli_cmd_data1)
                                time.sleep(2)
                                self.local_realm.json_post("/cli-json/wifi_cli_cmd", wifi_cli_cmd_data)

                        time.sleep(40)
                        self.wait_for_ip(sta_list)
                        bssid_list_1 = []
                        for sta_name in sta_list:
                            sta = sta_name.split(".")[2]
                            time.sleep(5)
                            bssid = self.station_data_query(station_name=str(sta), query="ap")
                            bssid_list_1.append(bssid)
                        print(bssid_list_1)
                        for i, x in zip(row_list, bssid_list_1):
                            i.append(x)
                        print("row list", row_list)
                        # check if all are equal
                        result = all(element == bssid_list_1[0] for element in bssid_list_1)

                        res = ""
                        pass_fail_list = []
                        pcap_file_list = []
                        if result:
                            station_after = bssid_list_1[0].lower()
                            if station_after == station_before or station_after == "na":
                                print("station did not roamed")
                                res = "FAIL"
                            elif station_after != station_before:
                                print("client performed roam")
                                res = "PASS"

                            if res == "FAIL":
                                res = "FAIL"

                        # stop sniff and attach data
                        print("stop sniff")
                        file_name_ = self.stop_sniffer()
                        file_name = "./pcap/" + str(file_name_)
                        print("pcap file name", file_name)
                        time.sleep(10)

                        if res == "PASS":
                            query_reasso_response = self.query_sniff_data(pcap_file=str(file_name),
                                                                          filter="(wlan.fc.type_subtype eq 3 && wlan.fixed.status_code == 0x0000 && wlan.tag.number == 55)")
                            print("query", query_reasso_response)
                            if len(query_reasso_response) != 0:
                                for i  in range(len(query_reasso_response)):
                                    if query_reasso_response[i] == "Successful":
                                        print("reassociation reponse present check for auth rquest")
                                        query_auth_response = self.query_sniff_data(pcap_file=str(file_name),
                                                                                filter="(wlan.fixed.auth.alg == 2 && wlan.fixed.status_code == 0x0000 && wlan.fixed.auth_seq == 0x0002)")
                                        if len(query_auth_response) != 0:
                                            if query_auth_response[i] == "Successful":
                                                print("authentcation is present")
                                                pass_fail_list.append("PASS")
                                                pcap_file_list.append(str(file_name))
                                            else:
                                                pass_fail_list.append("FAIL")
                                                pcap_file_list.append(str(file_name))

                                    else:
                                        print("pcap_file name for fail instance of iteration value ")

                            else:
                                print("pcap_file for fail instance of iteration value ")

                        else:
                            pass_fail_list.append("FAIL")
                            pcap_file_list.append(str(file_name))
                            print("pcap_file for fail instance of iteration value ")
                        for i, x in zip(row_list, pass_fail_list):
                            i.append(x)
                        print("row list", row_list)
                        for i, x in zip(row_list, pcap_file_list):
                            i.append(x)
                        print("row list", row_list)
                        for i, x in zip(file_n, row_list):
                            self.open_csv_append(fields=x, name=i)


                    else:
                        print("all stations are not connected to same ap")
                if self.duration_based:
                    if time.time() > timeout:
                        break

        else:
            print("station's failed to get associate at the begining")

        test_end = datetime.now()
        test_end = test_end.strftime("%b %d %H:%M:%S")
        print("Test ended at ", test_end)
        s1 = test_time
        s2 = test_end  # for example
        FMT = '%b %d %H:%M:%S'
        self.test_duration = datetime.strptime(s2, FMT) - datetime.strptime(s1, FMT)

    def generate_report(self, csv_list, current_path=None):
        report = lf_report_pdf.lf_report(_path= "", _results_dir_name="Hard Roam Test", _output_html="hard_roam.html",
                                         _output_pdf="Hard_roam_test.pdf")
        if current_path is not None:
            report.current_path = os.path.dirname(os.path.abspath(current_path))
        report_path = report.get_report_path()
        report.build_x_directory(directory_name="csv_data")
        for i in csv_list:
            report.move_data(directory="csv_data", _file_name=str(i))
        report.move_data(directory_name="pcap")
        date = str(datetime.now()).split(",")[0].replace(" ", "-").split(".")[0]
        test_setup_info = {
            "DUT Name": self.dut_name,
            "SSID": self.ssid_name,
            "Test Duration": self.test_duration,
        }
        report.set_title("HARD ROAM (11r) TEST")
        report.set_date(date)
        report.build_banner()
        report.set_table_title("Test Setup Information")
        report.build_table_title()

        report.test_setup_table(value="Device under test", test_setup_data=test_setup_info)

        report.set_obj_html("Objective", "The Hard Roam (11r) Test is designed to test the performance of the "
                                         "Access Point. The goal is to check whether the 11r configuration of AP for  all the "
                            + str(self.num_sta) +
                            " clients are working as expected or not")
        report.build_objective()



        for i, x in zip(range(self.num_sta), csv_list):
            report.set_table_title("Client information  " + str(i))
            report.build_table_title()
            lf_csv_obj = lf_csv()
            y = lf_csv_obj.read_csv(file_name=str(report_path) + "/csv_data/" + str(x), column="Iterations")
            z = lf_csv_obj.read_csv(file_name=str(report_path) + "/csv_data/" + str(x), column="bssid1")
            u = lf_csv_obj.read_csv(file_name=str(report_path) + "/csv_data/" + str(x), column="bssid2")
            h = lf_csv_obj.read_csv(file_name=str(report_path) + "/csv_data/" + str(x), column="PASS/FAIL")
            p = lf_csv_obj.read_csv(file_name=str(report_path) + "/csv_data/" + str(x), column="Pcap file Name")
            table = {
                "iterations": y,
                "Bssid before": z,
                "Bssid After": u,
                "PASS/FAIL": h,
                "pcap file name": p
            }
            test_setup = pd.DataFrame(table)
            report.set_table_dataframe(test_setup)
            report.build_table()

        test_input_infor = {
            "LANforge ip": self.lanforge_ip,
            "LANforge port": self.lanforge_port,
            "Bands": self.band,
            "Upstream": self.upstream,
            "Stations": self.num_sta,
            "SSID": self.ssid_name,
            "Security": self.security,
            "Contact": "support@candelatech.com"
        }
        report.set_table_title("Test input Information")
        report.build_table_title()
        report.test_setup_table(value="Information", test_setup_data=test_input_infor)

        report.build_footer()
        report.write_html()
        report.write_pdf_with_timestamp(_page_size='A4', _orientation='Landscape')
        return report_path


def main():
    obj = HardRoam(lanforge_ip="192.168.100.131",
                   lanforge_port=8080,
                   lanforge_ssh_port=22,
                   c1_bssid="10:f9:20:fd:f3:4d",
                   c2_bssid="68:7d:b4:5f:5c:3d",
                   fiveg_radio="wiphy1",
                   twog_radio=None,
                   sixg_radio=None,
                   band="fiveg",
                   sniff_radio="wiphy2",
                   num_sta=2,
                   security="wpa2",
                   security_key="something",
                   ssid="RoamAP5g",
                   upstream="eth2",
                   duration=None,
                   iteration=2,
                   channel=40,
                   option="ota",
                   duration_based=False,
                   iteration_based=True,
                   dut_name=["AP687D.B45C.1D1C", "AP687D.B45C.1D1C"]
                   )
    # obj.stop_sniffer()
    file = obj.generate_csv()
    obj.run(file_n=file)
    obj.generate_report(csv_list=file)


if __name__ == '__main__':
    main()
