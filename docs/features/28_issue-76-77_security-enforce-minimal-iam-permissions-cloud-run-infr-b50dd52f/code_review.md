There is a bug in the provided script `backend/scripts/setup_schedulers.sh`:

At line 54, the script runs:
```bash
  # Check if exists
  gcloud scheduler jobs describe $JOB_NAME --location=$LOCATION --project=$PROJECT_ID > /dev/null 2>&1
  
  local DESCRIPTION="⚠️ DO NOT EDIT - Managed by CI/CD setup_schedulers.sh"

  if [ $? -eq 0 ]; then
```

Because the `local` variable declaration and assignment `local DESCRIPTION="..."` is executed immediately after `gcloud scheduler jobs describe`, the exit status variable `$?` is overwritten by the success status of the `local` declaration (which is `0`). 

As a result, `if [ $? -eq 0 ]; then` will **always** evaluate to true. The script will always attempt to update the job (`gcloud scheduler jobs update http`), and if the job does not exist, the update command will fail rather than falling back to `gcloud scheduler jobs create`.

### Suggested Fix

Capture the exit status of the `gcloud scheduler jobs describe` command before declaring local variables, or declare `DESCRIPTION` before running the command:

```bash
  # Check if exists
  gcloud scheduler jobs describe $JOB_NAME --location=$LOCATION --project=$PROJECT_ID > /dev/null 2>&1
  local STATUS=$?
  
  local DESCRIPTION="⚠️ DO NOT EDIT - Managed by CI/CD setup_schedulers.sh"

  if [ $STATUS -eq 0 ]; then
```
