import socket
import json



HOST = "localhost"
PORT = 5000

filename = input("Please enter the filename:").strip()

client_socket = socket.socket()
client_socket.connect((HOST,PORT))

with open(filename,"r") as f:
    data = json.load(f)

batch_size = 16
data_to_send = [data[0]]


for i,item in enumerate(data,1):
    data_to_send.append(item)
    if i % batch_size == 0:
        message = json.dumps(data_to_send)
        client_socket.sendall(message.encode()+ b'\n')
        print(f"Sent batch of {batch_size}")
        data_to_send.clear()

if data_to_send:
    message = json.dumps(data_to_send)
    client_socket.sendall(message.encode()+b'\n')
    print(f"Sent final batch of {len(data_to_send)}")

client_socket.close()

