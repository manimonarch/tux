import boto3
def create_instance():
    ec2_client = boto3.client("ec2", region_name="ap-south-1")
    instances = ec2_client.run_instances(
        ImageId="ami-04db49c0fb2215364",
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        KeyName="amazon-box-key"
    )

    print(instances["Instances"][0]["InstanceId"])

create_instance()
