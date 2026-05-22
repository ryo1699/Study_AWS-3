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

GitHub Actionsがすぐ失敗する場合は、失敗したrunを開いて `Start EC2 runner` jobのどのstepで落ちたか確認します。

よくある原因:

| 失敗step | 見直す値 |
| --- | --- |
| `Check required settings` | 上記Secrets / Variablesの名前と値 |
| `Configure AWS credentials` | `STUDY_AWS_3_4_AWS_ROLE_TO_ASSUME`、OIDC provider、branch名 |
| `Start EC2 instance` | `STUDY_AWS_3_4_RUNNER_INSTANCE_ID`、課題4用IAM RoleのEC2権限 |
| `Create GitHub runner registration token` | `STUDY_AWS_3_4_GH_RUNNER_TOKEN` のrepository accessとAdministration write権限 |
| `Wait for SSM and runner bootstrap` | EC2のSSM online状態、public subnetの外向き通信、user data完了 |

`Start EC2 instance` で `UnauthorizedOperation` が出る場合は、課題4用GitHub Actions RoleのIAM policyがまだ更新されていません。Terraformを再applyしてから、GitHub Actionsを再実行します。

```bash
cd Study_AWS-3_4/infra/terraform
terraform apply
```

`Start EC2 instance` で `IncorrectInstanceState` が出る場合は、前回のworkflowでEC2が起動中、実行中、または停止中のまま次のrunを始めた状態です。workflowはEC2状態を確認し、`stopped` のときだけ起動するようにしています。

`Wait for SSM and runner bootstrap` が `NOT_READY` のまま失敗する場合は、同じstepのログに `cloud_init_output_tail` が出ます。そこにEC2のuser data失敗理由が表示されます。

`runner_user_data.sh.tftpl` を変更した後は、EC2のuser dataを反映するために再applyします。この構成では `user_data_replace_on_change = true` にしているため、user data変更時はrunner用EC2が作り直されます。

```bash
cd Study_AWS-3_4/infra/terraform
terraform apply
```

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
