# AWS EC2 Volume Management Script

## Overview

This script automates the management of AWS EC2 volumes. It facilitates snapshot creation, volume encryption, and instance handling with robust error handling and logging.

## Features

- Snapshot creation for EC2 volumes.
- Creation of encrypted volumes from snapshots.
- Starting, stopping, and attaching volumes to instances.
- Extensive logging for monitoring script activities.

## Requirements

- Python 3.x
- Boto3 (AWS SDK for Python)
- AWS CLI with configured credentials

## Configuration

Set these environment variables:

- `AWS_DEFAULT_REGION`: Your AWS region
- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret access key
- `AWS_SESSION_TOKEN`: Your AWS session token

## Detailed Function Descriptions

### `create_session`
- **Purpose:** Initializes a session with AWS using environment variables.
- **Output:** Returns a Boto3 session object.

### `robust_waiter`
- **Purpose:** Waits for an AWS operation to complete, with error handling.
- **Parameters:** `waiter` (AWS waiter object), `kwargs` (parameters for the waiter).
- **Output:**  Logs an error if the wait fails.

### `get_instance_name`
- **Purpose:** Retrieves the name tag of an EC2 instance.
- **Parameters:** `session` (Boto3 session), `instance_id` (ID of the instance).
- **Output:** Instance name or `None` if not found.

### `get_kms_key_arn`
- **Purpose:** Fetches the ARN of a KMS key.
- **Parameters:** `session` (Boto3 session), `alias_name` (alias of the KMS key).
- **Output:** KMS key ARN or `None` if not found.

### `get_volume_info`
- **Purpose:** Gets information about all EC2 volumes.
- **Parameters:** `session` (Boto3 session).
- **Output:** List of volume details.

### `create_snapshot`
- **Purpose:** Creates a snapshot of a specified volume.
- **Parameters:** `session` (Boto3 session), `volume_id` (ID of the volume).
- **Output:** Snapshot ID.

### `create_encrypted_volume`
- **Purpose:** Creates an encrypted volume from a snapshot.
- **Parameters:** `session`, `snapshot_id`, `availability_zone`, `size`, `volume_type`, `kms_key`.
- **Output:** Encrypted volume ID.

### `attach_encrypted_volume` and `detach_volume`
- **Purpose:** Attaches/detaches a volume to/from an instance.
- **Parameters:** `session`, `volume_id`/`encrypted_volume_id`, `instance_id`, `device_name`.
- **Output:**  Logs the operation status.

### `stop_instance` and `start_instance`
- **Purpose:** Stops/starts an EC2 instance.
- **Parameters:** `session`, `instance_id`.
- **Output:**  Logs the operation status.

### `log_volume_details`
- **Purpose:** Logs details of volume changes to a CSV file.
- **Parameters:** `details` (dictionary containing volume details).
- **Output:**  Updates the CSV file.

### `process_volumes_for_instance`
- **Purpose:** Processes all volumes for a given instance, creating snapshots and encrypted volumes.
- **Parameters:** `session`, `volumes` (list of volumes), `kms_key`.
- **Output:**  Performs multiple operations and logs details.

### `process_pending_snapshots`
- **Purpose:** Retries snapshot creation for pending snapshots.
- **Parameters:** `session`.
- **Output:**  Updates snapshot status and logs.

## Script Flow in `main`

1. **Initialization:** Sets up logging and creates a Boto3 session.
2. **KMS Key Retrieval:** Fetches the KMS key ARN required for volume encryption.
3. **Volume Information Gathering:** Collects information about all available volumes.
4. **Volume Processing:** Iterates through each volume to perform encryption operations.
5. **Instance Handling:** Stops and starts instances as required during volume processing.
6. **Snapshot Handling:** Manages pending snapshots and logs any failures.
7. **Logging:** Records all operations and their outcomes in a log file and a CSV file.

## Usage

1. Configure the necessary environment variables.
2. Run the script: `python script_name.py`

## Logging

Check `script_logs.log` and `volume_changes.csv` for detailed logs and volume change records.
FooterWorldpay, Inc.
Worldpay, Inc. 
Worldpay, Inc.
