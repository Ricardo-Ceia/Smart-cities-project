import json
import time
import paho.mqtt.client as mqtt
from datetime import datetime, timezone
import socket
import threading


def data_is_id(data):
    return data.startswith("sensor_id:")


BROKER = "172.17.0.2"
MQTT_PORT = 1883
TOPIC = "sensors/data"

mqtt_client = mqtt.Client()
mqtt_client.connect(BROKER, MQTT_PORT, 60)

HOST = "localhost"  
SERVER_PORT = 5000

def handle_client(conn,addr):
    print(f"New connection from: {str(addr)}")
    with conn:
        buffer = ""
        while True:
            data = conn.recv(1024).decode()
            #TODO optimize so it doesnt check every time for the id
            if data_is_id(data):
                #-2 cause of the \n sent on the client
                sensor_id = data[len(data)-2:]
                topic = TOPIC+sensor_id
                print(f"THIS IS THE TOPIC:{topic}")
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line,buffer = buffer.split('\n',1) 
                try:
                    json_list = json.loads(line)
                    for json_obj in json_list:
                       mqtt_client.publish(topic,json.dumps(json_obj))
                       print(f"Published to MQTT: {json_obj}")
                       time.sleep(1)
                except json.JSONDecodeError:
                    print("Warning: Received data is not valid JSON.")
    print(f"Connection finished with {str(addr)}")


server_socket = socket.socket()
server_socket.bind((HOST,SERVER_PORT))
server_socket.listen()
server_socket.settimeout(1)  # Timeout de 1 segundo

print(f"Server listening on {HOST}:{SERVER_PORT}")
try:
    while True:
        try:
            conn, addr = server_socket.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            #TODO read about daemon and understand what´s going on 
            thread.daemon = True
            thread.start()
            print(f"[{threading.active_count() - 1}] Active connections.")
        except socket.timeout:
            # Apenas continuamos o loop se ocorrer timeout
            continue
except KeyboardInterrupt:
    print("Shutting down server...")
finally:
    mqtt_client.disconnect()
    server_socket.close()
