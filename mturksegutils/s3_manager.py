import json
from os import path

import requests
import numpy as np
import boto3
from botocore.exceptions import NoCredentialsError
from PIL import Image
from io import BytesIO

from mturksegutils import other_utils


def upload_file_to_s3(file_dir, file_name, bucket, s3_file_name=None, verbose=False):
    """
    Uploads a file to an AWS S3 bucket.
    :param file_dir: Local path to the directory containing the file to be uploaded.
    :param file_name: Name of the file within the directory.
    :param bucket: Name of the S3 bucket.
    :param s3_file_name: Desired file name on S3. If not provided, uses the same name as the local file.
    :param verbose: if True, prints a detailed log to the console
    :return: True if file was successfully uploaded
    """

    # Create an S3 client
    s3 = boto3.client('s3')

    # If S3 object name was not specified, use file_name
    if s3_file_name is None:
        s3_file_name = file_name

    # Add the content type for this file so that it has the correct default open behavior
    content_type = 'image/png'
    if file_name.endswith('jpg'):
        content_type = 'image/jpeg'

    # If a directory and filename were passed instead of an absolute path, compose them into the path
    if file_dir is not None:
        file_name = path.join(file_dir, file_name)

    # Upload the file
    try:
        s3.upload_file(
            file_name,
            bucket,
            s3_file_name,
            ExtraArgs={
                'ContentType': content_type,
                'ContentDisposition': 'inline'
            }
        )
        if verbose:
            print(f"Upload Successful. File uploaded as {s3_file_name} in {bucket} bucket.")
        return True
    except FileNotFoundError:
        if verbose:
            print(f"The file {file_name} was not found.")
        return False
    except NoCredentialsError:
        if verbose:
            print("AWS credentials not available")
        return False


def save_image_to_s3(nparray, bucket, s3_file_name, verbose=False):
    """
    Saves a numpy array image to an S3 bucket
    :param nparray: The numpy array containing the image
    :param bucket: Name of the S3 bucket
    :param s3_file_name: Desired file name on S3
    :param verbose: if True, prints a detailed log to the console
    :return: True if file was uploaded, else False
    """

    # Create an S3 client
    s3 = boto3.client('s3')

    # Convert the image to PIL format
    img = Image.fromarray(nparray.astype('uint8'))

    # Save to an in-memory Bytes IO stream
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)  # Reset file pointer to beginning

    # Add the content type for this file so that it has the correct default open behavior
    content_type = 'image/png'

    try:
        s3.upload_fileobj(
            buffer,
            bucket,
            s3_file_name,
            ExtraArgs={
                'ContentType': content_type,
                'ContentDisposition': 'inline'
            }
        )
        if verbose:
            print(f"Upload Successful. File uploaded as {s3_file_name} in {bucket} bucket.")
        return True
    except NoCredentialsError:
        if verbose:
            print("Credentials not available")
        return False


def set_bucket_public(bucket_name):
    """
    Set a bucket policy to make all files in the bucket public by default.
    :param bucket_name: Name of the S3 bucket.
    """

    # Create an S3 client
    s3 = boto3.client('s3')

    # Define the policy
    bucket_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AddPublicReadPermissions",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }
        ]
    }

    # Set the new policy
    s3.put_bucket_policy(
        Bucket=bucket_name,
        Policy=json.dumps(bucket_policy)
    )

    print(f"Bucket {bucket_name} is now public.")



def upload_coco_image_to_s3(image_id, split, s3_bucket_name):
    """
    Uploads a single coco image to an S3 bucket from the original coco url
    :param image_id: the image ID
    :param split: the dataset split that the image comes from (train, test, or val)
    :param s3_bucket_name: The name of the S3 bucket
    :return: N/A
    """

    image_id = other_utils.add_leading_zeros_to_coco_image_ID(image_id)

    split_element = 'train'
    if split == 'test':
        split_element = 'val'
    image_url = f'http://images.cocodataset.org/{split_element}2017/{image_id}.jpg'
    print(image_url)

    # Read the image using requests and PIL
    response = requests.get(image_url)
    image = Image.open(BytesIO(response.content))

    # Convert to numpy and save to the S3 bucket
    image_np = np.asarray(image)
    s3_file_name = f'images/{image_id}.jpg'
    save_image_to_s3(image_np, s3_bucket_name, s3_file_name, verbose=True)
