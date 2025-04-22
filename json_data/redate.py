#NOTE: This variabel values need to be changed to the wanted values


import json
from datetime import datetime,timedelta

JSON_FILE = "data.json"
BLOCK = 16

initial_date = datetime(2025, 4, 18, 0, 0, 0)
timestamp_base = int(initial_date.timestamp())

with open(JSON_FILE,"r") as file:
    data = json.load(file)


for i,item in enumerate(data):
    group = i // BLOCK
    item["TimeStamp"] = timestamp_base + group
    print("Number :",i)

with open("data_updated.json","w") as f:
    json.dump(data,f,indent=2)