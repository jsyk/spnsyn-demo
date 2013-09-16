import time

shared_level = 0

class Timing:
    def __init__(self, name, start=True):
        self.start_tm = None
        self.stop_tm = None
        self.level = None
        self.name = name
        if start:
            self.start()

    def start(self):
        global shared_level
        self.level = shared_level
        self.start_tm = time.clock()
        shared_level += 1

    def stop(self):
        global shared_level
        self.stop_tm = time.clock()
        self.dur = self.stop_tm - self.start_tm
        shared_level -= 1

    def printout(self):
        print('-*-*- /{0}/ {1:.2f} sec: "{2}" -*-*-'.format(self.level, self.dur, self.name))

    def fin(self):
        if not self.stop_tm:
            self.stop()
        self.printout()

