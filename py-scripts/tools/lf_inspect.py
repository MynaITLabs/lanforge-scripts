#!/usr/bin/env python3
'''
    lf_inspect.py  --database <test.db>

    lf_inspect.py will do analysis on a database and comprare entries in a datbase.

TODO :  Add to help how to run or which parameters needed to run: on lanforge, a server that is not lanforge, At a desktop
'''
import sys
import os
import importlib
import plotly.express as px
import pandas as pd
import sqlite3
import argparse
from pathlib import Path
import time
import logging
import re
import csv
import traceback



sys.path.append(os.path.join(os.path.abspath(__file__ + "../../../../")))

lf_report = importlib.import_module("py-scripts.lf_report")
lf_report = lf_report.lf_report
logger = logging.getLogger(__name__)
lf_logger_config = importlib.import_module("py-scripts.lf_logger_config")

# Any style components can be used
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

class inspect_sql:
    def __init__(self,
                _path='.',
                _dir='',
                _database_list=[],
                _element_list=[],
                _csv_results = '',
                _table=None,
                _outfile='',
                _outfile_name='',
                _report_path='',
                _log_path='',
                _lf_inspect_report_path=''
                 ):
        self.path = _path
        self.dir = _dir
        self.table = _table
        self.lf_inspect_report_path = _lf_inspect_report_path
        logger.debug("path: {path}".format(path=self.path))
        logger.debug("dir: {dir}".format(dir=self.dir))
        self.database_list = _database_list
        self.database = []
        self.element_list = _element_list
        self.database_comp = []
        self.conn = None
        self.conn_comp = None
        self.kpi_list = []
        self.html_list = []
        self.conn = None
        self.df = pd.DataFrame()
        self.plot_figure = []
        self.html_results = ""


        # this may or maynot be needed 
        self.dut_model_num_list = "NA"
        self.dut_model_num = "NA"
        self.dut_sw_version_list = "NA"
        self.dut_sw_version = "NA"
        self.dut_hw_version_list = "NA"
        self.dut_hw_version = "NA"
        self.dut_serial_num_list = "NA"
        self.dut_serial_num = "NA"
        self.subtest_passed = 0
        self.subtest_failed = 0
        self.subtest_total = 0
        self.test_run = ""
        self.test_result = 'NA'

        self.junit_test = ''
        # TODO the comparison needs to have a name based
        # on the type of comparison
        self.test_suite = 'Compare Current Run to Previous Run'

        # Used for csv results
        self.csv_results = _csv_results
        self.csv_results_file = ""
        self.csv_results_writer = ""
        self.csv_results_column_headers = ""


        # results
        self.junit_results = ""
        self.html_results = ""
        self.background_green = "background-color:green"
        self.background_red = "background-color:red"
        self.background_orange = "background-color:orange"
        self.background_purple = "background-color:purple"
        self.background_blue = "background-color:blue"

        # Allure information
        self.junit_results = ""
        self.junit_path_only = ""        

    def set_junit_results(self, junit_results):
        self.junit_results = junit_results

    def set_junit_path_only(self, junit_path_only):
        self.junit_path_only = junit_path_only


    def get_html_results(self):
        return self.html_results

    # TODO allow for running of multiple test suites
    def start_junit_testsuites(self):
        self.junit_results += """<?xml version="1.0" encoding="UTF-8" ?>
            <testsuites>
        """

    def finish_junit_testsuites(self):
        self.junit_results += """
        </testsuites>
        """

    def start_junit_testsuite(self):
        self.junit_results += """
        <testsuite name="{suite}">
        """.format(suite=self.test_suite)

    def finish_junit_testsuite(self):
        self.junit_results += """
        </testsuite>
        """

    def get_junit_results(self):
        return self.junit_results


    def start_csv_results(self):
        logger.info("self.csv_results")
        self.csv_results_file = open(self.csv_results, "w")
        self.csv_results_writer = csv.writer(
            self.csv_results_file, delimiter=",")
        # TODO add the kernel information and build information or should that be 
        # done through inspection of the csv file
        # TODO have it match the html results
        self.csv_results_column_headers = [
            'test-rig',
            'test-tag',
            'Graph-Group',
            'test-id',
            'short-description',
            'Units', 
            'Date1',
            'numeric-score-1', 
            'Date2',
            'numeric-score-2',
            'percent']
        self.csv_results_writer.writerow(self.csv_results_column_headers)
        self.csv_results_file.flush()

    def get_junit_results(self):
        return self.junit_results

    # TODO allow for running of multiple test suites
    def start_junit_testsuites(self):
        self.junit_results += """<?xml version="1.0" encoding="UTF-8" ?>
            <testsuites>
        """

    def finish_junit_testsuites(self):
        self.junit_results += """
        </testsuites>
        """

    def start_junit_testsuite(self):
        self.junit_results += """
        <testsuite name="{suite}">
        """.format(suite=self.test_suite)

    def finish_junit_testsuite(self):
        self.junit_results += """
        </testsuite>
        """

    def get_junit_results(self):
        return self.junit_results

    def get_html_results(self):
        return self.html_results

    def start_html_results(self):
        self.html_results += """
                <table border="1" class="dataframe">
                    <thead>
                        <tr style="text-align: left;">
                          <th>test_rig</th>
                          <th>test_tag</th>
                          <th>group</th>
                          <th>test_id</th>
                          <th>description</th>
                          <th>units</th>
                          <th>date_1</th>
                          <th>numeric_score_1</th>
                          <th>date_2</th>
                          <th>numeric_score_2</th>
                          <th>percentage</th>
                          <th>analysis</th>
                          <th>results_1</th>
                          <th>report_dir_1</th>
                          <th>results_2</th>
                          <th>report_dir_2</th>
                        </tr>
                      </thead>
                      <tbody>
                      """

    def finish_html_results(self):
        self.html_results += """
                    </tbody>
                </table>
                <br>
                <br>
                <br>
                """

    # Helper methods
    # for the same db
    def compare_data(self):
        if len(self.database_list) == 1:
            # TODO in future have ability to extract single DUT and compare      
            # TODO make generic so could pass in kernel version or others      
            if not self.element_list:
                self.compare_single_db_info()
            else:
                self.compare_element_single_db_info()
        elif len(self.database_list) == 2:
            self.compare_multi_db_info()
        else:
            logger.critical("Only one or two database may be entered for compare")
            exit(1)


    def compare_multi_db_info(self):
        logger.info("compare the data in multiple db: {db_list}".format(db_list=self.database_list))

        # start the html results for the compare
        self.start_html_results()

        # based on the type of comparision
        # start the juni results 
        self.start_junit_testsuites()
        self.start_junit_testsuite()

        # TODO iterrate over multiple DB?
        self.database = self.database_list[0]
        self.database_comp = self.database_list[1]


        # get intial datafram
        self.conn =sqlite3.connect(self.database)
        df_1 = pd.read_sql_query("SELECT * from {}".format(self.table), self.conn)
        df_1.drop_duplicates(inplace=True)
        # sort by date from oldest to newest.
        try:
            df_1.sort_values(by='Date', ascending=False, inplace=True)
        except Exception as x:
            traceback.print_exception(Exception, x, x.__traceback__, chain=True)
            logger.info("Database empty: KeyError(key) when sorting by Date, check Database name, path to kpi, typo in path, exiting")
            exit(1)
            
        self.conn.close()

        # get intial datafram
        self.conn_comp =sqlite3.connect(self.database_comp)
        df_2 = pd.read_sql_query("SELECT * from {}".format(self.table), self.conn_comp)
        df_2.drop_duplicates(inplace=True)

        # sort by date from oldest to newest.
        try:
            df_2.sort_values(by='Date', ascending=False, inplace=True)
        except Exception as x:
            traceback.print_exception(Exception, x, x.__traceback__, chain=True)
            logger.info("Database empty: KeyError(key) when sorting by Date, check Database name, path to kpi, typo in path, exiting")
            exit(1)

        self.conn_comp.close()


        # iterate though the unique values of the dataframe
        for test_tag in df_1['test-tag'].unique():
            for graph_group in df_1['Graph-Group'].unique():
                for description in df_1['short-description'].unique():
                    df_tmp = df_1.loc[
                    ( df_1['Graph-Group'] == str(graph_group)) 
                    & (df_1['test-tag'] == str(test_tag)) 
                    & (df_1['short-description'] == str(description))]

                    # For comparing two databases there only needs to be a single entry
                    if not df_tmp.empty:
                        # find the same information in db2
                        df_tmp_comp = df_2.loc[
                        (df_2['Graph-Group'] == str(graph_group)) 
                        & (df_2['test-tag'] == str(test_tag)) 
                        & (df_2['short-description'] == str(description))]
                        if not df_tmp_comp.empty:
                            logger.info("db2 contains: {group} {tag} {desc}".format(group=graph_group,tag=test_tag,desc=description))

                            df_tmp.drop_duplicates(inplace=True) 
                            df_tmp.sort_values(by='Date', inplace=True, ascending=False)

                            logger.debug("First row {first}".format(first=df_tmp.iloc[0]))
                            df_data_1 = df_tmp.iloc[0]
                            logger.debug("type: {data} {data1}".format(data=type(df_data_1),data1=df_data_1))


                            df_tmp_comp.drop_duplicates(inplace=True) 
                            df_tmp_comp.sort_values(by='Date', inplace=True, ascending=False)

                            logger.debug("First row {first}".format(first=df_tmp_comp.iloc[0]))
                            df_data_2 = df_tmp_comp.iloc[0]
                            logger.debug("type: {data} {data2}".format(data=type(df_data_2),data2=df_data_2))

                            percent_delta = 0
                            if((int(df_data_1['numeric-score']) != 0 and df_data_1['numeric-score'] is not None ) and df_data_2 is not None):
                                percent_delta = round(((df_data_2['numeric-score']/df_data_1['numeric-score']) * 100), 2)

                            if percent_delta >= 90:
                                logger.info("Performance Good {percent}".format(percent=percent_delta))
                                self.test_result = "Good"
                                background = self.background_green
                            elif percent_delta >= 70:
                                logger.info("Performance Fair {percent}".format(percent=percent_delta))
                                self.test_result = "Fair"
                                background = self.background_purple
                            elif percent_delta >= 50:
                                logger.info("Performance Poor {percent}".format(percent=percent_delta))
                                self.test_result = "Poor"
                                background = self.background_orange
                            else:
                                logger.info("Performance Critical {percent}".format(percent=percent_delta))
                                self.test_result = "Critical"
                                background = self.background_red

                            # we can get most anything from the dataframe
                            # TODO use the dataframe export line to CSV?
                            row = [
                                df_data_1['test-rig'],
                                df_data_1['test-tag'],
                                df_data_1['Graph-Group'],
                                df_data_1['test-id'],
                                df_data_1['short-description'],
                                df_data_1['Units'],
                                df_data_1['Date'],
                                df_data_1['numeric-score'],
                                df_data_2['Date'],
                                df_data_2['numeric-score'],
                                percent_delta,
                                self.test_result
                            ]

                            self.csv_results_writer.writerow(row)
                            self.csv_results_file.flush()

                            # Set the relative path for results
                            report_path_1 =  df_data_1['kpi_path']+ "readme.html"
                            relative_report_1 = os.path.relpath(report_path_1, self.lf_inspect_report_path)

                            report_dir_path_1 =  df_data_1['kpi_path']
                            relative_report_dir_path_1 = os.path.relpath(report_dir_path_1, self.lf_inspect_report_path)

                            report_path_2 =  df_data_2['kpi_path']+ "readme.html"
                            relative_report_2 = os.path.relpath(report_path_2, self.lf_inspect_report_path)

                            report_dir_path_2 =  df_data_2['kpi_path']
                            relative_report_dir_path_2 = os.path.relpath(report_dir_path_2, self.lf_inspect_report_path)


                            self.html_results += """
                            <tr><td>""" + str(df_data_1['test-rig']) + """</td>
                            <td>""" + str(df_data_1['test-tag']) + """</td>
                            <td>""" + str(df_data_1['Graph-Group']) + """</td>
                            <td>""" + str(df_data_1['test-id']) + """</td>
                            <td>""" + str(df_data_1['short-description']) + """</td>
                            <td>""" + str(df_data_1['Units']) + """</td>
                            <td>""" + str(df_data_1['Date']) + """</td>
                            <td>""" + str(df_data_1['numeric-score']) + """</td>
                            <td>""" + str(df_data_2['Date']) + """</td>
                            <td>""" + str(df_data_2['numeric-score']) + """</td>

                            <td style=""" + str(background) + """>""" + str(percent_delta) + """</td>
                            <td style=""" + str(background) + """>""" + str(self.test_result) + """</td>
                            <td><a href=""" + str(relative_report_1) + """ target=\"_blank\">report_1</a></td>
                            <td><a href=""" + str(relative_report_dir_path_1) + """ target=\"_blank\">report_dir_1</a></td>
                            <td><a href=""" + str(relative_report_2) + """ target=\"_blank\">report_2</a></td>
                            <td><a href=""" + str(relative_report_dir_path_2) + """ target=\"_blank\">report_dir_2</a></td>


                            </tr>"""

                            self.junit_test = "{test_tag} {group} {test_id} {description}".format(
                                    test_tag=test_tag, group=graph_group, test_id=df_data_1['test-id'],description=df_data_1['short-description'])
                            # record the junit results
                            self.junit_results += """
                                <testcase name="{name}" id="{description}">
                                """.format(name=self.junit_test, description=description)

                            # remove junit xml characters
                            str_df_data_1 = str(df_data_1).replace('<','').replace('>','')
                            str_df_data_2 = str(df_data_2).replace('<','').replace('>','')

                            self.junit_results += """
                                <system-out>
                                Performance: {test_result}
                                Last Run: {numeric_score_1}
                                Prev Run: {numeric_score_2}
                                percent:  {percent}


                                df_data_1 : {df_data_1}


                                df_data_2 : {df_data_2}
                                </system-out>
                                """.format(test_result=self.test_result,numeric_score_1=df_data_1['numeric-score'],numeric_score_2=df_data_2['numeric-score'], 
                                percent=percent_delta,df_data_1=str_df_data_1, df_data_2=str_df_data_2)

                            # self.junit_results += """
                            #    <properties>
                            #    <property name= "{type1}" value= "{value1}"/>
                            #    </properties>.""".format(type1="this",value1="and that")
                            # need to have tests return error messages
                            if self.test_result != "Good" and self.test_result != "Fair":
                                self.junit_results += """
                                    <failure message="Performance: {result}  Percent: {percent}">
                                    </failure>""".format(result=self.test_result, percent=percent_delta)

                            self.junit_results += """
                                </testcase>
                                """


        # finish the results table     
        self.finish_html_results()    

        self.finish_junit_testsuite()
        self.finish_junit_testsuites()


    def compare_single_db_info(self):
        logger.info("compare the data in single db: {db_list}".format(db_list=self.database_list))

        # start the html results for the compare
        self.start_html_results()

        # TODO should this be outside the compare data? or should it be inside so that it may change 
        # based on the type of comparision
        # start the juni results 
        self.start_junit_testsuites()
        self.start_junit_testsuite()


        self.database = self.database_list[0]
        self.conn =sqlite3.connect(self.database)
        df3 = pd.read_sql_query("SELECT * from {}".format(self.table), self.conn)

        df3.drop_duplicates(inplace=True)
        # sort by date from oldest to newest.
        try:
            df3.sort_values(by='Date', ascending=False, inplace = True)
        except Exception as x:
            traceback.print_exception(Exception, x, x.__traceback__, chain=True)
            logger.info("Database empty: KeyError(key) when sorting by Date, check Database name, path to kpi, typo in path, exiting")
            exit(1)

        self.conn.close()

        
        # iterate though the unique values of the dataframe
        for test_tag in df3['test-tag'].unique():
            for graph_group in df3['Graph-Group'].unique():
                for description in df3['short-description'].unique():
                    df_tmp = df3.loc[( df3['Graph-Group'] == str(graph_group)) 
                        & (df3['test-tag'] == str(test_tag)) 
                        & (df3['short-description'] == str(description))]

                    # TODO need to be sure that there is not two entries 
                    if not df_tmp.empty and len(df_tmp.index) >= 2:
                        # Note if graph group is score there is sub tests for pass and fail
                        # would like a percentage
                        df_tmp.drop_duplicates(inplace=True) 
                        df_tmp.sort_values(by='Date', inplace=True, ascending=False)

                        logger.debug("First row {first}".format(first=df_tmp.iloc[0]))
                        df_data_1 = df_tmp.iloc[0]
                        logger.debug("type: {data} {data1}".format(data=type(df_data_1),data1=df_data_1))


                        logger.debug("Second row {second}".format(second=df_tmp.iloc[1]))
                        df_data_2 = df_tmp.iloc[1]

                        percent_delta = 0
                        if((int(df_data_1['numeric-score']) != 0 and df_data_1['numeric-score'] is not None ) and df_data_2 is not None):
                            percent_delta = round(((df_data_2['numeric-score']/df_data_1['numeric-score']) * 100), 2)

                        if percent_delta >= 90:
                            logger.info("Performance Good {percent}".format(percent=percent_delta))
                            self.test_result = "Good"
                            background = self.background_green
                        elif percent_delta >= 70:
                            logger.info("Performance Fair {percent}".format(percent=percent_delta))
                            self.test_result = "Fair"
                            background = self.background_purple
                        elif percent_delta >= 50:
                            logger.info("Performance Poor {percent}".format(percent=percent_delta))
                            self.test_result = "Poor"
                            background = self.background_orange
                        else:
                            logger.info("Performance Critical {percent}".format(percent=percent_delta))
                            self.test_result = "Critical"
                            background = self.background_red

                        # we can get most anything from the dataframe
                        # TODO use the dataframe export line to CSV?
                        row = [
                            df_data_1['test-rig'],
                            df_data_1['test-tag'],
                            df_data_1['Graph-Group'],
                            df_data_1['test-id'],
                            df_data_1['short-description'],
                            df_data_1['Units'],
                            df_data_1['Date'],
                            df_data_1['numeric-score'],
                            df_data_2['Date'],
                            df_data_2['numeric-score'],
                            percent_delta,
                            self.test_result
                        ]

                        self.csv_results_writer.writerow(row)
                        self.csv_results_file.flush()

                        # Set the relative path for results
                        report_path_1 =  df_data_1['kpi_path']+ "readme.html"
                        relative_report_1 = os.path.relpath(report_path_1, self.lf_inspect_report_path)

                        report_dir_path_1 =  df_data_1['kpi_path']
                        relative_report_dir_path_1 = os.path.relpath(report_dir_path_1, self.lf_inspect_report_path)

                        report_path_2 =  df_data_2['kpi_path']+ "readme.html"
                        relative_report_2 = os.path.relpath(report_path_2, self.lf_inspect_report_path)

                        report_dir_path_2 =  df_data_2['kpi_path']
                        relative_report_dir_path_2 = os.path.relpath(report_dir_path_2, self.lf_inspect_report_path)


                        # set up a loop to go through all the results
                        # need a kpi html library or in lf_report to compare the 
                        # kpi
                        self.html_results += """
                        <tr><td>""" + str(df_data_1['test-rig']) + """</td>
                        <td>""" + str(df_data_1['test-tag']) + """</td>
                        <td>""" + str(df_data_1['Graph-Group']) + """</td>
                        <td>""" + str(df_data_1['test-id']) + """</td>
                        <td>""" + str(df_data_1['short-description']) + """</td>
                        <td>""" + str(df_data_1['Units']) + """</td>
                        <td>""" + str(df_data_1['Date']) + """</td>
                        <td>""" + str(df_data_1['numeric-score']) + """</td>
                        <td>""" + str(df_data_2['Date']) + """</td>
                        <td>""" + str(df_data_2['numeric-score']) + """</td>

                        <td style=""" + str(background) + """>""" + str(percent_delta) + """</td>
                        <td style=""" + str(background) + """>""" + str(self.test_result) + """</td>
                        <td><a href=""" + str(relative_report_1) + """ target=\"_blank\">report_1</a></td>
                        <td><a href=""" + str(relative_report_dir_path_1) + """ target=\"_blank\">report_dir_1</a></td>
                        <td><a href=""" + str(relative_report_2) + """ target=\"_blank\">report_2</a></td>
                        <td><a href=""" + str(relative_report_dir_path_2) + """ target=\"_blank\">report_dir_2</a></td>


                        </tr>"""

                        self.junit_test = "{test_tag} {group} {test_id} {description}".format(
                            test_tag=test_tag, group=graph_group, test_id=df_data_1['test-id'],description=df_data_1['short-description'])
                        # record the junit results
                        self.junit_results += """
                            <testcase name="{name}" id="{description}">
                            """.format(name=self.junit_test, description=description)

                        # remove junit xml characters
                        str_df_data_1 = str(df_data_1).replace('<','').replace('>','')
                        str_df_data_2 = str(df_data_2).replace('<','').replace('>','')

                        self.junit_results += """
                            <system-out>
                            Performance: {test_result}
                            Last Run: {numeric_score_1}
                            Prev Run: {numeric_score_2}
                            percent:  {percent}


                            df_data_1 : {df_data_1}


                            df_data_2 : {df_data_2}
                            </system-out>
                            """.format(test_result=self.test_result,numeric_score_1=df_data_1['numeric-score'],numeric_score_2=df_data_2['numeric-score'], 
                            percent=percent_delta,df_data_1=str_df_data_1, df_data_2=str_df_data_2)

                        # self.junit_results += """
                        #    <properties>
                        #    <property name= "{type1}" value= "{value1}"/>
                        #    </properties>.""".format(type1="this",value1="and that")
                        # need to have tests return error messages
                        if self.test_result != "Good" and self.test_result != "Fair":
                            self.junit_results += """
                                <failure message="Performance: {result}  Percent: {percent}">
                                </failure>""".format(result=self.test_result, percent=percent_delta)

                        self.junit_results += """
                            </testcase>
                            """


        # finish the results table     
        self.finish_html_results()    

        self.finish_junit_testsuite()
        self.finish_junit_testsuites()

    def compare_element_single_db_info(self):

        # possibly want multiple column values 
        logger.info("compare the elements {element} in single db: {db_list}".format(element=self.element_list,db_list=self.database_list))

        col_list = []
        attrib_list = []
        for element in self.element_list:
            element_tmp = element.split("==")
            col_list.append(element_tmp[0])
            attrib_list.append(element_tmp[1])  # note this is a list of two elements separated by &&

        # start the html results for the compare
        self.start_html_results()

        # TODO should this be outside the compare data? or should it be inside so that it may change 
        # based on the type of comparision
        # start the juni results 
        self.start_junit_testsuites()
        self.start_junit_testsuite()
        # initiallly work for two elements    
        
        # query unique db for each of the selections 
        # TODO work out the loops for multiple columns like dut and kernel verion   
        sub_attrib_list = attrib_list[0].split('&&') 

        self.database = self.database_list[0]
        self.conn =sqlite3.connect(self.database)
        # https://stackoverflow.com/questions/3168644/can-a-table-field-contain-a-hyphen
        # let the sql query do some of the filtering
        df_1_total = pd.read_sql_query("SELECT * from {}".format(self.table), self.conn)

        df_1_total.drop_duplicates(inplace=True)
        try:
            df_1_total.sort_values(by='Date', ascending=False, inplace = True)
        except Exception as x:
            traceback.print_exception(Exception, x, x.__traceback__, chain=True)
            logger.info("Database empty: KeyError(key) when sorting by Date, check Database name, path to kpi, typo in path, exiting")
            exit(1)

        # TODO figure out how to loc more attributs
        df_1 = df_1_total.loc[df_1_total[col_list[0]] == sub_attrib_list[0]]
        # sort by date from oldest to newest.

        self.conn.close()

        if df_1.empty:
            logger.debug("df_2 empty exiting")
            exit(1)


        self.conn =sqlite3.connect(self.database)

        # let the sql query do some of the filtering
        df_2_total = pd.read_sql_query("SELECT * from {}".format(self.table), self.conn)

        df_2_total.drop_duplicates(inplace=True)
        # sort by date from oldest to newest.
        try:
            df_2_total.sort_values(by='Date', ascending=False, inplace = True)
        except Exception as x:
            traceback.print_exception(Exception, x, x.__traceback__, chain=True)
            logger.info("Database empty: KeyError(key) when sorting by Date, check Database name, path to kpi, typo in path, exiting")
            exit(1)
            
        df_2 = df_2_total.loc[df_2_total[col_list[0]] == sub_attrib_list[1]]

        self.conn.close()

        if df_2.empty:
            logger.debug("df_2 empty exiting")
            exit(1)

        # this can be a common function
        # iterate though the unique values of the dataframe
        for test_tag in df_1['test-tag'].unique():
            for graph_group in df_1['Graph-Group'].unique():
                for description in df_1['short-description'].unique():
                    df_tmp = df_1.loc[
                    ( df_1['Graph-Group'] == str(graph_group)) 
                    & (df_1['test-tag'] == str(test_tag)) 
                    & (df_1['short-description'] == str(description))]

                    # For comparing two databases there only needs to be a single entry
                    if not df_tmp.empty:
                        logger.debug("df_tmp {}".format(df_tmp))
                        # find the same information in db2
                        df_tmp_comp = df_2.loc[
                        (df_2['Graph-Group'] == str(graph_group)) 
                        & (df_2['test-tag'] == str(test_tag)) 
                        & (df_2['short-description'] == str(description))]
                        logger.debug("df_tmp_comp {}".format(df_tmp_comp))
                        if not df_tmp_comp.empty:
                            logger.info("db2 contains: {group} {tag} {desc}".format(group=graph_group,tag=test_tag,desc=description))

                            df_tmp.drop_duplicates(inplace=True) 
                            df_tmp.sort_values(by='Date', inplace=True, ascending=False)

                            logger.debug("First row {first}".format(first=df_tmp.iloc[0]))
                            df_data_1 = df_tmp.iloc[0]
                            logger.debug("type: {data} {data1}".format(data=type(df_data_1),data1=df_data_1))


                            df_tmp_comp.drop_duplicates(inplace=True) 
                            df_tmp_comp.sort_values(by='Date', inplace=True, ascending=False)

                            logger.debug("First row {first}".format(first=df_tmp_comp.iloc[0]))
                            df_data_2 = df_tmp_comp.iloc[0]
                            logger.debug("type: {data} {data2}".format(data=type(df_data_2),data2=df_data_2))

                            percent_delta = 0
                            if((int(df_data_1['numeric-score']) != 0 and df_data_1['numeric-score'] is not None ) and df_data_2 is not None):
                                percent_delta = round(((df_data_2['numeric-score']/df_data_1['numeric-score']) * 100), 2)

                            if percent_delta >= 90:
                                logger.info("Performance Good {percent}".format(percent=percent_delta))
                                self.test_result = "Good"
                                background = self.background_green
                            elif percent_delta >= 70:
                                logger.info("Performance Fair {percent}".format(percent=percent_delta))
                                self.test_result = "Fair"
                                background = self.background_purple
                            elif percent_delta >= 50:
                                logger.info("Performance Poor {percent}".format(percent=percent_delta))
                                self.test_result = "Poor"
                                background = self.background_orange
                            else:
                                logger.info("Performance Critical {percent}".format(percent=percent_delta))
                                self.test_result = "Critical"
                                background = self.background_red

                            # we can get most anything from the dataframe
                            # TODO use the dataframe export line to CSV?
                            row = [
                                df_data_1['test-rig'],
                                df_data_1['test-tag'],
                                df_data_1['Graph-Group'],
                                df_data_1['test-id'],
                                df_data_1['short-description'],
                                df_data_1['Units'],
                                df_data_1['Date'],
                                df_data_1['numeric-score'],
                                df_data_2['Date'],
                                df_data_2['numeric-score'],
                                percent_delta,
                                self.test_result
                            ]

                            self.csv_results_writer.writerow(row)
                            self.csv_results_file.flush()

                            # Set the relative path for results
                            report_path_1 =  df_data_1['kpi_path']+ "readme.html"
                            relative_report_1 = os.path.relpath(report_path_1, self.lf_inspect_report_path)

                            report_dir_path_1 =  df_data_1['kpi_path']
                            relative_report_dir_path_1 = os.path.relpath(report_dir_path_1, self.lf_inspect_report_path)

                            report_path_2 =  df_data_2['kpi_path']+ "readme.html"
                            relative_report_2 = os.path.relpath(report_path_2, self.lf_inspect_report_path)

                            report_dir_path_2 =  df_data_2['kpi_path']
                            relative_report_dir_path_2 = os.path.relpath(report_dir_path_2, self.lf_inspect_report_path)


                            self.html_results += """
                            <tr><td>""" + str(df_data_1['test-rig']) + """</td>
                            <td>""" + str(df_data_1['test-tag']) + """</td>
                            <td>""" + str(df_data_1['Graph-Group']) + """</td>
                            <td>""" + str(df_data_1['test-id']) + """</td>
                            <td>""" + str(df_data_1['short-description']) + """</td>
                            <td>""" + str(df_data_1['Units']) + """</td>
                            <td>""" + str(df_data_1['Date']) + """</td>
                            <td>""" + str(df_data_1['numeric-score']) + """</td>
                            <td>""" + str(df_data_2['Date']) + """</td>
                            <td>""" + str(df_data_2['numeric-score']) + """</td>

                            <td style=""" + str(background) + """>""" + str(percent_delta) + """</td>
                            <td style=""" + str(background) + """>""" + str(self.test_result) + """</td>
                            <td><a href=""" + str(relative_report_1) + """ target=\"_blank\">report_1</a></td>
                            <td><a href=""" + str(relative_report_dir_path_1) + """ target=\"_blank\">report_dir_1</a></td>
                            <td><a href=""" + str(relative_report_2) + """ target=\"_blank\">report_2</a></td>
                            <td><a href=""" + str(relative_report_dir_path_2) + """ target=\"_blank\">report_dir_2</a></td>


                            </tr>"""

                            self.junit_test = "{test_tag} {group} {test_id} {description}".format(
                                    test_tag=test_tag, group=graph_group, test_id=df_data_1['test-id'],description=df_data_1['short-description'])
                            # record the junit results
                            self.junit_results += """
                                <testcase name="{name}" id="{description}">
                                """.format(name=self.junit_test, description=description)

                            # remove junit xml characters
                            str_df_data_1 = str(df_data_1).replace('<','').replace('>','')
                            str_df_data_2 = str(df_data_2).replace('<','').replace('>','')

                            self.junit_results += """
                                <system-out>
                                Performance: {test_result}
                                Last Run: {numeric_score_1}
                                Prev Run: {numeric_score_2}
                                percent:  {percent}


                                df_data_1 : {df_data_1}


                                df_data_2 : {df_data_2}
                                </system-out>
                                """.format(test_result=self.test_result,numeric_score_1=df_data_1['numeric-score'],numeric_score_2=df_data_2['numeric-score'], 
                                percent=percent_delta,df_data_1=str_df_data_1, df_data_2=str_df_data_2)

                                # self.junit_results += """
                                #    <properties>
                                #    <property name= "{type1}" value= "{value1}"/>
                                #    </properties>.""".format(type1="this",value1="and that")
                                # need to have tests return error messages
                            if self.test_result != "Good" and self.test_result != "Fair":
                                self.junit_results += """
                                    <failure message="Performance: {result}  Percent: {percent}">
                                    </failure>""".format(result=self.test_result, percent=percent_delta)

                            self.junit_results += """
                                </testcase>
                                """


        # finish the results table     
        self.finish_html_results()    

        self.finish_junit_testsuite()
        self.finish_junit_testsuites()


    # TODO have variable type of output
    def start_html_results(self):
        self.html_results += """
                <table border="1" class="dataframe">
                    <thead>
                        <tr style="text-align: left;">
                          <th>test_rig    </th>
                          <th>test_tag</th>
                          <th>Graph_Group          </th>
                          <th>test_id          </th>
                          <th>short_description</th>
                          <th>Units            </th>
                          <th>Date1</th>
                          <th>numeric_score_1</th>
                          <th>Date2</th>
                          <th>numeric_score_2</th>
                          <th>percent</th>
                          <th>Analysis</th>
                          <th>report_1</th>
                          <th>report_dir_1</th>
                          <th>report_2</th>
                          <th>report_dir_2</th>
                        </tr>
                      </thead>
                      <tbody>
                      """


    def finish_html_results(self):
        self.html_results += """
                    </tbody>
                </table>
                <br>
                <br>
                <br>
                """


    def get_suite_html(self):
        suite_html_results = """
            <table class="dataframe" border="1">
                    <thead>
                        <tr style="text-align: center;">
                          <th>Test</th>
                          <th>Test_Tag</th>
                          <th>Links</th>
                          <th>Directory Name</th>
                        </tr>
                    </thead>
                <tbody>
        """

        path = Path(self.path)
        pdf_info_list = list(path.glob('**/*.pdf'))  # Hard code for now
        logger.info("pdf_info_list {}".format(pdf_info_list))
        for pdf_info in pdf_info_list:
            if "lf_inspect" in str(pdf_info):
                pass
            else:
                pdf_base_name = os.path.basename(pdf_info)
                if "check" in str(pdf_base_name):
                    pass
                else:
                    # TODO remove the fixed path code
                    # try relative path
                    parent_path = os.path.dirname(pdf_info)
                    parent_name = os.path.basename(parent_path)

                    # for the chamberview tests the results is in index.html
                    # so need to move index.html to readme.html
                    # use os.rename(source,destination) , 
                    # check for index
                    index_html_file = parent_path + "/index.html"
                    if os.path.exists(index_html_file):
                        readme_html_file = parent_path + "/readme.html"
                        os.rename(index_html_file,readme_html_file)

                    dir_path = '../' + parent_name 
                    pdf_path = '../' + parent_name + "/" +  pdf_base_name
                    html_path = "../" + parent_name + "/readme.html"

                    kpi_path = os.path.join(parent_path, "kpi.csv")
                    test_id, test_tag = self.get_test_id_test_tag(kpi_path)
                    suite_html_results += """
                    <tr style="text-align: center; margin-bottom: 0; margin-top: 0;">
                        <td>{test_id}</td><td>{test_tag}</td><td><a href="{html_path}" target="_blank">html</a> / 
                        <a href="{pdf_path}" target="_blank">pdf</a> / 
                        <a href="{dir_path}" target="_blank">results_dir</a></td>
                        <td>{parent_name}</td></tr> 
                    """.format(test_id=test_id, test_tag=test_tag, html_path=html_path, pdf_path=pdf_path, dir_path=dir_path, parent_name=parent_name)
        suite_html_results += """
                    </tbody>
                </table>
                <br>
                """

        return suite_html_results

    #
    def db_compare(self):
        pass

