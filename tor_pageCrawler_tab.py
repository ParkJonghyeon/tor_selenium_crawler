import csv
import os
import sys
import codecs
import traceback
from time import strftime, localtime, time, sleep
from pyvirtualdisplay import Display

import requests
from selenium.common.exceptions import TimeoutException as SelTimeExcept
from selenium.common.exceptions import WebDriverException as SelWebDriverExcept
from selenium.common.exceptions import NoSuchWindowException as SelWindowExcept
from selenium.webdriver.common.alert import Alert

from tbselenium.tbdriver import TorBrowserDriver
from tor_pageCrawler_enum import RequestsErrorCode as torReqEnum
from tor_pageCrawler_enum import tbSeleniumErrorCode as torSelEnum


PATH_LIST = {"ROOT_DIRECTORY" : '',
             "TBB_PATH" : '',
             "LINK_SET_PATH" : '',
             "OUTPUT_DIR_PATH" : '',
             "OUTPUT_FILE_PATH" : '',
             "OUTPUT_HTML_DIR_PATH" : '',
             "LOG_DIR_PATH" : '',
             "LOG_PATH" : '',
             "HEADER_PATH" : ''}
ACCESS_TIMEOUT = 30
MAX_TAB_NUM = 5

DEFAULT_XVFB_WIN_W = 1280
DEFAULT_XVFB_WIN_H = 800
XVFB_DISPLAY = Display(visible=0, size=(DEFAULT_XVFB_WIN_W, DEFAULT_XVFB_WIN_H))


def request_setup():
    session = requests.Session()
    session.proxies = {'http': 'socks5h://127.0.0.1:9150', 'https': 'socks5h://127.0.0.1:9150'}
    session.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; rv:45.0) Gecko/20100101 Firefox/45.0'}
    return session


def tor_browser_open():
    print("tor browser open")
    open_tor_browser = False
    try_count = 0
    driver = None
    while not open_tor_browser and try_count < 5 :
        try:
            print(try_count)
            try_count += 1
            driver = TorBrowserDriver(PATH_LIST["TBB_PATH"], tbb_logfile_path='./tor_browser_log.txt')
            open_tor_browser = True
            print("Tor Browser is open! Connecting to hidden service ...")
        except SelWebDriverExcept:
            print("[BROWSER_ERROR] Tor Browser open error! Try reopening...")
            continue
    return driver


def hs_request_status_code(session, onion_address, header_list_file):
    try:
        response = session.get(onion_address, timeout=ACCESS_TIMEOUT)
        hs_status_code = response.status_code
        hs_header = str(response.headers)
        # 같은 주소에 대해 변화가 있을 경우 갱신하는 식으로 코드 수정 필요함
        header_list_file.write(onion_address+'\t'+hs_header+'\n')
    except requests.ConnectTimeout:
        # print("[REQ_ERROR] "+onion_address+" ConnectTimeout")
        return torReqEnum.REQ_CONNECT_TIMEOUT.value
    except requests.ReadTimeout:
        # print("[REQ_ERROR] "+onion_address+" ReadTimeout")
        return torReqEnum.REQ_READ_TIMEOUT.value
    except requests.ConnectionError:
        # print("[REQ_ERROR] "+onion_address+" ConnectioinError")
        return torReqEnum.REQ_CONNECTION_ERROR.value
    except:
        # print("[REQ_ERROR] "+onion_address+" Undefined exception")
        return torReqEnum.REQ_UNDEFINED_EXCEPT.value
    return hs_status_code


def hs_main_page_get(driver, onion_address):
    try:
        driver.load_url(onion_address, wait_on_page=ACCESS_TIMEOUT, wait_for_page_body=True)
    except SelWebDriverExcept:
        # print("[DRIVER_ERROR] "+onion_address+" WebDriverExcept")
        return torSelEnum.TB_SEL_WEBDRIVER_EXCEPT.value
    except SelTimeExcept:
        # print("[DRIVER_ERROR] "+onion_address+" TimeExcept")
        return torSelEnum.TB_SEL_TIME_EXCEPT.value
    except:
        e_log = traceback.format_exc()
        crawler_logging("a", "[TB_SEL_UNDEFINED_EXCEPT] : " + strftime('%Y/%m/%d-%H:%M:%S', localtime(time())) + "\nin "
                        + onion_address + "\n" + e_log)
        # print("[DRIVER_ERROR] "+onion_address+" Undefined exception")
        return torSelEnum.TB_SEL_UNDEFINED_EXCEPT.value
    return torSelEnum.TB_SEL_SUCCESS.value


def reset_other_tabs(driver):
    other_tab_idx = driver.window_handles[1:]
    while len(other_tab_idx) > 0:
        # print("while loop start")
        for tab_idx in other_tab_idx:
            driver.switch_to_window(tab_idx)
            # print("close tab idx is " + str(tab_idx))
            driver.close()
        other_tab_idx = driver.window_handles[1:]

    # print("end while loop")
    driver.switch_to_window(driver.window_handles[0])


