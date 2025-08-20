#seeder.py

import socket
import os
import threading
import math
import time
import hashlib
import struct
import sys


#Seeder configuration
SEEDER_IP = "127.0.0.1" #localhost IP addresss
TRACKER_IP = "127.0.0.1" #localhost IP addresss
TRACKER_PORT = 5000

#Port to run the seeder obtained as an argument
SEEDER_PORT = int(sys.argv[1])

#File to share
FILE_DIRECTORY = f"seeder_{SEEDER_PORT}/files"
#list all files in the directory
files = os.listdir(FILE_DIRECTORY) 

# Check if the directory exists and contains a file
if not os.path.exists(FILE_DIRECTORY) or not os.listdir(FILE_DIRECTORY):
    print(f"Error: Directory {FILE_DIRECTORY} is missing or empty!")
    exit()

# Each seeder only has one file
FILE_NAME = files[0] 
file_path = os.path.join(FILE_DIRECTORY, FILE_NAME)

#Fixed-sized chunks the file will be split into
CHUNK_SIZE = 512 * 1024 #Calculate 512 kb as bytes
file_size = os.path.getsize(file_path) #size of file in bytes
NUMBER_OF_CHUNKS = math.ceil(file_size/CHUNK_SIZE) #Calculate number of chunks the file will be sent over
size_kb = file_size/1024   #size of file in kb

#Create a TCP socket for the seeder
seeder_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
seeder_socket.bind((SEEDER_IP, SEEDER_PORT))
seeder_socket.listen(5)

#print(f"Seeder running on {SEEDER_IP}:{SEEDER_PORT}")

#Register the seeder with a tracker
def seeder_registration():
    try:
       #Create a UDP socket to register with the tracker
       udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

       #Send the register message with file name, number of chunks and port number
       message = f"REGISTER {FILE_NAME} {NUMBER_OF_CHUNKS} {SEEDER_PORT}"
       udp_socket.sendto(message.encode(), (TRACKER_IP, TRACKER_PORT))
       udp_socket.close()
       #print(f"Sent registration message to tracker: {message}")
    except Exception as e:
        print(f"Error registering with tracker: {e}")

#Periodically notify the tracker that the seeder is available on the network
def status_available():
    while True:
        try:
            available_udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            status_message = f"AVAILABLE {SEEDER_IP}:{SEEDER_PORT}"
            available_udp_socket.sendto(status_message.encode(), (TRACKER_IP, TRACKER_PORT))

            available_udp_socket.close()

            #print(f"Sent status available to tracker")
        except Exception as e:
            print(f"Error sending update to tracker: {e}")
        time.sleep(5)

#Calculate sha256 hash value of the chunk for file integrity
def calculate_hash(chunk):
    return hashlib.sha256(chunk).hexdigest()

#Handle leecher requests 
def handle_client(client_socket):
    try:
        # Receive the leecher request
        request = client_socket.recv(1024).decode()
        print(f"Received request: {request}")

        # Process the leecher request
        if request.startswith("GET_CHUNKS"):
            _, file_name, start_chunk, end_chunk = request.split()
            start_chunk = int(start_chunk)
            end_chunk = int(end_chunk)


           # print(f"Seeder {SEEDER_PORT} sending chunks {start_chunk} to {end_chunk - 1} of {file_name}")

            # Open the file and send requested chunks to the leecher
            with open(file_path, "rb") as file:
                for proc_chunk in range(start_chunk, end_chunk):
                    # Calculate the offset for the chunk
                    offset = proc_chunk * CHUNK_SIZE
                    file.seek(offset)

                    bytes_remaining = file_size - offset #see how many bytes left to send in file

                    #if bytes remaining is less than 512kb that means it is the last byte so to get size of last chunk we implement this minimum function
                    current_chunk_size = min(CHUNK_SIZE, bytes_remaining)

                    # Read the chunk
                    chunk = file.read(current_chunk_size)
                    if not chunk:
                        break  # No more chunks being sent so end of file

                    #Calculate hash of chunk
                    chunk_hash = calculate_hash(chunk)

                    #Message to send chunk data to leecher
                    chunk_data = struct.pack(f'!I{len(chunk)}s{len(chunk_hash)}s', current_chunk_size, chunk, chunk_hash.encode())


                    # Send the chunk to the leecher
                    client_socket.send(chunk_data)
                    #print(f"Seeder {SEEDER_PORT} sent chunk {proc_chunk}")

            #print(f"Seeder {SEEDER_PORT} sent chunks {start_chunk} to {end_chunk - 1}")
        else:
            print(f"Invalid request: {request}")

    except Exception as e:
        print(f"Error handling leecher request: {e}")
    finally:
        # Close the client socket
        client_socket.close()
        #print("Connection closed")

#Register the seeder
seeder_registration()
#Threading implemneted to allow the seeder to periodically update the tracker uninterrupted by the rest of the program
threading.Thread(target=status_available, daemon=True).start()

while True:
    # Accept incoming connections from leechers
    client_socket, addr = seeder_socket.accept()
    print(f"Connected to leecher: {addr}")
    #Threading enables us the seeder to receive multiple requests from leechers
    threading.Thread(target=handle_client, args=(client_socket,)).start()
