#!/usr/bin/env python3
import subprocess
import json
import os
import sys

def sync_schedulers():
    print("Fetching Cloud Scheduler jobs from GCP...")
    
    project_id = os.getenv("GCP_PROJECT", "fonmayang")
    location = os.getenv("GCP_LOCATION", "asia-southeast1")

    try:
        result = subprocess.run([
            "gcloud", "scheduler", "jobs", "list",
            "--location", location,
            "--project", project_id,
            "--format", "json"
        ], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error fetching jobs: {e.stderr}")
        sys.exit(1)

    jobs = json.loads(result.stdout)
    
    synced_jobs = []
    
    for job in jobs:
        name_full = job.get("name", "")
        job_name = name_full.split("/")[-1]
        
        # We only care about jobs for our app (prefix fonmayang)
        if not job_name.startswith("fonmayang-"):
            continue
            
        schedule = job.get("schedule")
        time_zone = job.get("timeZone")
        description = job.get("description", "")
        
        # Extract endpoint path from the URI
        http_target = job.get("httpTarget", {})
        uri = http_target.get("uri", "")
        
        # uri looks like: https://fontokmai-api-xyz.a.run.app/api/v1/cron/check-rain
        endpoint_path = ""
        if "/api/v1/cron/" in uri:
            endpoint_path = uri.split("/api/v1/cron/")[-1]
            
        synced_jobs.append({
            "job_name": job_name,
            "schedule": schedule,
            "endpoint_path": endpoint_path,
            "time_zone": time_zone,
            "description": description
        })
        
    config_dir = os.path.join(os.path.dirname(__file__), "../config")
    os.makedirs(config_dir, exist_ok=True)
    config_path = os.path.join(config_dir, "schedulers.json")
    
    with open(config_path, "w") as f:
        json.dump(synced_jobs, f, indent=2)
        
    print(f"✅ Successfully synced {len(synced_jobs)} jobs to {os.path.abspath(config_path)}")

if __name__ == "__main__":
    sync_schedulers()
