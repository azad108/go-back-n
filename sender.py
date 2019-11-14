import string, sys, packet, threading, time, os, datetime
from socket import *

packets = []
sendSequence = [] 
ackSequence = []
DEBUG = True
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
		self.firstPacket = False

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
		print (threading.currentThread().getName()+": "+ str(threading.active_count()))
		## mod adjustment of nextseqnum to accommodate eternal Base of 0 and curState N = 10
		if curState.nextSeqNum >= curState.N: curState.nextSeqNum = curState.nextSeqNum % curState.N
		## once timer expires all UNACKed packets in window are resent
		timer = threading.Timer(0.1, resendUnacked)
		while curState.nextSeqNum < len(packets):

			if curState.nextSeqNum < curState.N:
				if DEBUG: print("sending packet at index.. "+str(curState.nextSeqNum)+ " with SeqNum: "+str(packets[curState.nextSeqNum].seq_num))
				## sending the packet over dataSocket 
				dataSocket.sendto(packets[curState.nextSeqNum].get_udp_data(), (curState.emHostAddr, curState.dataPort)) 
				sendSequence.append(packets[curState.nextSeqNum].seq_num)
				if DEBUG:
					print ("sent : "+str(curState.nextSeqNum))
					print("LENGTH = " + str(len(packets)))
				if curState.base == curState.nextSeqNum: 
					timer.start()
				elif curState.N == curState.nextSeqNum:
					timer.cancel()
				curState.nextSeqNum += 1
				# if curState.nextSeqNum >= len(packets): timer.cancel()
			else:
				lock.wait()

def resendUnacked():
	with lock: 
		if len(packets) < 1: os._exit(0)
		if DEBUG:
			print (threading.currentThread().getName()+": "+ str(threading.active_count()))
			print ("RESENDERRRR : "+str(curState.nextSeqNum) + " " + str(curState.base))
		## once timer expires this thread yields to sendPackets
		timer = threading.Timer(0.1, sendPackets)
		timer.start()
		## waiting for the first packet to be acked when p-value is too high
		while not curState.firstPacket:
			dataSocket.sendto(packets[0].get_udp_data(), (curState.emHostAddr, curState.dataPort))
			sendSequence.append(packets[0].seq_num)
			lock.notify()

		for i in range(curState.base, curState.nextSeqNum):
			if DEBUG:
				print ("resent : "+str(i))
				print("LENGTH = " + str(len(packets)))
			if i >= len(packets): break
			dataSocket.sendto(packets[i].get_udp_data(), (curState.emHostAddr, curState.dataPort))
			lock.notify()
		timer.cancel()
		lock.notify()
		

def recvAcks():
	ackSocket = socket(AF_INET, SOCK_DGRAM) # the UDP socket to receive ack packets over
	ackSocket.bind(('', curState.ackPort))
	while len(packets) > 0: 
		if DEBUG:  print (threading.currentThread().getName()+": "+str(threading.active_count()))
		with lock:
			if DEBUG: print ("SEQNUM = "+str(curState.nextSeqNum)) 
			if len(packets) < 0: break
			## once timer expires all UNACKed packets in window are resent
			timer = threading.Timer(0.1, resendUnacked) 
			timer.start()
			lock.notify()
			if DEBUG: print("Receiving ACK from receiver:")
			ackPacket, addr = ackSocket.recvfrom(2048) 
			
			ackPacket = packet.packet.parse_udp_data(ackPacket)
			if DEBUG: print("recieved ACK For: " + str(ackPacket.seq_num))
			ackSequence.append(ackPacket.seq_num)
			if ackPacket.seq_num == 0: curState.firstPacket = True ## the first packet was ACKed successfully
																## safe to continue with the rest
			topNum = packets[0].seq_num+32
			ackNum = ackPacket.seq_num+32 
			if DEBUG: print ("Array top : "+str(packets[0].seq_num) + " - " + " ack seq: " +str(ackPacket.seq_num)) 
			## if the incoming ACK is for a packet that's already been ACKed before, ask for another ack
			if (topNum > ackNum):
				## once timer expires all UNACKed packets in window are resent
				timer = threading.Timer(0.1, resendUnacked) 
				timer.start()
				if DEBUG: print("_____________________operation failed______________________")
				lock.notify()
				continue


			# timer = threading.Timer(0.1, resendUnacked) 
			# timer.start()

			ackedPacket = packets.pop(0)
			## readjusting the sequence number here to accommodate for the popped of first element
			curState.nextSeqNum -= 1
			## readjusting the sequence number here to accommodate to the window size
			if curState.nextSeqNum >= curState.N: 
				curState.nextSeqNum = curState.nextSeqNum % curState.N
				# lock.notify()
			if DEBUG: print("NEW SHORTER LENGTH = " + str(len(packets))) 

			if ackPacket.type == 2: ## on receipt of EOT packet's ack we exit thread
				dataSocket.close()
				createFiles()
				break 	
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
		packets.append(packet.packet.create_eot(seqnum)) 
		curState.beginTransmission = datetime.datetime.now() 
		transmit = transmitGoBackN() # this call is kinda like rdt_send()
main()