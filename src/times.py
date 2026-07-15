class TimeConverter:
    def __init__(self, start_time, env):
        self.start_time = start_time
        self.env = env

    def set_start_time_to_minutes(self):
        self.start_time = self.format_time_string_to_mins(self.start_time)

    def get_start_time(self):
        return self.start_time

    def format_time_minutes_to_hours(self, minutes):
        minutes = int(minutes)
        minutes = minutes % 1440
        hours = minutes // 60
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"

    def format_time_string_to_mins(self, time):
        hours, minutes = map(int, time.split(":"))
        total_minutes = hours * 60 + minutes
        return total_minutes

    def get_real_time(self, time=None):

        if not time:
            time = int(self.env.now)
        else:
            time = int(time)

        total_minutes = time + self.start_time

        return self.format_time_minutes_to_hours(total_minutes)
