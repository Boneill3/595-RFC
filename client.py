import concurrent.futures
import threading
import time
from random import randint
from socket import *
from data_objects import *
from pending_ack import PendingAck


class WildfireClient:
    def __init__(self, server_name='localhost', server_port=12000):
        self.server = (server_name, server_port)
        self.clientSocket = socket(AF_INET, SOCK_DGRAM)
        self.clientSocket.settimeout(5)
        self.pending_ack_queue = dict()
        self.received_events = dict()
        response = input('Use Default Name and Address? (Y/N): ')
        self.outgoing_queue = []
        self.outgoing_queue_lock = threading.Lock()
        self.quit = False
        if response.upper() == "Y":
            self.subscriber = Subscriber("Brian", "123 main st.", "Portland",
                                         "OR", 97127)
        else:
            name = input("Name: ")
            address = input("Street Address: ")
            city = input("City: ")
            state = input("State: ")
            zipcode = input("Zipcode: ")
            self.subscriber = Subscriber(name, address, city, state, zipcode)

    def interface(self):
        event_id = randint(0, 99999)
        while not self.quit:
            response = input("(S)ubscribe, (U)nsubscribe, (R)equest, (Q)uit, "
                             "(A)ck Messages")

            if response.upper() == "S":
                message = EmergencyMessage("subscribe",
                                           self.subscriber.encode(),
                                           event_id)
                with self.outgoing_queue_lock:
                    pending_ack = PendingAck(message, self.server, 5)
                    self.pending_ack_queue[event_id] = pending_ack
                event_id += 1

            elif response.upper() == "U":
                message = EmergencyMessage("unsubscribe",
                                           "",
                                           event_id)
                with self.outgoing_queue_lock:
                    pending_ack = PendingAck(message, self.server, 5)
                    self.pending_ack_queue[event_id] = pending_ack
                event_id += 1

            elif response.upper() == "R":
                request_type = input("Enter Type: ")
                message = EmergencyMessage("request", request_type)
                with self.outgoing_queue_lock:
                    self.outgoing_queue.append((self.server, message))

            elif response.upper() == "Q":
                print("Quitting...")
                self.quit = True

            elif response.upper() == "A":
                response = ""
                while response != -1:
                    for event_id, event in self.received_events.items():
                        print(f"{event_id}: {event.message.message_type} - "
                              f"{event.message.message}")
                    response = input("Enter id to acknowledge or -1 to exit: ")
                    event_ack = self.received_events.pop(response)
                    if event_ack is not None:
                        ack = Acknowledgement("User", response)
                        message = EmergencyMessage("EventAck", ack.encode())
                        pending_ack = PendingAck(message, self.server, 5)
                        self.pending_ack_queue[response] = pending_ack

    def sender(self):
        while not self.quit:
            for event_id, pending_ack in self.pending_ack_queue.items():
                if pending_ack.is_timed_out():
                    self.outgoing_queue.append((pending_ack.destination,
                                                pending_ack.message))
                    pending_ack.update_last_issued()
            with self.outgoing_queue_lock:
                for client_address, message in self.outgoing_queue:
                    print(f"Sending {message.message_type} to {client_address}")
                    self.clientSocket.sendto(message.encode(), client_address)
                    self.outgoing_queue.pop()

            time.sleep(1)

    def receiver(self):
        while not self.quit:
            for event_id, event in self.received_events.items():
                if event.is_timed_out():
                    print(f"{event.message.message_type} Message Received!\n"
                          f"{event.message.message}")
                    event.update_last_issued()

            try:
                message, server_address = self.clientSocket.recvfrom(2048)
                print(f"Message Received from {server_address}")
                message = decode_message(message)
                if message.message_type == "Ack":
                    ack = decode_acknowledgement(message.message)
                    print(f"ACK Received!\nType: {ack.acknowledgement_type}\n"
                          f"Ref: {ack.reference}")
                    self.pending_ack_queue.pop(ack.reference)

                elif message.message_type.startswith("level"):
                    pending_ack = PendingAck(message, self.server, 5)
                    if message.event not in self.received_events:
                        self.received_events[message.event] = pending_ack

                    ack = Acknowledgement("System", message.event)
                    message = EmergencyMessage("EventAck", ack.encode())
                    with self.outgoing_queue_lock:
                        self.outgoing_queue.append((self.server, message))

                else:
                    print(f"{message.message_type} message received! \n"
                          f"source: {server_address} \n"
                          f"{message.message}")

            except timeout:
                test = 123


"""
def request_data(request_type):
    requestMessage = EmergencyMessage("request", request_type)
    clientSocket.sendto(requestMessage.encode(), (serverName, serverPort))
    clientSocket.settimeout(1)
    ack, serverAddress = clientSocket.recvfrom(2048)
    ack = decode_message(ack)
    ack = decode_acknowledgement(ack.message)


def send_heartbeat(id):
    heartbeatMessage = EmergencyMessage("heartbeat", id)
    clientSocket.sendto(heartbeatMessage.encode(), (serverName, serverPort))


response = "Y"

try:
    ack, serverAddress = clientSocket.recvfrom(2048)
    ack = decode_message(ack)
    ack = decode_acknowledgement(ack.message)
    print(f"ACK Received!\nType: {ack.acknowledgement_type}\nRef: "
          f"{ack.reference}")

except timeout:
    print("ACK TIMEOUT OCCURRED")
    response = "N"

while response.upper() == "Y":
    try:
        message, serverAddress = clientSocket.recvfrom(2048)
        message = decode_message(message)
        print(
            f"Message Type: {message.message_type}\nMessage: {message.message}")
        user_ack = input("Send System Ack? (Y/N): ")
        if user_ack.upper() == "Y":
            ack = Acknowledgement("System", message.event)
            message = EmergencyMessage("EventAck", ack.encode())
            clientSocket.sendto(message.encode(), (serverName, serverPort))
        user_ack = input("Send User Ack? (Y/N): ")
        if user_ack.upper() == "Y":
            ack = Acknowledgement("User", message.event)
            message = EmergencyMessage("EventAck", ack.encode())
            clientSocket.sendto(message.encode(), (serverName, serverPort))


    except timeout:
        response = input("Continue (Y/N): ")

clientSocket.close()
"""

if __name__ == '__main__':
    print(f"Starting client...")
    client = WildfireClient()
    jobs = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        jobs.append(executor.submit(client.receiver))
        jobs.append(executor.submit(client.interface))
        jobs.append(executor.submit(client.sender))
    print("Exited")
