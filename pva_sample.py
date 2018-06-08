import math
import time
import argparse
from datetime import datetime

from collections import OrderedDict

import pytz

import pvaccess as pva


ENTITIES = ["sine", "cos", "ramp", "string", "point3"]


def get_sine_cos(entity, start, end, param1):
    if param1:
        try:
            deg = float(param1)
        except (ValueError, TypeError):
            deg = 0
    else:
        deg = 0

    interval = (end - start)//999
    deg_int = deg/999.0

    value = []
    seconds = []
    nano = []

    for i in range(1000):
        if entity == "sine":
            value.append(math.sin(math.radians(deg_int*i)))
        elif entity == "cos":
            value.append(math.cos(math.radians(deg_int*i)))
        else:
            value.append(0)
        seconds.append(start + i*interval)
        nano.append(0)

    return {"value": value, "type": pva.DOUBLE,
            "secondsPastEpoch": seconds, "nano": nano}


def get_ramp(start, end, param1):
    interval = (end - start)//999

    value = []
    seconds = []
    nano = []

    if param1:
        try:
            offset = int(param1)
        except (ValueError, TypeError):
            offset = 0
    else:
        offset = 0

    for i in range(1000):
        value.append(offset + i)
        seconds.append(start + i*interval)
        nano.append(0)

    return {"value": value, "type": pva.DOUBLE,
            "secondsPastEpoch": seconds, "nano": nano}


def get_string(start, end):
    value = ["PvAccess test first", "PvAccess test"]
    seconds = [start, end]
    nano = [0, 0]

    return {"value": value, "type": pva.STRING,
            "secondsPastEpoch": seconds, "nano": nano}


def get_point3(start, end):
    interval = (end - start)//2

    value = []
    seconds = []
    nano = []

    for i in range(3):
        value.append(i)
        seconds.append(start + i*interval)
        nano.append(0)

    return {"value": value, "type": pva.ULONG,
            "secondsPastEpoch": seconds, "nano": nano}


def get(x):
    try:
        entity = x.getString("entity")
        starttime = x.getString("starttime")
        endtime = x.getString("endtime")
    except (pva.FieldNotFound, pva.InvalidRequest):
        return pva.PvString("error")

    param1 = x.getString("param1") if x.hasField("param1") else None

    str_sec = is_to_unixtime_seconds(starttime)
    end_sec = is_to_unixtime_seconds(endtime)

    if entity == "sine" or entity == "cos":
        data = get_sine_cos(entity, str_sec, end_sec, param1)
    elif entity == "string":
        data = get_string(str_sec, end_sec)
    elif entity == "point3":
        data = get_point3(str_sec, end_sec)
    else:
        data = get_ramp(str_sec, end_sec, param1)

    value = data["value"]
    seconds = data["secondsPastEpoch"]
    nano = data["nano"]
    val_type = data["type"]

    vals = OrderedDict([("column0", [val_type]),
                        ("column1", [pva.DOUBLE]),
                        ("column2", [pva.DOUBLE])])
    table = pva.PvObject(OrderedDict({"labels": [pva.STRING], "value": vals}),
                         "epics:nt/NTTable:1.0")
    table.setScalarArray("labels", ["value", "secondsPastEpoch", "nanoseconds"])
    table.setStructure("value", OrderedDict({"column0": value,
                                             "column1": seconds,
                                             "column2": nano}))

    return table


def search(x):
    try:
        query = x.getString("entity")
        name = x.getString("name")
    except (pva.FieldNotFound, pva.InvalidRequest):
        return pva.PvString("error")

    org_value = ENTITIES if str(name) == "entity" else []

    value = [val for val in org_value if val.startswith(query)]

    pv = pva.PvObject({"value": [pva.STRING]}, "epics:nt/NTScalarArray:1.0")
    pv["value"] = value

    return pv


def annotation(x):
    try:
        entity = x.getString("entity")
        starttime = x.getString("starttime")
        endtime = x.getString("endtime")
    except (pva.FieldNotFound, pva.InvalidRequest):
        return pva.PvString("error")

    str_sec = is_to_unixtime_seconds(starttime)
    end_sec = is_to_unixtime_seconds(endtime)

    time = [(int(end_sec) + int(str_sec))//2*1000]
    title = [entity]
    tags = ["test1 test2"]
    text = ["test text"]

    vals = OrderedDict([("column0", [pva.ULONG]),
                        ("column1", [pva.STRING]),
                        ("column2", [pva.STRING]),
                        ("column3", [pva.STRING])])
    table = pva.PvObject(OrderedDict({"labels": [pva.STRING], "value": vals}),
                         "epics:nt/NTTable:1.0")
    table.setScalarArray("labels", ["time", "title", "tags", "text"])
    table.setStructure("value", OrderedDict({"column0": time,
                                             "column1": title,
                                             "column2": tags,
                                             "column3": text}))

    return table


def is_to_unixtime_seconds(iso_str):
    dt = None
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        print "Invalid time"
    return int(dt.strftime("%s"))


def parsearg():
    parser = argparse.ArgumentParser(description="Grafana pvAccess sample.")
    parser.add_argument("-p", "--prefix", dest="prefix", required=True,
                        help="PV Name Prefix")
    return parser.parse_args()


def main():
    arg = parsearg()

    srv = pva.RpcServer()
    srv.registerService(arg.prefix + "get", get)
    srv.registerService(arg.prefix + "search", search)
    srv.registerService(arg.prefix + "annotation", annotation)
    srv.startListener()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print "exit"


if __name__ == "__main__":
    main()
