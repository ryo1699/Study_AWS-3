# 課題4: EC2上でDocker build用GitHub Actions runnerを動かす

GitHub Actionsの最初のjobでEC2を起動し、SSM経由でEC2を一時的なself-hosted runnerとして登録します。Docker buildとECR pushはEC2 runner上で実行し、最後のjobでEC2を停止します。

```text
GitHub Actions ubuntu-latest
  -> EC2 start
  -> SSMでephemeral self-hosted runner登録
  -> Docker build / pushをEC2で実行
  -> EC2 stop
```

## 構成

```text
Study_AWS-3_4/
  app/                 # Docker build対象
  infra/terraform/     # EC2 runner, ECR, VPC, SSM用IAM

.github/workflows/study-aws-3-4-ec2-docker-build.yml
```

## Terraform

GitHub Actions用のOIDC provider (`token.actions.githubusercontent.com`) は、リポジトリ直下のREADMEにある手順で作成済みである前提です。課題4のTerraformでは、そのOIDC providerを使う課題4専用Roleを作ります。

```bash
cd Study_AWS-3_4/infra/terraform
cp backend.hcl.example backend.hcl
cp terraform.tfvars.example terraform.tfvars
terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

Terraform apply後に次を確認します。

```bash
terraform output runner_instance_id
terraform output docker_build_ecr_repository_name
terraform output github_actions_role_arn
```

## GitHub Secrets / Variables

GitHub repositoryの `Settings > Secrets and variables > Actions` で設定します。

Secrets:

| Name | Value |
| --- | --- |
| `STUDY_AWS_3_4_AWS_ROLE_TO_ASSUME` | `terraform output -raw github_actions_role_arn` |
| `STUDY_AWS_3_4_GH_RUNNER_TOKEN` | self-hosted runner registration token作成用のGitHub token |

Variables:

| Name | Value |
| --- | --- |
| `STUDY_AWS_3_4_AWS_REGION` | `ap-northeast-1` |
| `STUDY_AWS_3_4_RUNNER_INSTANCE_ID` | `terraform output -raw runner_instance_id` |
| `STUDY_AWS_3_4_ECR_REPOSITORY` | `terraform output -raw docker_build_ecr_repository_name` |

`STUDY_AWS_3_4_GH_RUNNER_TOKEN` はrepository self-hosted runnerのregistration tokenを作れる権限が必要です。fine-grained tokenを使う場合は対象repositoryを限定し、Administrationのwrite権限を付けます。

## GitHub Actions実行

手動実行する場合:

```text
Actions -> Build Docker Image on EC2 Runner -> Run workflow
```

pushで実行される対象:

```text
Study_AWS-3_4/**
.github/workflows/study-aws-3-4-ec2-docker-build.yml
```

成功するとECRに次のタグがpushされます。

```text
<account_id>.dkr.ecr.ap-northeast-1.amazonaws.com/study-aws-3-4-docker-build:<github_sha>
<account_id>.dkr.ecr.ap-northeast-1.amazonaws.com/study-aws-3-4-docker-build:latest
```

## ローカルでDocker buildだけ確認

```bash
cd Study_AWS-3_4/app
docker build -t study-aws-3-4-local .
docker run --rm study-aws-3-4-local
```

期待される出力:

```text
Study_AWS-3_4 Docker image built on an EC2-hosted GitHub Actions runner.
```
