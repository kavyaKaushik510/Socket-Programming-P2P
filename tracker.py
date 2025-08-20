#tracker.py

import socket
import time
import threading
import json
import tkinter as tk  #library to implement Tracker UI
from tkinter import ttk 

#Tracker configuration
TRACKER_IP = "127.0.0.1" #localhost IP addresss
TRACKER_PORT = 5000      #Tracker port number

#List of active seeders
seeders_available = {}

#Number of chunks for each file name
file_chunks = {}

#Time-out for seeder in seconds
SEEDER_TIMEOUT = 10

#File to store list of available seeder
seeders_available_file = "seeders_available.txt"

# Create the seeders file if it does not exist
try:
    with open(seeders_available_file, "x") as f:
        json.dump({}, f)
except FileExistsError:
    pass

#update current state of seeders available to the file
def save_seeders_to_file():
    with open(seeders_available_file, "w") as f:
        json.dump(seeders_available, f, indent=4)

# Create a UDP socket for the tracker to listen to messages
tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
tracker_socket.bind((TRACKER_IP, TRACKER_PORT))

print(f"Tracker running on {TRACKER_IP, TRACKER_PORT}")

#GUI launch

#https://tkdocs.com/tutorial/tree.html was used as a reference to implment the code
tree = tk.Tk()
tree.title("Available file on the P2P network") #Start dashboard
tree.geometry("1000x300")

#Set a GUI style
style = ttk.Style()
style.theme_use("clam") 

#Create a GUI frame
frame = ttk.Frame(tree)
frame.pack(fill=tk.BOTH, expand=True) #fills the widget frame horizontally and vertically , True allows the widget to expand

#Declare columns to show the files and seeders
column_headings = ("File Name", "IP", "Port", "Chunks", "Last Active")
seeder_table = ttk.Treeview(frame, columns=column_headings, show="headings")

for column in column_headings:
    seeder_table.heading(column, text=column)
    seeder_table.column(column, anchor="center")

seeder_table.pack(fill=tk.BOTH, expand=True) #Fill widget

#Setup the tracker GUI
def set_gui():
    children = seeder_table.get_children() #Ensure we can retrieve rows
    seeder_table.delete(*children) #Delete all rows data
    #Update with new entries
    for file_name, seeders in seeders_available.items():
        for ip, port, chunks, last_update in seeders:
            seeder_table.insert("", tk.END, values=(file_name, ip, port, chunks, time.ctime(last_update)))
    #Run the GUI again after 5s
    tree.after(5000, set_gui)

#Handle incoming requests from seeders for registration
def handle_seeder_registration(message, seeder_address):
    try:
        # Expected message format: "REGISTER <file_name> <number of chunks> <port>"

        file_name = message[1]
        number_chunks = int(message [2])
        seeder_port = int(message[3])

        if file_name not in seeders_available:
            seeders_available[file_name] = []
            file_chunks[file_name] = number_chunks  
        seeders_available[file_name].append((seeder_address[0], seeder_port, number_chunks, time.time())) #stores IP, port, number of chunks, timestamp
        print(f"Seeder registered for file '{file_name}':{seeder_address[0]}:{seeder_port} with {number_chunks} chunks")
         # Update file for seeders available
        save_seeders_to_file()
    except (IndexError, ValueError) as e:
        print(f"Invalid registration message from {seeder_address}: {message}. Error: {e}")

#Handle incoming leecher request for seeder_available_list
def handle_leecher_request(message, leecher_address):
    try:
        #File requested by leecher
        file_name = message[1]
        
        #Check seeders available for the file rquested and send message to leecher via the UDP socket
        if file_name in seeders_available:
            seeder_list = ",".join([f"{ip}:{port}:{chunks}" for ip, port, chunks,time in seeders_available[file_name]])
            tracker_socket.sendto(seeder_list.encode(), leecher_address)
            print(f"Sent avalaible seeders list to leecher for {file_name}")
        else:
            tracker_socket.sendto(b"No seeders available", leecher_address)
            print(f"No seeder available for file name {file_name}")

    except (IndexError, ValueError) as e:
        print(f"Invalid request message from {leecher_address}: {message}. Error: {e}")

#Update last active time of a seeder
def handle_update(message, seeder_address):
    try:
        seeder_ip, seeder_port = message[1].split(":")
        seeder_port = int(seeder_port)

        for file_name, seeders in seeders_available.items():
            for i, seeder in enumerate(seeders):
                if len(seeder) == 3:  # If missing timestamp, add default 0
                    ip, port, chunks = seeder
                    last_update = 0  
                else:  
                    ip, port, chunks, last_update = seeder

                if ip == seeder_ip and port == seeder_port:
                    seeders_available[file_name][i] = (ip, port, chunks, time.time())
                    #print(f"Updated last active for {ip}:{port} hosting '{file_name}'")
                    return
        
        print(f"Seeder {seeder_ip}:{seeder_port} not found in records")

    except (IndexError, ValueError) as e:
        print(f"Invalid update message from {seeder_address}: {message}. Error: {e}")

#Remove seeders who havent't updated their availability
def remove_inactive_seeders():
    while True:
        time.sleep(SEEDER_TIMEOUT)
        current_time = time.time()
        seeders_removed = False
        
        for file_name in list(seeders_available.keys()):
            active_seeders = [
                (ip, port, chunks, last_update) for ip, port, chunks, last_update in seeders_available[file_name] 
                if current_time - last_update < SEEDER_TIMEOUT
            ]
            
            if len(active_seeders) != len(seeders_available[file_name]):
                print(f"Removed inactive seeders for file '{file_name}'")
                seeders_available[file_name] = active_seeders
                save_seeders_to_file()
                
            
            if not seeders_available[file_name]:
                print(f"No active seeders for file '{file_name}'")
                del seeders_available[file_name]
                del file_chunks[file_name]
                  
#Handle all income requests to tracker
def handle_clients():
    while True:
        try:
            #Receive data requests from clients (leechers/seeders)
            data, addr = tracker_socket.recvfrom(1024) 
            message = data.decode().split()

            #Handle file requests and registration requests accordingly
            if message[0] == "REGISTER":
                print(f"Received message from {addr}: {message}")
                handle_seeder_registration(message, addr)
            elif message[0] == "GET_SEEDERS":
                print(f"Received message from {addr}: {message}")
                handle_leecher_request(message, addr)
            elif message[0] == "AVAILABLE":
                handle_update(message, addr)
            else:
                print(f"Unknown message from {addr}: {message}")

        except Exception as e:
            print(f"Error handling request: {e}")

#start tracking
threading.Thread(target=remove_inactive_seeders, daemon=True).start() #thread to regularly remove inactive seeders uninterrupted by the rest of the program
#Tracker handles incoming requests without interupting other processes
threading.Thread(target=handle_clients, daemon=True).start()

#Update gui
set_gui()
tree.mainloop() #Run trinket application


