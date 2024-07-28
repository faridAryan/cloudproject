import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as iam from "aws-cdk-lib/aws-iam";
import { Duration } from "aws-cdk-lib";

export class CloudAiStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create an S3 bucket for storing images
    const bucket = new s3.Bucket(this, "ImageBucket", {
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // Create a DynamoDB table for user feedback
    const table = new dynamodb.Table(this, "UserFeedbackTable", {
      partitionKey: { name: "UserID", type: dynamodb.AttributeType.STRING },
      sortKey: { name: "Timestamp", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
    });

    // Define the Lambda functions
    const descriptionLambda = new lambda.Function(this, "DescriptionFunction", {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "description_lambda.handler",
      code: lambda.Code.fromAsset("lambda"),
      environment: {
        LOG_LEVEL: "INFO",
        TABLE_NAME: table.tableName,
        BUCKET_NAME: bucket.bucketName,
      },
      timeout: Duration.minutes(1),
    });

    // Add permissions for Bedrock model invocation
    descriptionLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel"],
        resources: [
          "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
        ],
      })
    );

    const articleLambda = new lambda.Function(this, "ArticleFunction", {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "article_lambda.handler",
      code: lambda.Code.fromAsset("lambda"),
      environment: {
        LOG_LEVEL: "INFO",
      },
      timeout: Duration.minutes(1),
    });

    articleLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel"],
        resources: [
          "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0",
        ],
      })
    );

    const generateImageLambda = new lambda.Function(
      this,
      "GenerateImageFunction",
      {
        runtime: lambda.Runtime.PYTHON_3_11,
        handler: "generate_image_lambda.handler",
        code: lambda.Code.fromAsset("lambda"),
        environment: {
          LOG_LEVEL: "INFO",
          BUCKET_NAME: bucket.bucketName,
        },
        timeout: Duration.minutes(1),
      }
    );

    generateImageLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel"],
        resources: [
          "arn:aws:bedrock:us-east-1::foundation-model/stability.stable-diffusion-xl-v1",
        ],
      })
    );

    const queryImagesLambda = new lambda.Function(this, "QueryImagesFunction", {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "query_images_lambda.handler",
      code: lambda.Code.fromAsset("lambda"),
      environment: {
        LOG_LEVEL: "INFO",
        BUCKET_NAME: bucket.bucketName,
      },
      timeout: Duration.minutes(5),
    });

    // Grant permissions to Lambda functions to read/write to the DynamoDB table and S3 bucket
    table.grantReadWriteData(descriptionLambda);
    bucket.grantReadWrite(descriptionLambda);
    bucket.grantReadWrite(generateImageLambda);
    bucket.grantReadWrite(queryImagesLambda);

    // Create a single API Gateway
    const api = new apigateway.RestApi(this, "InstagramStoryPostAPI", {
      restApiName: "Instagram Story Post Service",
    });

    // Add methods for each Lambda function
    const descriptionIntegration = new apigateway.LambdaIntegration(
      descriptionLambda
    );
    api.root
      .addResource("generate-description")
      .addMethod("POST", descriptionIntegration);

    const articleIntegration = new apigateway.LambdaIntegration(articleLambda);
    api.root
      .addResource("generate-article")
      .addMethod("POST", articleIntegration);

    const generateImageIntegration = new apigateway.LambdaIntegration(
      generateImageLambda
    );
    api.root
      .addResource("generate-image")
      .addMethod("POST", generateImageIntegration);

    const queryImagesIntegration = new apigateway.LambdaIntegration(
      queryImagesLambda
    );
    api.root
      .addResource("list-images")
      .addMethod("POST", queryImagesIntegration);

    // Outputs
    new cdk.CfnOutput(this, "GenerateDescriptionURL", {
      value: `${api.url}generate-description`,
      description: "URL for generating descriptions",
    });

    new cdk.CfnOutput(this, "GenerateArticleURL", {
      value: `${api.url}generate-article`,
      description: "URL for generating article titles and subtitles",
    });

    new cdk.CfnOutput(this, "GenerateImageURL", {
      value: `${api.url}generate-image`,
      description: "URL for generating images",
    });

    new cdk.CfnOutput(this, "ListImagesURL", {
      value: `${api.url}list-images`,
      description: "URL for listing images",
    });
    new cdk.CfnOutput(this, "S3Bucket", {
      value: `${bucket.bucketName}`,
      description: "Bucket Name",
    });
  }
}
