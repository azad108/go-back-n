## CS456 F19 A2
## Student: Azad Rahman (20638008)

import string, sys, packet
from socket import *
DEBUG = True

packets = []
dataSequence = [] 
ackSequence = []

class cur_state:
	def __init__(self):
		self.dataPort = 0
		self.ackPort = 0
		self.emHostAddr = 0
		self.expectedSeqNum = 0

curState = cur_state()

def recieveGoBackN():
	dataSocket = socket(AF_INET, SOCK_DGRAM) # the UDP socket for receiving data packets over
	ackSocket = socket(AF_INET, SOCK_DGRAM) # the UDP socket to receive ack packets over
	dataSocket.bind(('', curState.dataPort)) 
	lastAcked = packet.packet.create_ack(31) ## initial ACK for establishing connection 
											## useful for high p-value connections
	while True:
		if DEBUG:
			print('-----------------------------')
			print("LEN = "+str(len(packets))) 
		dataPacket, addr = dataSocket.recvfrom(6144)
		dataPacket = packet.packet.parse_udp_data(dataPacket)
		dataSequence.append(dataPacket.seq_num)
		if DEBUG: 
			print("received packet = "+str(dataPacket.seq_num)) 
			print ("expected packet: "+str(curState.expectedSeqNum))
		if dataPacket.type == 2 and dataPacket.seq_num == curState.expectedSeqNum: ## aka EOT received successfully
			## send an EOT packet back to the receiver
			lastAcked = dataPacket
			## will send back EOT packets to mark the End of transmission
			# for i in range(10): 
			ackSocket.sendto(packet.packet.create_eot(curState.expectedSeqNum).get_udp_data(), (curState.emHostAddr, curState.ackPort))
			ackSequence.append(curState.expectedSeqNum)
			f = open(curState.filename, "w")
			f.write("") ## create the file / empty it if there's previous content 
			f.close()
			f = open(curState.filename, "a") ## reopen the empty file to add the packet data
			for i in range(len(packets)):
				if packets[i].type == 1:
					f.write(packets[i].data) 
			f.close()
			break

		## the recieved data packet is as expected, CAN ACK NOW!!
		if dataPacket.seq_num == curState.expectedSeqNum: 
			## send back ack for the received packet
			lastAcked = dataPacket
			ackSocket.sendto(packet.packet.create_ack(curState.expectedSeqNum).get_udp_data(), (curState.emHostAddr, curState.ackPort))
			ackSequence.append(curState.expectedSeqNum)
			packets.append(dataPacket)
			curState.expectedSeqNum += 1
			curState.expectedSeqNum = curState.expectedSeqNum % 32
			if DEBUG: print ("updated expected: "+str(curState.expectedSeqNum))

		else:
			## send an ack back for the last acked data packet
			ackSocket.sendto(lastAcked.get_udp_data(), (curState.emHostAddr, curState.ackPort))
			ackSequence.append(lastAcked.seq_num)
#################################################3
		if DEBUG: 
			print ("Data Sequence:")
			datas = ""
			for data in dataSequence:
				datas += str(data) + " "
			print(datas)
			print ("ACK Sequence:")
			acks = ""
			for ack in ackSequence:
				acks += str(ack) + " " 
			print(acks)
			print("PACKET")
			pack = ""
			for p in packets:
				pack += str(p.seq_num) + " " 
			print(pack)
##################################################
	dataSocket.close()
	ackSocket.close()

def main(): 
	seqnum=0
	if len(sys.argv) != 5:
		print("Insufficient arguments. Suggested format: python3 receiver.py <eEmulator host_addr> <UDP ACK port> <UPD data port> <filename>")
	else:
		curState.emHostAddr = sys.argv[1]
		curState.ackPort = int(sys.argv[2])
		curState.dataPort = int(sys.argv[3])
		curState.filename = sys.argv[4] 
		recieveGoBackN()
main()