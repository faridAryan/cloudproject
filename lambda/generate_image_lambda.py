import json
import base64
import logging
import boto3
import random
from datetime import datetime, timezone
import os

class ImageError(Exception):
    "Custom exception for errors returned by SDXL"
    def __init__(self, message):
        self.message = message

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

s3 = boto3.client('s3')
BUCKET_NAME = os.getenv('BUCKET_NAME')

def upload_image_to_s3(image_bytes):
    now = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    key = f"{random.randint(1,1000000)}/{now}.png"
    s3.put_object(Bucket=BUCKET_NAME, Key=key, Body=image_bytes, ContentType='image/png')
    return key

def generate_image(model_id, body):
    logger.info("Generating image with SDXL model %s", model_id)
    bedrock = boto3.client('bedrock-runtime')
    accept = "application/json"
    content_type = "application/json"
    response = bedrock.invoke_model(
        body=body, modelId=model_id, accept=accept, contentType=content_type
    )
    response_body = json.loads(response.get("body").read())
    base64_image = response_body.get("artifacts")[0].get("base64")
    base64_bytes = base64_image.encode('ascii')
    image_bytes = base64.b64decode(base64_bytes)
    finish_reason = response_body.get("artifacts")[0].get("finishReason")
    if finish_reason == 'ERROR' or finish_reason == 'CONTENT_FILTERED':
        raise ImageError(f"Image generation error. Error code is {finish_reason}")
    logger.info("Successfully generated image with the SDXL 1.0 model %s", model_id)
    return image_bytes

def handler(event, context):
    body = json.loads(event['body'])
    model_id = 'stability.stable-diffusion-xl-v1'
    try:
        image_bytes = generate_image(model_id=model_id, body=json.dumps(body))
        key = upload_image_to_s3(image_bytes)
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        return {
            'statusCode': 200,
            'body': json.dumps({'image_base64': image_base64, 's3_key': key})
        }
    except Exception as e:
        logger.error(str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
