# CHECKLIST
# 1. Multiple Sensors (Done)
# 2. Multiple Cluster heads (Done)
# 3. Priority queues for data to ensure that all data can be sent (Done)
# 4. Buffering on cluster (Done)
# 5. Data Format (Done)
# 6. How cluster heads communicate if any (Communicate at the main server)
# 7. ACK and NAK for received data (Done)
# 8. Redundancy to ensure data integrity
# 9. Main server receive and write to file
import socket
import time
import threading
import json
import datetime
import random
from manifest import *
from multiprocessing import Process, Lock
from colorama import Fore, Style, init
import firebase_admin
from firebase_admin import db, credentials
import sys

FIREBASE_URL = "https://networks-af47e-default-rtdb.asia-southeast1.firebasedatabase.app"
SECRET_KEY = "lU8WbmrGewdMbErL0AYyFvHFY9dsH7eXP4YTLgtD"

cred = credentials.Certificate("./networks-af47e-firebase-adminsdk-mgw4o-ea47d45684.json")

default_app = firebase_admin.initialize_app(cred, {
	'databaseURL': FIREBASE_URL
	})

init()

# Blue for Sending 

# Red for NAK
# Green for Received ACKS
# Cyan for Received Pkt
# 
# Simple window mechanism, we keep track of the most recently received pkt and the next expected pkt. If receive a pkt that is less than the next expected pkt, we drop the pkt. Else update. 
# Edge case: If the value is less than over 20, then can reset buffer to new one as can assume some issue occured rather than 20 pkts skipped.

# Buffer for server is different, it stores the data itself and checks if anty of the clussters send repeat cause there will be redundancy.



corrupt_prob = 0.1
pkt_loss_prob = 0.1
pkt_loss_to_database_prof = 0.5

data_packet_schema = {
    "id": int,
    "priority": bool,
    "pkt_no": int,
    "time": str,
    "data": dict
}

ack_packet_schema = {
    "id": int,
    "pkt_no": int,
    "received": bool
}

def validate_data_packet(data):
    required_keys = data_packet_schema
    if not isinstance(data, dict):
        return False
    for key, expected_type in required_keys.items():
        if key not in data or not isinstance(data[key], expected_type):
            return False
    return True

def validate_ack_packet(data):
    required_keys = ack_packet_schema
    if not isinstance(data, dict):
        return False
    for key, expected_type in required_keys.items():
        if key not in data or not isinstance(data[key], expected_type):
            return False
    return True

def convert_to_short(data):
    # Return data pkt source id and packet number
    return data.get('id'),data.get('pkt_no')

# ------------------------ Packet Definitions ------------------------
class DataPacket:
    def __init__(self, id, priority, data, pkt_no):
        self.id = id
        self.priority = priority
        self.data = data
        self.pkt_no = pkt_no
        
    def get_data(self):
        return json.dumps({"id": self.id, "priority": self.priority,"pkt_no":self.pkt_no,"time": str(datetime.datetime.now()), "data": self.data}), self.pkt_no
    
class AckPacket:
    def __init__(self, id, received, pkt_no):
        self.id = id
        self.received = received
        self.pkt_no = pkt_no
    
    def get_data(self):
        return json.dumps({"id": self.id, "pkt_no": self.pkt_no, "received": self.received})

