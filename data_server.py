import json
import time
#import paho.mqtt.client as mqtt
from datetime import datetime, timezone
import socket
import threading


BROKER = "172.17.0.2"
MQTT_PORT = 1883
TOPIC = "sensors/data"

#mqtt_client = mqtt.Client()
#mqtt_client.connect(BROKER, MQTT_PORT, 60)

HOST = "localhost"  
SERVER_PORT = 5000

def handle_client(conn,addr):
    print(f"New connection from: {str(addr)}")
    with conn:
        buffer = ""
        while True:
            data = conn.recv(1024).decode()
            if not data:
                break
            buffer += data
            while '\n' in buffer:
                line,buffer = buffer.split('\n',1) 
                print(f"Recieved: {data} from->{str(addr)}")
                try:
                    json_list = json.loads(line)
                    for json_obj in json_list:
                       print(f"Received JSON: {json_obj}") 
                       #mqtt_client.publish(TOPIC,json.dumps(json_obj))
                       print(f"Published to MQTT: {json_obj}")
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
            thread.start()
            print(f"[{threading.active_count() - 1}] Active connections.")
        except socket.timeout:
            # Apenas continuamos o loop se ocorrer timeout
            continue
except KeyboardInterrupt:
    print("Shutting down server...")
finally:
    #mqtt_client.disconnect()
    server_socket.close()
