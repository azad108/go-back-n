import string, sys, packet, threading, time, os, datetime
from socket import *

packets = []
sendSequence = []
ackSequence = []
DEBUG = False
## will use this class to determine the packet transmission status
class cur_state:
        def __init__(self):
                self.dataPort = 0
                self.ackPort = 0
                self.emHostAddr = 0
                self.nextSeqNum = 0
                self.base = 0
                self.N = 10
                self.transmissionTime = 0
                self.firstPacket = False ## set to true after successful ACK of first packet
                self.lastAcked = None ## stores the last acked packet
                self.EOT = False  ## set to True when sender recieves the EOT
                self.EOTSent = False  ## set to True when sender sends the EOT
                self.lastPacketSeq = -1

curState = cur_state()
lock = threading.Condition()
dataSocket = socket(AF_INET, SOCK_DGRAM) # the UDP socket for sending data packets over

## function to create all the 3 required files
def createFiles():
        finishTransmission = datetime.datetime.now()
        executionTime = (finishTransmission - curState.beginTransmission).total_seconds()
        print("File Transmission with Go-Back-N Completed in: " + str(executionTime) + " seconds")
        f = open("time.log", "w")
        f.write(str(executionTime) + " seconds") ## create the file / empty it if there's previous content
        f.write('\n')
        f.close()

        f = open("seqnum.log", "w")
        f.write("") ## empty seqnum.log of previous runs
        f.close()
        f = open("seqnum.log", "a")
        for seq in sendSequence:
                f.write(str(seq))
                f.write('\n')
        f.close()

        f = open("ack.log", "w")
        f.write("") ## empty ack.log of previous runs
        f.close()
        f = open("ack.log", "a")
        for ack in ackSequence:
                f.write(str(ack))
                f.write('\n')
        f.close()

def sendPackets():
        with lock:
                if DEBUG: print (threading.currentThread().getName()+": "+ str(threading.active_count()) + " ++++++++++++++++++++++++")
                ## mod adjustment of nextseqnum to accommodate eternal Base of 0 and curState N = 10
                if curState.nextSeqNum >= curState.N: curState.nextSeqNum = curState.nextSeqNum % curState.N
                ## once timer expires all UNACKed packets in window are resent

                while curState.nextSeqNum < len(packets):
                        if curState.nextSeqNum < curState.N:
                                if DEBUG: print("sending packet at index.. "+str(curState.nextSeqNum)+ " with SeqNum: "+str(packets[curState.nextSeqNum].seq_num))
                                ## sending the packet over dataSocket
                                if packets[curState.nextSeqNum].type == 2: curState.EOTSent = True## EOT SEND 
                                dataSocket.sendto(packets[curState.nextSeqNum].get_udp_data(), (curState.emHostAddr, curState.dataPort))
                                sendSequence.append(packets[curState.nextSeqNum].seq_num)
                                if DEBUG: print ("sent : "+str(curState.nextSeqNum))
                                if DEBUG: print("LENGTH = " + str(len(packets)))
                                timer = threading.Timer(0.1, resendUnacked)
                                if curState.base == curState.nextSeqNum:
                                        timer.start()
                                elif curState.N == curState.nextSeqNum:
                                        timer.cancel()
                                curState.nextSeqNum += 1
                        else:
                                lock.wait() ## Wait for some ACKs to be received since window is full


def resendFirst():
        with lock:
                if DEBUG: print (threading.currentThread().getName()+": "+ str(threading.active_count()) + " #####################")
                if len(packets) <= 0 or curState.EOT or curState.firstPacket:
                        os._exit(0) ## quit thread if there are no more packets left
                if DEBUG: print ("RESENDERRRR : "+str(curState.nextSeqNum) + " " + str(curState.base))
                ## once timer expires this thread yields to sendPackets
                ## waiting for the first packet to be acked when p-value is too high

                if DEBUG: print("Resending For First Packet a bunch of times ")
                for i in range (10):
                        dataSocket.sendto(packets[0].get_udp_data(), (curState.emHostAddr, curState.dataPort))
                        sendSequence.append(packets[0].seq_num)
                lock.notify()

