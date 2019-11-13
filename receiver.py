import string, sys, packet
from socket import *

packets = []
          
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
	lastAcked = -1
	while True:
		print('-----------------------------')
		print("LEN = "+str(len(packets)))
		dataPacket, addr = dataSocket.recvfrom(2048)
		dataPacket = packet.packet.parse_udp_data(dataPacket)

		if dataPacket.type == 2 and dataPacket.seq_num == curState.expectedSeqNum: ## aka EOT received successfully
			## send an EOT packet back to the receiver
			lastAcked = dataPacket.seq_num
			ackSocket.sendto(packet.packet.create_eot(curState.expectedSeqNum).get_udp_data(), (curState.emHostAddr, curState.ackPort))
			f = open(curState.filename, "w")
			f.write("") ## create the file / empty it if there's previous content 
			f.close()
			f = open(curState.filename, "a") ## reopen the empty file to add the packet data
			for i in range(len(packets)):
				if packets[i].type == 1:
					f.write(packets[i].data) 
			f.close()
			break

		print("data: "+str(dataPacket.seq_num))
		print ("expected: "+str(curState.expectedSeqNum))
		# print(dataPacket.data[0:40])
		if dataPacket.seq_num == curState.expectedSeqNum: ## the recieved data packet is as expected
			## send back ack for the received packet
			lastAcked = dataPacket.seq_num
			ackSocket.sendto(packet.packet.create_ack(curState.expectedSeqNum).get_udp_data(), (curState.emHostAddr, curState.ackPort))
			packets.append(dataPacket)
			curState.expectedSeqNum += 1
			curState.expectedSeqNum = curState.expectedSeqNum % 32
			print ("updated expected: "+str(curState.expectedSeqNum))

		else:
			if lastAcked != -1: 
				ackSocket.sendto(packet.packet.create_ack(lastAcked).get_udp_data(), (curState.emHostAddr, curState.ackPort))
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