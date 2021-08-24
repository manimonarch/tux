import boto3

def start_instance(instance_id):
    ec2_client = boto3.client("ec2", region_name="ap-south-1")
    response = ec2_client.start_instances(InstanceIds=[instance_id])
    print(response)

start_instance("i-010f218e4e5b6c48c")
