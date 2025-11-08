# Infrastructure – Kauri (AWS)

Préparation de l’infrastructure AWS sans déploiement automatique : ce dossier contient uniquement l’IaC nécessaire pour créer l’environnement Kauri lorsque vous serez prêt à exécuter `terraform apply`.

## Vue d’ensemble

- **Compute** : 1 instance `t4g.large` (Ubuntu 22.04 ARM) destinée à héberger tout le stack Docker (`kauri_chatbot_service`, `kauri_user_service`, frontend, Postgres, Redis, ChromaDB, Grafana).  
- **Stockage** : volume EBS gp3 80 Go (persistant) + bucket S3 versionné pour `base_connaissances` et les dumps (tiering Glacier pour les sauvegardes).  
- **Sécurité** : VPC dédié /24, sous-réseau public, Security Group minimal (22 + 80/443 + 3000 restreint). Les secrets restent dans **SSM Parameter Store** (`/${project}/…`).  
- **FinOps** : Budgets AWS (`global` 30 $/mois, `kauri` 18 $/mois), SNS pour alertes, CloudWatch alarms (CPU + Status Check), EventBridge Scheduler pour démarrer/arrêter automatiquement l’instance selon les plages de démos (réduction des coûts tout en gardant l’instance on-demand).  
- **Observabilité** : l’IAM du serveur autorise CloudWatch Agent + accès S3/SSM; Grafana tournant dans Docker consommera ses dashboards depuis cette machine.

Rien n’est déployé tant que vous n’exécutez pas Terraform.

## Pré-requis

1. **Terraform ≥ 1.6** et AWS CLI configuré (`aws configure sso` ou clés d’API).  
2. Un **Key Pair EC2** déjà existant (nom passé via `-var="ssh_key_name=..."`).  
3. (Optionnel) Liste d’e-mails pour les alertes budgets/CloudWatch.  
4. IAM disposant des permissions nécessaires (EC2, VPC, S3, Budgets, SNS, Scheduler, SSM).

## Arborescence

```
infrastructure/aws/kauri/
├── compute.tf          # Instance, IAM, EIP
├── locals.tf           # Tags + helpers
├── monitoring.tf       # SNS, budgets, CloudWatch alarms
├── network.tf          # VPC + subnet + routes
├── outputs.tf
├── providers.tf
├── scheduler.tf        # EventBridge start/stop
├── security.tf         # Security group
├── ssm.tf              # Parameter Store map
├── storage.tf          # S3 bucket + lifecycle
├── variables.tf
└── versions.tf
```

## Utilisation (planification uniquement)

1. Copier `terraform.tfvars.example` (à créer) ou passer les variables sensibles en ligne de commande. Ex :

```hcl
aws_region  = "eu-west-1"
ssh_key_name = "kauri-demo-key"
budget_notification_emails = ["ops@example.com"]
ssm_parameters = {
  "OPENAI_API_KEY" = {
    value = "replace-me"
  }
}
```

2. Initialiser et vérifier le plan **sans appliquer** :

```bash
cd infrastructure/aws/kauri
terraform init
terraform validate
terraform plan -var-file="terraform.tfvars"
```

3. Quand vous serez prêt à lancer les démos, appliquez le plan puis connectez-vous via l’EIP fourni (`ssh ubuntu@<ip>`). Tant que vous n’exécutez pas `terraform apply`, aucune ressource n’est créée.

## Étapes opérationnelles après déploiement

1. **Installer Docker** + `docker compose` sur l’instance (script cloud-init ou Ansible).  
2. **Monter les volumes** : `/data/postgres`, `/data/redis`, `/data/chroma` et `/opt/models` (bind mount EBS).  
3. **Synchroniser** les données :
   - `aws s3 sync base_connaissances/ s3://<bucket>/` (structure intacte).
   - `scp -r chroma_db ubuntu@<ip>:/data/chroma/` puis `docker compose` pour la monter.  
4. **Déployer** les images depuis ECR ou build sur place, puis `docker compose up -d`.  
5. Configurer Cloudflare pour pointer le sous-domaine vers l’EIP et activer le mode proxy.

## Notes

- `use_spot_instance` permet de basculer sur Spot si vous préférez optimiser encore le budget, mais l’architecture recommandée reste on-demand + scheduler.  
- Les expressions cron du scheduler sont configurées pour 07:00–21:00 CET (lun→ven). Adaptez `scheduler_*_expression` si vos démos sont moins fréquentes pour diminuer encore la facture.  
- Les budgets se basent sur les tags `Project=<project_name>` — gardez ce tag si vous ajoutez d’autres ressources (Snapshots, Lambda, etc.).  
- Les paramètres SSM n’ont pas de valeur par défaut (car sensibles). Fournissez-les via `-var-file` ou `TF_VAR_ssm_parameters` lorsque vous serez prêt.

## Next Steps

- Compléter `terraform.tfvars.example` (non versionné) avec les valeurs réelles.  
- Ajouter un script Ansible ou cloud-init pour installer Docker/Grafana agent automatiquement.  
- Brancher votre pipeline CI/CD afin de pousser les images dans ECR avant la première démo.  
- Tester `terraform plan` sur un environnement de sandbox pour valider les droits IAM avant le go-live.