# ------------------------ Sensor Class ------------------------
class Sensor:
    def __init__(self, id, cluster_heads_info, timeout):
        self.timeout = timeout
        self.id = id
        self.cluster_heads_info = cluster_heads_info
        

    def connect_and_send(self, host_id, host, port, data, pkt_no):
        attempts = 0
        while attempts < 3:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    print("----------------------------------")
                    print(f"{Fore.BLUE} Sending Data from Sensor: {self.id} to Cluster: {host_id}, Pkt Num: {pkt_no} {Style.RESET_ALL}")
                    print("----------------------------------")
                    sock.connect((host, port))
                    sock.settimeout(self.timeout)
                    attempts += 1
                    time.sleep(3)
                    sock.sendall(data.encode())
                    received = sock.recv(1024)
                    # Mimics corrupted Packet
                    if random.random() < pkt_loss_prob:
                        print("----------------------------------")
                        print(f"{Fore.YELLOW} Simulating Corrupted Data from Cluster: {host_id} {Style.RESET_ALL} ")
                        print("----------------------------------")
                        continue
                    if not received:
                        continue
                    received = received.decode()
                    received = json.loads(received)
                    if validate_ack_packet(received):
                        src, pkt_num = convert_to_short(received)
                        if received.get('received') and pkt_no == received.get('pkt_no'):
                            print("----------------------------------")
                            print(f"{Fore.GREEN} Received from Cluster: {src}, ACK Num: {pkt_num} {Style.RESET_ALL}")
                            print("----------------------------------")
                            break
                    else:
                        print("----------------------------------") 
                        print(f"{Fore.RED} Received Invalid Data: {data} {Style.RESET_ALL}")
                        print("----------------------------------") 
            except Exception as e:
                attempts += 1
                print("----------------------------------")
                print(f"{Fore.RED} Error connecting to Cluster: {host_id} {Style.RESET_ALL}" )
                print("----------------------------------")
                
    def send_data(self, data, pkt_no):
        threads = []
        for host_id, host, port in self.cluster_heads_info:
            thread = threading.Thread(target=self.connect_and_send, args=(host_id, host, port, data, pkt_no))
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
# ------------------------ Cluster Head Class ------------------------
class ClusterHead:
    def __init__(self, id, host, port, server_host, server_port, timeout=10):
        self.timeout = timeout
        self.id = id
        self.host = host
        self.port = port
        self.lock = Lock()
        self.server_host = server_host
        self.server_port = server_port
        self.pkt_no = 0
        self.main_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.high_priority = []
        self.low_priority = []
        self.buffer = {}
        self.mapping = {}
        
    def connect_and_send(self, host_id, host, port, data, pkt_no, priority):
        try:
            attempts = 0
            while attempts < 3:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    attempts += 1
                    print("----------------------------------")
                    print(f"{Fore.BLUE} Sending Data from Cluster: {self.id} to Server: {host_id}, Pkt Num: {pkt_no}, Sensor ID: {data.get('data').get('id')} , Sensor Pkt Num: {data.get('data').get('pkt_no')} {Style.RESET_ALL}")
                    print("----------------------------------")
                    sock.connect((host, port))
                    sock.settimeout(self.timeout)
                    time.sleep(3)
                    sock.sendall(json.dumps(data).encode())
                    data = sock.recv(1024)
                    # Mimics corrupted Packet
                    if random.random() < pkt_loss_prob:
                        print("----------------------------------")
                        print(f"{Fore.YELLOW}Simulating Corrupted Data {Style.RESET_ALL}")
                        print("----------------------------------")
                        continue
                    if not data:
                        continue
                    data = data.decode()
                    data = json.loads(data)
                    if validate_ack_packet(data):
                        src, pkt_num = convert_to_short(data)
                        if data.get('received') and pkt_no == data.get('pkt_no'):
                            print("----------------------------------")
                            print(f"{Fore.GREEN} Received from SERVER: {src}, ACK Num: {pkt_num} {Style.RESET_ALL}")
                            print("----------------------------------")
                            break
                            
                    else:
                        print("----------------------------------") 
                        print(f"{Fore.RED} Received Invalid Data: {data} {Style.RESET_ALL}")
                        print("----------------------------------") 
        except Exception as e:
            print("----------------------------------")
            print(f"{Fore.RED} Error connecting to {host}:{port} - {str(e)} {Style.RESET_ALL}" )
            print("----------------------------------")
    
    def constant_sending(self):
        while True: 
            time.sleep(3)
            self.lock.acquire()
            print("----------------------------------")
            print(f"High Priority: {self.high_priority}")
            print(f"Low Priority: {self.low_priority}")
            print(f"Buffer: {self.buffer}")
            data_id = None
            priority = False
            if len(self.high_priority) > 0:
                data_id = self.high_priority[0]
                priority = True
            elif len(self.low_priority) > 0:
                data_id = self.low_priority[0]
            if data_id is not None:
                data_pkt = {
                    "id": self.id,
                    "priority": self.mapping[data_id].get('priority'),
                    "pkt_no": self.pkt_no,
                    "time": str(datetime.datetime.now()),
                    "data": self.mapping[data_id]
                }
                print(f"Sending: {data_id} from {convert_to_short(data_pkt)}")
                self.connect_and_send(data_id, self.server_host, self.server_port, data_pkt, self.pkt_no, priority)
                # if after 3 attempts, just remove
                if priority:
                    self.high_priority.pop(0)
                elif not priority:
                    self.low_priority.pop(0)
    
                self.pkt_no += 1
            print("----------------------------------")
            self.lock.release()
            
            
    def handle_client(self, conn, addr):
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                data = data.decode()
                data = json.loads(data)
                if validate_data_packet(data):
                    src, pkt_num = convert_to_short(data)
                    print("----------------------------------")
                    print(f"{Fore.CYAN} Received from Sensor: {src}, Pkt Num: {pkt_num} {Style.RESET_ALL}")
                    print("----------------------------------")
                    
                    self.lock.acquire()
                    short = f"{src}_{pkt_num}"
                    if src not in self.buffer:
                        self.buffer[src] = (pkt_num,pkt_num + 1)
                        self.mapping[short] = data
                        if data.get('priority'):
                            self.high_priority.append(short)
                        elif not data.get('priority'):
                            self.low_priority.append(short)
                            
                    else:
                        if pkt_num < self.buffer[src][1] and pkt_num > (self.buffer[src][1] - 20):
                            print(f"{Fore.RED} Unexpected Pkt: {pkt_num} < Expected {self.buffer[src][1]} {Style.RESET_ALL}")
                        else:
                            self.buffer[src] = (pkt_num, pkt_num + 1)
                            self.mapping[short] = data
                            if data.get('priority'):
                                self.high_priority.append(short)
                            elif not data.get('priority'):
                                self.low_priority.append(short)
                    self.lock.release()
                    # Send ACK regardless, just dont add to buffer etc.
                    
                    
                    pkt = AckPacket(self.id, True, data.get('pkt_no')).get_data()
                    # Mimics Packet Loss (Dont send means sensor dont receive)
                    if random.random() < corrupt_prob:
                        print("----------------------------------")
                        print(f"{Fore.YELLOW} Simulating ACK Loss from Cluster: {self.id} {Style.RESET_ALL}")
                        print("----------------------------------")
                        continue
                    conn.sendall(pkt.encode())
                else:
                    print("----------------------------------")
                    print(f"{Fore.RED} Received Invalid Data: {data} {Style.RESET_ALL}")
                    print("----------------------------------")
                    pkt = AckPacket(self.id, False, data.get('pkt_no')).get_data()
                    conn.sendall(pkt.encode())
        finally:
            conn.close()
        
    def start_server(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen()
        sender_thread = threading.Thread(target=self.constant_sending)
        sender_thread.start()
        while True:
            conn, addr = self.sock.accept()
            client_thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            client_thread.start()
        
# ------------------------ Main Server Class ------------------------
class MainServer():
    def __init__(self, host, port, id = 1, buffer_size = 3, send_interval = 10):
        self.send_limit = 5
        self.id = id
        self.counter = 0
        self.buffer_size = buffer_size
        self.host = host
        self.port = port
        self.lock = Lock()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.buffer = {}
        self.priority = []
        self.send_interval = send_interval
        
        
        
    def constant_sending(self):
        while True: 
            time.sleep(self.send_interval)
            self.lock.acquire()
            print("----------------------------------")
            print(f"Buffer: {list(self.buffer.values())}")
            sorted_keys = sorted(self.buffer, key=lambda k: self.buffer[k], reverse=True)
            if len(sorted_keys) == 0:
                self.lock.release()
                continue
            idx = len(sorted_keys) - 1
            str_data  = sorted_keys[idx]
            while self.buffer[str_data][2] <= 0 and idx > 0:
                idx = idx - 1
                str_data = sorted_keys[idx]
            if self.buffer[str_data][2] <= 0:
                print("----------------------------------")
                self.lock.release()
                continue
            try:
                if random.random() < pkt_loss_to_database_prof:
                    raise Exception
                data = json.loads(str_data)
                ref = db.reference(f"/Sensor_{data.get('id')}")
                ref.push().set(data)
                print(f"{Fore.GREEN} Sent to Database: Sensor_{data.get('id')} {Style.RESET_ALL}")
                if len(self.buffer) <= self.buffer_size: 
                    self.buffer[str_data] = (self.buffer[str_data][0], self.buffer[str_data][1], 0)
                else:    
                    del self.buffer[str_data]
            except:
                self.buffer[str_data] = (self.buffer[str_data][0], self.buffer[str_data][1], self.buffer[str_data][2] - 1)
                print(f"{Fore.RED} Packet Loss, remaining tries: {self.buffer[str_data][1]} {Style.RESET_ALL}")
            finally:
                print("----------------------------------")
                self.lock.release()
                continue
            
    def handle_client(self, conn, addr):
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                data = data.decode()
                data = json.loads(data)
                if validate_data_packet(data):
                    src, pkt_num = convert_to_short(data)
                    print("----------------------------------")
                    print(f"{Fore.CYAN} Received from Cluster: {src}, Pkt Num: {pkt_num}, Sensor ID: {data.get('data').get('id')} , Sensor Pkt Num: {data.get('data').get('pkt_no')} {Style.RESET_ALL}")
                    print("----------------------------------")
                    
                    self.lock.acquire()
                    sensor_data = data.get("data")
                    if json.dumps(sensor_data) not in self.buffer.keys():
                        self.counter += 1
                        priority = 0 if data.get('priority') else 1
                        self.buffer[json.dumps(sensor_data)] = (priority, self.counter, self.send_limit)
                        with open ("local_db.txt", "a") as f:
                            f.write(json.dumps(sensor_data))
                            f.write("\n")
                        if len(self.buffer) > self.buffer_size:
                            sorted_keys = sorted(self.buffer, key=lambda k: self.buffer[k], reverse=True)
                            del self.buffer[sorted_keys[-1]]
                    else:
                        print(f"{Fore.RED} Pkt already received: (Sensor ID: {sensor_data.get('id')}, Sensor Pkt Num: {sensor_data.get('pkt_no')}), ignore data from Cluster: {src} {Style.RESET_ALL}")
                    self.lock.release()
                    
                    
                    # Mimics Packet Loss (Dont send means sensor dont receive)
                    pkt = AckPacket(self.id, True, data.get('pkt_no')).get_data()
                    if random.random() < pkt_loss_prob:
                        print("----------------------------------")
                        print(f"{Fore.YELLOW} Simulating ACK Loss from Server: {self.id} {Style.RESET_ALL}")
                        print("----------------------------------")
                        continue
                    conn.sendall(pkt.encode())
                else:
                    pkt = AckPacket(self.id, True, data.get('pkt_no')).get_data()
                    print("----------------------------------")
                    print(f"{Fore.RED} Received Invalid Data: {data} {Style.RESET_ALL}")
                    print("----------------------------------")
                    conn.sendall(pkt.encode())
        finally:
            conn.close()
        
    def start_server(self):
        self.sock.bind((self.host, self.port))
        self.sock.listen()
        sender_thread = threading.Thread(target=self.constant_sending)
        sender_thread.start()
        while True:
            conn, addr = self.sock.accept()
            client_thread = threading.Thread(target=self.handle_client, args=(conn, addr))
            client_thread.start()
    
    