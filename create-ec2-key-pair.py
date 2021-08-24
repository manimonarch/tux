import boto3
def create_key_pair():
    ec2_client = boto3.client("ec2", region_name="ap-south-1")
    key_pair = ec2_client.create_key_pair(KeyName="ec2-great-key")

    private_key = key_pair["GreatKey"]

    # write private key to file with 400 permissions
    with os.fdopen(os.open("/tmp/aws_ec2_key.pem", os.O_WRONLY | os.O_CREAT, 0o400), "w+") as handle:
        handle.write(private_key)

create_key_pair()

