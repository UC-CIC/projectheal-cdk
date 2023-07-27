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


class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return json.JSONEncoder.default(self, obj)

class Titan():
    def prompt_engineer_baseline_twitter( counteract, audience ):
        prompt = 'Write a tweet As a Public Health Administrator for the ' + audience + '. The Tweet should contain only truthful information counteracting the claim "' + counteract + '". Confine it to 140 characters and include hashtags. Do not include harmful content.'
        return prompt
    def prompt_engineer_update_twitter( previous, prompt ):
        prompt = 'Given the following tweet: "' + previous + '", rewrite it while still maintaining 140 characters and including hashtags to reflect the following request: "' + prompt + '". Do not include harmful content.'
        return prompt

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
        print("Fail safe generation executed")
        counteracts=["Only gay men can get Mpox"]
        audiences=["General Public"]
        platforms=["Twitter"]
        mode="baseline"
        previous_prompt=""
        new_prompt=""

    print(counteracts)
    print(audiences)
    print(platforms)
    print(mode)
    print(previous_prompt)
    print(new_prompt)
    
    combos_choices = [counteracts,audiences,platforms]
    combos=list(itertools.product(*combos_choices))

    responses = []

    i = 1
    for combo in combos:
        counteract=combo[0]
        audience=combo[1]
        platform=combo[2]

        prompt = ""
        if platform == "Twitter":
            if mode == "baseline":
                prompt = Titan.prompt_engineer_baseline_twitter( counteract, audience )
            else:
                prompt = Titan.prompt_engineer_update_twitter( previous_prompt, new_prompt )

        print("Prompt: " + prompt + "\n")
        bedrock_payload = json.dumps(
            {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": 512,
                    "stopSequences": [],
                    "temperature": 0,
                    "topP": 0.8
                } 
            }
        )
        modelId = 'amazon.titan-tg1-large' # change this to use a different version from the model provider
        accept = 'application/json'
        contentType = 'application/json'

        response = bedrock.invoke_model(body=bedrock_payload, modelId=modelId, accept=accept, contentType=contentType)
        response_body =  json.loads(response.get('body').read())
        print( response_body )
        responses.append(response_body.get('results')[0].get('outputText'))
        # short circuit for fail safe
        i += 1
        if i > 3:
            break

    
        

    return {
        "statusCode":200,
        "headers": CORS_HEADERS,
        "body": json.dumps(responses,cls=JSONEncoder)
    }