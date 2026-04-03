import dotenv
from fastapi import FastAPI
import json
import os
import time
dotenv.load_dotenv()
api = FastAPI()

DB_FILE = 'UPSdata.jsonl'
FILEPATH = os.path.join(os.getcwd(), DB_FILE)
ups_data = []
pending_command = None

if os.path.exists(FILEPATH):
    with open(FILEPATH, 'r') as f:
        for line in f:
            if line.strip():
                ups_data.append(json.loads(line))
    print(f"{len(ups_data)} records")
else:
    with open(FILEPATH, 'w') as f:
        pass
    print("Created new DB file!")

"""
batteries in parallel, 12v boost converter, 2 channel relay, esp32 p4 board, and a lot of wires and soldering.

my relay stup
R1 (GPIO 2)
├─ NC  → R2 NC
├─ COM → Wall
└─ NO  → R2 NO

R2 (GPIO 27)
├─ NC  → R1 NC
├─ COM → 輸出端電容
└─ NO  → UPS 電池端 + R1 NO

R1: ON, R2: ON -> NO POWER
R1: ON, R2: OFF -> BAT ONLY 
R1: OFF, R2: OFF -> BAT+WALL 
R1: OFF, R2: ON -> WALL POWER 

"""
def verify_token(token: str):
    if token != os.getenv("SEC_TOKEN"):
        return False
    return True

@api.post("/UpdateData")
def update_data(data: dict):
    if not data:
        return {"error": "No data"}, 400
    if "v" not in data or "p" not in data or "chg" not in data or "secToken" not in data:
        return {"error": "Missing required fields"}, 400
    if not verify_token(data["secToken"]):
        return {"error": "Unauthorized"}, 401
    r1 = data.get("r1", 0)
    r2 = data.get("r2", 0)
    record = {
        "v": data.get("v", 0.0),      # volt
        "p": data.get("p", 0),        # percent
        "chg": data.get("chg", False),# Charging status
        "r1" : data.get("r1", 0),       # relay 1
        "r2" : data.get("r2", 0),       # relay 2
        "possibleMode": (
            "NOPOWER" if (r1 and r2) else
            "BAT ONLY" if (r1 and not r2) else
            "BAT+WALL" if (not r1 and not r2) else
            "WALL ONLY" if (not r1 and r2) else
            "UNKNOWN"
        ),                          # possible mode
        "ts": int(time.time())        # timestamp
    }
    ups_data.append(record)
    
    with open(DB_FILE, 'a') as f:
        f.write(json.dumps(record) + '\n')
    return {"status": "success"}

@api.get("/GetData")
def get_data():
    return ups_data
@api.post("/GetData")
def getdataP(data: dict):
    result = ups_data

    if "range" in data:
        result = ups_data[-data["range"]:]

    elif "TSFROM" in data and "TSTO" in data:
        result = [
            r for r in ups_data
            if data["TSFROM"] <= r["ts"] <= data["TSTO"]
        ]
    else:
        result = ups_data[-400:]
    # downsample or the chart will crash
    max_points = data.get("maxPoints", None)

    if max_points and len(result) > max_points:
        step = len(result) // max_points
        result = result[::step]

    return result
    
@api.post("/SetRelay")
def set_relay(data: dict):
    if not verify_token(data.get("secToken", "")):
        return {"error": "Unauthorized"}, 401
    global pending_command
    r1 = data.get("r1")
    r2 = data.get("r2")
    if r1 not in [0,1] or r2 not in [0,1]:
        return {"error": "invalid relay values"}, 400 # ew esp32 boot loop
    pending_command = {
        "r1": r1,
        "r2": r2,
        "ts": int(time.time())
    }
    return {"status": "command set", "cmd": pending_command}

@api.get("/GetCommand")
def get_command():
    global pending_command
    if pending_command is None:
        return {"cmd": None}
    cmd = pending_command
    pending_command = None  # clear after reading
    return {"cmd": cmd}

