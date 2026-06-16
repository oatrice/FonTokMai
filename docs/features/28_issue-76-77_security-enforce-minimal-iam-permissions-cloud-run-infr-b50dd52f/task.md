# Task: Security & Infrastructure Automation

- `[x]` Create Service Account `cloud-run-runtime`
- `[x]` Assign IAM roles to the Service Account
- `[x]` Update `.gitlab-ci.yml` (Set Service Account)
- `[x]` Create `backend/scripts/setup_schedulers.sh`
- `[x]` Execute the setup script to deploy 4 new Scheduler jobs
- `[x]` Delete the old `us-central1` job
- `[x]` Edit `.gitlab-ci.yml` to run `scripts/setup_schedulers.sh` automatically on deploy
- `[x]` Verify all changes
