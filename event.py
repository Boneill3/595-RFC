import datetime
import pytz
from data_objects import *
import copy


class EmergencyEvent:
    def __init__(self, event_id, level, message, subscribers,
                 timezone=pytz.timezone('America/Los_Angeles')):
        self.__event_id = event_id
        self.__level = level
        self.__message = EmergencyMessage(f"level{level}", message, event_id)
        self.__waiting_sys_ack = copy.deepcopy(subscribers)
        self.__waiting_user_ack = copy.deepcopy(subscribers)
        self.__timezone = timezone
        self.__issued = datetime.datetime.now(self.__timezone)
        self.__first_issued = None
        self.__last_issued = None

    @property
    def event_id(self):
        return self.__event_id

    @property
    def level(self):
        return self.__level

    @property
    def message(self):
        return self.__message

    @property
    def waiting_sys_ack(self):
        return self.__waiting_sys_ack

    @property
    def waiting_user_ack(self):
        return self.__waiting_user_ack

    @property
    def issued(self):
        return self.__issued

    @property
    def last_issued(self):
        return self.__last_issued

    @property
    def timezone(self):
        return self.__timezone

    @property
    def is_active(self):
        return len(self.__waiting_user_ack) > 0 or \
               len(self.__waiting_sys_ack) > 0

    def log_system_ack(self, client_address):
        self.__waiting_sys_ack.pop(client_address)

    def log_user_ack(self, client_address):
        self.__waiting_user_ack.pop(client_address)

    def update_last_issued(self):
        self.__last_issued = datetime.datetime.now(self.__timezone)
        if self.__first_issued is None:
            self.__first_issued = self.__last_issued

    def cancel(self):
        self.__waiting_sys_ack = []
        self.__waiting_user_ack = []
