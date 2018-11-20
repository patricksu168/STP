# UDP SERVER PROGRAM
#
# This is the server-side program to
# receive requests from the sender.

from socket import *
import sys
import random
import time
import json

class STPReceiver:
    def __init__(self, server_port, file_name):
        self.ip = gethostbyname(gethostname())
        self.port_num = server_port
        self.file_name = file_name
        self.init_seq_num = random.randint(1, 101)
        self.base_ACK = 0
        self.buffer = []
        self.file = None

    def runReceiver(self):
        serverSocket = socket(AF_INET, SOCK_DGRAM)
        serverSocket.bind(('', self.port_num))
        print("The server is ready to receive")

        while (1):
            #receive segment
            seg_string, address = serverSocket.recvfrom(2048)
            segment = json.loads(seg_string.decode('utf-8'))
            print(segment)
            print(self.base_ACK)
            if (segment["SYN"] == 1):
                #send SYNACK segment back to sender
                self.base_ACK = segment["seq_num"] + 1
                self.send(serverSocket, segment)
                self.init_seq_num += 1

            #end of 3 way handshake where client acknowledge SYNACK segment
            elif (segment["FIN"] == 0 and  segment["data"] == ""):
                self.base_ACK += 1

            elif (segment["data"] != ""):
                if not self.file:

                    #create the text file to be written
                    self.file = open(self.file_name, "w+")

                if (segment["seq_num"] == self.base_ACK):
                    #if sequence number of the segment is what the server is expecting, simply
                    #send the segment to upper level by extracting the data
                    self.extract(segment)
                    self.base_ACK += len(segment["data"])
                    #if there are segments buffered, that means the gap is completely filled and extract
                    #all segments buffered
                    if (self.buffer != []):
                        if (self.buffer[0].seq_num == self.base_ACK):
                            for seg in self.buffer:
                                self.extract(seg)
                                self.base_ACK += len(seg.data)

                    self.send(serverSocket, segment)
                #there is gap detected between server's expected next sequence number and that of received segment
                #therefore buffer the segment until the gap is filled
                else:
                    self.buffer.append(segment)
                    self.send(serverSocket, segment)
            elif (segment["FIN"] == 1):
                self.file.close()
                self.base_ACK += 1
                self.send(serverSocket, segment)
                self.send(serverSocket, segment)
                segment, address = serverSocket.recvfrom(2048)
                break

        #time.sleep(10)
        print("The server is closing down")
        serverSocket.close()

    #send ack packet to sender through serverSocket
    def send(self, serverSocket, segment):
        increment = 0

        #if segment has no data, it's either a SYN segment or a FIN segment,
        #therefore need to increment acknowledgement number as well as sequence number of the next packet by 1
        if segment["data"] != "":
            increment = 1

        seg_string = {
            "source_ip": self.ip,
            "source_port": self.port_num,
            "data": "",
            "SYN": segment["SYN"],
            "FIN": segment["FIN"],
            "ACK_num": self.base_ACK + increment,
            "seq_num": self.init_seq_num
        }
        ack_seg = json.dumps(seg_string)
        serverSocket.sendto(ack_seg.encode('utf-8'), (segment["source_ip"], segment["source_port"]))


    #extract data from packet and write it to the textfile
    def extract(self, segment):
        self.file.write(segment["data"])

hikki = STPReceiver(12000, "test2.txt")
hikki.runReceiver()
