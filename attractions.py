import times
import source
from outputs.code import logs

class Attraction:
    def __init__(self, env, resource, cz_name, attraction_data, min_fill, max_wait, time_converter):
        self.env = env
        self.cz_name = cz_name
        self.resource = resource
        self.attraction_data = attraction_data
        self.min_fill = min_fill
        self.max_wait = max_wait
        self.time_converter = time_converter
        self.attraction_state = source.Attraction_states.WAITING

        self.current_riders = 0
        self.ride_start = env.event()
        self.ride_end = env.event()

        env.process(self.run())

    def run(self):
        while True:
            
            while self.current_riders == 0:
                yield self.env.timeout(1)

            start_wait = self.env.now

            while True:
                filled_ratio = self.current_riders / self.resource.capacity

                if filled_ratio >= 1:
                    break

                if filled_ratio >= self.min_fill and (self.env.now - start_wait) >= (self.max_wait / 2):
                    break

                if self.env.now - start_wait >= self.max_wait and self.current_riders > 0:
                    break

                yield self.env.timeout(1)


            self.ride_start.succeed()
            self.ride_start = self.env.event()

            self.switch_attraction_state()
            message = f"ČAS {self.time_converter.get_real_time()}: Atrakce {self.cz_name} zahajuje jízdu s počtem {self.current_riders} návštěvníků."
            logs.log_message(message)
            
            yield self.env.timeout(self.attraction_data["duration"])


            self.ride_end.succeed()
            self.ride_end = self.env.event()

            self.switch_attraction_state()
            message = f"ČAS {self.time_converter.get_real_time()}: Atrakce {self.cz_name} ukončila jízdu."
            logs.log_message(message)
    
    def get_current_riders(self):
        return self.current_riders
    
    def add_rider(self):
        self.current_riders += 1

    def sub_rider(self):
        self.current_riders -= 1

    def get_ride_start(self):
        return self.ride_start

    def get_ride_end(self):
        return self.ride_end
    
    def get_data(self):
        return self.attraction_data

    def get_attraction_state(self):
        return self.attraction_state
    
    def get_cz_name(self):
        return self.cz_name
    
    def switch_attraction_state(self):
        if self.attraction_state == source.Attraction_states.WAITING:
            self.attraction_state = source.Attraction_states.RUNNING
        else:
            self.attraction_state = source.Attraction_states.WAITING