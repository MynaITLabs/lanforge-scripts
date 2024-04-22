#!/usr/bin/env python3
# This script will start a named set of voip connections and report their data to a csv file
import argparse
import csv
import importlib
import logging
import os
import pprint
import sys
import time
import traceback
# from time import sleep
from pprint import pprint

if sys.version_info[0] != 3:
    print("This script requires Python 3")
    exit(1)
sys.path.append(os.path.join(os.path.abspath(__file__ + "../../../")))
lanforge_api = importlib.import_module("lanforge_client.lanforge_api")
from lanforge_client.lanforge_api import LFSession
from lanforge_client.lanforge_api import LFJsonCommand
from lanforge_client.lanforge_api import LFJsonQuery

logger = logging.getLogger(__name__)


# lf_logger_config = importlib.import_module("py-scripts.lf_logger_config")
# LFUtils = importlib.import_module("py-json.LANforge.LFUtils")
# lfcli_base = importlib.import_module("py-json.LANforge.lfcli_base")
# LFCliBase = lfcli_base.LFCliBase
# realm = importlib.import_module("py-json.realm")
# Realm = realm.Realm


class VoipEndp:
    def __init__(self,
                 name: str,
                 num_calls: int = 0,
                 **kwargs):
        self._name: str = name

        self._phone_num: str = None
        self._mobile_bt_mac: str = None

        self._num_calls = num_calls

    @property
    def name(self):
        """Endpoint name."""
        return self._name

    @property
    def num_calls(self):
        """Number of calls for endpoint when in loop mode."""
        return self._num_calls

    @num_calls.setter
    def num_calls(self, num_calls: str):
        """Set number of calls for endpoint when in loop mode."""
        self._num_calls= num_calls

    @property
    def phone_num(self):
        """Endpoint phone number."""
        return self._phone_num

    @phone_num.setter
    def phone_num(self, phone_num: str):
        """Set endpoint phone number."""
        self._phone_num = phone_num

    @property
    def mobile_bt_mac(self):
        """Endpoint Bluetooth MAC, if resource is a phone."""
        return self._mobile_bt_mac

    @mobile_bt_mac.setter
    def mobile_bt_mac(self, mobile_bt_mac: str):
        """Set endpoint Bluetooth MAC, if resource is a phone."""
        self._mobile_bt_mac = mobile_bt_mac


class VoipCx:
    def __init__(self,
                 name: str,
                 endp_a: VoipEndp = None,
                 endp_b: VoipEndp = None,
                 **kwargs):
        self._name = name

        self._endp_a = endp_a
        self._endp_b = endp_b

    @property
    def name(self):
        """VoIP CX name."""
        return self._name

    @property
    def endp_a(self):
        """VoIP CX endpoint A."""
        return self._endp_a

    @property
    def endp_b(self):
        """VoIP CX endpoint B."""
        return self._endp_b


