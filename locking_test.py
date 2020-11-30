import concurrent.futures
import threading
import time
from multiprocessing import Pool, Lock, Process


class MessageTest:
    def __init__(self):
        self.to_send = 0
        self.display_lock = threading.Lock()
        self.to_send_lock = threading.Lock()
        self.menu = "(S)end another message or (L)eave:"
        self.quit = False

    def worker(self):
        with self.display_lock:
            print("Worker Starting..")
        while not self.quit:
            if self.to_send > 0:
                with self.to_send_lock:
                    self.to_send -= 1
                    print("Decremented")
                with self.display_lock:
                    print("Message Sent!")
            time.sleep(0.5)

    def main(self):
        print("Main Starting")
        while not self.quit:
            response = input(self.menu)
            if response == "S":
                with self.to_send_lock:
                    self.to_send += 1
                    print("Incremented")
            if response == "L":
                self.quit = True
        print("Exiting")


if __name__ == "__main__":
    runner = MessageTest()
    jobs = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        jobs.append(executor.submit(runner.main))
        jobs.append(executor.submit(runner.worker))
    print("program end")
