import boto3

def get_eks_clusters():
    eks_client = boto3.client('eks')
    
    try:
        # Retrieve the list of EKS clusters
        response = eks_client.list_clusters()
        
        # Extract the cluster names from the response
        cluster_names = response['clusters']
        
        return cluster_names
    
    except Exception as e:
        print(f"Error retrieving EKS clusters: {e}")
        return []

def get_cluster_instances(cluster_name):
    eks_client = boto3.client('eks')
    ec2_client = boto3.client('ec2')
    
    try:
        # Retrieve the cluster details
        response = eks_client.describe_cluster(name=cluster_name)
        
        # Extract the worker node group names from the response
        node_group_names = [group['nodegroupName'] for group in response['cluster']['nodegroups']]
        
        # Retrieve the instances for each worker node group
        instances = []
        for node_group_name in node_group_names:
            response = eks_client.describe_nodegroup(clusterName=cluster_name, nodegroupName=node_group_name)
            instance_ids = [instance['instanceId'] for instance in response['nodegroup']['instances']]
            
            # Retrieve the instance details using EC2 client
            response = ec2_client.describe_instances(InstanceIds=instance_ids)
            for reservation in response['Reservations']:
                instances.extend(reservation['Instances'])
        
        return instances
    
    except Exception as e:
        print(f"Error retrieving instances for cluster {cluster_name}: {e}")
        return []

def write_logs_to_file(logs, file_path):
    with open(file_path, 'w') as file:
        for log in logs:
            file.write(log + '\n')

def main():
    logs = []  # List to store the logs

    # Get the list of EKS clusters
    clusters = get_eks_clusters()
    
    if clusters:
        logs.append("EKS Clusters and Instances:")
        for cluster in clusters:
            logs.append(f"\nCluster: {cluster}")
            
            # Get the instances for the current cluster
            instances = get_cluster_instances(cluster)
            
            if instances:
                logs.append("Instances:")
                for instance in instances:
                    logs.append(f"  - Instance ID: {instance['InstanceId']}")
                    logs.append(f"    Instance Type: {instance['InstanceType']}")
                    logs.append(f"    Private IP: {instance['PrivateIpAddress']}")
                    logs.append(f"    Public IP: {instance.get('PublicIpAddress', 'N/A')}")
            else:
                logs.append("No instances found for the cluster.")
    else:
        logs.append("No EKS clusters found.")
    
    # Write the logs to a file
    write_logs_to_file(logs, 'eks_cluster_logs.txt')

if __name__ == '__main__':
    main()