def resendUnacked():
        with lock:
                if len(packets) < 1 or curState.EOT: os._exit(0) ## quit thread if there are no more packets left
                if DEBUG: print (threading.currentThread().getName()+": "+ str(threading.active_count()) + " #####################")
                if DEBUG: print ("RESENDERRRR : "+str(curState.nextSeqNum) + " " + str(curState.base))
                ## once timer expires this thread yields to sendPackets
                ## waiting for the first packet to be acked when p-value is too high

                for i in range(curState.base, curState.nextSeqNum):
                        if DEBUG: print ("resent : "+str(packets[i].seq_num))
                        if DEBUG: print("LENGTH = " + str(len(packets)))
                        if i >= len(packets): break
                        if packets[i].type == 2: curState.EOTSent = True## EOT SEND
                        dataSocket.sendto(packets[i].get_udp_data(), (curState.emHostAddr, curState.dataPort))

                lock.notify() ## go back to the sender thread once retransmitted !!


def recvAcks():
        ackSocket = socket(AF_INET, SOCK_DGRAM) # the UDP socket to receive ack packets over
        ackSocket.bind(('', curState.ackPort))
        with lock:
                if DEBUG: print (threading.currentThread().getName()+": "+str(threading.active_count()) + " -=-=-=-=-=-=-=-=-=-=-=-=-=-=-")
                while True:
                        lock.notify()
                        if DEBUG: print ("SEQNUM = "+str(curState.nextSeqNum) + "-- N = " + str(curState.N))
                        if len(packets) <= 0  or curState.EOT:
                                curState.EOT = True
                                dataSocket.close()
                                break

                        if curState.lastAcked:
                                ## wrapping around because it's only 0-31
                                baseNow = packets[curState.base].seq_num
                                lastAckNum = curState.lastAcked.seq_num
                                if baseNow < 10 and lastAckNum > 22: baseNow += 32
                                elif lastAckNum < 10 and baseNow > 22: lastAckNum += 32
                                if DEBUG: print ("BASE SEQ: " +str(baseNow)+ " - " + "LAST ACKED SEQ: " + str(lastAckNum))
                                ## when the previous ack received was for an already-ACKed packet, sleep
                                if lastAckNum < baseNow:
                                        lock.wait()

                        if len(packets) == 1: ## ie only the EOT is left
                                lock.wait()       ## must wake up sender to send EOT
                        if curState.nextSeqNum >= curState.N:
                                curState.nextSeqNum = curState.nextSeqNum % curState.N
                                lock.notify()
                        if not curState.firstPacket and curState.lastAcked != None:
                                resendFirstT = threading.Thread(name='FIRST SENDER', target=resendFirst, args = ())
                                resendFirstT.start()
                        ## the case when the entire window was already acked. need to transfer to sender here
                        if curState.nextSeqNum == 0 and curState.firstPacket:
                                lock.notify_all()
                        if DEBUG and curState.lastAcked: print("LAST ACKED WAS: " + str(curState.lastAcked.seq_num))
                        if DEBUG: print("Receiving ACK from receiver:")
                        ackPacket, addr = ackSocket.recvfrom(6144)
                        ackPacket = packet.packet.parse_udp_data(ackPacket)
                        if DEBUG: print("recieved ACK For: " + str(ackPacket.seq_num))
                        if ackPacket.seq_num == 0 and not curState.firstPacket:
                                curState.firstPacket = True ## the first packet was ACKed successfully
                                                                    ## safe to continue with the rest
                        elif ackPacket.seq_num == 31 and not curState.firstPacket and curState.lastAcked == None:
                        ## checking if it was the DEFAULT ACK THAT JUST CAME IN
                                if DEBUG: print("DEFAULT ACK RECEIVED")
                                resendFirstT = threading.Thread(name='FIRST SENDER', target=resendFirst, args = ())
                                resendFirstT.start()
                                lock.wait() ###
                                continue ## initial default packet from sender


                        ## once timer expires all UNACKed packets in window are resent
                        timer = threading.Timer(0.1, resendUnacked)
                        timer.start()
                        ackSequence.append(ackPacket.seq_num)
                        
                        ## wrapping around because it's only 0-31
                        base = packets[0].seq_num
                        ackNum = ackPacket.seq_num
                        if base < 10 and ackNum > 22: base += 32
                        elif ackNum < 10 and base > 22: ackNum += 32
                        if DEBUG: print ("Array top : "+str(packets[0].seq_num) + " - " + " ack seq: " +str(ackPacket.seq_num))
                        if DEBUG: print ("BASE : "+str(packets[0].seq_num) + " - " + " ACKNUM: " +str(ackPacket.seq_num))
                        if DEBUG: print ("SEQNUM = "+str(curState.nextSeqNum))
                        ## if the incoming ACK is for a packet that's already been ACKed before, ask for another ack
                        if (base > ackNum):
                                if DEBUG: print("____acking unsuccessful____")
                                if curState.nextSeqNum >= curState.N:
                                        curState.nextSeqNum = curState.nextSeqNum % curState.N
                                ## once timer expires all UNACKed packets in window are resent
                                timer = threading.Timer(0, resendUnacked)
                                timer.start()
                                lock.notify() ## notify sender to start reserding # important
                                continue
                        timer = threading.Timer(0.5, resendUnacked)
                        timer.start()
                        #### OTHERWISE: we accept the ACK and remove all previously acked elements
                        curState.lastAcked = ackPacket                                                                                                                     
                        if ackPacket.type == 2 or (len(packets) == 1 and curState.EOTSent and curState.lastPacketSeq == ackPacket.seq_num): ## on receipt of EOT packet's ack we exit thread     
                                packets.pop(0)                                                                                                                             
                                curState.EOT = True                                                                                                                        
                                dataSocket.close()                                                                                                                         
                                createFiles()                                                                                                                              
                                os._exit(0)                                                                                                                                
                        for i in range(ackNum - base + 1):
                                if len(packets) <= 0: break
                                ackedPacket = packets.pop(0)
                                ## readjusting the sequence number here to accommodate for the popped of first element
                                curState.nextSeqNum -= 1
                                if DEBUG: print("NEW SHORTER LENGTH = " + str(len(packets)))
                                ## need to sleep when all the packets have been ACKed for
                                if curState.nextSeqNum == curState.base and curState.firstPacket:
                                        lock.wait()


                        ## readjusting the sequence number here to accommodate to the window size
                        if curState.nextSeqNum >= curState.N or curState.nextSeqNum < 0:
                                curState.nextSeqNum = curState.nextSeqNum % curState.N

                        lock.notify() ## Wake up sleeping threads to notify em about the change in
                                                ## nextseqnum and arraysize
        ackSocket.close()