def page_crawler():
    # print("page_cralwer")
    session = request_setup()
    # setup file reader
    read_file = open(PATH_LIST["LINK_SET_PATH"], 'r')
    reader = csv.reader(read_file, delimiter='\t')

    reader_list = []
    for row in reader:
        reader_list.append(row)

    # setup file writer
    output_file = open(PATH_LIST["OUTPUT_FILE_PATH"], 'w')
    writer = csv.writer(output_file, delimiter='\t')

    hs_header_list_file = open(PATH_LIST["HEADER_PATH"], 'a')

    # driver open try
    driver = tor_browser_open()
    # driver.set_page_load_timeout(ACCESS_TIMEOUT)
    print("driver setup")
    if driver is None:
        crawler_logging("a", "[BROWSER_ERROR] Tor Browser open Error. Please retry.")
        # print("[BROWSER_ERROR] Tor Browser open Error. Please retry.")
        exit_crawler(driver, read_file, output_file)
    # main crawling code

    address_queue = []
    for address_idx in range(len(reader_list)):
        row = reader_list[address_idx]
        onion_address = row[0]
        # print(onion_address)
        # http status code check
        hs_status_code = hs_request_status_code(session, onion_address, hs_header_list_file)
        # response_header의 내용 갱신이 있을 경우 내용을 수정/내용이 바뀌지 않았다면 데이터 유지. 하나의 파일에서 response_header의 정보는 최신으로 관리. 변경 이력은 따로 로그파일을 만들어서 기록할 것

        # http가 접속 가능한 경우를 제외하고는 모두 바로 결과 기록
        # 접속 가능하다면 address_queue에 넣어서 접속 가능한 사이트 주소를 리스트로
        if hs_status_code < 400 or hs_status_code == torReqEnum.REQ_UNDEFINED_EXCEPT.value:
            address_queue.append(row)
            # print("add queue")
        # http status code is under 500 and not equal 404 or 410, access forbidden by hidden service (= HS is live)
        elif hs_status_code != (404 or 410) and hs_status_code < 500:
            row.append("live")
            row.append(str(hs_status_code))
            writer.writerow(row)
        # HS is dead (No Request response)
        elif hs_status_code == torReqEnum.REQ_CONNECT_TIMEOUT.value:
            row.append("dead")
            row.append("REQ_connectionTimeout")
            writer.writerow(row)
        elif hs_status_code == torReqEnum.REQ_READ_TIMEOUT.value:
            row.append("dead")
            row.append("REQ_readTimeout")
            writer.writerow(row)
        elif hs_status_code == torReqEnum.REQ_CONNECTION_ERROR.value:
            row.append("dead")
            row.append("REQ_connectionError")
            writer.writerow(row)
        # RequestException
        else:
            row.append("dead")
            row.append(hs_status_code)
            writer.writerow(row)
        # processed_address_num += 1
        # print("[CRAWL] ", processed_address_num, " address visited")

        # 접속 가능한 사이트 주소의 리스트가 MAX_TAB_NUM 만큼 큐에 쌓이면 MAX_TAB_NUM 개의 빈 탭을 연다
        # blank_tab_idx로 빈탭의 index를 확인 후 빈 탭을 돌며 get()으로 페이지를 연다.
        # get()으로 주소를 가져오면서 탭의 id가 바뀌므로 opened_tab_idx에 변경 된 탭 index를 넣는다.
        # 30초 페이지 로드를 대기하고, opened_tab_idx 로 탭을 돌며 페이지를 저장
        # reset_other_tabs를 통해 가장 처음 탭을 제외한 모든 탭을 닫는다.
        if len(address_queue) == MAX_TAB_NUM or address_idx == len(reader_list)-1:
            # print("queue max")
            for count in range(len(address_queue)):
                # print("make tab "+str(count))
                driver.execute_script("window.open();")
            # print("open blank tab as address_queue number")

            # 가장 처음 탭은 driver가 close 되지 않도록 빈 탭으로 사용하지 않음(2번째 탭 부터 사용)
            blank_tab_idx = driver.window_handles[1:]
            # print(blank_tab_idx)

            opened_tab_idx = []
            for current_tab_idx in blank_tab_idx:
                driver.switch_to.window(current_tab_idx)
                get_onion_address = address_queue[blank_tab_idx.index(current_tab_idx)][0]
                # print(str(blank_tab_idx.index(current_tab_idx)) + " tab access " + get_onion_address+"\n this tab index is "+str(current_tab_idx))
                driver.get(get_onion_address)
                opened_tab_idx.append(driver.current_window_handle)
                # print(str(driver.current_window_handle))

            sleep(30)

            # print("get window")
            for current_tab_idx in opened_tab_idx:
                # print("Try to move "+str(current_tab_idx)+" tab")
                try:
                    driver.switch_to.window(current_tab_idx)
                except SelWindowExcept:
                    # print("Except!")
                    crawler_logging("a", "[TB_SEL_NO_SUCH_WINDOW_EXCEPT] : Current tab idx " + str(current_tab_idx) + "\n"
                                    + "Current Queue " + str(address_queue) + "\n")
                    break
                # print("Success")
                alert_present_check(driver)
                page_title = driver.title
                # print("get title")
                if page_title != 'Problem loading page':
                    # print(page_title," get source. tab index = ",tab_idx_num)
                    address_queue[opened_tab_idx.index(current_tab_idx)].append("live")
                    address_queue[opened_tab_idx.index(current_tab_idx)].append(str(torSelEnum.TB_SEL_SUCCESS.value))
                    # print(page_title," result update")
                    writer.writerow(address_queue[opened_tab_idx.index(current_tab_idx)])
                    with codecs.open(PATH_LIST["OUTPUT_HTML_DIR_PATH"] + "/" + address_queue[opened_tab_idx.index(current_tab_idx)][0][7:23] + ".html", "w",
                                     "utf-8") as html_writer:
                        html_writer.write(driver.page_source)
                else:
                    # print("problem page")
                    address_queue[opened_tab_idx.index(current_tab_idx)].append("dead")
                    address_queue[opened_tab_idx.index(current_tab_idx)].append(str(torSelEnum.TB_SEL_UNDEFINED_EXCEPT.value))
                    writer.writerow(opened_tab_idx.index(current_tab_idx))
            # print("reset focus")
            reset_other_tabs(driver)
            address_queue = []

    exit_crawler(driver, read_file, output_file)


