# 課題3: EventBridge -> Step Functions -> ECS Task -> Slack通知

EventBridgeのスケジュールでStep Functionsを開始し、Step FunctionsがECS Fargate taskを実行した後、LambdaからSlackへ通知します。

## ローカル確認

Batch:

```bash
cd Study_AWS-3_3/batch
python3 -m app.main
```

期待される出力:

```json
{"status": "complete", "task": "study-aws-3-batch", "message": "ECS batch task finished successfully.", "finishedAt": "..."}
```

Slack Lambdaのメッセージ整形:

```bash
cd Study_AWS-3_3/lambda
python3 - <<'PY'
import json
from lambda_function import build_message
with open("local_event.json") as f:
    print(json.dumps(build_message(json.load(f)), ensure_ascii=False, indent=2))
PY
```

期待される出力:

```json
{
  "text": "Study_AWS-3 課題3: ECS batch finished. execution=local-test, status=SUCCEEDED"
}
```

## Terraform

```bash
cd Study_AWS-3_3/infra/terraform
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars` の `slack_webhook_url` にはSlack Incoming Webhook URLを入れます。このファイルは `.gitignore` 済みです。

```hcl
slack_webhook_url = "https://hooks.slack.com/services/XXX/YYY/ZZZ"
eventbridge_schedule_expression = "rate(1 day)"
```

初回:

```bash
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

期待される出力:

```text
Apply complete! Resources: ... added, ... changed, ... destroyed.
```

## Batch imageをECRへpush

Terraform apply後、ECR repository URLを確認します。

```bash
terraform output batch_ecr_repository_url
```

手元でpushする場合:

```bash
ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
AWS_REGION="ap-northeast-1"
REPO_URL="$(terraform output -raw batch_ecr_repository_url)"

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

cd ../../batch
docker build -t "${REPO_URL}:latest" .
docker push "${REPO_URL}:latest"
```

`terraform.tfvars` の `batch_container_image` を次のように更新し、再applyします。

```hcl
batch_container_image = "ACCOUNT_ID.dkr.ecr.ap-northeast-1.amazonaws.com/study-aws-3-3-batch:latest"
```

```bash
cd ../infra/terraform
terraform apply
```

GitHub Actionsでpushする場合は、GitHub Variablesに `ECR_REPOSITORY_BATCH` を設定し、`Build Study AWS 3 Task 3 Batch Image` を実行します。

## Step Functions手動実行

```bash
STATE_MACHINE_ARN="$(terraform output -raw step_functions_state_machine_arn)"
aws stepfunctions start-execution \
  --state-machine-arn "$STATE_MACHINE_ARN" \
  --input '{}'
```

期待される出力:

```json
{
  "executionArn": "arn:aws:states:ap-northeast-1:123456789012:execution:...",
  "startDate": "..."
}
```

実行状況:

```bash
aws stepfunctions list-executions \
  --state-machine-arn "$STATE_MACHINE_ARN" \
  --max-results 5
```

期待される状態:

```text
SUCCEEDED
```

Slackに次のような通知が届けば成功です。

```text
Study_AWS-3 課題3: ECS batch finished. execution=..., status=SUCCEEDED
```

## EventBridge確認

```bash
terraform output eventbridge_rule_name
aws events describe-rule --name "$(terraform output -raw eventbridge_rule_name)"
```

期待される出力:

```json
{
  "ScheduleExpression": "rate(1 day)",
  "State": "ENABLED"
}
```

