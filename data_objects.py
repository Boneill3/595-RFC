import json
import hashlib

VERSION = 1.0


class EmergencyMessage:
    def __init__(self, message_type, message, event=0, version=VERSION):
        self.__version = version
        self.__message_type = message_type
        self.__message = message
        self.__event = event

    @property
    def version(self):
        return self.__version

    @property
    def message_type(self):
        return self.__message_type

    @property
    def message(self):
        return self.__message

    @property
    def event(self):
        return self.__event

    def encode(self):
        encoded_message = json.dumps({"version": self.__version,
                                      "message_type": self.__message_type,
                                      "event": self.__event,
                                      "message": self.__message})
        encoded_message += hashlib.md5(encoded_message.encode()).hexdigest()
        return encoded_message.encode()


def decode_message(json_object) -> EmergencyMessage:
    json_object = json_object.decode()
    checksum = json_object[-32:]
    if hashlib.md5(json_object[:-32].encode()).hexdigest() != checksum:
        print("CHECKSUM ERROR")
        print(hashlib.md5(json_object[:-32].encode()))
        print(checksum)
    json_object = json.loads(json_object[:-32])
    if json_object['version'] != VERSION:
        raise ValueError("Invalid message version")
    version = json_object['version']
    message_type = json_object['message_type']
    event = json_object['event']
    message = json_object['message']
    return EmergencyMessage(message_type, message, event, version)


class Subscriber:
    def __init__(self, name, address, city, state, zipcode, version=VERSION):
        self.__name = name
        self.__address = address
        self.__city = city
        self.__state = state
        self.__zipcode = zipcode
        self.__version = version

    @property
    def name(self):
        return self.__name

    @property
    def address(self):
        return self.__address

    @property
    def city(self):
        return self.__city

    @property
    def state(self):
        return self.__state

    @property
    def zipcode(self):
        return self.__zipcode

    def encode(self):
        encoded_message = json.dumps({"version": self.__version,
                                      "name": self.__name,
                                      "address": self.__address,
                                      "city": self.__city,
                                      "state": self.__state,
                                      "zipcode": self.__zipcode})
        return encoded_message


def decode_subscriber(json_object) -> Subscriber:
    json_object = json.loads(json_object)
    if json_object['version'] != VERSION:
        raise ValueError("Invalid message version")
    version = json_object['version']
    name = json_object['name']
    address = json_object['address']
    city = json_object['city']
    state = json_object['state']
    zipcode = json_object['zipcode']

    return Subscriber(name, address, city, state, zipcode, version)


class Acknowledgement:
    def __init__(self, acknowledgement_type, reference, version=VERSION):
        self.__acknowledgement_type = acknowledgement_type
        self.__reference = reference
        self.__version = version

    @property
    def acknowledgement_type(self):
        return self.__acknowledgement_type

    @property
    def reference(self):
        return self.__reference

    @property
    def version(self):
        return self.__version

    def encode(self):
        encoded_message = json.dumps({"version": self.__version,
                                      "acknowledgement_type":
                                          self.__acknowledgement_type,
                                      "reference": self.__reference})
        return encoded_message


def decode_acknowledgement(json_object) -> Acknowledgement:
    json_object = json.loads(json_object)
    if json_object['version'] != VERSION:
        raise ValueError("Invalid message version")
    version = json_object['version']
    acknowledgement_type = json_object['acknowledgement_type']
    reference = json_object['reference']

    return Acknowledgement(acknowledgement_type, reference, version)
