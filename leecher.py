#Leecher.py

import socket
import threading
import hashlib
import struct
import os
import time
import sys
import subprocess
import signal
from tqdm import tqdm  # Import tqdm for progress bar
import atexit
import psutil

# Configuration
TRACKER_IP = "127.0.0.1" #localhost IP addresss
TRACKER_PORT = 5000
CHUNK_SIZE = 512 * 1024  # Chunk size of 512 KB
processes = []  # List to store subprocesses

#Calculate SHA-256 hash value of a chunk for file integrity
def calculate_chunk_hash(chunk):
    return hashlib.sha256(chunk).hexdigest() # Ensure the folder exists

#Start the initial seeders for the network
#Logic source credits : https://stackoverflow.com/questions/12051485/killing-processes-with-psutil
def kill_existing_seeders():
    for proc in psutil.process_iter(attrs=['pid', 'name', 'cmdline']): #list all current processes
        try:
            cmdline = proc.info['cmdline'] #check argument of command line to obtain which files were run
            #If process is an instance of seeder.py
            if cmdline and 'python' in cmdline[0] and 'seeder.py' in cmdline:
                print(f"Terminating existing seeder process (PID: {proc.info['pid']})")
                proc.terminate() #end process
                proc.wait()  # wait for process to end
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

#Start the initial seeders for the network
def start_seeders():
    for port in [6000, 6001, 6002, 6003]:
        seeder_folder = f"seeder_{port}/files"
        os.makedirs(seeder_folder, exist_ok=True)  # Ensure the folder exists

        # Start seeder process
        print(f"Starting seeder on port {port}...")
        seeder_process = subprocess.Popen(["python", "seeder.py", str(port)])
        processes.append(seeder_process)