def transmitGoBackN():
        ## calling the initial 2 threads for sending data packets and receiving their corr. ACKs
        sendDataThread = threading.Thread(name='PACKET SENDER', target=sendPackets, args = ())
        recvAcksThread = threading.Thread(name='ACK RECEIVER', target=recvAcks, args = ())
        sendDataThread.start()
        recvAcksThread.start()

        return 1


def main():
        seqnum=0
        if len(sys.argv) != 5:
                print("Insufficient arguments. Suggested format: python3 sender.py <eEmulator host_addr> <UPD data port> <UDP ACK port> <filename>")
        else:
                curState.emHostAddr = sys.argv[1]
                curState.dataPort = int(sys.argv[2])
                curState.ackPort = int(sys.argv[3])
                filename = sys.argv[4]

                content = ""
                with open(filename, "r") as lines:
                        for lineString in lines:
                                content += lineString

                data = ""
                for c in content:
                        data += c
                        if len(data) == 500:
                                packets.append(packet.packet.create_packet(seqnum, data))
                                data = ""
                                seqnum += 1
                if len(data) > 0:
                        packets.append(packet.packet.create_packet(seqnum, data))
                        seqnum += 1
                curState.lastPacketSeq = seqnum-1 ## seqnum of last data packet
                packets.append(packet.packet.create_eot(seqnum))
                curState.beginTransmission = datetime.datetime.now()
                transmit = transmitGoBackN() # this call is kinda like rdt_send()
main()
