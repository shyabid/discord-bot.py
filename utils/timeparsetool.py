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

def convert_seconds(total_seconds):
    if total_seconds < 60:
        return f"{total_seconds}s"
    
    minutes = total_seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h {minutes % 60}m" if minutes % 60 else f"{hours}h"
    
    days = hours // 24
    
    return f"{days}d {hours % 24}h" if hours % 24 else f"{days}d"
