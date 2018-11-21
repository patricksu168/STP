# UDP CLIENT PROGRAM
#
# This is a client-side program for making ping requests to a server
#
# UDP CLIENT PROGRAM
#
# This is the client-side program to
# send requests to the server.

import random
import time
import json
from select import select
from socket import *


class STPSender:
    def __init__(self, server_ip, server_port, mws, mss, timeout, pdrop, seed):
        self.ip = gethostbyname(gethostname())
        self.port_num = 13000
        self.server_ip = server_ip
        self.server_port = server_port
        self.mws = mws
        self. mss = mss
        self.timeout_interval = timeout
        self.pdrop = pdrop
        self.seed = seed
        self.buffer = []
        self.data_buffered = 0
        self.send_base = random.randint(1, 101)
        self.init_seq_num = self.send_base
        self.ack_num = 0
        self.temp_data = ""
        self.duplicate_count = 0

        self.timer = None

    def run_sender(self, file_name):

        clientSocket = socket(AF_INET, SOCK_DGRAM)
        clientSocket.bind(('', self.port_num))

        file = open(file_name, "r")
        content = file.read()

        # flag to indicate if we need to set up connection
        connect = True
        inputs = [clientSocket]
        outputs = [clientSocket]
        while outputs != []:
            # check if socket is receiving segment
            rec_sock, send_sock, err_sock = select(inputs, outputs, [])

            if self.timer != None:
                #print(time.time() - self.timer)
                if time.time() - self.timer > self.timeout_interval:
                    self.timeout(clientSocket)
                    continue
            # when socket is sending data chunks
            for s in send_sock:
                if connect == True:
                    if self.buffer == []:
                        self.send(s, "", None, 1)
                elif content == "":
                    if not file.closed:
                        file.close()
                        self.send(s, "", None, 2)
                else:
                    if self.temp_data == "":
                        seg_data= content[0:self.mss]
                        content = content[self.mss:]
                        self.send(s, seg_data, None, 0)
                    else:
                        self.send(s, self.temp_data, None, 0)

            for r in rec_sock:
                seg_string, address = r.recvfrom(2048)
                ack_seg = json.loads(seg_string.decode('utf-8'))
                print(ack_seg)
                print("send_base is: " + str(self.send_base))
                if ack_seg["SYN"] == 1:
                    self.buffer.pop(0)
                    self.ack_num += ack_seg["seq_num"] + 1
                    self.send(r, "", None, 0)
                    connect = False
                elif ack_seg["FIN"] == 1:
                    self.buffer.pop(0)
                    self.send(r, "", None, 2)
                    self.ack_num += 1
                    # sent last ack packet, tear down connection and close socket
                    print("closing down client socket")
                    clientSocket.close()
                    clientSocket = None
                    inputs.pop(0)
                    outputs.pop(0)

                elif ack_seg["ACK_num"] > self.send_base:
                    self.send_base = ack_seg["ACK_num"]
                    while self.buffer != []:
                        if self.buffer[0]["seq_num"] < self.send_base:
                            print("clearing window")
                            temp = self.buffer.pop(0)
                            print(temp)
                        else:
                            break
                    if self.buffer != []:
                        self.start_timer()
                    else:
                        self.timer = None
                    self.duplicate_count = 0

                elif ack_seg["ACK_num"] <= self.send_base:
                    self.duplicate_count += 1
                    if self.duplicate_count == 3:
                        for s in self.buffer:
                            if s["seq_num"] == ack_seg["ACK_num"]:
                                seg = json.dumps(s)
                                self.send(r, "", seg, 0)
                                self.start_timer()

        print("exit program")

    def send(self, socket, data, segment, SYNFIN):
        increment = 1 if data == "" else 0
        if self.data_buffered + len(data) > self.mws:
            self.temp_data = data
        else:
            if segment == None:
                syn = 1 if (SYNFIN == 1) else 0
                fin = 1 if (SYNFIN == 2) else 0
                seg_string = {
                    "source_ip": self.ip,
                    "source_port": self.port_num,
                    "data": data,
                    "SYN": syn,
                    "FIN": fin,
                    "ACK_num": self.ack_num,
                    "seq_num": self.init_seq_num
                }
                segment = json.dumps(seg_string)
                self.init_seq_num += len(data) + increment
                self.buffer.append(seg_string)
            # send packet to pld module to check if packet is dropped
            result = True
            print(segment)
            if SYNFIN == 0:
                result = self.run_pld()
            if result:
                socket.sendto(segment.encode('utf-8'), (self.server_ip, self.server_port))
            else:
                print("dropped!!!")
            if self.timer is None:
                self.start_timer()

    def timeout(self, socket):
        seg = json.dumps(self.buffer[0])
        print("timeout occurs!")
        self.send(socket, "", seg, 0)
        self.start_timer()

    def start_timer(self):
        self.timer = time.time()


    def run_pld(self):
        #random.seed(self.seed)
        prob = random.random()
        return True if prob < self.pdrop else False

hikki = STPSender(gethostbyname(gethostname()), 12000, 3, 3, 1, 0.7, 50)
hikki.run_sender("test.txt")