def alert_present_check(driver):
    try:
        alert = driver.switch_to_alert()
        alert.accept()
        return True
    except:
        print("no alert")
        return False


def dir_exist_check(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)


def crawler_logging(mode, log):
    crawler_logger = open(PATH_LIST["LOG_PATH"], mode)
    crawler_logger.write(log)
    crawler_logger.close()


def exit_crawler(driver, read_file, output_file):
    if driver:
        driver.close()
    if XVFB_DISPLAY.is_alive():
        XVFB_DISPLAY.stop()
    if read_file:
        read_file.close()
    if output_file:
        output_file.close()
    # print("Closing tor_pageCrawler.py...")


def crawling_env_init(machine_num):
    crawl_date = strftime('%Y%m%d%H', localtime(time()))
    PATH_LIST["ROOT_DIRECTORY"] = '/home/tordocker'
    PATH_LIST["TBB_PATH"] = PATH_LIST["ROOT_DIRECTORY"]+'/tor-browser_en-US'
    PATH_LIST["LINK_SET_PATH"] = PATH_LIST["ROOT_DIRECTORY"]+'/shared_dir/onion_link_set_dir/onion_link_set'+machine_num+'.tsv'
    PATH_LIST["OUTPUT_DIR_PATH"] = PATH_LIST["ROOT_DIRECTORY"] + '/shared_dir/output_dir'
    PATH_LIST["OUTPUT_FILE_PATH"] = PATH_LIST["OUTPUT_DIR_PATH"]+'/output_'+machine_num+'_'+crawl_date+'.tsv'
    PATH_LIST["OUTPUT_HTML_DIR_PATH"] = PATH_LIST["ROOT_DIRECTORY"]+'/shared_dir/html_source_dir_'+crawl_date
    PATH_LIST["LOG_DIR_PATH"] = PATH_LIST["ROOT_DIRECTORY"] + '/shared_dir/log_dir'
    PATH_LIST["LOG_PATH"] = PATH_LIST["LOG_DIR_PATH"]+'/tor_visit_log_'+machine_num+'.txt'
    PATH_LIST["HEADER_PATH"] = PATH_LIST["ROOT_DIRECTORY"] + '/shared_dir/output_dir/hidden_service_header'+machine_num+'.tsv'


def main(machine_num):
    crawling_env_init(machine_num)
    dir_exist_check(PATH_LIST["OUTPUT_DIR_PATH"])
    dir_exist_check(PATH_LIST["OUTPUT_HTML_DIR_PATH"])
    dir_exist_check(PATH_LIST["LOG_DIR_PATH"])
    try:
        crawler_logging("a+", "[START] : "+strftime('%Y/%m/%d-%H:%M:%S', localtime(time()))+"\n")
        page_crawler()
    except:
        e_log = traceback.format_exc()
        crawler_logging("a", "[ERROR_END] : " + strftime('%Y/%m/%d-%H:%M:%S', localtime(time()))+"\n"+e_log)
    crawler_logging("a", "[END] : " + strftime('%Y/%m/%d-%H:%M:%S', localtime(time()))+"\n")
    print("tor crawling is ended")


if __name__ == '__main__':
    XVFB_DISPLAY.start()
    ACCESS_TIMEOUT = int(sys.argv[2])
    main(sys.argv[1])
    if XVFB_DISPLAY.is_alive():
        XVFB_DISPLAY.stop()
