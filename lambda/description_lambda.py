import json
import boto3
import base64
from datetime import datetime, timezone
import os
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

class ImageError(Exception):
    def __init__(self, message):
        self.message = message

dynamodb = boto3.resource('dynamodb')
table_name = os.getenv('TABLE_NAME')
table = dynamodb.Table(table_name)
s3 = boto3.client('s3')
BUCKET_NAME = os.getenv('BUCKET_NAME')

def get_response_from_model(temperature, prompt_content, image_bytes):
    try:
        session = boto3.Session()
        bedrock = session.client(service_name='bedrock-runtime')
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 600,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": base64.b64encode(image_bytes).decode('utf-8')
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt_content
                        }
                    ]
                }
            ],
            "temperature": temperature,
        }
        
        # Convert the body to a JSON string and then to bytes
        body_bytes = json.dumps(body).encode('utf-8')
        
        logger.info("Invoking model with body: %s", body_bytes)

        response = bedrock.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=body_bytes,
            contentType="application/json",
            accept="application/json"
        )
        
        # Read the response body
        response_body = response['body'].read()
        logger.info("Model response body: %s", response_body)

        response_data = json.loads(response_body)
        logger.info("Parsed model response: %s", response_data)


        output = response_data['content'][0]['text']
        return output
    except Exception as e:
        logger.error(f"Error in get_response_from_model: {str(e)}")
        raise

def get_prompt_template(prompt_type, custom_template, user_description):
    if custom_template:
        return custom_template
    elif user_description:
        return f"""
        I will provide an image and a brief description provided by the user, and I want you to generate a catchy title and a brief description suitable for an Instagram {prompt_type.lower()}.
        User Description: {user_description}
        Example Format:
        Provide Image:
        [Attach your image]
        Title and Description:
        """
    elif prompt_type == "Instagram Story":
        return """
        I will provide an image, and I want you to generate a catchy title and a very brief description suitable for an Instagram story.
        Example Format:
        Provide Image:
        Title and Description:
        Title: "Sweet Moments 🍦"
        Description: "Perfect day for a treat! #IceCreamDay #SunnyVibes"
        """
    elif prompt_type == "Instagram Post":
        return """
        I will provide an image, and I want you to generate a catchy title and a brief description suitable for an Instagram post.
        Example Format:
        Provide Image:
        Title and Description:
        Title: "Urban Exploration"
        Description: "Discovering the hidden gems of the city, one mural at a time. 🎨🌆 #CityLife #StreetArt"
        """
    else:
        return None

def store_feedback(user_id, image_bytes, initial_description, user_feedback, final_description, status):
    try:
        timestamp = datetime.now(timezone.utc).isoformat()
        table.put_item(
            Item={
                'UserID': user_id,
                'Timestamp': timestamp,
                'ImageBytes': base64.b64encode(image_bytes).decode('utf-8'),
                'InitialDescription': initial_description,
                'UserFeedback': user_feedback,
                'FinalDescription': final_description,
                'Status': status
            }
        )
    except Exception as e:
        logger.error(f"Error in store_feedback: {str(e)}")
        raise

def handler(event, context):
    logger.info("Event: " + json.dumps(event))
    try:
        # Fallback for test events without 'body'
        if 'body' not in event:
            logger.error("Missing body in event")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing body in event'})
            }

        body = json.loads(event['body'])
        prompt_type = body['prompt_type']
        custom_template = body.get('custom_template', None)
        user_description = body.get('user_description', None)
        user_id = body['user_id']
        image_bytes = base64.b64decode(body['image_bytes'])
        temperature = body["temperature"]

        logger.info("Generating prompt content")
        prompt_content = get_prompt_template(prompt_type, custom_template, user_description)
        if not prompt_content:
            logger.error("Invalid prompt type")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Invalid prompt type'})
            }

        logger.info("Getting response from model")
        response_text = get_response_from_model(temperature, prompt_content, image_bytes)

        title = ""
        description = ""
        for line in response_text.split("\n"):
            if line.startswith("Title:"):
                title = line[len("Title:"):].strip()
            elif line.startswith("Description:"):
                description = line[len("Description:"):].strip()
        result = {
            'title': title,
            'description': description
        }

        logger.info("Storing feedback in DynamoDB")
        store_feedback(user_id, image_bytes, description, user_description, description, "Accepted")

        logger.info("Returning successful response")
        return {
            'statusCode': 200,
            'body': json.dumps(result)
        }
    except Exception as e:
        logger.error("Error: " + str(e))
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }








