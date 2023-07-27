import os

from constructs import Construct
from aws_cdk import (
    Stack,
    aws_lambda as lambda_,
    Duration,
    aws_iam as iam
)


class PittCommCdkStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        ALLOW_LOCALHOST_ORIGIN=True
        FULL_CFRONT_URL=""
        LOCALHOST_ORIGIN="http://localhost:3000"

        layer_bedrock_sdk = lambda_.LayerVersion(
            self, "layer_bedrock_sdk",
            code=lambda_.Code.from_asset(os.path.join("pitt_comm_cdk/lambda/custom_packages/layers","bedrock-boto3-1.26.162.zip")),
            compatible_runtimes=[lambda_.Runtime.PYTHON_3_9],
            description="SDK to support bedrock.",
            layer_version_name="layer_bedrock_sdk"
        )

        layer_bedrock_botocore_sdk = lambda_.LayerVersion(
            self, "layer_bedrock_botocore_sdk",
            code=lambda_.Code.from_asset(os.path.join("pitt_comm_cdk/lambda/custom_packages/layers","bedrock-botocore-1.26.162.zip")),
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
            code=lambda_.Code.from_asset(os.path.join("pitt_comm_cdk/lambda","bedrock_handler")),
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