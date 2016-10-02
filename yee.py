#!/usr/bin/python
import socket
import fcntl
import re
import os
import errno
import struct
from threading import Thread
from time import sleep
import logging
import sys
import json
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient


detected_bulbs = {}
bulb_idx2ip = {}
DEBUGGING = False
RUNNING = True
current_command_id = 0
MCAST_GRP = '239.255.255.250'

scan_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
fcntl.fcntl(scan_socket, fcntl.F_SETFL, os.O_NONBLOCK)
listen_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
listen_socket.bind(("", 1982))
fcntl.fcntl(listen_socket, fcntl.F_SETFL, os.O_NONBLOCK)
mreq = struct.pack("4sl", socket.inet_aton(MCAST_GRP), socket.INADDR_ANY)
listen_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

# Configure logging
logger = None
if sys.version_info[0] == 3:
    logger = logging.getLogger("core")  # Python 3
else:
    logger = logging.getLogger("AWSIoTPythonSDK.core")  # Python 2
logger.setLevel(logging.DEBUG)
streamHandler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
streamHandler.setFormatter(formatter)
logger.addHandler(streamHandler)

# Init AWSIoTMQTTClient

myAWSIoTMQTTClient = AWSIoTMQTTClient("alexa_light_subs", useWebsocket=True)
myAWSIoTMQTTClient.configureEndpoint("a3d2g35udo4lz5.iot.eu-west-1.amazonaws.com", 443)
myAWSIoTMQTTClient.configureCredentials("/opt/cert/rootCA.pem")

# AWSIoTMQTTClient connection configuration
myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec


def debug(msg):
    if DEBUGGING:
        logging.info(msg)


def next_cmd_id():
    global current_command_id
    current_command_id += 1
    return current_command_id


def send_search_broadcast():
    '''
    multicast search request to all hosts in LAN, do not wait for response
    '''
    multicase_address = (MCAST_GRP, 1982)
    debug("send search request")
    msg = "M-SEARCH * HTTP/1.1\r\n"
    msg = msg + "HOST: 239.255.255.250:1982\r\n"
    msg = msg + "MAN: \"ssdp:discover\"\r\n"
    msg = msg + "ST: wifi_bulb"
    scan_socket.sendto(msg, multicase_address)


def bulbs_detection_loop():
    '''
    a standalone thread broadcasting search request and listening on all responses
    '''
    debug("bulbs_detection_loop running")
    search_interval=30000
    read_interval=100
    time_elapsed=0

    while RUNNING:
        if time_elapsed%search_interval == 0:
            send_search_broadcast()

        # scanner
        while True:
            try:
                data = scan_socket.recv(2048)
            except socket.error, e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    break
                else:
                    logging.error(e)
                    sys.exit(1)
            handle_search_response(data)

        # passive listener
        while True:
            try:
                data, addr = listen_socket.recvfrom(2048)
            except socket.error, e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    break
                else:
                    logging.error(e)
                    sys.exit(1)
            handle_search_response(data)

        time_elapsed+=read_interval
        sleep(read_interval/1000.0)
    scan_socket.close()
    listen_socket.close()


def get_param_value(data, param):
    '''
    match line of 'param = value'
    '''
    param_re = re.compile(param+":\s*([ -~]*)") #match all printable characters
    match = param_re.search(data)
    if match != None:
        value = match.group(1)
        return value


def handle_search_response(data):
    '''
    Parse search response and extract all interested data.
    If new bulb is found, insert it into dictionary of managed bulbs.
    '''
    location_re = re.compile("Location.*yeelight[^0-9]*([0-9]{1,3}(\.[0-9]{1,3}){3}):([0-9]*)")
    match = location_re.search(data)
    if match == None:
        debug( "invalid data received: " + data )
        return

    host_ip = match.group(1)
    if detected_bulbs.has_key(host_ip):
        bulb_id = detected_bulbs[host_ip][0]
    else:
        bulb_id = len(detected_bulbs)+1
    host_port = match.group(3)
    model = get_param_value(data, "model")
    power = get_param_value(data, "power")
    bright = get_param_value(data, "bright")
    rgb = get_param_value(data, "rgb")
    # use two dictionaries to store index->ip and ip->bulb map
    detected_bulbs[host_ip] = [bulb_id, model, power, bright, rgb, host_port]
    bulb_idx2ip[bulb_id] = host_ip


