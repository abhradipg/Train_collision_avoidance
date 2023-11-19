from time import sleep
from random import random
from multiprocessing import Process
from multiprocessing import Queue
from queue import Empty
import time
from math import radians, sin, cos, sqrt, atan2
import socket
import time
import ast


my_dict = {}
def generate_dict():

    key = b'61d0'
    gps = [38.897701, -77.036552] 
    track_id = 7
    my_dict[key] = [gps, track_id]

    key = b'61d1'
    gps = [23.66, 4.53] 
    track_id = 7            
    my_dict[key] = [gps, track_id]

    key = b'61d2'
    gps = [56.44, -74.02] 
    track_id = 7            
    my_dict[key] = [gps, track_id]

    key = b'61d3'
    gps = [73.80, 153.56] 
    track_id = 7            
    my_dict[key] = [gps, track_id]

    key = b'61d4'
    gps = [49.12, -33.71] 
    track_id = 7            
    my_dict[key] = [gps, track_id]

    key = b'61d5'
    gps = [-47.97, 144.98] 
    track_id = 7            
    my_dict[key] = [gps, track_id]

    key = b'61d6'
    gps = [-78.87,-32.05] 
    track_id = 7            
    my_dict[key] = [gps, track_id]
    


def reader():
    tags=[b'61d0',b'61d1',b'61d2',b'61d3',b'61d4',b'61d5',b'61d6']
    return tags[int(random()*7)]

def rfid_reader(queue):
    old_data=''
    file_path = 'dummy_data1.txt'
    while True:
        with open(file_path, 'r') as file:
            for line in file:
                if "'EPCData':" in line:
                    # Convert the string representation of the dictionary to an actual dictionary
                    data_dict = ast.literal_eval(line.strip())
                    # Extracting the 'EPC' value and return it
                    data=data_dict['EPCData']['EPC']

                if data!=old_data:
                    old_data=data
                    sleep(2)
                    queue.put(my_dict[data])
                    print("put data",data)

def sender(queue):
    server_ip = '10.217.59.110'
    server_port = 2000
    server_addr = (server_ip, server_port)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    queue_empty=0
    data=0
    old_data=0
    received_ack=0
    ack_no=0
    curr_ack
    rtt_approx=1
    speed=100
    current_gps=0

    while True:
        try:
            queue_empty=0
            data = queue.get(block=False)
        except Empty:
            queue_empty = 1

        if queue_empty == 0:
            data = data+","+speed+","+ack_no
            curr_ack=ack_no
            ack_no=ack_no+1
            received_ack=0
            #curr_time=time.time()
            client_socket.sendto(data.encode(), (server_ip, server_port))
        
        if received_ack==0:
            client_socket.settimeout(rtt_approx)
            try:
                ack_data, server_address = client_socket.recvfrom(1024)
                if server_address==server_addr and ack_data==ack_no:
                    received_ack=1

            except socket.timeout:
                received_ack=0

def reciver():
    server_ip = '10.217.59.110'
    server_port = 3000

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    server_socket.bind((server_ip, server_port))

    while True:
        data, client_address = server_socket.recvfrom(1024)
        segments = data.split(',')
        ack_message = segments[-1]
        server_socket.sendto(ack_message.encode(), client_address)
        process_data(segments[:-2])

def process_data(lat1, lon1, lat2, lon2):
    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    # Radius of the Earth in kilometers (change it to 3958.8 for miles)
    radius = 6371.0

    # Calculate the distance
    distance = radius * c

    return distance

if __name__ == '__main__':
    queue = Queue()
    reader_process = Process(target=rfid_reader, args=(queue,))
    reader_process.start()
    sender_process = Process(target=sender, args=(queue,))
    sender_process.start()
    reciver_process = Process(target=reciver)
    reciver_process.start()
    reader_process.join()
    sender_process.join()
    reciver_process.join()
