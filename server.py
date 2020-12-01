import threading
import time
from random import randint
from socket import *
from data_objects import *
from event import *
import datetime
import concurrent.futures


class WildfireServer:
    def __init__(self, port, timezone=pytz.timezone('America/Los_Angeles')):
        self.serverPort = port
        self.serverSocket = socket(AF_INET, SOCK_DGRAM)
        self.subscribers = dict()
        self.events = dict()
        self.serverSocket.bind(('', self.serverPort))
        self.serverSocket.settimeout(5)
        print("The server is ready to receive")
        self.quit = False
        self.outgoing_queue = []
        self.outgoing_queue_lock = threading.Lock()
        self.last_heartbeat = dict()
        self.timezone = timezone

    def receiver(self):
        while not self.quit:
            try:
                now = datetime.datetime.now(self.timezone)
                twenty_five_secs_ago = now - datetime.timedelta(seconds=25)
                for client_address, last_heartbeat in self.last_heartbeat.items():
                    if last_heartbeat < twenty_five_secs_ago \
                            and client_address in self.subscribers:
                        name = self.subscribers[client_address].name
                        print(f"{name} force unsubscribed")
                        self.subscribers.pop(client_address)

                received_message, client_address = self.serverSocket.recvfrom(
                    2048)
                received_message = decode_message(received_message)
                print(f"Message Received from {client_address}")

                if received_message.message_type == "subscribe":
                    subscriber = decode_subscriber(received_message.message)
                    self.subscribers[client_address] = subscriber
                    print(f"{subscriber.name} Subscribed")
                    ack = Acknowledgement("subscribe", received_message.event)
                    response = EmergencyMessage("Ack", ack.encode())
                    with self.outgoing_queue_lock:
                        self.outgoing_queue.append((client_address, response))

                elif received_message.message_type == "unsubscribe":
                    if client_address in self.subscribers:
                        name = self.subscribers[client_address].name
                        print(f"{name} unsubscribed")
                        self.subscribers.pop(client_address)
                    # Send Acknowledgement regardless of status
                    ack = Acknowledgement("unsubscribe",
                                          received_message.event)
                    response = EmergencyMessage("Ack", ack.encode())
                    with self.outgoing_queue_lock:
                        self.outgoing_queue.append((client_address, response))

                elif received_message.message_type == "heartbeat":
                    if client_address in self.subscribers:
                        now = datetime.datetime.now(self.timezone)
                        self.last_heartbeat[client_address] = now
                        ack = Acknowledgement("heartbeat",
                                              received_message.event)
                        response = EmergencyMessage("Ack", ack.encode())
                        with self.outgoing_queue_lock:
                            self.outgoing_queue.append((client_address,
                                                        response))
                    else:
                        print(f"heartbeat from non-subscriber "
                              f"{client_address} ignored")

                elif received_message.message_type == "request":
                    if client_address not in self.subscribers:
                        print(f"Request from non-subscriber {client_address} "
                              f"ignored")
                        continue
                    if received_message.message == "time":
                        now = str(datetime.datetime.now(self.timezone))
                        response = EmergencyMessage("time", now,
                                                    received_message.event)

                    elif received_message.message == "weather":
                        response = EmergencyMessage("weather", "70 degrees, "
                                                               "clear",
                                                    received_message.event)

                    elif received_message.message == "AQI":
                        aqi_message = "151: Some members of the general " \
                                      "public may experience health effects; " \
                                      "members of sensitive groups may " \
                                      "experience more serious health " \
                                      "effects."
                        response = EmergencyMessage("AQI", aqi_message,
                                                    received_message.event)

                    else:
                        continue

                    with self.outgoing_queue_lock:
                        self.outgoing_queue.append((client_address, response))

                elif received_message.message_type == "EventAck":
                    ack = decode_acknowledgement(received_message.message)
                    print(f"Ack Type: {ack.acknowledgement_type}\n"
                          f"Reference: {ack.reference}")

                    try:
                        emergency_event = self.events[ack.reference]
                        if ack.acknowledgement_type == "System":
                            emergency_event.log_system_ack(client_address)
                        if ack.acknowledgement_type == "User":
                            ack = Acknowledgement("Ack", ack.reference)
                            response = EmergencyMessage("Ack", ack.encode())
                            with self.outgoing_queue_lock:
                                self.outgoing_queue.append(
                                    (client_address, response))
                            emergency_event.log_user_ack(client_address)
                    except KeyError:
                        print("Invalid or Duplicate Event ID Referenced")

                elif received_message.message_type == "SOS":
                    if client_address not in self.subscribers:
                        print(f"SOS from non-subscriber {client_address} "
                              f"ignored")
                        continue
                    name = self.subscribers[client_address].name
                    print(f"SOS Received from {name}: "
                          f"{received_message.message}")
                    ack = Acknowledgement("Ack", received_message.event)
                    response = EmergencyMessage("Ack", ack.encode())
                    with self.outgoing_queue_lock:
                        self.outgoing_queue.append((client_address, response))

                else:
                    print("Invalid Message Received")
            except timeout:
                test = 123

    def sender(self):
        while not self.quit:
            now = datetime.datetime.now(self.timezone)
            five_seconds_ago = now - datetime.timedelta(seconds=5)
            five_minutes_ago = now - datetime.timedelta(minutes=5)
            one_hour_ago = now - datetime.timedelta(hours=1)
            for event_id, event in self.events.items():
                if event.level == 1:
                    event_timeout = one_hour_ago
                elif event.level == 2:
                    event_timeout = five_minutes_ago
                else:
                    event_timeout = five_seconds_ago
                if len(event.waiting_sys_ack) > 0 and \
                        (event.last_issued is None or
                         event.last_issued < event_timeout):
                    event.update_last_issued()
                    for client_address in event.waiting_sys_ack.keys():
                        with self.outgoing_queue_lock:
                            self.outgoing_queue.append(
                                (client_address, event.message))

            with self.outgoing_queue_lock:
                for client_address, message in self.outgoing_queue:
                    self.serverSocket.sendto(message.encode(), client_address)
                    self.outgoing_queue.pop()

            time.sleep(1)

    def interface(self):
        event_id = randint(0, 99999)
        while not self.quit:
            response = input(
                "Send (E)mergency message, (N)on-Emergency message, ("
                "S)kip, (Q)uit or (L)ist Subscribers: ")

            if response.upper() == "E":
                event_id += 1
                event = create_emergency(event_id, self.subscribers)
                if event is not None:
                    self.events[event_id] = event

            elif response.upper() == "N":
                request_type = input("Request (T)ime, (W)eather or (A)QI, "
                                     "(M)essage: ")
                if request_type == "T":
                    now = str(datetime.datetime.now(self.timezone))
                    message = EmergencyMessage("time", now)
                elif request_type == "W":
                    message = EmergencyMessage("weather", "70 degrees, clear")
                elif request_type == "A":
                    aqi_message = "151: Some members of the general " \
                                  "public may experience health effects; " \
                                  "members of sensitive groups may " \
                                  "experience more serious health " \
                                  "effects."
                    message = EmergencyMessage("AQI", aqi_message)
                elif request_type == "M":
                    message = input("Broadcast Message (Warning unreliable): ")
                    message = EmergencyMessage("message", message, event_id)
                else:
                    continue

                for client_address in self.subscribers:
                    with self.outgoing_queue_lock:
                        self.outgoing_queue.append((client_address, message))

            elif response.upper() == "L":
                if len(self.subscribers) == 0:
                    print("No Subscribers")
                else:
                    for client_address, subscriber in self.subscribers.items():
                        print(f"{client_address}: {subscriber.name}")

            elif response.upper() == "Q":
                print("Quitting...")
                self.quit = True


def create_emergency(event_id, subscribers):
    print(f"Creating event {event_id}")
    level = input("Enter Emergency level (1), (2) or (3): ")
    if level in ("1", "2", "3"):
        message = input("Enter Message: ")
        event = EmergencyEvent(event_id, level, message, subscribers)
        return event

    return None


if __name__ == "__main__":
    port = 12000
    print(f"Starting Server on port {port}..")
    server = WildfireServer(port)
    jobs = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        jobs.append(executor.submit(server.receiver))
        jobs.append(executor.submit(server.interface))
        jobs.append(executor.submit(server.sender))
        for job in jobs:
            data = job.result()
    print("Exited")
