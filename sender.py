import string, sys, packet, threading, time, os
from socket import *

packets = []

class cur_state:
	def __init__(self):
		self.dataPort = 0
		self.ackPort = 0
		self.emHostAddr = 0
		self.nextSeqNum = 0 
		self.base = 0
		self.N = 10
		

curState = cur_state()
lock = threading.Condition() 
dataSocket = socket(AF_INET, SOCK_DGRAM) # the UDP socket for sending data packets over'

def resendUnacked():
	with lock:
		# print ("SENDING N AGAIN!!!!!!!!!!!!!!!!!!!!!!!!!!")
		print (threading.currentThread().getName()+": "+ str(threading.active_count()))
		
		# print ("RESENDERRRR : "+str(curState.nextSeqNum) + " " + str(curState.base))
		# print("LENGTH = " + str(len(packets)))
		for i in range(curState.base, curState.nextSeqNum):
			print ("resent : "+str(i))
			if i >= len(packets): break
			dataSocket.sendto(packets[i].get_udp_data(), (curState.emHostAddr, curState.dataPort))
		lock.notify()



def sendPackets():
	with lock:
		# print ("NEW SENDDDDDDDDDDDDDDDDDDDDDDDDDDDD")
		print (threading.currentThread().getName()+": "+ str(threading.active_count()))
		if curState.nextSeqNum >= curState.N: curState.nextSeqNum = curState.nextSeqNum % curState.N
		while curState.nextSeqNum < len(packets):
			if curState.nextSeqNum < curState.N:
				print ("sent : "+str(curState.nextSeqNum))
				# print("LENGTH = " + str(len(packets)))
				dataSocket.sendto(packets[curState.nextSeqNum].get_udp_data(), (curState.emHostAddr, curState.dataPort)) ## sending the packet over dataSocket 
				if curState.base == curState.nextSeqNum: 
					timer = threading.Timer(0.1, resendUnacked)
					timer.start()
				curState.nextSeqNum += 1 
				# if curState.nextSeqNum >= len(packets): timer.cancel()
			else:
				lock.wait()		



def recvAcks():
	ackSocket = socket(AF_INET, SOCK_DGRAM) # the UDP socket to receive ack packets over
	ackSocket.bind(('', curState.ackPort))
	while len(packets) > 0: 
		print (threading.currentThread().getName()+": "+str(threading.active_count()))
		with lock:
			# print("RECEIVINGGGGGGGG!!!!!!!!!!!!!!")
			lock.notify()
			ackPacket, addr = ackSocket.recvfrom(2048)
			ackPacket = packet.packet.parse_udp_data(ackPacket)
			print("recieved ACK For: " + str(ackPacket.seq_num))
			topNum = packets[0].seq_num+32
			ackNum = ackPacket.seq_num+32 

			print ("Array top : "+str(packets[0].seq_num) + " - " + " ack seq: " +str(ackPacket.seq_num)) 
			if (topNum > ackNum):
				timer = threading.Timer(0.1, resendUnacked) 
				timer.start()
				print("operation failed______________________________________________")
				lock.wait()
				continue

			
			timer = threading.Timer(0.1, resendUnacked) 
			timer.start()
			ackedPacket = packets.pop(0)
			curState.nextSeqNum -= 1
			if curState.nextSeqNum >= curState.N: 
				curState.nextSeqNum = curState.nextSeqNum % curState.N
				lock.wait() 
			print("++++++++++++++++LENGTH = " + str(len(packets))) 
			print(str(ackPacket.type))
			if ackPacket.type == 2: ## on receipt of EOT packet's ack we exit thread
				print("END OF TRANSS")
				dataSocket.close()
				packets.pop(0)
				break 	

	ackSocket.close()


def transmitGoBackN():
	sendDataThread = threading.Thread(name='PACKET SENDER', target=sendPackets, args = ())
	recvAcksThread = threading.Thread(name='ACK RECEIVER', target=recvAcks, args = ())
	sendDataThread.start()
	recvAcksThread.start()


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
		transmitGoBackN() # this call is kinda like rdt_send()
main()