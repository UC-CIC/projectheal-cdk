#!/usr/bin/env python3

import aws_cdk as cdk

from pitt_comm_cdk.pitt_comm_cdk_stack import PittCommCdkStack


app = cdk.App()
PittCommCdkStack(app, "pitt-comm-cdk")

app.synth()
