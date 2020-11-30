import datetime
import pytz


class PendingAck:
    def __init__(self, message, destination, timeout,
                 timezone=pytz.timezone('America/Los_Angeles')):
        self.__message = message
        self.__last_issued = None
        self.__destination = destination
        self.__timeout = timeout
        self.__attempts = 0
        self.__timezone = timezone

    @property
    def message(self):
        return self.__message

    @property
    def last_sent(self):
        return self.__last_sent

    @property
    def destination(self):
        return self.__destination

    def update_last_issued(self):
        self.__last_issued = datetime.datetime.now(self.__timezone)
        self.__attempts += 1

    def is_timed_out(self) -> bool:
        if self.__last_issued is None:
            return True

        timeout = datetime.datetime.now(self.__timezone) - \
                  datetime.timedelta(seconds=self.__timeout)

        return self.__last_issued < timeout
