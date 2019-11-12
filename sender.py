import string, sys, packet, threading, time
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

def resendUnacked():
	with lock:
		print("RESENDING ACKS")
		# if curState.base >= curState.nextSeqNum: lock.wait() 
		for i in range(curState.base, curState.nextSeqNum):
			dataSocket.sendto(packets[i].get_udp_data(), (curState.emHostAddr, curState.dataPort))
lock = threading.Condition() 
dataSocket = socket(AF_INET, SOCK_DGRAM) # the UDP socket for sending data packets over'


def sendPackets(): 
	with lock:
		print("PACKET SENDDD")
		while curState.nextSeqNum < len(packets):		
			print ("send : "+str(curState.nextSeqNum) + " " + str(curState.base))
			if curState.nextSeqNum < curState.base + curState.N:
				dataSocket.sendto(packets[curState.nextSeqNum].get_udp_data(), (curState.emHostAddr, curState.dataPort)) ## sending the packet over dataSocket 
				if curState.base == curState.nextSeqNum:
					timer = threading.Timer(0.15, resendUnacked)
					timer.start()
				curState.nextSeqNum += 1
			else:
				lock.wait()


def recvAcks(): 

	ackSocket = socket(AF_INET, SOCK_DGRAM) # the UDP socket to receive ack packets over
	ackSocket.bind(('', curState.ackPort))
	while True:
		print("ACK RECEPTION:")
		with lock:
			if curState.nextSeqNum < curState.base + curState.N:
				lock.notify()
			ackPacket, addr = ackSocket.recvfrom(2048)
			ackPacket = packet.packet.parse_udp_data(ackPacket)
			
			tmp = curState.base + ackPacket.seq_num + 1
			if (tmp > curState.base + curState.N): tmp = tmp % 32
			curState.base = tmp  
			print ("ack : "+str(curState.nextSeqNum) + " " + str(curState.base) + " " + str(curState.N))
			print("ack seq_num: " + str(ackPacket.seq_num))
			
			timer = threading.Timer(0.15, resendUnacked)
			if curState.base == curState.nextSeqNum:
				print("azadddddddddddddddddddddd")
				timer.cancel()
				lock.notify()
			else:
				print("RAHMAAAAN")
				timer.start() 
				
			if curState.base == len(packets) or ackPacket.type == 2:
				dataSocket.close()
				lock.notify()
				break
			
	ackSocket.close()


def transmitGoBackN():
	sendDataThread = threading.Thread(target=sendPackets, args = ())
	recvAcksThread = threading.Thread(target=recvAcks, args = ())
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
		print(len(packets))
		transmitGoBackN() # this call is kinda like rdt_send()

main()