import os

from constructs import Construct
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    Duration,
    aws_apigateway as apigateway,
    aws_iam as iam
)


class AntiMisinfoCommCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ALLOW_LOCALHOST_ORIGIN=True
        FULL_CFRONT_URL=""
        LOCALHOST_ORIGIN="http://localhost:3000"

        layer_bedrock_sdk = lambda_.LayerVersion(
            self, "layer_bedrock_sdk",
            code=lambda_.Code.from_asset(os.path.join("antimisinfo_comm_cdk/lambda/custom_packages/layers","bedrock-boto3-1.26.162.zip")),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
            description="SDK to support bedrock.",
            layer_version_name="layer_bedrock_sdk"
        )

        layer_bedrock_botocore_sdk = lambda_.LayerVersion(
            self, "layer_bedrock_botocore_sdk",
            code=lambda_.Code.from_asset(os.path.join("antimisinfo_comm_cdk/lambda/custom_packages/layers","bedrock-botocore-1.26.162.zip")),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
            description="SDK to support bedrock.",
            layer_version_name="layer_bedrock_botocore_sdk"
        )

        bedrock_lambda_role = iam.Role(self, "bedrock-lambda-role",
          assumed_by=iam.CompositePrincipal(
            iam.ServicePrincipal("lambda.amazonaws.com"),
            )
        )

        fn_bedrock_handler = lambda_.Function(
            self,"fn-bedrock-handler",
            description="fn-bedrock-handler", #microservice tag
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="index.handler",
            role=bedrock_lambda_role,
            timeout=Duration.seconds(300),  
            code=lambda_.Code.from_asset(os.path.join("antimisinfo_comm_cdk/lambda","bedrock_handler")),
            environment={
                "CORS_ALLOW_UI":FULL_CFRONT_URL,
                "LOCALHOST_ORIGIN":LOCALHOST_ORIGIN if ALLOW_LOCALHOST_ORIGIN else "",
            },
            layers=[ layer_bedrock_sdk,layer_bedrock_botocore_sdk ]
        )

        bedrock_lambda_role.attach_inline_policy(iam.Policy(self, "bedrock-allow-policy",
            statements=[iam.PolicyStatement(
                actions=["bedrock:InvokeModel"],
                resources=["*"]
            )             
            ]
        ))
        bedrock_lambda_role.attach_inline_policy(iam.Policy(self, "bedrock-basic-execution-logging",
            statements=[iam.PolicyStatement(
                actions=["logs:CreateLogGroup","logs:CreateLogStream","logs:PutLogEvents"],
                resources=["*"]
            )             
            ]
        ))
        core_api = apigateway.RestApi(
            self,"core-api",
            endpoint_configuration=apigateway.EndpointConfiguration(
                types=[apigateway.EndpointType.REGIONAL]
            ),
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_methods=['GET', 'OPTIONS','PUT','PATCH','POST'],
                allow_origins=[FULL_CFRONT_URL, LOCALHOST_ORIGIN if ALLOW_LOCALHOST_ORIGIN else ""])
        )

        ###### Route Base = /api [match for cloud front purposes]
        api_route = core_api.root.add_resource("api")

        # /generate/communication

        # /generate/
        public_route_generate=api_route.add_resource("generate")
        # /generate/communication
        public_route_communication=public_route_generate.add_resource("communication")
        # POST: /generate/communication
        communication_post_integration=apigateway.LambdaIntegration(fn_bedrock_handler)
        method_uploader_post=public_route_communication.add_method(
            "POST",communication_post_integration,
            api_key_required=True
        )       


        #################################################################################
        # Usage plan and api key to "lock" API to only CFRONT calls (or local in our case)
        #################################################################################
        plan = core_api.add_usage_plan(
            "UsagePlan",name="public plan",
            throttle=apigateway.ThrottleSettings(
                rate_limit=10,
                burst_limit=2
            )
        )

        core_key=core_api.add_api_key("core-api-key")
        plan.add_api_key(core_key)
        plan.add_api_stage(api=core_api,stage=core_api.deployment_stage)
