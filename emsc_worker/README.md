# EMSC WebSocket Worker

This is a lightweight standalone worker designed to run on a Google Compute Engine e2-micro VM (Free Tier). 
It connects to the EMSC earthquake WebSocket and forwards events to the main Cloud Run API via an internal webhook.

This decouples the persistent WebSocket connection from the Cloud Run instances, preventing memory leaks and allowing Cloud Run to scale to zero (Issue #89).

## Deployment Instructions (Ubuntu VM)

1. **Provision an e2-micro VM** in Google Cloud Console.
2. **SSH into the VM** and install python/pip:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv -y
   ```
3. **Upload this folder** (`emsc_worker/`) to the VM (e.g., `/home/ubuntu/emsc_worker`).
4. **Create a virtual environment** and install dependencies:
   ```bash
   cd /home/ubuntu/emsc_worker
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
5. **Create the Environment File (`.env`)**:
   - Copy the example file and edit it to include your actual Cloud Run URL and the secret:
     ```bash
     cp .env.example .env
     nano .env
     ```
6. **Configure the Systemd Service**:
   - Copy the service file to systemd:
     ```bash
     sudo cp emsc_worker.service /etc/systemd/system/
     sudo systemctl daemon-reload
     sudo systemctl enable emsc_worker.service
     sudo systemctl start emsc_worker.service
     ```
7. **Check Logs**:
   ```bash
   sudo journalctl -u emsc_worker -f
   ```

## Architecture

```mermaid
flowchart LR
    subgraph External
        EMSC[EMSC Seismic Portal]
    end

    subgraph Free Tier VM
        Worker[emsc_worker\nContinuous Listener]
    end

    subgraph Google Cloud Run
        API[FastAPI Server\n/api/v1/internal/emsc-webhook]
        BG[Background Tasks\nDisaster Processing]
    end

    subgraph Services
        DB[(Firestore DB)]
        Users[Telegram / LINE Users]
    end

    EMSC == "1. WebSocket (wss://)\nALWAYS OPEN" === Worker
    Worker -- "2. HTTP POST (Short-lived)\nX-Internal-Secret" --> API
    API -. "3. Return 200 OK\n(Closes connection instantly)" .-> Worker
    API -- "4. Handoff to Background" --> BG
    BG -- "5. Process & Save" --> DB
    BG -- "6. Broadcast Alert" --> Users

    classDef external fill:#f9d0c4,stroke:#333,stroke-width:2px;
    classDef worker fill:#d4e157,stroke:#333,stroke-width:2px;
    classDef serverless fill:#81d4fa,stroke:#333,stroke-width:2px;
    classDef db fill:#ffcc80,stroke:#333,stroke-width:2px;
    
    class EMSC external;
    class Worker worker;
    class API,BG serverless;
    class DB,Users db;
```
