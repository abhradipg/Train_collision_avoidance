from time import sleep
from random import random
from multiprocessing import Lock
from multiprocessing import Process, Value, Array, Manager
from multiprocessing import Queue
from queue import Empty
import time
import pickle
import socket
import time

'''
receiver
------------
-runs as a separate process
-receive data from trains
-update the train table based on the received data (delete if present on other track, add if not already present, update ACK no. if on same track)
-put the recived data on queue to be read be sender function (which runs a separate process)
-need to take lock for train_table as it is used by sender function
'''
def receiver(train_table,queue,pending_ack,lock,ack_lock):

    #put our own IP and port on receiver IP and port
    print("receiver started")
    receiver_ip='10.114.241.211'
    receiver_port=2000
    sender_port=3000
    receiver_new_data=0
    curr_ack_no=0
    train_list=['10.114.241.43','10.114.241.208']
   
    #start a UDP socket connection for receiver
    receiver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver_socket.bind((receiver_ip, receiver_port))

    #start receiving data
    while True:
        '''
        #received data is of the format 
        [   gps,    trackid,    speed,  trainid,    ack_no  ]
        '''
        data, client_address = receiver_socket.recvfrom(1024)
        #unpikl the data received
        data = pickle.loads(data)
        ip_addr, port_no = client_address
        if ip_addr in train_list:
            print("data received by server-")
            print(data)
            if len(data) != 2:
                track_id = data[1] 
                ip_addr, port_no = client_address
                train_id = data[3]
                ack_no = [data[-1]]

                #pikle the ACK and send 
                ack_no = pickle.dumps(ack_no)
                print("sending ack")
                print((ip_addr,sender_port))
                receiver_socket.sendto(ack_no, (ip_addr,sender_port))

                #remove the entry if train was present in another track in the table
                lock.acquire()
                for tid in train_table.keys():
                    if tid != track_id:
                        tuple_list = train_table[tid].copy()
                        for tuple in tuple_list:
                            if tuple[0] == train_id:
                                print(tid)
                                print(tuple)
                                train_table[tid].remove(tuple)
                lock.release()
            
                #Update the train table
                tuple = [train_id,ip_addr]
                lock.acquire()
                if track_id in train_table.keys():
                    # Key already exists, append value to the existing list
                    if tuple not in train_table[track_id]:
                        print(f"Before table: {train_table}")
                        print("append")
                        train_table[track_id]+=[tuple]
                else:
                    # Key does not exist, create a new entry with a list containing the value
                    train_table[track_id] = list()
                    train_table[track_id]+=[tuple]
                lock.release()

                print(f"Updated table: {train_table}")
                print(data)

                #pikle the data received and put in the queue to be read by sender function
                data_new=data[0:4]
                data_new.append(ip_addr)
                data_new.append(curr_ack_no)
                curr_ack_no=curr_ack_no+1
                data_new=pickle.dumps(data_new)
                #Append train IP and insert in queue
                queue.put(data_new)

            elif len(data)==2:
                print("got ack")
                print(data)
                ip_addr, port_no = client_address
                print(ip_addr)
                ack_no = data[0]
                ack_lock.acquire()
                acked_list = []
                for ack in pending_ack:
                    #pending_ack is a list which has pending acks
                    #format is [ train_ip_fwd, pikled data, time_ack_sent, ack_no ]
                    if ack[0] == ip_addr and str(ack[3]) == str(ack_no):
                        print("appended")
                        acked_list.append(ack)
                for ack in acked_list:
                    pending_ack.remove(ack)
                print(pending_ack)
                ack_lock.release()

'''
sender
------------
-runs as a separate process
-read data from queue, do a table lookup and forward the data to respective trains
-need to take lock for train_table as it is used by receiver function
'''
def sender(train_table,queue,pending_ack,lock,ack_lock):
    pending_ack_list=[]
    train_address=0
    queue_empty=0
    rto = 5 #retransmission timeout
    #read from queue
    ack_no=0
    while True:
        try:
            queue_empty=0
            data=queue.get(block=False)
            data = pickle.loads(data)
            ack_no=data[-1]
            print("ack no while sending")
            print(ack_no)

        except:
            queue_empty=1

        if queue_empty==0:
            trackid=data[1]
            print(data)
            lock.acquire()
            train_list=train_table[trackid]
            lock.release()

            #Forward the data to all trains in the tracks
            #tuple = [  train_id,   ip_addr ] #old comment more members might be added
            for train in train_list:
                if train[0]!=data[3]:
                    train_ip=train[1]
                    print(train_ip)
                    train_port=3000
                    train_address=(train_ip,train_port)
                    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    print("sending gps")
                    print(data)
                    packet=pickle.dumps(data)

                    ack_lock.acquire()
                    #pending_ack is a list which has pending acks
                    #format is [ train_ip_fwd, pikled data, time_ack_sent, ack_no ]
                    pending_ack.append([train_ip,packet,time.time(),ack_no])
                    ack_lock.release()
                    server_socket.sendto(packet, train_address)

        ack_lock.acquire()
        for ack in pending_ack:
            if time.time() - ack[2] > rto:
                print("Ack not received resending-")
                train_ip = ack[0]
                port = 3000
                train_address=(train_ip,port)
                packet = ack[1]
                ack[2]=time.time()
                server_socket.sendto(packet, train_address)
        ack_lock.release()


if __name__ == '__main__':
    queue = Queue()
    manager = Manager()
    lock=Lock()
    ack_lock=Lock()
    train_table = manager.dict()
    pending_ack = manager.list()
    receiver_process = Process(target=receiver, args=(train_table,queue,pending_ack,lock,ack_lock))
    sender_process = Process(target=sender, args=(train_table,queue,pending_ack,lock,ack_lock))
    sender_process.start()
    receiver_process.start()
    sender_process.join()
    receiver_process.join()
