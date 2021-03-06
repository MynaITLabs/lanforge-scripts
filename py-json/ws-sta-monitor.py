#!/usr/bin/python3
'''
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#                                                                             -
# Example of how to filter messages from the :8081 websocket                  -
#                                                                             -
# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
You will need websocket-client:
apt install python3-websocket
'''

import sys
if sys.version_info[0] != 3:
    print("This script requires Python 3")
    exit()
import argparse
import json
import logging
import traceback
import time
from time import sleep
import websocket
import re
try:
    import thread
except ImportError:
    import _thread as thread
import pprint
import LANforge
from LANforge import LFRequest
from LANforge import LFUtils
from LANforge.LFUtils import NA

cre={
    "phy":              re.compile(r'^(1\.\d+):\s+(\S+)\s+\(phy', re.I),
    "ifname":           re.compile(r'(1\.\d+):\s+IFNAME=(\S+)\s+', re.I),
    "port":             re.compile(r'Port (\S+)', re.I),
    "connected":        re.compile(r'.*?CTRL-EVENT-CONNECTED - Connection to ([a-f0-9:]+) complete', re.I),
    "associated":       re.compile(r'^.*?Associated with ([a-f0-9:]+)$', re.I),
    "auth":             re.compile(r'.*: auth ([a-f0-9:]+) -> ([a-f0-9:]+) status: 0: Successful', re.I),
    "authenticated":    re.compile(r'.*?Authenticated with ([a-f0-9:]+)', re.I),
    "associating":      re.compile(r'.*?Trying to associate with ([a-f0-9:]+)', re.I),
    "authenticating":   re.compile(r'.*?[>]SME: Trying to authenticate with ([a-f0-9:]+)', re.I),
}

ignore=[
    ": scan finished",
    ": scan started",
    ": scan aborted: ",
    "CTRL-EVENT-SCAN-STARTED",
    "SCAN-STARTED",
    "SSID-TEMP-DISABLED",
    "CTRL-EVENT-DISCONNECTED",
    "CTRL-EVENT-REGDOM-CHANGE",
    "CTRL-EVENT-SUBNET-STATUS-UPDATE",
    "Reject scan trigger since one is already pending",
    "Failed to initiate AP scan",
    "new station",
    "del station",
    "ping",
    ": Key negotiation completed with ",
    "deleted-alert",
    ": deauth ",
    ": disconnected ",
    "regulatory domain change",
]

rebank = {
    "ifname" : re.compile("IFNAME=(\S+)")
}
websock = None

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
def main():
    global websock
    host = "localhost"
    base_url = "ws://%s:8081"%host
    resource_id = 1     # typically you're using resource 1 in stand alone realm

    parser = argparse.ArgumentParser(description="test creating a station")
    parser.add_argument("-m", "--host", type=str, help="json host to connect to")

    args = None
    try:
      args = parser.parse_args()
      if (args.host is not None):
         host = args.host,
         baseurl = base_url = "ws://%s:8081"%host
    except Exception as e:
      logging.exception(e)
      usage()
      exit(2)

    # open websocket
    websock = start_websocket(base_url, websock)


# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
def sock_filter(wsock, text):
    global ignore
    global interesting
    global rebank
    global cre
    debug = 0
    station_name = None
    resource = None

    for test in ignore:
        if (test in text):
            if (debug):
                print ("                ignoring ",text)
            return;

    try:
        message = json.loads(text)
    except Exception as ex:
        print ("Json Exception: ", repr(ex))
        traceback.print_exc()

    try:
        # big generic filter for wifi-message or details keys
        try:
            if ("details" in message.keys()):
                for test in ignore:
                    if (test in message["details"]):
                        return;
        except KeyError:
            print ("Message lacks key 'details'")

        try:
            if ("wifi-event" in message.keys()):
                for test in ignore:
                    #print ("      is ",test, " in ", message["wifi-event"])
                    if (test in message["wifi-event"]):
                        return;
        except KeyError:
            print("Message lacks key 'wifi-event'" )

        if (("time" in message.keys()) and ("timestamp" in message.keys())):
            return

        if ("name" in message.keys()):
            station_name = message["name"]
        if ("resource" in message.keys()):
            resource = "1.", message["resource"]

        if ("event_type" in message.keys()):
            match_result = cre["port"].match(message["details"])
            if (match_result is not None):
                station_name = match_result.group(1)

            if (message["is_alert"]):
                print ("alert: ", message["details"])
                #LFUtils.debug_printer.pprint(message)
                return
            else:
                #LFUtils.debug_printer.pprint(message)
                if (" IP change from " in message["details"]):
                    if (" to 0.0.0.0" in messsage["details"]):
                        print ("e: %s.%s lost IP address",[resource,station_name])
                    else:
                        print ("e: %s.%s gained IP address",[resource,station_name])
                if ("Link DOWN" in message["details"]):
                    return # duplicates alert

                print ("event: ", message["details"])
                return

        if ("wifi-event" in message.keys()):
            if ("CTRL-EVENT-CONNECTED" in message["wifi-event"]):
                # redunant
                return
            if (("CTRL-EVENT-CONNECTED - Connection to " in message["wifi-event"]) and (" complete" in message["wifi-event"])):
                return;
            if ((": assoc " in message["wifi-event"]) and ("status: 0: Successful" in message["wifi-event"])):
                return
            if ((station_name is None) or (resource is None)):
                try:
                    match_result = cre["phy"].match(message["wifi-event"])
                    if (match_result is not None):
                        #LFUtils.debug_printer.pprint(match_result)
                        #LFUtils.debug_printer.pprint(match_result.groups())
                        resource = match_result.group(1)
                        station_name = match_result.group(2)
                    else:
                        match_result = cre["ifname"].match(message["wifi-event"])
                        #LFUtils.debug_printer.pprint(match_result)
                        #LFUtils.debug_printer.pprint(match_result.groups())
                        if (match_result is not None):
                            resource = match_result.group(1)
                            station_name = match_result.group(2)
                        else:
                            print ("Is there some other combination??? :", message["wifi-event"])
                            station_name = 'no-sta'
                            resource_name = 'no-resource'
                            print ("bleh!")
                except Exception as ex2:
                    print ("No regex match:")
                    print(repr(ex2))
                    traceback.print_exc()
                    sleep(1)

            #print ("Determined station name: as %s.%s"%(resource, station_name))
            if ((": auth ") and ("status: 0: Successful" in message["wifi-event"])):
                match_result = cre["auth"].match(message["wifi-event"])
                if (match_result and match_result.groups()):
                    bssid = match_result.group(1)
                    print ("station %s.%s auth with %s"%(resource,station_name,bssid))
                    return
                else:
                    print ("station %s.%s auth with ??"%(resource,station_name))
                    LFUtils.debug_printer.pprint(match_result)

            if ("Associated with " in message["wifi-event"]):
                match_result = cre["associated"].match(message["wifi-event"])
                if (match_result and match_result.groups()):
                    bssid = match_result.group(1)
                    print ("station %s.%s assocated with %s"%(resource,station_name,bssid))
                    return
                else:
                    print ("station %s.%s assocated with ??"%(resource,station_name))
                    LFUtils.debug_printer.pprint(match_result)

            if (" - Connection to " in message["wifi-event"]):
                match_result = cre["connected"].match(message["wifi-event"])
                if (match_result and match_result.groups()):
                    bssid = match_result.group(1)
                    print ("station %s.%s connected to %s"%(resource,station_name,bssid))
                    return
                else:
                    print ("station %s.%s connected to ??"%(resource,station_name))
                    LFUtils.debug_printer.pprint(match_result)

            if ("disconnected" in message["wifi-event"]):
                print ("Station %s.%s down"%(resource,station_name))
                return

            if ("Trying to associate with " in message["wifi-event"]):
                match_result = cre["associating"].match(message["wifi-event"])

                if (match_result and match_result.groups()):
                    bssid = match_result.group(1)
                    print ("station %s.%s associating with %s"%(resource,station_name,bssid))
                    return
                else:
                    print ("station %s.%s associating with ??"%(resource,station_name))
                    LFUtils.debug_printer.pprint(match_result)

            if ("Trying to authenticate" in message["wifi-event"]):
                match_result = cre["authenticating"].match(message["wifi-event"])

                if (match_result and match_result.groups()):
                    bssid = match_result.group(1)
                    print ("station %s.%s authenticating with %s"%(resource,station_name,bssid))
                    return
                else:
                    print ("station %s.%s authenticating with ??"%(resource,station_name))
                    LFUtils.debug_printer.pprint(match_result)

            if ("Authenticated" in message["wifi-event"]):
                match_result = cre["authenticed"].match(message["wifi-event"])
                LFUtils.debug_printer.pprint(match_result)
                if (match_result and match_result.groups()):
                    bssid = match_result.group(1)
                    print ("station %s.%s authenticated with %s"%(resource,station_name,bssid))
                else:
                    print ("station %s.%s authenticated with ??"%(resource,station_name))

            print ("w: ", message["wifi-event"])
        else:
            print ("\nUnhandled: ")
            LFUtils.debug_printer.pprint(message)

    except KeyError as kerr:
        print ("# ----- Bad Key: ----- ----- ----- ----- ----- ----- ----- ----- ----- -----")
        print ("input: ",text)
        print (repr(kerr))
        traceback.print_exc()
        print ("# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----")
        sleep(1)
        return
    except json.JSONDecodeError as derr:
        print ("# ----- Decode err: ----- ----- ----- ----- ----- ----- ----- ----- ----- -----")
        print ("input: ",text)
        print (repr(derr))
        traceback.print_exc()
        print ("# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----")
        sleep(1)
        return
    except Exception as ex:
        print ("# ----- Exception: ----- ----- ----- ----- ----- ----- ----- ----- ----- -----")
        print(repr(ex))
        print ("input: ",text)
        LFUtils.debug_printer.pprint(message)
        traceback.print_exc()
        print ("# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----")
        sleep(1)
        return

# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
def m_error(wsock, err):
    print ("# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----\n")
    LFUtils.debug_printer.pprint(err)
    print ("# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----\n")

# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
def m_open(wsock):
    def run(*args):
        time.sleep(0.1)
        #ping = json.loads();
        wsock.send('{"text":"ping"}')
    thread.start_new_thread(run, ())
    print ("started websocket client")

# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
def m_close(wsock):
    LFUtils.debug_printer.pprint(wsock)

# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
def start_websocket(uri, websock):
    #websocket.enableTrace(True)
    websock = websocket.WebSocketApp(uri,
        on_message = sock_filter,
        on_error = m_error,
        on_close = m_close)
    websock.on_open = m_open
    websock.run_forever()
    return websock


# ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- ----- -----
if __name__ == '__main__':
    main()


####
####
####