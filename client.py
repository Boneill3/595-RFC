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
        self.heartbeat_event = None
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
                pending_ack = PendingAck(message, self.server, 5)
                self.pending_ack_queue[event_id] = pending_ack
                # event_id + 1 reserved for heartbeat
                event_id += 2

            elif response.upper() == "U":
                message = EmergencyMessage("unsubscribe", "", event_id)
                if self.heartbeat_event is not None:
                    self.heartbeat_event = None
                    if self.heartbeat_event in self.pending_ack_queue:
                        self.pending_ack_queue.pop(self.heartbeat_event)
                    pending_ack = PendingAck(message, self.server, 5)
                    self.pending_ack_queue[event_id] = pending_ack
                event_id += 1

            elif response.upper() == "R":
                request_type = input("Request (T)ime, (W)eather or (A)QI: ")
                if request_type == "T":
                    request_type = "time"
                elif request_type == "W":
                    request_type = "weather"
                elif request_type == "A":
                    request_type = "AQI"
                else:
                    continue

                message = EmergencyMessage("request", request_type, event_id)
                pending_ack = PendingAck(message, self.server, 20)
                self.pending_ack_queue[event_id] = pending_ack
                event_id += 1

            elif response.upper() == "Q":
                message = EmergencyMessage("unsubscribe", "", event_id)
                with self.outgoing_queue_lock:
                    self.outgoing_queue.append((self.server, message))
                time.sleep(3)
                print("Quitting...")
                self.quit = True

            elif response.upper() == "A":
                response = ""
                while response != "-1":
                    for event_id, event in self.received_events.items():
                        print(f"{event_id}: {event.message.message_type} - "
                              f"{event.message.message}")
                    response = input("Enter id to acknowledge or -1 to exit: ")
                    try:
                        if int(response) in self.received_events:
                            self.received_events.pop(int(response))
                            ack = Acknowledgement("User", int(response))
                            message = EmergencyMessage("EventAck", ack.encode())
                            pending_ack = PendingAck(message, self.server, 5)
                            self.pending_ack_queue[int(response)] = pending_ack
                    except ValueError:
                        continue

    def sender(self):
        while not self.quit:
            for event_id, pending_ack in self.pending_ack_queue.items():
                if pending_ack.is_timed_out():
                    with self.outgoing_queue_lock:
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

            if self.heartbeat_event is not None \
                    and self.heartbeat_event in self.pending_ack_queue:
                heartbeat_event = self.pending_ack_queue[self.heartbeat_event]
                if heartbeat_event.attempts > 5:
                    print(f"server {self.server} disconnected!")
                    self.pending_ack_queue.pop(self.heartbeat_event)
                    self.heartbeat_event = None
                    for event_id, pending_ack in self.pending_ack_queue.items():
                        if pending_ack.destination == self.server:
                            self.pending_ack_queue.pop(event_id)

            try:
                message, server_address = self.clientSocket.recvfrom(2048)
                print(f"Message Received from {server_address}")
                message = decode_message(message)
                if message.message_type == "Ack":
                    ack = decode_acknowledgement(message.message)
                    print(f"ACK Received!\nType: {ack.acknowledgement_type}\n"
                          f"Ref: {ack.reference}")
                    if ack.acknowledgement_type == "subscribe":
                        self.pending_ack_queue.pop(ack.reference)
                        event_id = ack.reference + 1
                        self.heartbeat_event = event_id
                        message = EmergencyMessage("heartbeat", "", event_id)
                        pending_ack = PendingAck(message, self.server, 5)
                        self.pending_ack_queue[event_id] = pending_ack

                    elif ack.acknowledgement_type == "unsubscribe":
                        if ack.reference in self.pending_ack_queue:
                            self.pending_ack_queue.pop(ack.reference)

                    elif ack.acknowledgement_type == "heartbeat":
                        self.pending_ack_queue[ack.reference].timeout = 5

                    else:
                        if ack.reference in self.pending_ack_queue:
                            self.pending_ack_queue.pop(ack.reference)

                elif message.message_type == "time" \
                        or message.message_type == "weather" \
                        or message.message_type == "AQI" \
                        or message.message_type == "message":
                    print(f"{message.message_type} received. {message.message}")
                    if message.event in self.pending_ack_queue:
                        self.pending_ack_queue.pop(message.event)

                elif message.message_type.startswith("level"):
                    if message.message_type == "level1":
                        display_timeout = 1800
                    elif message.message_type == "level2":
                        display_timeout = 60
                    else:
                        display_timeout = 5
                    pending_ack = PendingAck(message, self.server,
                                             display_timeout)
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


if __name__ == '__main__':
    print(f"Starting client...")
    client = WildfireClient()
    jobs = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        jobs.append(executor.submit(client.receiver))
        jobs.append(executor.submit(client.interface))
        jobs.append(executor.submit(client.sender))
        for job in jobs:
            data = job.result()
    print("Exited")
