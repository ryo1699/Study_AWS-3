# 課題2: CSV非同期出力

課題1のTask API/UIにCSV出力機能を追加します。

```text
CSV出力ボタン
  -> APIでcsv_export_jobsへpending作成
  -> SQSへjobId送信
  -> Worker ECSがCSV生成
  -> S3へ保存
  -> RDSをcompleteへ更新
  -> APIがdownload presigned URLを発行
```

## ローカル確認

API:

```bash
cd Study_AWS-3_2/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd Study_AWS-3_2/frontend
npm install
npm run dev
```

WorkerのCSV生成ロジック確認は、AWS上のSQS/S3/RDSを使う前提です。ローカルで構文だけ確認する場合:

```bash
cd Study_AWS-3_2/worker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m py_compile app/main.py
```

期待される出力:

```text
# エラーが出なければOK
```

## Terraform

```bash
cd Study_AWS-3_2/infra/terraform
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars`:

```hcl
db_password = "YOUR_DB_PASSWORD"
allowed_ssh_cidr = "153.246.177.112/32"
bastion_key_name = "ryo-key"
maintenance_mode_enabled = false
```

実行:

```bash
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

期待される出力:

```text
Apply complete! Resources: ... added, ... changed, ... destroyed.
```

## Migration

```bash
terraform output bastion_public_ip
terraform output rds_endpoint

scp -i /Users/ryo/Documents/研究室/勉強会_AWS_3/AWS_resources/ryo-key.pem \
  ../../api/migrations/001_create_tasks.sql \
  ec2-user@BASTION_PUBLIC_IP:/home/ec2-user/001_create_tasks.sql

ssh -i /Users/ryo/Documents/研究室/勉強会_AWS_3/AWS_resources/ryo-key.pem \
  ec2-user@BASTION_PUBLIC_IP
```

踏み台内:

```bash
sudo dnf install -y postgresql15
psql "postgresql://app_user:YOUR_DB_PASSWORD@RDS_ENDPOINT:5432/tasks" \
  -f /home/ec2-user/001_create_tasks.sql
```

期待される出力:

```text
CREATE TABLE
CREATE INDEX
```

## GitHub Actions CD

Terraform outputをGitHub Variablesへ設定します。

```bash
terraform output api_ecr_repository_name
terraform output frontend_ecr_repository_name
terraform output worker_ecr_repository_name
terraform output ecs_cluster_name
terraform output api_ecs_service_name
terraform output frontend_ecs_service_name
terraform output worker_ecs_service_name
terraform output api_task_definition_family
terraform output frontend_task_definition_family
terraform output worker_task_definition_family
```

GitHub Actionsの `Deploy Study AWS 3 Task 2` を実行すると、API/frontend/workerをECRへpushし、ECS serviceを更新します。

## 動作確認

1. `terraform output cloudfront_domain_name` でURLを確認します。
2. ブラウザで `https://CLOUDFRONT_DOMAIN_NAME/` を開きます。
3. タスクを数件作成します。
4. `Export CSV` を押します。
5. `Refresh` を押し、状態が `pending` -> `processing` -> `complete` になることを確認します。
6. `Download` を押します。

CSVの期待列:

```text
id,title,description,status,picture_s3_key,created_at,updated_at
```

AWS CLIで確認する場合:

```bash
aws sqs get-queue-attributes \
  --queue-url "$(terraform output -raw csv_export_queue_url)" \
  --attribute-names ApproximateNumberOfMessages ApproximateNumberOfMessagesNotVisible
```

期待される出力:

```json
{
  "Attributes": {
    "ApproximateNumberOfMessages": "0",
    "ApproximateNumberOfMessagesNotVisible": "0"
  }
}
```
