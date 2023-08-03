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

bedrock = boto3.client('bedrock' , 'us-east-1')
TEMPERATURE=.1
TOP_P=.8

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

class Titan():
    def prompt_engineer_baseline_twitter( counteract, audience ):
        prompt = "You are a nurse needing to combat incorrect information.\n"
        prompt += "You have been given the following list of incorrect statements:\n" + counteract + "\n\n"
        prompt += "As a nurse, write a single Tweet that provides truthful information instead for the following audience: " + audience + "\n\n"
        prompt += "The created Tweet should contain three hashtags and not include harmful content."
        return prompt.replace("\n", " ")
    def prompt_engineer_baseline_blog( counteract, audience ):
        prompt = "You are a nurse needing to combat incorrect information.\n"
        prompt += "You have been given the following list of incorrect statements:\n" + counteract + "\n\n"
        prompt += "As a nurse, write a single blog post that provides truthful information instead for the following audience" + audience + "\n\n"
        prompt += "The created blog post should be no longer than three paragraphs and not include harmful content."
        return prompt.replace("\n", " ")
    def prompt_engineer_baseline_reddit( counteract, audience ):
        prompt = "You are a health professional needing to combat incorrect information.\n"
        prompt += "You have been given the following list of incorrect statements:\n" + counteract + "\n\n"
        prompt += "As a nurse, write a single Reddit post that provides truthful information instead for the following audience" + audience + "\n\n"
        prompt += "The created Reddit post should include a TLDR at the end and not include harmful content."
        return prompt.replace("\n", " ")

    def prompt_engineer_update_twitter( previous, prompt_instructions ):
        prompt = "Who you are:  You are a smart assistant.  Prompt: " + previous + "\n\nOutput only text."
        prompt += "Prompt:" + prompt_instructions + "\n\n"
        return prompt.replace("\n", " ")
    def prompt_engineer_update_blog( previous, prompt_instructions ):
        prompt = "Who you are:  You are a smart assistant.  Prompt: " + previous + "\n\nOutput only text."
        prompt += "Prompt:" + prompt_instructions + "\n\n"
        return prompt.replace("\n", " ")
    def prompt_engineer_update_reddit( previous, prompt_instructions ):
        prompt = "Who you are:  You are a smart assistant.  Prompt: " + previous + "\n\nOutput only text."
        prompt += "Prompt:" + prompt_instructions + "\n\nOutput only text."
        return prompt.replace("\n", " ")    

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
    bedrock_payload = json.dumps(
        {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": 512,
                "stopSequences": [],
                "temperature": TEMPERATURE,
                "topP": TOP_P
            } 
        }
    )
    modelId = 'amazon.titan-tg1-large' # change this to use a different version from the model provider
    accept = 'application/json'
    contentType = 'application/json'

    response = bedrock.invoke_model(body=bedrock_payload, modelId=modelId, accept=accept, contentType=contentType)
    response_body =  json.loads(response.get('body').read())
    print( response_body )
    responses.append(response_body.get('results')[0].get('outputText').strip())

    return {
        "statusCode":200,
        "headers": CORS_HEADERS,
        "body": json.dumps(responses,cls=JSONEncoder)
    }