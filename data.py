import json
import time
import paho.mqtt.client as mqtt
from datetime import datetime, timezone

BROKER = "172.17.0.2"
PORT = 1883
TOPIC = "sensors/data"
JSON_FILE = "data2_updated.json"

client = mqtt.Client()
client.connect(BROKER, PORT, 60)

def send_data():
    with open(JSON_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    for item in data:
        dt = datetime.utcfromtimestamp(item["TimeStamp"])
        # Prepare the JSON message correctly
        message = {
            "measurement": "sound_level",
            "tags": {
                "sensor": "acoustic"
            },
            "LAEA": float(item["LAEA"]),
            "LCpeak": float(item["LCpeak"]),
            "LCpeakT": float(item["LCpeakT"]),
            "LAFmax": float(item["LAFmax"]),
            "LAFmaxT": float(item["LAFmaxT"]),
            "LAFmin": float(item["LAFmin"]),
            "LAFminT": float(item["LAFminT"]),
            "LAeq": float(item["LAeq"]),
            "timestamp": datetime.fromtimestamp(item["TimeStamp"], tz=timezone.utc).isoformat()
        }


        try:
            # Convert the message to a valid JSON string
            message_json = json.dumps(message)
            # Publish the message to MQTT
            client.publish(TOPIC, message_json)
            print(f"Sent to MQTT: {message_json}")
        except Exception as e:
            print(f"Error creating JSON: {e}")

        time.sleep(0.1)  # Optional: adjust sleep time if needed

    client.disconnect()

if __name__ == "__main__":
    send_data()