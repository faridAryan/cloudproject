import json
import boto3
import logging
import os
from datetime import datetime, timezone

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

client = boto3.client('bedrock-runtime')

def generate_titles_and_subtitles(content):
    prompt = """I will provide a content of an article, and I want you to generate 5 title and for each subtitle 5 more for each paragraph.
    Example Format:
    Content:
    1.
    Lorem ipsum dolor sit amet...
    2.
    Consectetur adipiscing elit...
    Response:
    Title: Example Title
    Subtitles:
    1. Example Subtitle 1
    2. Example Subtitle 2
    """
    
    # The messages should be an array of objects, with the content field also an array
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": content}
            ]
        }
    ]

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 2000,
        "system": prompt,
        "messages": messages,
        "temperature": 0.7,
        "top_p": 0.9
    })
    
    logger.info("Body: %s", body)

    modelId = 'anthropic.claude-3-sonnet-20240229-v1:0'

    response = client.invoke_model(
        body=body,
        modelId=modelId,
        contentType="application/json",
        accept="application/json"
    )

    response_body = json.loads(response['body'].read())
    logger.info(response_body)
    output = response_body['content'][0]['text']
    return output


def handler(event, context):
    logger.info("Event: %s", event)
    try:
        body = json.loads(event['body'])
        content = body['content']

        result = generate_titles_and_subtitles(content)

        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except Exception as e:
        logger.error("Error: %s", str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
