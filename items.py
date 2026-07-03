import random

class Phone:
    def __init__(self, env):
        self.env = env
        self.battery = random.randint(70, 100)
        self.is_charging = False

    def get_state_of_battery(self):
        return self.battery 

    def set_battery_state(self, percent):
        self.battery = percent

    def charging(self):
        while True:
            yield self.env.timeout(1)

            if self.is_charging:
                self.battery = min(100, self.battery + random.uniform(0.7, 1.2))
    
    def put_on_charger(self):
        self.is_charging = True
    
    def take_from_charger(self):
        self.is_charging = False
