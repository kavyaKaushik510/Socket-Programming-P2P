# MINI P2P FILE SHARING SYSTEM

A lightweight peer-to-peer file sharing system built in Python using socket programming. The system is designed to simulate a mini BitTorrent-like environment with a central tracker and multiple seeders and leechers. It supports parallel downloads, file integrity checking, re-seeding, and a basic tracker GUI.

## Features

- **Tracker**: Maintains list of available seeders via UDP
- **Seeder**: Registers with tracker and sends file chunks to leechers via TCP
- **Leecher**: Requests files, downloads in parallel from multiple seeders, and re-registers as a seeder
- **Parallel Downloads**: Splits file into chunks and downloads from multiple sources
- **File Integrity Verification**: Uses SHA-256 hashing per chunk
- **Re-Seeding**: Leechers automatically become seeders after complete download
- **Error Handling**: Robust process tracking and safe shutdown
- **Progress GUI**: Tracker shows available seeders and activity in real-time

## File Structure

```
.
├── tracker.py               # Tracker (UDP): manages seeder registrations and availability
├── seeder.py                # Seeder (TCP): serves chunks to leechers
├── leecher.py               # Leecher: requests file, downloads from seeders, becomes seeder
├── backup_files/
│   └── leecher_backup.py    # Modular leecher to run separate from initial seeder spawning
├── requirements.txt         # Python dependencies
├── seeder_<port>/files/     # Directory where each seeder stores a single shareable file
```

## Installation

Install required Python packages:

```bash
pip install -r requirements.txt
```

## Configuration

Before running the system, configure the appropriate IP addresses:

1. Replace `TRACKER_IP` in `tracker.py`, `seeder.py`, and `leecher.py`
2. Replace `SEEDER_IP` in `tracker.py` and `seeder.py`

- For **localhost testing**, set IP as:
```python
IP_ADDRESS = "127.0.0.1"
```

- For **local network testing**, find your IPv4 address:
  - Open `cmd` → run `ipconfig` → look under *IPv4 Address*

## Running the System

Use **separate terminals** for each file.

### Standard Mode (recommended)

```bash
# Terminal 1
py tracker.py

# Terminal 2
py leecher.py
```

`leecher.py` automatically launches seeders on ports `6000`, `6001`, `6002`, and `6003`.

### When prompted:
- Enter a unique port between `6010–7000`
- Enter the name of the file to download
- Uploaded files must be placed in `seeder_<port>/files/` for each initial seeder
- Each seeder must contain **only one file**

## Manual Mode (for debugging / fallback)

If needed, run the components modularly:

```bash
# Extract backup leecher
cp backup_files/leecher_backup.py .

# Terminal 1
py tracker.py

# Terminal 2
py seeder.py 6000

# Terminal 3
py seeder.py 6001

# Terminal 4
py seeder.py 6002

# Terminal 5
py leecher.py
```

## GUI and Interaction

- `tracker.py` displays a simple GUI listing all active seeders, their IP/port, file, and last update
- `leecher.py` shows a real-time progress bar during file downloads
- After file completion, leecher becomes a new seeder (on its port)

## Protocol Messages

| Message Type     | Description                                      |
|------------------|--------------------------------------------------|
| `GET_SEEDERS`    | Leecher asks tracker for seeders of a file       |
| `GET_CHUNKS`     | Leecher requests file chunks from seeder         |
| `REGISTER`       | Seeder registers file metadata to tracker        |
| `AVAILABLE`      | Seeder sends periodic status update to tracker   |
| Data Messages    | Include file chunk size, content, and SHA256 hash|

## Notes

- Chunks are fixed at **512 KB**
- Leecher checks for missing chunks and reports if download is incomplete
- Tracker drops inactive seeders after 10 seconds without `AVAILABLE` update
- Each file download spawns a new seeder from the leecher side
- Always terminate with `exit` or `no` when prompted to prevent orphan processes

## License

This project was developed as part of the CSC3002F Networks course.  
All rights reserved © 2025. For academic and learning purposes only.

