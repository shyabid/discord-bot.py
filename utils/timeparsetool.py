import re

def strtoint(time_str): # honestly, i am proud of this function
    total_seconds = 0
    pattern = re.compile(r'(?:(\d+)\s*(hr|hrs|h|hour|hours|mins|min|m|minutes|seconds|sec|s|second|secs)?\s*)')
    matches = pattern.findall(time_str)

    for value, unit in matches:
        value = int(value)
        if unit in ['hr', 'hrs', 'h', 'hour', 'hours']:
            total_seconds += value * 3600
        elif unit in ['min', 'mins', 'm', 'minutes']:
            total_seconds += value * 60
        elif unit in ['sec', 's', 'seconds', 'secs']:
            total_seconds += value
            

    return total_seconds