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

pkt_loss_prob = 0.3
pkt_loss_to_database_prof = 0.3

data_packet_schema = {
    "id": int,
    "priority": bool,
    "pkt_no": int,
    "time": str,
    "metric": bool,
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
    def __init__(self, id, priority, data, pkt_no, metric = False):
        self.id = id
        self.priority = priority
        self.data = data
        self.pkt_no = pkt_no
        self.metric = metric
        
    def get_data(self):
        return json.dumps({"id": self.id, "priority": self.priority,"pkt_no":self.pkt_no,"time": str(datetime.datetime.now()), "data": self.data, "metric": self.metric}), self.pkt_no
    
class AckPacket:
    def __init__(self, id, received, pkt_no):
        self.id = id
        self.received = received
        self.pkt_no = pkt_no
    
    def get_data(self):
        return json.dumps({"id": self.id, "pkt_no": self.pkt_no, "received": self.received})

# ------------------------ Sensor Class ------------------------
class Sensor:
    def __init__(self, id, cluster_heads_info, timeout, repeats = 3):
        self.total_sent = {}
        for host_id, host, port in cluster_heads_info:
            self.total_sent[host_id] = 0
        self.timeout = timeout
        self.id = id
        self.repeats = repeats
        self.cluster_heads_info = cluster_heads_info
        self.lock = Lock()
        

    def connect_and_send(self, host_id, host, port, data, pkt_no, priority):
        attempts = 0
        while attempts < self.repeats:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    attempts += 1
                    self.lock.acquire()
                    self.total_sent[host_id] += 1
                    self.lock.release()
                    print("----------------------------------")
                    print(f"{Fore.BLUE} Sending Data from Sensor: {self.id} to Cluster: {host_id}, Pkt Num: {pkt_no} , Priority: {priority} {Style.RESET_ALL}")
                    print("----------------------------------")
                    sock.connect((host, port))
                    sock.settimeout(self.timeout)
                    sock.sendall(data.encode())
                    received = sock.recv(1024)
                    # Mimics corrupted Packet
                    if random.random() < pkt_loss_prob:
                        print("----------------------------------")
                        print(f"{Fore.YELLOW} Simulating ACK Loss from Cluster: {host_id} {Style.RESET_ALL} ")
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
                            print(f"{Fore.GREEN} Received ACK from Cluster: {src}, ACK Num: {pkt_num} {Style.RESET_ALL}")
                            print("----------------------------------")
                            break
                    else:
                        print("----------------------------------") 
                        print(f"{Fore.RED} Received Invalid Data: {data} {Style.RESET_ALL}")
                        print("----------------------------------") 
            except Exception as e:
                print("----------------------------------")
                print(f"{Fore.RED} Error connecting to Cluster: {host_id} {Style.RESET_ALL}" )
                print("----------------------------------")
            finally: 
                sock.close()
                
    def send_data(self, data, pkt_no, priority):
        threads = []
        for host_id, host, port in self.cluster_heads_info:
            thread = threading.Thread(target=self.connect_and_send, args=(host_id, host, port, data, pkt_no, priority))
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
# ------------------------ Cluster Head Class ------------------------
class ClusterHead:
    def __init__(self, id, host, port, server_host, server_port, timeout=2, repeats = 3, send_interval = 10, buffer_size = 20):
        self.total_received = {}
        self.total_sent = {1: 0}
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
        self.repeats = repeats
        self.send_interval = send_interval
        self.buffer_size = buffer_size
        
    def connect_and_send(self, host_id, host, port, send_data, pkt_no, priority):
        attempts = 0
        while attempts < self.repeats:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    attempts += 1
                    self.total_sent[1] += 1
                    print("----------------------------------")
                    print(f"{Fore.BLUE} Sending Data from Cluster: {self.id} to Server: {host_id}, Pkt Num: {pkt_no}, Sensor ID: {send_data.get('data').get('id')} , Sensor Pkt Num: {send_data.get('data').get('pkt_no')} {Style.RESET_ALL}")
                    print("----------------------------------")
                    sock.connect((host, port))
                    sock.settimeout(self.timeout)
                    sock.sendall(json.dumps(send_data).encode())
                    data = sock.recv(1024)
                    if random.random() < pkt_loss_prob:
                        print("----------------------------------")
                        print(f"{Fore.YELLOW}Simulating ACK Loss from Server {Style.RESET_ALL}")
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
                            print(f"{Fore.GREEN} Received ACK from SERVER: {src}, ACK Num: {pkt_num} {Style.RESET_ALL}")
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
            finally: 
                sock.close()
    
    def constant_sending(self):
        while True: 
            time.sleep(self.send_interval)
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
                if self.pkt_no % 10 == 0:
                    data_pkt = {
                        "id": self.id,
                        "priority": False,
                        "pkt_no": self.pkt_no,
                        "time": str(datetime.datetime.now()),
                        "data": {"received": self.total_received, "sent": self.total_sent},
                        "metric": True
                    }
                    self.connect_and_send("Metric", self.server_host, self.server_port, data_pkt, self.pkt_no, priority)
                else:
                    data_pkt = {
                        "id": self.id,
                        "priority": self.mapping[data_id].get('priority'),
                        "pkt_no": self.pkt_no,
                        "time": str(datetime.datetime.now()),
                        "data": self.mapping[data_id],
                        "metric": self.mapping[data_id].get('metric')
                    }
                    self.connect_and_send(1, self.server_host, self.server_port, data_pkt, self.pkt_no, priority)
                    if priority:
                        self.high_priority.pop(0)
                    elif not priority:
                        self.low_priority.pop(0)
                    del self.mapping[data_id]
    
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
                    # Simulate Packet Loss
                    if random.random() < pkt_loss_prob:
                        print("----------------------------------")
                        print(f"{Fore.YELLOW}Simulating Packet Loss from Sensor: {src} {Style.RESET_ALL}")
                        print("----------------------------------")
                        break
                    print("----------------------------------")
                    print(f"{Fore.CYAN} Received from Sensor: {src}, Pkt Num: {pkt_num} {Style.RESET_ALL}")
                    print("----------------------------------")
                    
                    self.lock.acquire()
                    short = f"{src}_{pkt_num}"
                    if src not in self.total_received:
                        self.total_received[src] = 1
                    else:
                        self.total_received[src] += 1
                    if src not in self.buffer:
                        self.buffer[src] = (pkt_num,pkt_num + 1)
                        self.mapping[short] = data
                        if data.get('priority'):
                            self.high_priority.append(short)
                        elif not data.get('priority'):
                            self.low_priority.append(short)
                        if len(self.high_priority) > self.buffer_size:
                            remove = self.high_priority.pop(0)
                            # del self.mapping[remove]
                        elif len(self.low_priority) > self.buffer_size:
                            remove = self.low_priority.pop(0)
                            # del self.mapping[remove]
                            
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
        self.overall_rcv = {}
        self.sensors_sent = {}
        self.clusters_rcv = {}
        self.clusters_sent = {}
        self.server_rcv = {}
        
        
        
    def constant_sending(self):
        while True: 
            time.sleep(self.send_interval)
            self.lock.acquire()
            print("----------------------------------")
            print(f"Buffer: {list(self.buffer.values())}")
            sorted_keys = sorted(self.buffer, key=lambda k: self.buffer[k], reverse=True)
            if len(sorted_keys) == 0:
                print("----------------------------------")
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
                print(f"{Fore.YELLOW} Simulating Packet Loss from Database, remaining tries: {self.buffer[str_data][2]} {Style.RESET_ALL}")
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
                    if random.random() < pkt_loss_prob:
                        print("----------------------------------")
                        print(f"{Fore.YELLOW} Simulating Packet Loss from Cluster: {src} {Style.RESET_ALL}")
                        print("----------------------------------")
                        break
                    print("----------------------------------")
                    print(f"{Fore.CYAN} Received from Cluster: {src}, Pkt Num: {pkt_num}, Sensor ID: {data.get('data').get('id')} , Sensor Pkt Num: {data.get('data').get('pkt_no')} {Style.RESET_ALL}")
                    print("----------------------------------")
                    
                    self.lock.acquire()
                    sensor_data = data.get("data")

                    if data.get("metric"):
                        metrics = data.get("data")
                        sens_id = metrics.get("id")
                        if metrics.get("received"):
                            if src in self.clusters_rcv.keys():
                                # metrics.get("received") is a dictionary {sensor_id: number}
                                for key in metrics.get("received").keys():
                                    if key in self.clusters_rcv[src].keys():
                                        self.clusters_rcv[src][key] = max(self.clusters_rcv[src][key], metrics.get("received")[key])
                                    else:
                                        self.clusters_rcv[src][key] = metrics.get("received")[key]
                                for key in metrics.get("sent").keys():
                                    if key in self.clusters_sent[src].keys():
                                        self.clusters_sent[src][key] = max(self.clusters_sent[src][key], metrics.get("sent")[key])
                                    else:
                                        self.clusters_sent[src][key] = metrics.get("sent")[key]
                            else:
                                for key in metrics.get("received").keys():
                                    self.clusters_rcv[src] = {key: metrics.get("received")[key]}
                                for key in metrics.get("sent").keys():
                                    self.clusters_sent[src] = {key: metrics.get("sent")[key]}
                        else:
                            if sens_id in self.sensors_sent.keys():
                                for key in metrics.get("data").get("sent").keys():
                                    if key in self.sensors_sent[sens_id].keys():
                                        self.sensors_sent[sens_id][key] = max(self.sensors_sent[sens_id][key], metrics.get("data").get("sent")[key])
                                    else:
                                        self.sensors_sent[sens_id][key] = metrics.get("data").get("sent")[key]
                            else:
                                for key in metrics.get("data").get("sent").keys():
                                    self.sensors_sent[sens_id] = {key: metrics.get("data").get("sent")[key]}
                        print("----------------------------------")
                        percentages = [(x,round(len(self.overall_rcv[x])/max(self.overall_rcv[x]),4)) for x in self.overall_rcv]
                        print(f"{Fore.LIGHTRED_EX} Overall Rcv Rate: {round(sum([x[1] for x in percentages])/len(percentages),4) if percentages else 0} {Style.RESET_ALL}")
                        print(f"{Fore.LIGHTRED_EX} Overall Rcv Rates: {[f'Sensor {x[0]}: %= {x[1]}' for x in percentages]} {Style.RESET_ALL}")
                        print(f"{Fore.LIGHTRED_EX} Overall Received: {[f"Sensor {x}: Total = {max(self.overall_rcv[x])}, RCV = {len(self.overall_rcv[x])}" for x in self.overall_rcv]} {Style.RESET_ALL}")
                        print(f"{Fore.LIGHTRED_EX} Sensors Sent: {self.sensors_sent} {Style.RESET_ALL}")
                        print(f"{Fore.LIGHTRED_EX} Clusters Rcv: {self.clusters_rcv} {Style.RESET_ALL}")
                        print(f"{Fore.LIGHTRED_EX} Clusters Sent: {self.clusters_sent} {Style.RESET_ALL}")
                        print(f"{Fore.LIGHTRED_EX} Server Rcv: {self.server_rcv} {Style.RESET_ALL}")
                        print("----------------------------------")
                       
                    if json.dumps(sensor_data) not in self.buffer.keys():
                        if data.get("data").get("id") is not None and data.get("data").get("id") in self.overall_rcv.keys() and data.get("data").get("pkt_no") not in self.overall_rcv[data.get("data").get("id")]:
                            self.overall_rcv[data.get("data").get("id")].append(data.get("data").get("pkt_no"))
                        elif data.get("data").get("id") is not None and data.get("data").get("id") not in self.overall_rcv.keys():
                            self.overall_rcv[data.get("data").get("id")] = [data.get("data").get("pkt_no")]
                        self.counter += 1
                        
                        
                        if src in self.server_rcv.keys():
                            self.server_rcv[src] += 1
                        else:
                            self.server_rcv[src] = 1
                            
                            
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
                    pkt = AckPacket(self.id, True, data.get('pkt_no')).get_data()
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
    
    