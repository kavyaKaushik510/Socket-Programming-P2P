MINI P2P FILE SHARING SYSTEM
============================

##Install the necessary libraries:

pip install -r requirements.txt

##Run the program
Remember to configure your IP address in place of:
1) TRACKER_IP in tracker.py, seeder.py and leecher.py 
2) SEEDER_IP in tracker.py ,seeder.py

To configure your localhost address use IP address = "127.0.0.1"
To configure your local IPv4 address to transfer files over the internet. 
On windows, in the search bar search "cmd" and launch the command prompt. 
Type "ipconfig" and press enter. 
Your IPv4 address will be listed

Run the python file using the following commands on separate terminals:
py tracker.py
py leecher.py


When asked for a port number: enter any port between 6010 - 7000. Remember to not enter the same port number again. If any exceptions occur that break the program type exit.

##File system and backend process
Running leecher.py launches seeders on port 6000, 6001, 6002 and 6003 in the backend - these are the initial seeders in the network. 
You can configure the program to run with any types of files just be sure to upload them in the seeder_<port number>/files directory for any of the initial seeders on pot 6000, 6001, 6002, 6003. Ensure that each seeder only has one file as that is what the program assumes. 


##Only do if code has any unexpected failures:
While the programme ensures all error handling, if you wish to operate the code more modularly with the seeders and leechers separately do the following:
Extract leecher_backup.py from backup_files folder. 

Run each of the following on a separte terminal

py tracker.py
py seeder.py 6000
py seeder.py 6001
py seeder.py 6002
py leecher.py