class VoipReport():
    def __init__(self,
                 lfsession: LFSession,
                 csv_file: str,
                 cx_names_str: str,
                 debug: bool,
                 **kwargs):
        """Initialize VoIP test."""
        self.lfsession = lfsession
        self.debug = debug

        self.__init_csv_output(csv_file=csv_file)
        self.__initialize_voip_cxs(cx_names_str=cx_names_str,
                                   **kwargs)

    def __init_csv_output(self, csv_file: str):
        """Initialize CSV output file."""

        # Parse CSV file, if specified. Otherwise, use generate default in `/home/lanforge/report-data/`
        csv_file_name = f"/home/lanforge/report-data/voip-{time.time()}.csv"
        if csv_file:
            self.csv_filename = csv_file
        else:
            self.csv_filename = csv_file_name
        logger.info(f"Test CSV output file is \'{csv_file_name}\'")

        self.ep_col_names: list = (
            "epoch_time",
            "name",
            "state",
            "reg state",
            "mos-lqo#",
            "mos-lqo",
            "attenuation (agc)",
            "avg delay",
            "snr ref",
            "snr deg",
            "scoring bklg",
            "tx pkts",
            "rx pkts",
            "tx bytes",
            "rx bytes",
            "dropped",
            "ooo pkts",
            "dup pkts",
            "jb silence",
            "jb under",
            "jb over",
            "jb cur",
            "delay",
            "rtp rtt",
            "jitter",
            "vad pkts",
            "calls attempted",
            "calls completed",
            "calls failed",
            "cf 404",
            "cf 408",
            "cf busy",
            "cf canceled",
            "calls answered",
            "destination addr",
            "source addr",
            "elapsed",
            "rst",
            "run",
            "mng",
            "eid",
            # "entity id"
        )
        self.csv_data: list = []

        # Attempt to open CSV file
        try:
            self.csv_fileh = open(self.csv_filename, "w")
            self.csv_writer = csv.writer(self.csv_fileh)
            self.csv_writer.writerow(self.ep_col_names)
            self.last_written_row = 0
        except Exception as e:
            e.print_exc()
            traceback.print_exc()
            exit(1)

    def __initialize_voip_cxs(self, cx_names_str: str, **kwargs):
        """
        Given user-specified list, initialize data structures
        used to store, configure, and query VoIP CXs.
        """
        self.cxs = []
        self.endps_a = []
        self.endps_b = []

        # Parse out CX list string into actual list of CX names
        cx_list = []
        if cx_names_str.find(',') < 0:
            # Only one cx name specified
            cx_list.append(cx_names_str)
        else:
            # Multiple cx names specified
            cx_list.extend(cx_names_str.split(','))

        # If only one CX and is 'all' or 'ALL', user specified to use all VoIP CXs.
        # Check for equality, as want to make sure user can specify
        # a cx name with string 'all' or 'ALL' in it.
        if len(cx_list) == 1 and (cx_list[0] == "all") or (cx_list[0]== "ALL"):
            logger.debug(f"Querying all VoIP CXs")
        else:
            logger.debug(f"Querying parsed VoIP CXs: {cx_list}")

        # TODO: Don't hardcode endpoint names
        #queried_endps = self.__query_voip_endps(endp_list=["all"])

        queried_cxs = self.__query_voip_cxs(cx_list=cx_list)
        for queried_cx in queried_cxs:
            # Queried Cx data is a list of dicts, where each dict
            # has a single key which is the CX name. For example:
            # [
            #   {'TEST1': {'name': 'TEST1'}},
            # ]
            cx_name = list(queried_cx.keys())[0]

            # CX endpoint A
            endp_a = VoipEndp(name=cx_name + "-A")
            self.endps_a.append(endp_a)

            # CX endpoint B
            endp_b = VoipEndp(name=cx_name + "-B")
            self.endps_b.append(endp_b)

            cx = VoipCx(name=cx_name,
                        endp_a=endp_a,
                        endp_b=endp_b,
                        **kwargs)
            self.cxs.append(cx)


    def __query_voip_cxs(self, cx_list: list[str], columns: list[str] = ["name"]):
        """Query and return all VoIP CXs."""
        e_w_list: list = []
        lf_query: LFJsonQuery = self.lfsession.get_query()
        response = lf_query.get_voip(eid_list=cx_list,
                                     requested_col_names=columns,
                                     errors_warnings=e_w_list,
                                     debug=True)
        if not response:
            logger.error(f"Unable to query \'{columns}\' data for VoIP CXs \'{cx_list}\'")
            exit(1)

        # When multiple to return, returned as list of dicts.
        # When one to return, returned as just dict.
        # Package into list of dict (with single element) to simplify processing.
        if isinstance(response, dict):
            response = [response]

        return response


    def __query_voip_endps(self, endp_list: list[str], columns: list[str] = ["name"]):
        """Query and return all VoIP endpoints."""
        e_w_list: list = []
        lf_query: LFJsonQuery = self.lfsession.get_query()
        response = lf_query.get_voip_endp(eid_list=endp_list,
                                          requested_col_names=columns,
                                          errors_warnings=e_w_list,
                                          debug=True)
        if not response:
            logger.error(f"Unable to query \'{columns}\' data for VoIP endpoints \'{endp_list}\'")
            exit(1)

        # When multiple to return, returned as list of dicts.
        # When one to return, returned as just dict.
        # Package into list of dict (with single element) to simplify processing.
        if isinstance(response, dict):
            response = [response]

        return response

    def start(self):
        # query list of voip connections, warn on any not found
        lf_query: LFJsonQuery = self.lfsession.get_query()
        lf_cmd: LFJsonCommand = self.lfsession.get_command()
        e_w_list: list = []

        response = lf_query.get_voip(eid_list=self.cx_list,
                                     requested_col_names=("name"),
                                     errors_warnings=e_w_list,
                                     debug=True)
        lf_cmd: LFJsonCommand = self.lfsession.get_command()
        e_w_list: list = []

        # print(" - - - - - - -  - - - - - - -  - - - - - - -  - - - - - - - ")
        # pprint(response)
        # print(" - - - - - - -  - - - - - - -  - - - - - - -  - - - - - - - ")

        if not response:
            raise ValueError("unable to find voip connections")

        if isinstance(response, dict):
            response = [response]

        for entry in response:
            for (key, value) in entry.items():
                if key == "name":
                    key = value
                if str(self.cx_list[0]).lower() == "all":
                    print(f"adding endpoints for {key}")
                elif key not in self.cx_list:
                    print(f"cx [{key}] not found in {self.cx_list}")
                    continue
                self.voip_endp_list.append(f"{key}-A")
                self.voip_endp_list.append(f"{key}-B")
                # start cx
                try:
                    # print(f"Starting cx {key}")
                    lf_cmd.post_set_cx_state(cx_name=key,
                                             test_mgr='ALL',
                                             suppress_related_commands=True,
                                             cx_state=lf_cmd.SetCxStateCxState.RUNNING.value,
                                             errors_warnings=e_w_list)
                except Exception as e:
                    pprint(['exception:', e, "cx:", key, e_w_list])

    def write_rows(self):
        if self.last_written_row >= (len(self.csv_data) - 1):
            print(f"write_row: row[{self.last_written_row}] already written, rows: {len(self.csv_data)} rows")
            return
        for i in range(self.last_written_row, len(self.csv_data)):
            # pprint(["i:", i, "csv:", self.csv_data[i]])
            row_strs: list = map(str, self.csv_data[i])
            self.csv_writer.writerow(row_strs)
            self.last_written_row = i
        self.csv_fileh.flush()

    def append_to_csv(self, ep_name: str = None, ep_record: dict = None):
        if not ep_name:
            raise ValueError("append_to_csv needs endpoint name")
        if not ep_record:
            raise ValueError("append_to_csv needs endpoint record")
        # pprint(["ep_record:", ep_record])
        new_row: list[str] = []
        # ep_col_names defines the sorted order to retrieve the column values
        for key in self.ep_col_names:
            if "epoch_time" == key:
                new_row.extend([int(time.time())])
                continue
            new_row.append(ep_record[key])
        # pprint(["csv_row:", new_row])
        self.csv_data.append(new_row)

    def monitor(self):
        if not self.ep_col_names:
            raise ValueError("no endpoint names")
        num_running_ep = 1
        lf_query: LFJsonQuery = self.lfsession.get_query()
        # lf_cmd: LFJsonCommand = self.lfsession.get_command()
        e_w_list: list = []
        response: list
        old_mos_value_A = 0
        old_mos_value_B = 0
        append_row_zero_endp_A_flag = True
        append_row_zero_endp_B_flag = True
        wait_flag_A = True
        wait_flag_B = True

        # stop until endpoints actually starts the test else script terminates early.
        while wait_flag_A or wait_flag_B:
            response = lf_query.get_voip_endp(eid_list=self.voip_endp_list,
                                                  debug=False,
                                                  errors_warnings=e_w_list)

            if not response:
                    # pprint(e_w_list)
                    raise ValueError("unable to find endpoint data")

            for entry in response:
                name = list(entry.keys())[0]
                record = entry[name]

                if "-A" in name: # endp A
                    if "Stopped" != record['state']:
                        wait_flag_A = False

                if "-A" in name: # endp B
                    if "Stopped" != record['state']:
                        wait_flag_B = False

                time.sleep(1)

        print("Script is now running....")

        while num_running_ep > 0:
            time.sleep(1)
            try:
                # pprint(["self.voip.endp_list:", self.voip_endp_list])
                num_running_ep = len(self.voip_endp_list)
                response = lf_query.get_voip_endp(eid_list=self.voip_endp_list,
                                                  debug=False,
                                                  errors_warnings=e_w_list)
                if not response:
                    # pprint(e_w_list)
                    raise ValueError("unable to find endpoint data")

                for entry in response:
                    name = list(entry.keys())[0]
                    record = entry[name]
                    # print(f"checking {name}, ", end=None)

                    if "-A" in name: # endp A

                        if (int(record['mos-lqo#']) == 0) and (float(record['mos-lqo']) != 0):
                            if (append_row_zero_endp_A_flag):
                                self.append_to_csv(ep_name=name, ep_record=record) # check record
                                append_row_zero_endp_A_flag = False

                        if int(record['mos-lqo#']) != old_mos_value_A:
                            self.append_to_csv(ep_name=name, ep_record=record)
                            old_mos_value_A = int(record['mos-lqo#'])

                    if "-B" in name: # endp B

                        if (int(record['mos-lqo#']) == 0) and (float(record['mos-lqo']) != 0):
                            if append_row_zero_endp_B_flag:
                                self.append_to_csv(ep_name=name, ep_record=record)
                                append_row_zero_endp_B_flag = False

                        if int(record['mos-lqo#']) != old_mos_value_B:
                            self.append_to_csv(ep_name=name, ep_record=record)
                            old_mos_value_B = int(record['mos-lqo#'])

                    # print("Debug: int(record['calls completed']) " + str(record['calls completed']))
                    # print("Debug: int(record['calls failed']) " + str(record['calls failed']))
                    # print("Debug: int(record['mos-lqo#']) " + str(record['mos-lqo#']))
                    # print("Debug: record['state'] " + str(record['state']))
                    # print()

                    # exit if endp is scoring polqa/pesq and test is stopped.
                    # wait until last call data is fetched
                    # both endp needs to stop separately as we are in a for loop.
                    if int(record['calls completed']) + int(record['calls failed']) == int(record['mos-lqo#']) + 1:
                        if "Stopped" == record['state']:
                            num_running_ep -= 1

                    # exit if other endp is not scoring polqa/pesq and test is stopped.
                    if int(record['mos-lqo#']) == 0:
                        if "Stopped" == record['state']:
                            num_running_ep -= 1

            except Exception as e:
                # self.write_rows()
                traceback.print_exc()
                pprint(['exception:', e, 'e_w_list:', e_w_list])
                self.write_rows()
                exit(1)
            # self.write_rows()

    def report(self):
        self.write_rows()
        print(f"saved {self.csv_filename}")
        print("Script is done....")
        self.csv_fileh.close()


def parse_args():
    parser = argparse.ArgumentParser(
        prog=__file__,
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--host", "--mgr",
                        dest="host",
                        help="URL of the LANforge GUI machine (localhost is default, http://localhost:8080)",
                        type=str,
                        default="localhost")
    parser.add_argument("--csv_file",
                        help="name of the csv output file",
                        required=True,
                        type=str)
    parser.add_argument("--cx_list", "--cx_names",
                        dest="cx_names_str",
                        help="comma separated list of voip connection names, or 'ALL'",
                        required=True,
                        type=str)
    parser.add_argument("--debug",
                        help='Enable debugging',
                        action="store_true",
                        default=False)
    parser.add_argument("--log_level",
                        help='debug message verbosity',
                        type=str)

    return parser.parse_args()


def main():
    args = parse_args()
    lfapi_session = LFSession(lfclient_url=args.host,
                              debug=args.debug)

    # The '**vars(args)' unpacks arguments into named parameters
    # of the VoipReport initializer.
    voip_report = VoipReport(lfsession=lfapi_session,
                             **vars(args))
    voip_report.start()
    voip_report.monitor()
    voip_report.report()


if __name__ == "__main__":
    main()
