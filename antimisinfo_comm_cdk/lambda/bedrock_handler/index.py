import json
import os
import boto3
import botocore
import itertools
from botocore.exceptions import ClientError
import json
from decimal import Decimal

CORS_HEADERS = {
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Allow-Origin': os.environ["CORS_ALLOW_UI"] if os.environ["LOCALHOST_ORIGIN"] == "" else os.environ["LOCALHOST_ORIGIN"],
    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET,PUT'
}

bedrock = boto3.client('bedrock-runtime' , 'us-east-1')
TEMPERATURE=.1
TOP_P=.8

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

class Titan():
    def prompt_engineer_baseline_twitter(counteract, audience):
        prompt = """
        You are a nurse combating incorrect health information. The incorrect statements are: {counteract} 
        Write a single truthful Tweet with 3 hashtags for the audience: {audience}. Do not include any harmful or incorrect content.
        """

        return prompt.format(counteract=counteract, audience=audience)

    def prompt_engineer_baseline_blog(counteract, audience):
        prompt = """
        You are a nurse combating incorrect health information. The incorrect statements are: {counteract}
        Write a truthful blog post of up to 3 paragraphs for the audience: {audience}. Do not include any harmful or incorrect content.
        """

        return prompt.format(counteract=counteract, audience=audience)

    def prompt_engineer_baseline_reddit(counteract, audience):
        prompt = """
        You are a health professional combating incorrect information. The incorrect statements are: {counteract}
        Write a truthful Reddit post with a TLDR for the audience: {audience}. Do not include any harmful or incorrect content.
        """

        return prompt.format(counteract=counteract, audience=audience)

    def prompt_engineer_update_twitter(previous, prompt_instructions):
        prompt = """
        You are a helpful human assistant. Update the following text based on the prompt:
        Text: {previous}
        Prompt: {prompt_instructions}
        Output:
        """
        
        return prompt.format(previous=previous, prompt_instructions=prompt_instructions)
    
    def prompt_engineer_update_blog(previous, prompt_instructions):
        prompt = """
        You are a smart assistant. Update text based on prompt.
        Text: {previous}
        Prompt: {prompt_instructions}
        Output only text.
        """

        return prompt.format(previous=previous, prompt_instructions=prompt_instructions).replace("\n", " ")

    def prompt_engineer_update_reddit(previous, prompt_instructions):
        prompt = """
        You are a smart assistant. Update text based on prompt.
        Text: {previous}
        Prompt: {prompt_instructions}
        Output only text.
        """
        
        return prompt.format(previous=previous, prompt_instructions=prompt_instructions).replace("\n", " ")


def handler(event,context):
    print(boto3.__version__)
    print(botocore.__version__)

    # Generation Data
    try:
        field_values=json.loads(event["body"])
        print(field_values)
        
        counteracts=field_values["counteract"]
        audiences=field_values["audiences"]
        platforms=field_values["platforms"]
        mode=field_values["mode"]
        previous_prompt=field_values["previous_prompt"]
        new_prompt=field_values["prompt"]
    except:
        print("<<<Fail safe generation executed>>>")
        counteracts=["Only gay men can get Mpox"]
        audiences=["General Public"]
        platforms=["Twitter"]
        mode="baseline"
        previous_prompt=""
        new_prompt=""

    '''
    print(counteracts)
    print(audiences)
    print(platforms)
    print(mode)
    print(previous_prompt)
    print(new_prompt)
    '''
    

    responses=[]

    counteract=""
    for count,entry in enumerate(counteracts):
        counteract += str(count+1) + ") " + entry + "\n"
    print(counteract)
    audience=audiences[0]
    platform=platforms[0]

    prompt = ""
    if mode == "baseline":
        if platform == "Twitter":
            prompt = Titan.prompt_engineer_baseline_twitter( counteract, audience )
        elif platform == "Blog Post":
            prompt = Titan.prompt_engineer_baseline_blog( counteract, audience )
        elif platform == "Reddit":
            prompt = Titan.prompt_engineer_baseline_reddit( counteract, audience )
    elif mode == "update":
        if platform == "Twitter":
            prompt = Titan.prompt_engineer_update_twitter( previous_prompt, new_prompt )
        elif platform == "Blog Post":
            prompt = Titan.prompt_engineer_update_blog( previous_prompt, new_prompt )
        elif platform == "Reddit":
            prompt = Titan.prompt_engineer_update_reddit( previous_prompt, new_prompt )

    
    print("Prompt: " + prompt + "\n")
    messages = [{
        "role":"user",
        "content":prompt
    }]
    
    bedrock_payload = json.dumps(
        {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages":messages
        }
    )
    modelId = 'anthropic.claude-3-sonnet-20240229-v1:0' # change this to use a different version from the model provider
    accept = 'application/json'
    contentType = 'application/json'

    response = bedrock.invoke_model(body=bedrock_payload, modelId=modelId, accept=accept, contentType=contentType)
    response_body =  json.loads(response.get('body').read())
    print( response_body )
    responses.append(response_body.get('content')[0].get('text').strip())

    return {
        "statusCode":200,
        "headers": CORS_HEADERS,
        "body": json.dumps(responses,cls=JSONEncoder)
    }