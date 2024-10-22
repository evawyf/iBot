

def barsize_valid_check(frequency):

    """
    barSizeSetting:str - Specifies the size of the bars that will be returned (within IB/TWS listimits).
    Valid values include:
        1 sec
        5 secs
        15 secs
        30 secs
        1 min
        2 mins
        3 mins
        5 mins
        15 mins
        30 mins
        1 hour
        1 day
    """


    valid_freq_map = {
        "sec": [1, 5, 15, 30],
        "min": [1, 2, 3, 5, 15, 30],
        "hour": [1],
        "day": [1]
    }

    # Split the frequency into value and unit
    parts = frequency.split()
    if len(parts) != 2:
        raise ValueError("Invalid frequency format. Expected 'value unit'.")
    
    value, unit = parts
    value = int(value)

    # Check if the unit is valid
    if unit.lower() in ["sec", "secs", "s", "second", "seconds", "S"]:
        unit = "sec"
    elif unit.lower() in ["min", "mins", "m", "minute", "minutes", "M"]:
        unit = "min"
    elif unit.lower() in ["hour", "hours", "h", "hourly", "H"]:
        unit = "hour"
    elif unit.lower() in ["day", "days", "D"]:
        unit = "day"
    
    if unit not in valid_freq_map:
        raise ValueError(f"Invalid frequency unit. Expected one of {list(valid_freq_map.keys())}.")

    # Check if the value is valid for the given unit
    if value not in valid_freq_map[unit]:
        raise ValueError(f"Invalid value for {unit}. Expected one of {valid_freq_map[unit]}.")

    # Format the bar size setting correctly
    if unit == "sec":
        return f"{value} secs" if value > 1 else "1 sec"
    elif unit == "min":
        return f"{value} mins" if value > 1 else "1 min"
    elif unit == "hour":
        return "1 hour"
    elif unit == "day":
        return "1 day"