#Leecher downloads the file from the seeder and converts into a seeder itself
def download_file(leecher_port, file_name):
    
    # Create a UDP socket to request seeder information from the tracker
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Request the list of seeders from the tracker
    message = f"GET_SEEDERS {file_name}"
    udp_socket.sendto(message.encode(), (TRACKER_IP, TRACKER_PORT))
    print(f"Sent request to tracker: {message}")

    # Wait for the tracker's response
    data, _ = udp_socket.recvfrom(1024)
    seeders_list = data.decode().split(",")

    if len(seeders_list) == 0 or seeders_list[0] == "No seeders available":
        print("Tracker: No seeders available")
        return
    
    #Setup folder directory to store downloaded file
    DOWNLOAD_FOLDER = f"seeder_{leecher_port}/files"
    os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
    file_path = os.path.join(DOWNLOAD_FOLDER, file_name)


    #Setup which chunks to request from a seeder
    num_seeders = len(seeders_list)  #total number of seeder
    file_chunks = int(seeders_list[0].split(":")[2])  # Total number of chunks in the file
    num_chunks_per_seeder = file_chunks // num_seeders #Evenly distribute chunks between seeders
    remaining_chunks = file_chunks % num_seeders   #Calculate if there are remaining chunks

    total_received_chunks = 0 #Variable to hold the total number of chunks received


    # Open the file in write-binary mode to create it
    with open(file_path, "wb") as file:
        pass

    print(f"Tracker: {num_seeders} seeders available. File consists of {file_chunks} chunks.")

    progress_bar = tqdm(total=file_chunks, desc="Downloading", unit="chunk", colour="green", leave=True)

    # Lock for thread-safe progress bar updates
    progress_lock = threading.Lock()

    #Function to request and download specific chunks from seeders
    def download_chunks(seeder_ip, seeder_port, start_chunk, end_chunk):
        nonlocal total_received_chunks  # Allow modification of global count
        try:

            #Establish TCP socket for chunk download
            tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            tcp_socket.connect((seeder_ip, seeder_port))

            request_message = f"GET_CHUNKS {file_name} {start_chunk} {end_chunk}"
            tcp_socket.send(request_message.encode())
            #print(f"[THREAD] Requesting chunks {start_chunk}-{end_chunk-1} from {seeder_ip}:{seeder_port}")
            tqdm.write(f"[THREAD] Requesting chunks {start_chunk}-{end_chunk-1} from {seeder_ip}:{seeder_port}")

            #Count the total number of chunks received from each seeder
            chunks_received = 0

            with open(file_path, "r+b") as file:
                while chunks_received < (end_chunk - start_chunk):
                    #chunk format = {chunk_size}{chunk_data}{chunk_hash}

                    # Read the chunk size contained in the first 4 bytes
                    chunk_length_data = b"" #initiate a byte object to read data in bytes
                    while len(chunk_length_data) < 4:

                        #Get data from seeder in one call
                        data = tcp_socket.recv(4 - len(chunk_length_data))

                        #If invalid data
                        if not data:
                            break
                        chunk_length_data += data

                    #INvalid chunk size    
                    if len(chunk_length_data) < 4:
                        break  # Connection issue

                    #Extract the chunk size from the data
                    chunk_length = struct.unpack("!I", chunk_length_data)[0]  #Obtain teh integer value of the unsigned bytes integer object converted to a python object

                    #Read chunk data of length chunk_length
                    chunk_data = b""
                    while len(chunk_data) < chunk_length:
                        data = tcp_socket.recv(chunk_length - len(chunk_data))

                        #Invalid data
                        if not data:
                            break

                        chunk_data += data
                    
                    #If complete data not received
                    if len(chunk_data) < chunk_length:
                        break  # Connection issue

                    #Read sha256 hash string - 64 bytes long
                    chunk_hash = b""
                    while len(chunk_hash) < 64:
                        data = tcp_socket.recv(64 - len(chunk_hash))

                        #Invalid data
                        if not data:
                            break

                        chunk_hash += data
                    if len(chunk_hash) < 64:
                        break

                    
                    chunk_hash = chunk_hash.decode()

                    #Verify the chunk hashes match for chunk integrity 
                    if calculate_chunk_hash(chunk_data) != chunk_hash:
                        tqdm.write(f"[THREAD] Chunk {start_chunk + chunks_received} failed integrity check.")
                        continue

                   #Write the bytres received in chunk_data to the file
                    file.seek((start_chunk + chunks_received) * CHUNK_SIZE) #Set the position on the file to write
                    file.write(chunk_data)

                    #Increment chunks recieved from this seeder
                    chunks_received += 1 

                    #Update the progress bar
                    with progress_lock:
                        progress_bar.update(1) 

                    #Increament total number of chunks received of the file
                    total_received_chunks+=1
                                           
            #tqdm.write(f"[THREAD] Finished downloading {chunks_received} chunks from {seeder_ip}:{seeder_port}")
            tcp_socket.close()

        except Exception as e:
            tqdm.write(f"[THREAD] Error downloading from {seeder_ip}:{seeder_port}: {e}")

        # Create threads to download data from multiple seeders for parallel donwloads
    leecher_threads = []

    #Loop through all seeders available
    for i in range(num_seeders):

        seeder_ip, seeder_port, _ = seeders_list[i].split(":")
        seeder_port = int(seeder_port)
        
        #Assign start chunk and ending chunk to each seeder in a logical manner
        start_chunk = i * num_chunks_per_seeder
        end_chunk = start_chunk + num_chunks_per_seeder

        if i == num_seeders - 1:  # Last seeder gets remaining chunks
            end_chunk += remaining_chunks

        #Threads to download chunks parallely from the seeders
        thread = threading.Thread(target=download_chunks, args=(seeder_ip, seeder_port, start_chunk, end_chunk))
        leecher_threads.append(thread)   #keep track of running threads
        thread.start()                   #Start leeching from seeders using parallel threads

    # Wait for all threads to finish
    for thread in leecher_threads:
        thread.join()

   
    progress_bar.close()  # Close progress bar when done

    #Code to check if the entire file has been received
    if total_received_chunks == file_chunks:
        print("Download complete! The file has been fully received.")

        try:
            # Convert the leecher to a seeder at the relevant port
            seeder_process = subprocess.Popen(["python", "seeder.py", str(LEECHER_PORT)])
            processes.append(seeder_process) #keep track of all seeder processes running

            print(f"Leecher is registered as a seeder on port {LEECHER_PORT}...")

        except FileNotFoundError:
            print("Error: The specified file 'seeder.py' was not found.")
        except PermissionError:
            print("Error: Insufficient permissions to execute 'seeder.py'.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    else:
            print("Warning: Some chunks are missing! Cannot register as a seeder. Try again")

    

cleanup_called = False #prevent repated cleaning print statements

#Cleanup all running processes. Error handling implemented to ensure the file exists successfully
def cleanup():
    global cleanup_called
    if cleanup_called:
        return #to avoid multiple cleanups
    cleanup_called = True

    print("\nClosing all running processes...")
    for process in processes:
        process.terminate()
        process.wait()
    print("All processes closed successfully.")


#Cleanup on exit - this ensures program exits regardless of how it exits
#source - https://docs.python.org/3/library/atexit.html
atexit.register(cleanup)

# Handle termination signals
signal.signal(signal.SIGINT, lambda signum, frame: cleanup())
signal.signal(signal.SIGTERM, lambda signum, frame: cleanup())

# Start sinitial seeeders for the network
start_seeders()

# Main loop for user interaction
while True:
    try:
        LEECHER_PORT = int(input("Enter the port number for this leecher: "))
        file_name = input("Enter the file name to download(textbook.pdf/video.mp4): ").strip().lower()

        if not file_name:
            print("Error: File name cannot be empty!")
            continue
        
        download_file(LEECHER_PORT, file_name)

        choice = input("\nDo you want to leech another file? (yes/no): ").strip().lower()
        if choice not in ["yes", "y"]:
            cleanup()
            break

    except ValueError:
        print("Invalid input! Please enter a valid port number.")
    except KeyboardInterrupt:
        cleanup()
        break  # Exit loop
