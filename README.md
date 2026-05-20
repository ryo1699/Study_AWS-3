# Study_AWS-3

課題1〜3を実践するための完成用フォルダです。`Study_AWS-2` は参照元として残し、このフォルダだけをGitHubへ連携します。

## フォルダ構成

```text
Study_AWS-3/
  Study_AWS-3_1/  # 画像を安全に扱うTask API + React UI + ECS/RDS/S3/CloudFront/WAF
  Study_AWS-3_2/  # CSV非同期出力 API + SQS + Worker + S3
  Study_AWS-3_3/  # EventBridge + Step Functions + ECS RunTask + Slack通知
```

## 事前に決めた値

| 項目 | 値 |
| --- | --- |
| AWS region | `ap-northeast-1` |
| EC2 Key Pair名 | `ryo-key` |
| DB password | Git管理しない。手元の `terraform.tfvars` にだけ書く |
| SSH許可CIDR | `153.246.177.112/32` |
| GitHub repo | `ryo1699/Study_AWS-3` |
| Terraform state bucket | `study-aws-3-terraform-state-ryo1699` を作成する |

IPが変わった場合は次で確認し、`allowed_ssh_cidr` を更新してください。

```bash
curl -s https://checkip.amazonaws.com
```

期待される出力例:

```text
153.246.177.112
```

## Terraform state用S3バケット作成

初回だけ実行します。

```bash
aws s3api create-bucket \
  --bucket study-aws-3-terraform-state-ryo1699 \
  --region ap-northeast-1 \
  --create-bucket-configuration LocationConstraint=ap-northeast-1

aws s3api put-bucket-versioning \
  --bucket study-aws-3-terraform-state-ryo1699 \
  --versioning-configuration Status=Enabled

aws s3api put-bucket-encryption \
  --bucket study-aws-3-terraform-state-ryo1699 \
  --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

期待される出力:

```text
# create-bucket は Location が返る
{
    "Location": "http://study-aws-3-terraform-state-ryo1699.s3.amazonaws.com/"
}
```

## GitHub Actions用OIDC Role作成

課題ごとのTerraformに `github_oidc` 用の設定は含めず、AWS IAM側に一度だけ作ります。AWS CLIで作る場合は次の流れです。

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

既に同じOIDC providerがある場合は `EntityAlreadyExists` が出ます。その場合は次へ進んで問題ありません。

`trust-policy.json` をローカルに作成します。`sub` はこのリポジトリの `main` ブランチだけを許可します。

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::058898200941:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:ryo1699/Study_AWS-3:ref:refs/heads/main"
        }
      }
    }
  ]
}
```

`ACCOUNT_ID` を置き換えてから実行します。

```bash
aws iam create-role \
  --role-name study-aws-3-github-actions-role \
  --assume-role-policy-document file://trust-policy.json

aws iam attach-role-policy \
  --role-name study-aws-3-github-actions-role \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

aws iam get-role \
  --role-name study-aws-3-github-actions-role \
  --query 'Role.Arn' \
  --output text
```

期待される出力:

```text
arn:aws:iam::123456789012:role/study-aws-3-github-actions-role
```

学習用に `AdministratorAccess` を使っています。本番ではECR/ECS/iam:PassRoleなど必要権限だけに絞ってください。

## GitHub連携

最終配置先へ移動する前でも後でも使えます。ここでは現在の `Study_AWS-3` で初回pushする例です。

```bash
cd /Users/ryo/Documents/研究室/勉強会_AWS_2/Study_AWS-3
git init
git branch -M main
git remote add origin git@github.com:ryo1699/Study_AWS-3.git
git status
git add .
git commit -m "Initial Study_AWS-3 implementation"
git push -u origin main
```

## GitHub Secrets / Variables

GitHub repositoryの `Settings > Secrets and variables > Actions` で設定します。

Secrets:

| Name | Value |
| --- | --- |
| `AWS_ROLE_TO_ASSUME` | `arn:aws:iam::058898200941:role/study-aws-3-github-actions-role` |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |

Variables:

| Name | Value |
| --- | --- |
| `AWS_REGION` | `ap-northeast-1` |
| `ECR_REPOSITORY_API` | Terraform outputのAPI ECR repository名 |
| `ECR_REPOSITORY_FRONTEND` | Terraform outputのfrontend ECR repository名 |
| `ECR_REPOSITORY_WORKER` | Terraform outputのworker ECR repository名 |
| `ECR_REPOSITORY_BATCH` | Terraform outputのbatch ECR repository名 |
| `ECS_CLUSTER` | Terraform outputのECS cluster名 |
| `ECS_SERVICE_API` | Terraform outputのAPI service名 |
| `ECS_SERVICE_FRONTEND` | Terraform outputのfrontend service名 |
| `ECS_SERVICE_WORKER` | Terraform outputのworker service名 |
| `ECS_TASK_DEFINITION_API` | Terraform outputのAPI task definition family |
| `ECS_TASK_DEFINITION_FRONTEND` | Terraform outputのfrontend task definition family |
| `ECS_TASK_DEFINITION_WORKER` | Terraform outputのworker task definition family |

## VSCode連携

1. VSCodeで `File > Open Folder...` を選びます。
2. 最終移動前なら `/Users/ryo/Documents/研究室/勉強会_AWS_2/Study_AWS-3` を開きます。
3. 最終移動後なら `/Users/ryo/Documents/研究室/勉強会_AWS_3/Study_AWS-3` を開きます。
4. 左のSource Controlタブで変更差分を確認します。
5. ターミナルで次を確認します。

```bash
git remote -v
git status
```

GitHubへpushできる状態なら、Source Controlタブの `Sync Changes` またはターミナルの `git push` を使えます。

## 最終移動

`Study_AWS-3` を最終的に `/Users/ryo/Documents/研究室/勉強会_AWS_3` へ移動します。

```bash
mv /Users/ryo/Documents/研究室/勉強会_AWS_2/Study_AWS-3 \
   /Users/ryo/Documents/研究室/勉強会_AWS_3/Study_AWS-3
```

移動後:

```bash
cd /Users/ryo/Documents/研究室/勉強会_AWS_3/Study_AWS-3
git status
git remote -v
```

期待される出力:

```text
On branch main
Your branch is up to date with 'origin/main'.
```

鍵ファイルは次のパスを使う想定です。

```text
/Users/ryo/Documents/研究室/勉強会_AWS_3/AWS_resources/ryo-key.pem
```