# Feature, Sum up the subtests passed/failed from the kpi files for each
# run, poke those into the database, and generate a kpi graph for them.
def main():

    parser = argparse.ArgumentParser(
        prog='lf_inspect.py',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''\
        read kpi.csv into sqlite database , save png of history and preset on dashboard

            ''',
        description='''\
Read in two databases and compare the inputs
Usage: lf_inspect.py --db  db_one,db_two

        ''')
    parser.add_argument('--path', help=''' --path to where to place the results ''', default='')

    parser.add_argument('--database', help='--database db_one,db_two may be a list of up to 2 db', default='qa_test_db')
    parser.add_argument('--element', help='''
                        --element  dut-model-num==dut1&&dut2  will column element dut-model-num between  dut1,dut2  
                        for single db will look in same db for both, 
                        (not supported) if two db then first dut queried in first db and second dut quired in second db''')
    parser.add_argument('--table', help='--table qa_table  default: qa_table', default='qa_table')
    parser.add_argument('--dir', help="--dir <results directory> default lf_qa", default="lf_inspect")
    parser.add_argument('--outfile', help="--outfile <Output Generic Name>  used as base name for all files generated", default="lf_inspect")
    parser.add_argument('--logfile', help="--logfile <logfile Name>  logging for output of lf_check.py script", default="lf_inspect.log")
    parser.add_argument('--flat_dir', help="--flat_dir , will place the results in the top directory", action='store_true')


    # logging configuration:
    parser.add_argument('--log_level', default=None, help='Set logging level: debug | info | warning | error | critical')

    parser.add_argument("--lf_logger_config_json", help="--lf_logger_config_json <json file> , json configuration of logger")

    args = parser.parse_args()

    # set up logger

    # set the logger level to debug
    logger_config = lf_logger_config.lf_logger_config()

    if args.log_level:
        logger_config.set_level(level=args.log_level)

    if args.lf_logger_config_json:
        # logger_config.lf_logger_config_json = "lf_logger_config.json"
        logger_config.lf_logger_config_json = args.lf_logger_config_json
        logger_config.load_lf_logger_config()

    __database_list = args.database.split(',')
    if args.element is not None:
        __element_list = args.element.split(',')
    else:
        __element_list = []        

    __dir = args.dir
    __path = args.path
    __table = args.table


    if __path == '' :
        logger.info("--path may be used ")

    # create report class for reporting
    report = lf_report(_path=__path,
                       _results_dir_name=__dir,
                       _output_html="lf_inspect.html",
                       _output_pdf="lf_inspect.pdf")

    current_time = time.strftime("%Y-%m-%d-%H-%M-%S", time.localtime())
    csv_results = "{dir}-{outfile}-{current_time}.csv".format(dir=__dir, outfile=args.outfile, current_time=current_time)
    csv_results = report.file_add_path(csv_results)
    outfile_name = "{dir}-{outfile}-{current_time}".format(dir=__dir, outfile=args.outfile, current_time=current_time)
    outfile = report.file_add_path(outfile_name)
    if args.flat_dir:
        report_path = report.get_flat_dir_report_path()
    else:
        report_path = report.get_report_path()

    log_path = report.get_log_path()


    # for relative path reporting 
    __lf_inspect_report_path = report.get_path_date_time()

    inspect_db = inspect_sql(
        _path=__path,
        _dir = __dir,
        _database_list=__database_list,
        _element_list=__element_list,
        _table=__table,
        _csv_results=csv_results,
        _outfile=outfile,
        _outfile_name=outfile_name,
        _report_path=report_path,
        _log_path=log_path,
        _lf_inspect_report_path = __lf_inspect_report_path
        )

    # TODO add abilit to pass in unique names
    inspect_db.start_csv_results()

    # One database in list indicates a nightly comparison with 
    # current run being compared to the previous run
    inspect_db.compare_data()

    # csv_dash.sub_test_information()

    #if args.store:
    #    csv_dash.store()
        

    # generate output reports
    report.set_title("Compare Results: Verification Test Run")
    report.build_banner_left()
    report.start_content_div2()
    if len(__database_list) == 1:
        objective = "QA test run comparision between last and previous run in {db}".format(db=__database_list)
    else:
        objective = "QA test run comparision between {db}".format(db=__database_list)

    report.set_obj_html("Objective", objective)
    report.build_objective()
    report.set_table_title("Test Compare")
    report.build_table_title()
    html_results = inspect_db.get_html_results()
    report.set_custom_html(html_results)
    report.build_custom()

    report_path = report.get_path()
    report_basename = os.path.basename(report_path)
    report_url = './../../' + report_basename
    report.build_link("Current Test Suite Results Directory", report_url)

    report_parent_path = report.get_parent_path()
    report_parent_basename = os.path.basename(report_parent_path)
    report_parent_url = './../../../' + report_parent_basename
    report.build_link("All Test-Rig Test Suites Results Directory", report_parent_url)

    report.build_footer()


    html_report = report.write_html_with_timestamp()
    # logger.info("html report: {}".format(html_report))
    logger.info("html report: {}".format(html_report))
    try:
        report.write_pdf_with_timestamp()
    except Exception as x:
        traceback.print_exception(Exception, x, x.__traceback__, chain=True)
        logger.info("exception write_pdf_with_timestamp()")

    logger.info("lf_inspect_html_report: " + html_report)

    # save the juni.xml file
    junit_results = inspect_db.get_junit_results()
    report.set_junit_results(junit_results)
    junit_xml = report.write_junit_results()
    junit_path_only = junit_xml.replace('junit.xml','')

    inspect_db.set_junit_results(junit_xml)
    inspect_db.set_junit_path_only(junit_path_only)

    # print later so shows up last
    logger.info("junit.xml: allure serve {}".format(junit_xml))
    logger.info("junit.xml path: allure serve {}".format(junit_path_only))

    

if __name__ == '__main__':
    main()