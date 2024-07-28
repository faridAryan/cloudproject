import json
import boto3
import os

s3 = boto3.client('s3')
BUCKET_NAME = os.getenv('BUCKET_NAME')

def list_images(next_token=None):
    if next_token:
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME,
            ContinuationToken=next_token
        )
    else:
        response = s3.list_objects_v2(
            Bucket=BUCKET_NAME
        )

    image_keys = [item['Key'] for item in response.get('Contents', [])]
    next_token = response.get('NextContinuationToken', None)

    return image_keys, next_token

def generate_presigned_url(key):
    url = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': BUCKET_NAME, 'Key': key},
        ExpiresIn=3600
    )
    return url

def handler(event, context):
    body = json.loads(event['body'])
    next_token = body.get('next_token')

    image_keys, next_token = list_images(next_token)

    presigned_urls = [generate_presigned_url(key) for key in image_keys]

    return {
        'statusCode': 200,
        'body': json.dumps({'images': presigned_urls, 'next_token': next_token})
    }
