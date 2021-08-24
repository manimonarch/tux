import boto3

def terminate_instance(instance_id):
    ec2_client = boto3.client("ec2", region_name="ap-south-1")
    response = ec2_client.terminate_instances(InstanceIds=[instance_id])
    print(response)

terminate_instance("i-010f218e4e5b6c48c")
