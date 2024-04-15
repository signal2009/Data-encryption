import boto3
import os
from datetime import datetime
from collections import defaultdict
import botocore
import logging

VOLUME_DETAILS_LIST = []
PENDING_SNAPSHOTS = []
FAILED_SNAPSHOTS = []
EXCLUDED_INSTANCES = []  # Add your instance IDs here

logging.basicConfig(filename='script_logs.log', format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger()
MAX_RETRIES = 5

def create_session():
    return boto3.Session(
        region_name=os.environ.get('AWS_DEFAULT_REGION'),
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        aws_session_token=os.environ.get('AWS_SESSION_TOKEN'),
    )

def robust_waiter(waiter, **kwargs):
    try:
        waiter.wait(
            **kwargs,
            WaiterConfig={
                'Delay': 120,
                'MaxAttempts': 60
            }
        )
    except botocore.exceptions.WaiterError as e:
        logger.error(f"Waiter failed for parameters: {kwargs}. Error: {str(e)}")
        raise

def get_instance_name(session, instance_id):
    ec2_client = session.client("ec2")
    response = ec2_client.describe_instances(InstanceIds=[instance_id])
    for tag in response['Reservations'][0]['Instances'][0].get('Tags', []):
        if tag['Key'] == 'Name':
            return tag['Value']
    return None

def get_kms_key_arn(session, alias_name='alias/aws/ebs'):
    kms_client = session.client('kms')
    try:
        response = kms_client.describe_key(KeyId=alias_name)
        return response['KeyMetadata']['Arn']
    except kms_client.exceptions.NotFoundException:
        logger.error(f"KMS key with alias {alias_name} not found.")
        return None

def get_volume_info(session):
    ec2_client = session.client("ec2")
    response = ec2_client.describe_volumes()
    return response['Volumes']

def create_snapshot(session, volume_id):
    ec2_client = session.client("ec2")
    start_time = datetime.now()
    response = ec2_client.create_snapshot(VolumeId=volume_id)
    snapshot_id = response['SnapshotId']
    waiter = ec2_client.get_waiter('snapshot_completed')
    robust_waiter(waiter, SnapshotIds=[snapshot_id])
    elapsed_time = datetime.now() - start_time
    logger.info(f"Snapshot {snapshot_id} created in {elapsed_time}")
    return snapshot_id

def create_encrypted_volume(session, snapshot_id, availability_zone, size, volume_type, kms_key):
    ec2_client = session.client("ec2")
    start_time = datetime.now()
    response = ec2_client.create_volume(
        SnapshotId=snapshot_id,
        AvailabilityZone=availability_zone,
        Size=size,
        VolumeType=volume_type,
        Encrypted=True,
        KmsKeyId=kms_key,
    )
    volume_id = response['VolumeId']
    waiter = ec2_client.get_waiter('volume_available')
    robust_waiter(waiter, VolumeIds=[volume_id])
    elapsed_time = datetime.now() - start_time
    logger.info(f"Encrypted volume {volume_id} created in {elapsed_time}")
    return volume_id

def attach_encrypted_volume(session, encrypted_volume_id, instance_id, device_name):
    ec2_client = session.client("ec2")
    ec2_client.attach_volume(
        VolumeId=encrypted_volume_id,
        InstanceId=instance_id,
        Device=device_name
    )

def detach_volume(session, volume_id):
    ec2_client = session.client("ec2")
    start_time = datetime.now()
    ec2_client.detach_volume(VolumeId=volume_id)
    waiter = ec2_client.get_waiter('volume_available')
    robust_waiter(waiter, VolumeIds=[volume_id])
    elapsed_time = datetime.now() - start_time
    logger.info(f"Volume {volume_id} detached in {elapsed_time}")

def stop_instance(session, instance_id):
    ec2_client = session.client("ec2")
    start_time = datetime.now()
    ec2_client.stop_instances(InstanceIds=[instance_id])
    waiter = ec2_client.get_waiter('instance_stopped')
    robust_waiter(waiter, InstanceIds=[instance_id])
    elapsed_time = datetime.now() - start_time
    logger.info(f"Instance {instance_id} stopped in {elapsed_time}")

def start_instance(session, instance_id):
    ec2_client = session.client("ec2")
    start_time = datetime.now()
    ec2_client.start_instances(InstanceIds=[instance_id])
    waiter = ec2_client.get_waiter('instance_running')
    robust_waiter(waiter, InstanceIds=[instance_id])
    elapsed_time = datetime.now() - start_time
    logger.info(f"Instance {instance_id} started in {elapsed_time}")

def log_volume_details(details):
    with open('volume_changes.csv', 'a') as file:
        file.write(f"{details['old_volume_id']},{details['new_volume_id']},{details['instance_id']},{details['instance_name']},{details['device_name']},{details['disk_size']},{details['snapshot_id']},{details['availability_zone']}\n")

def process_volumes_for_instance(session, volumes, kms_key):
    instance_id = volumes[0]['Attachments'][0]['InstanceId']
    stop_instance(session, instance_id)

    for volume in volumes:
        volume_id = volume['VolumeId']
        snapshot_id = create_snapshot(session, volume_id)
        encrypted_volume_id = create_encrypted_volume(session, snapshot_id, volume['AvailabilityZone'], volume['Size'], volume['VolumeType'], kms_key)
        detach_volume(session, volume_id)
        attach_encrypted_volume(session, encrypted_volume_id, instance_id, volume['Attachments'][0]['Device'])

        instance_name = get_instance_name(session, instance_id)
        details = {
            'old_volume_id': volume_id,
            'new_volume_id': encrypted_volume_id,
            'instance_id': instance_id,
            'instance_name': instance_name,
            'device_name': volume['Attachments'][0]['Device'],
            'disk_size': volume['Size'],
            'snapshot_id': snapshot_id,
            'availability_zone': volume['AvailabilityZone']
        }
        log_volume_details(details)

    start_instance(session, instance_id)

def process_pending_snapshots(session):
    ec2_client = session.client("ec2")
    retry_count = 0

    while PENDING_SNAPSHOTS and retry_count < MAX_RETRIES:
        completed_snapshots = []

        for pending_snapshot in PENDING_SNAPSHOTS:
            volume_id = pending_snapshot['volume_id']
            response = ec2_client.describe_volumes(VolumeIds=[volume_id])
            volume_status = response['Volumes'][0]['State']

            if volume_status == 'completed':
                completed_snapshots.append(pending_snapshot)
                snapshot_id = create_snapshot(session, volume_id)
                encrypted_volume_id = create_encrypted_volume(session, snapshot_id, pending_snapshot['availability_zone'], pending_snapshot['size'], pending_snapshot['volume_type'], pending_snapshot['kms_key'])
                detach_volume(session, volume_id)
                attach_encrypted_volume(session, encrypted_volume_id, pending_snapshot['instance_id'], pending_snapshot['device_name'])
            else:
                FAILED_SNAPSHOTS.append(pending_snapshot)

        for completed_snapshot in completed_snapshots:
            PENDING_SNAPSHOTS.remove(completed_snapshot)

        if PENDING_SNAPSHOTS:
            retry_count += 1

    if PENDING_SNAPSHOTS:
        for failed in PENDING_SNAPSHOTS:
            logger.error(f"Failed snapshot details: {failed}")

def main():
    start_time = datetime.now()

    # Only write the header if the file doesn't exist
    if not os.path.exists('volume_changes.csv'):
        with open('volume_changes.csv', 'w') as file:
            file.write("Old Volume ID,New Volume ID,Instance ID,Instance Name,Device Name,Disk Size,Snapshot ID,Availability Zone\n")

    session = create_session()
    kms_key = get_kms_key_arn(session)
    if not kms_key:
        logger.error("Error: Could not retrieve the KMS key ARN. Exiting.")
        return

    volume_info = get_volume_info(session)
    
    zone_to_instance_to_volumes_map = defaultdict(lambda: defaultdict(list))
    encountered_zones = set()
    
    for volume in volume_info:
        if volume['State'] == 'in-use' and not volume['Encrypted']:
            instance_id = volume['Attachments'][0]['InstanceId']
            availability_zone = volume['AvailabilityZone']
            encountered_zones.add(availability_zone)
            zone_to_instance_to_volumes_map[availability_zone][instance_id].append(volume)

    zones_order = list(encountered_zones)

    for zone in zones_order:
        instance_to_volumes_map = zone_to_instance_to_volumes_map[zone]

        for instance_id, volumes in instance_to_volumes_map.items():
            if instance_id in EXCLUDED_INSTANCES:
                logger.info(f"Skipping encryption process for excluded instance: {instance_id}")
                continue
            process_volumes_for_instance(session, volumes, kms_key)

    if PENDING_SNAPSHOTS:
        process_pending_snapshots(session)

    elapsed_time = datetime.now() - start_time
    logger.info(f"Script completed in {elapsed_time}")

if __name__ == '__main__':
    main()