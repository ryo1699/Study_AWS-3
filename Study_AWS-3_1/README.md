# 課題1: 画像をセキュアに扱うTask API

CloudFront + ALB + ECR + ECS(API) + ECS(React) + RDS + S3 private bucket + CloudFront OAC + WAF を使います。

## ローカル確認

API:

```bash
cd Study_AWS-3_1/api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

期待される出力:

```text
Uvicorn running on http://127.0.0.1:8000
```

別ターミナル:

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/tasks \
  -H 'Content-Type: application/json' \
  -d '{"title":"画像付きタスク","description":"S3に画像を保存する"}'
curl http://localhost:8000/api/tasks
```

期待される出力:

```json
{"status":"ok"}
```

Frontend:

```bash
cd Study_AWS-3_1/frontend
npm install
npm run dev
```

期待される出力:

```text
Local:   http://localhost:5173/
```

## CloudFront署名鍵の作成

CloudFront signed URL用に鍵を作ります。秘密鍵はGit管理しません。

```bash
mkdir -p ~/.study-aws-3
openssl genrsa -out ~/.study-aws-3/cloudfront_private_key.pem 2048
openssl rsa -pubout -in ~/.study-aws-3/cloudfront_private_key.pem -out ~/.study-aws-3/cloudfront_public_key.pem
```

`cloudfront_public_key_pem` には公開鍵の中身を入れます。`cloudfront_private_key_pem` には秘密鍵の中身を入れます。

## Terraform

```bash
cd Study_AWS-3_1/infra/terraform
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
```

`terraform.tfvars` を編集します。`db_password` は手元にだけ保存してください。

```hcl
db_password = "YOUR_DB_PASSWORD"
allowed_ssh_cidr = "153.246.177.112/32"
bastion_key_name = "ryo-key"
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

## RDS migration

Terraform outputを確認します。

```bash
terraform output bastion_public_ip
terraform output rds_endpoint
```

SQLを踏み台へコピーします。

```bash
scp -i /Users/ryo/Documents/研究室/勉強会_AWS_3/AWS_resources/ryo-key.pem \
  ../../api/migrations/001_create_tasks.sql \
  ec2-user@BASTION_PUBLIC_IP:/home/ec2-user/001_create_tasks.sql
```

踏み台へ入ります。

```bash
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
CREATE INDEX
```

## GitHub Actions CD

Terraform apply後、次を確認してGitHub Variablesへ設定します。

```bash
terraform output api_ecr_repository_name
terraform output frontend_ecr_repository_name
terraform output ecs_cluster_name
terraform output api_ecs_service_name
terraform output frontend_ecs_service_name
terraform output api_task_definition_family
terraform output frontend_task_definition_family
```

設定後、GitHub Actionsの `Deploy Study AWS 3 Task 1` を手動実行するか、`main` にpushします。

## AWS確認

CloudFront URL:

```bash
terraform output cloudfront_domain_name
```

ブラウザで次を開きます。

```text
https://CLOUDFRONT_DOMAIN_NAME/
```

確認すること:

- タスク作成ができる
- 一覧が表示される
- 画像を選択してアップロードできる
- `View image` でCloudFront signed URL経由の画像が表示される

## メンテナンスモード

`terraform.tfvars` で次にするとCloudFrontにWAFが付き、全リクエストをブロックします。

```hcl
maintenance_mode_enabled = true
```

反映:

```bash
terraform apply
```

戻す場合:

```hcl
maintenance_mode_enabled = false
```
