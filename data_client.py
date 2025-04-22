import socket
import json



HOST = "localhost"
PORT = 5000

sensor_id,filename = input("Please enter the sensor id and the filename in this format :sensor id,filename:").strip().split(",")
print(f"test {sensor_id} {filename}")
client_socket = socket.socket()
client_socket.connect((HOST,PORT))

with open(filename,"r") as f:
    data = json.load(f)

batch_size = 16
data_to_send = [data[0]]
sensor_id_message = {"sensor_id":sensor_id} 
client_socket.send(bytes(f"sensor_id:{sensor_id}\n","UTF-8"))

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

