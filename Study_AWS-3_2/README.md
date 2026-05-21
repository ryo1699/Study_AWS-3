# 課題2: CSV非同期出力

課題1のTask API/UIにCSV出力機能を追加します。タスク作成、一覧表示、画像アップロード、CloudFront signed URL経由の画像表示は課題1と同じ流れです。

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
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Frontend:

```bash
cd Study_AWS-3_2/frontend
npm install
npm run dev
```

期待される出力:

```text
API:      Uvicorn running on http://127.0.0.1:8000
Frontend: Local:   http://localhost:5173/
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

## CloudFront署名鍵

CloudFront signed URL用の鍵は課題1と同じものを再利用できます。課題1で次のファイルを作成済みなら、作り直す必要はありません。

```text
~/.study-aws-3/cloudfront_private_key.pem
~/.study-aws-3/cloudfront_public_key.pem
```

未作成の場合だけ作成します。

```bash
mkdir -p ~/.study-aws-3
openssl genrsa -out ~/.study-aws-3/cloudfront_private_key.pem 2048
openssl rsa -pubout -in ~/.study-aws-3/cloudfront_private_key.pem -out ~/.study-aws-3/cloudfront_public_key.pem
```

鍵を再利用する場合でも、課題2の `terraform.tfvars` には `cloudfront_public_key_pem` と `cloudfront_private_key_pem` を設定します。

## Terraform

```bash
cd Study_AWS-3_2/infra/terraform
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars`:

```hcl
resource_owner = "ryo"
bucket_name_suffix = "ryo1699"
db_password = "YOUR_DB_PASSWORD"
allowed_ssh_cidr = "153.246.177.112/32"
bastion_key_name = "ryo-key"
maintenance_mode_enabled = false
```

`resource_owner` は各リソース名の先頭に入り、誰のリソースかを見分けるために使います。`bucket_name_suffix` はS3バケット名をグローバル一意にするためのサフィックスです。

この設定では主なリソース名は次の形になります。

```text
ryo-study-aws-3-2-api
ryo-study-aws-3-2-frontend
ryo-study-aws-3-2-worker
ryo-study-aws-3-2-images-ryo1699
ryo-study-aws-3-2-csv-ryo1699
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

export RDS_ENDPOINT="RDS_ENDPOINT_FROM_TERRAFORM_OUTPUT"
export PGPASSWORD="YOUR_DB_PASSWORD"

psql "host=$RDS_ENDPOINT port=5432 dbname=tasks user=app_user sslmode=require" \
  -f /home/ec2-user/001_create_tasks.sql
```

`RDS_ENDPOINT_FROM_TERRAFORM_OUTPUT` にはローカルPC側で確認した `terraform output -raw rds_endpoint` の値を入れます。`YOUR_DB_PASSWORD` には課題2の `terraform.tfvars` に設定した `db_password` と完全に同じ値を入れてください。

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
3. 課題1と同じようにタスクを作成し、一覧表示を確認します。
4. 必要に応じて画像を選択してアップロードし、`View image` で表示できることを確認します。
5. タスクを数件作成します。
6. `Export CSV` を押します。
7. `Refresh` を押し、状態が `pending` -> `processing` -> `complete` になることを確認します。
8. `Download` を押します。

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

## 削除

課題2のリソースを削除する場合:

```bash
cd Study_AWS-3_2/infra/terraform
terraform destroy
```

ECRリポジトリと画像/CSV用S3バケットは中身ごと削除できる設定にしています。Terraform state用S3バケット `study-aws-3-terraform-state-ryo1699` はこの課題のdestroy対象ではないため削除されません。