def display_bulb(idx):
    if not bulb_idx2ip.has_key(idx):
        logging.error("error: invalid bulb idx")
        return
    bulb_ip = bulb_idx2ip[idx]
    model = detected_bulbs[bulb_ip][1]
    power = detected_bulbs[bulb_ip][2]
    bright = detected_bulbs[bulb_ip][3]
    rgb = detected_bulbs[bulb_ip][4]
    logging.info(str(idx) + ": ip=" \
          +bulb_ip + ",model=" + model \
          +",power=" + power + ",bright=" \
          + bright + ",rgb=" + rgb)


def display_bulbs():
    logging.info(str(len(detected_bulbs)) + " managed bulbs")
    for i in range(1, len(detected_bulbs)+1):
        display_bulb(i)


def operate_on_bulb(idx, method, params):
    '''
    Operate on bulb; no gurantee of success.
    Input data 'params' must be a compiled into one string.
    E.g. params="1"; params="\"smooth\"", params="1,\"smooth\",80"
    '''
    if not bulb_idx2ip.has_key(idx):
        logging.error("error: invalid bulb idx")
        return
    bulb_ip=bulb_idx2ip[idx]
    port=detected_bulbs[bulb_ip][5]
    try:
        tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print "connect ",bulb_ip, port ,"..."
        tcp_socket.connect((bulb_ip, int(port)))
        msg="{\"id\":" + str(next_cmd_id()) + ",\"method\":\""
        msg += method + "\",\"params\":[" + params + "]}\r\n"
        logging.info(msg)
        tcp_socket.send(msg)
        tcp_socket.close()
    except Exception as e:
        logging.error("Unexpected error:", e)


def set_power(idx, action):
    params = '"' + str(action) + '"' + ', "smooth", 500'
    logging.info(params)
    operate_on_bulb(idx, "set_power", params=params)

def set_crazy(idx, action):
    params = '0, 2, "' + str(action) + '"'
    logging.info(params)
    operate_on_bulb(idx, "start_cf", params=params)

def toggle_bulb(idx):
    operate_on_bulb(idx, "toggle", "")

def set_bright(idx, bright):
    operate_on_bulb(idx, "set_bright", str(bright))

def set_rgb(idx, action):
    params = '{}, "smooth", 500'.format(action)
    print params
    operate_on_bulb(idx, "set_rgb", params=params)

def subscribe():
    # Connect and subscribe to AWS IoT
    myAWSIoTMQTTClient.connect()
    myAWSIoTMQTTClient.subscribe("/yee/light", 0, customCallback)
    while True:
        pass

# Custom MQTT message callback
def customCallback(client, userdata, message):
    print("Received a new message: ")

    msg = json.loads(str(message.payload))

    event = msg['event']
    action = msg['action']

    if event == "list":
        display_bulbs()
    elif event == "refresh":
        detected_bulbs.clear()
        bulb_idx2ip.clear()
        send_search_broadcast()
    elif event == "toggle":
        try:
            i = int(float(1))
            toggle_bulb(i)
        except:
            print("error in toggle")
    elif event == "set_power":
        try:
            i = int(float(1))
            set_power(i, action)
        except Exception as e:
            print("Unexpected error in set power: ", e)
    elif event == "start_cf":
        try:
            i = int(float(1))
            set_crazy(i, action)
        except Exception as e:
            print("Unexpected error in set power: ", e)
    elif event == "bright":
        try:
            idx = int(float(1))
            bright = int(float(action))
            set_bright(idx, bright)
        except:
            print("error in set bright")
    elif event == "set_rgb":
        try:
            i = int(float(1))
            set_rgb(i, action)
        except Exception as e:
            print("error in set color: ", str(e))
    else:
        logging.error("error in parse event")

    logging.info("event: " + event)
    logging.info("action: " + action)
    logging.info("--------------\n\n")


## main starts here
# print welcome message first
logging.info("Welcome to Yeelight WifiBulb Lan controller with Alexa")
# start the bulb detection thread
detection_thread = Thread(target=bulbs_detection_loop)
detection_thread.start()
# give detection thread some time to collect bulb info
sleep(0.2)
# user interaction loop
subscribe()
# user interaction end, tell detection thread to quit and wait
RUNNING = False
detection_thread.join()
# done