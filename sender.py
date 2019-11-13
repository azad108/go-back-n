import string, sys, packet, threading, time, os, datetime
from socket import *

packets = []
sendSequence = [] 
ackSequence = []

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
	f = open("time.log", "w")
	f.write(str(executionTime) + " seconds" + '\n') ## create the file / empty it if there's previous content 
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
		if curState.nextSeqNum >= curState.N: curState.nextSeqNum = curState.nextSeqNum % curState.N
		print("seq_num = " + str(curState.nextSeqNum))
		while curState.nextSeqNum < len(packets):
			if curState.nextSeqNum < curState.N: 

				print("SEND LENGTH = " + str(len(packets)))
				dataSocket.sendto(packets[curState.nextSeqNum].get_udp_data(), (curState.emHostAddr, curState.dataPort)) ## sending the packet over dataSocket 
				print ("sent : "+str(curState.nextSeqNum))
				sendSequence.append(packets[curState.nextSeqNum].seq_num) ## append to the send array since it was a success
				 
				timer = threading.Timer(0.1, resendUnacked)
				if curState.base == curState.nextSeqNum: 
					# if not timer.is_alive(): 
					print("TIMERRSSSTART")
					timer.start()
				elif curState.N == curState.nextSeqNum:
					print("TIMERCANCELLLLLL")
					timer.cancel()

				curState.nextSeqNum += 1
				# lock.notify() ## notify ack receiver about the transmission
				# if curState.nextSeqNum >= len(packets): timer.cancel()
			else:
				lock.wait()	 


def resendUnacked():
	with lock: 
		print (threading.currentThread().getName()+": "+ str(threading.active_count()))
		
		# print ("RESENDERRRR : "+str(curState.nextSeqNum) + " " + str(curState.base))
		timer = threading.Timer(0.1, sendPackets)
		if not timer.is_alive(): timer.start()
		# timer.start()
		lock.notify()
		## waiting for the first packet to be acked when p-value is too high
		while not curState.firstPacket:
			dataSocket.sendto(packets[0].get_udp_data(), (curState.emHostAddr, curState.dataPort))

		## resending all other previously sent but not yet ACKed pakcets
		for i in range(curState.base, curState.nextSeqNum):
			print("RESEND LENGTH = " + str(len(packets)))
			if i >= len(packets): break
			if curState.nextSeqNum >= curState.N: curState.nextSeqNum = curState.nextSeqNum % curState.N
			dataSocket.sendto(packets[i].get_udp_data(), (curState.emHostAddr, curState.dataPort))
			print ("resent : "+str(i))
			sendSequence.append(packets[i].seq_num) ## append to the send array since it was a success
		timer.cancel()
		lock.notify()
		os._exit(0)
		

def recvAcks():
	ackSocket = socket(AF_INET, SOCK_DGRAM) # the UDP socket to receive ack packets over
	ackSocket.bind(('', curState.ackPort))
	while len(packets) > 0:
		print (threading.currentThread().getName()+": "+str(threading.active_count()))
		with lock: 
			if len(packets) < 0: break
			timer = threading.Timer(0.1, resendUnacked) 
			timer.start()
			lock.notify()
			ackPacket, addr = ackSocket.recvfrom(2048)
			ackPacket = packet.packet.parse_udp_data(ackPacket) 

			print("recieved ACK For: " + str(ackPacket.seq_num))

			if ackPacket.seq_num == 0: curState.firstPacket = True ## the first packet was ACKed successfully
																## safe to continue with the rest
			ackSequence.append(ackPacket.seq_num) ## all received acks are logged 
			## a wrap around technique for comparing the 2 values
			## aka, the base packet(topNum) and the received ACK 
			topNum = packets[0].seq_num+32
			ackNum = ackPacket.seq_num+32 

			print ("Array top : "+str(packets[0].seq_num) + " - " + " ack seq: " +str(ackPacket.seq_num)) 
			if (topNum > ackNum):
				timer = threading.Timer(0.1, resendUnacked) 
				timer.start()
				lock.notify()
				print("operation failed______________________________________________")
				# lock.wait()
				continue

			timer = threading.Timer(0.1, resendUnacked) 
			timer.start()
			lock.notify()
			ackedPacket = packets.pop(0)
			curState.nextSeqNum -= 1
			if curState.nextSeqNum >= curState.N: 
				curState.nextSeqNum = curState.nextSeqNum % curState.N
				# lock.wait() 
			lock.notify() ## need to notify sender / to wake it up since nextSeqNum is updated

			print("++++++++++++++++LENGTH = " + str(len(packets))) 
			if ackPacket.type == 2: ## on receipt of EOT packet's ack we exit thread
				print("END OF TRANSS")
				dataSocket.close()
				createFiles()
				break 	

	ackSocket.close()


def transmitGoBackN():
	## calling the initial 2 threads for sending data packets and receiving their corr. ACKs
	sendDataThread = threading.Thread(name='PACKET SENDER', target=sendPackets, args = ())
	sendDataThread.start()
	recvAcksThread = threading.Thread(name='ACK RECEIVER', target=recvAcks, args = ())
	recvAcksThread.start()

	return 0

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