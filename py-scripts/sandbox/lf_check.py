#!/usr/bin/python3

'''
NAME:
lf_check.py

PURPOSE:
Configuration for lf_check.py , runs various tests

EXAMPLE:
lf_check.py

NOTES:

'''

import sys
if sys.version_info[0]  != 3:
    print("This script requires Python3")
    exit()

import os
import logging
import time
from time import sleep
import argparse
import json
from json import load
import configparser
from pprint import *
import subprocess
import sys
#from ..lf_report import lf_report
sys.path.append('../')
from lf_report import lf_report
    

CONFIG_FILE = os.getcwd() + '/lf_check_config.ini'    
RUN_CONDITION = 'ENABLE'

# see https://stackoverflow.com/a/13306095/11014343
class FileAdapter(object):
    def __init__(self, logger):
        self.logger = logger
    def write(self, data):
        # NOTE: data can be a partial line, multiple lines
        data = data.strip() # ignore leading/trailing whitespace
        if data: # non-blank
           self.logger.info(data)
    def flush(self):
        pass  # leave it to logging to flush properly


class lf_check():
    def __init__(self,
                _csv_outfile):
        self.lf_mgr_ip = ""
        self.lf_mgr_port = "" 
        self.radio_dict = {}
        self.test_dict = {}
        path_parent = os.path.dirname(os.getcwd())
        os.chdir(path_parent)
        self.scripts_wd = os.getcwd()
        self.results = ""
        self.csv_outfile = _csv_outfile

    
    # Functions in this section are/can be overridden by descendants
    def read_config_contents(self):
        print("read_config_contents {}".format(CONFIG_FILE))
        config_file = configparser.ConfigParser()
        success = True
        success = config_file.read(CONFIG_FILE)
        print("{}".format(success))
        print("{}".format(config_file))

        if 'LF_MGR' in config_file.sections():
            section = config_file['LF_MGR']
            self.lf_mgr_ip = section['LF_MGR_IP']
            self.lf_mgr_port = section['LF_MGR_PORT']
            print("lf_mgr_ip {}".format(self.lf_mgr_ip))
            print("lf_mgr_port {}".format(self.lf_mgr_port))

        # NOTE: this may need to be a list for ssi 
        if 'RADIO_DICTIONARY' in config_file.sections():
            section = config_file['RADIO_DICTIONARY']
            self.radio_dict = json.loads(section.get('RADIO_DICT', self.radio_dict))

        if 'TEST_DICTIONARY' in config_file.sections():
            section = config_file['TEST_DICTIONARY']
            # for json replace the \n and \r they are invalid json characters, allows for multiple line args 
            self.test_dict = json.loads(section.get('TEST_DICT', self.test_dict).replace('\n',' ').replace('\r',' '))
            #print("test_dict {}".format(self.test_dict))

    def load_factory_default_db(self):
        print("file_wd {}".format(self.scripts_wd))
        try:
            os.chdir(self.scripts_wd)
            print("Current Working Directory {}".format(os.getcwd()))
        except:
            print("failed to change to {}".format(self.scripts_wd))

        # no spaces after FACTORY_DFLT
        command = "./{} {}".format("scenario.py", "--load FACTORY_DFLT")
        process = subprocess.run((command).split(' '), check= True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,timeout=20)
        print("###################### STDOUT - scenario load FACTORY_DFLT #########################")
        print(process.stdout)
        print("###################### STDERR - scenario load FACTORY_DFLT #########################")
        print(process.stderr)

    def load_blank_db(self):
        print("file_wd {}".format(self.scripts_wd))
        try:
            os.chdir(self.scripts_wd)
            print("Current Working Directory {}".format(os.getcwd()))
        except:
            print("failed to change to {}".format(self.scripts_wd))

        # no spaces after FACTORY_DFLT
        command = "./{} {}".format("scenario.py", "--load BLANK")
        process = subprocess.run((command).split(' '), check= True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,timeout=20)
        print("###################### STDOUT - scenario load BLANK #########################")
        print(process.stdout)
        print("###################### STDERR - scenario load BLANK #########################")
        print(process.stderr)


    def run_script_test(self):
        for test in self.test_dict:
            # load the default database 
            if self.test_dict[test]['enabled'] == "TRUE":
                # loop through radios
                for radio in self.radio_dict:
                    # Replace RADIO, SSID, PASSWD, SECURITY with actual config values (e.g. RADIO_0_CFG to values)
                    # not "KEY" is just a word to refer to the RADIO define (e.g. RADIO_0_CFG) to get the vlaues
                    if self.radio_dict[radio]["KEY"] in self.test_dict[test]['args']:
                        self.test_dict[test]['args'] = self.test_dict[test]['args'].replace(self.radio_dict[radio]["KEY"],'--radio "{}" --ssid "{}" --passwd "{}" --security "{}"'
                        .format(self.radio_dict[radio]['RADIO'],self.radio_dict[radio]['SSID'],self.radio_dict[radio]['PASSWD'],self.radio_dict[radio]['SECURITY']))
                # Clear out the database
                self.load_factory_default_db()
                #self.load_blank_db()
                sleep(5) # the sleep is to allow for the database to stablize

                # CMR this is just to get the directory with the scripts to run. 
                print("file_wd {}".format(self.scripts_wd))
                try:
                    os.chdir(self.scripts_wd)
                    print("Current Working Directory {}".format(os.getcwd()))
                except:
                    print("failed to change to {}".format(self.scripts_wd))
                cmd_args = "{}".format(self.test_dict[test]['args'])
                command = "./{} {}".format(self.test_dict[test]['command'], cmd_args)
                #command = "{}/{}".format(scripts_wd,self.test_dict[test]['command'])
                # cmd_args = "{}".format(self.test_dict[test]['args'])
                print("command: {}".format(command))
                print("cmd_args {}".format(cmd_args))

                # Put lanforge in known state

                #try:
                process = subprocess.run((command).split(' '), check= True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
                #process = subprocess.run((command).split(' '), check= True, capture_output=True, timeout=30 )
                #pss1 = process.stdout.decode('utf-8', 'ignore')
                #print(pss1)

                
                #print("###################### STDOUT #########################")
                print(process.stdout)
                if (process.stdout == ''):
                    print("stdout empty")
                else:
                    print("stdout not empty")                    
                #print("###################### STDERR #########################")
                # if the stderr is empty the test is considered , does there need to check for pass fail
                print(process.stderr)
                if (process.stderr == ''):
                    print("stderr empty")
                else:
                    print("stderr not empty")
                #except:
                #    print("exception on command: {}".format(command))

def main():
    # arguments
    parser = argparse.ArgumentParser(
        prog='lf_check.py',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''\
            lf_check.py : for running scripts listed in lf_check_config.ini file
            ''',
        description='''\
lf_check.py
-----------

Summary :
---------
for running scripts listed in lf_check_config.ini
            ''')

    parser.add_argument('--csv_outfile', help="--csv_outfile <Output file for csv data", default="")

    args = parser.parse_args()    

    # Create report, instanciate a reporting class
    # need to be able to pass in the naming?
    report = lf_report(_results_dir_name = "lf_check",_output_html="lf_check.html",_output_pdf="lf_check.pdf")

    current_time = time.strftime("%m_%d_%Y_%H_%M_%S", time.localtime())
    csv_outfile = "lf_check_{}_{}.csv".format(args.csv_outfile,current_time)
    csv_outfile = report.file_add_path(csv_outfile)
    print("csv output file : {}".format(csv_outfile))

    # create header


    # lf_check() class created
    check = lf_check(_csv_outfile = csv_outfile)

    #check.parse_ap_stats()
    check.read_config_contents() # CMR need mode to just print out the test config and not run 


    check.run_script_test()

    # Get Results
    # csv_test_results_file =     
    # csv_kpi_file

    # report.set_title("LF Check (lf_check.py)")
    # report.build_banner()
    # report.set_table_title("LF Check Test Results")
    # report.build_table_title()
    # report.set_table_dataframe_from_csv(csv_kpi_file)
    # report.build_table()
    # report.write_html()
    # report.write_pdf(_page_size = 'A3', _orientation='Landscape')
    # report.write_pdf(_page_size = 'A4', _orientation='Portrait')




if __name__ == '__main__':
    main()


