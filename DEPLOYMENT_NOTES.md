# KAURI – Notes de déploiement AWS

Ce document résume toute l’infra préparée pour KAURI, comment accéder au serveur et les actions restantes.

## 1. Infrastructure

- **Terraform** dans `infrastructure/aws/kauri`. Le dernier `terraform apply` (09/11/2025) crée :
  - VPC `10.42.0.0/20`, sous-réseau public `10.42.1.0/24`, IGW, route table.
  - EC2 `m7i-flex.large` (ID `i-0f4e5290d3a801f3b`) avec EIP `52.18.6.235`. Agent SSM actif.
  - Security Group `kauri-demo-sg` : 22/80/443/3000 ouverts, 3201/3202 ouverts temporairement à `82.67.87.81/32`.
  - IAM role + policies SSM/S3/CloudWatch, instance profile.
  - Bucket S3 `kauri-demo-knowledge-qvv7v` (versioning + lifecycle) utilisé pour les dumps `.env` et la future base Chroma.
  - SNS `kauri-alerts`, budgets globaux + tag `Project=kauri`, alarmes CloudWatch (CPU + StatusCheck), scheduler EventBridge start 07h / stop 21h CET.
  - Paramètres SSM `/kauri/OPENAI_API_KEY` et `/kauri/DEEPSEEK_API_KEY`.

## 2. Provisionnement de l’EC2

Toutes les opérations ont été faites via **AWS SSM** :

1. Installation Docker CE + compose plugin, AWS CLI, git.
2. Clonage `https://github.com/henribesnard/kauri.git` dans `/home/ubuntu/kauri`.
3. Synchronisation du `.env` (stocké provisoirement sur S3) + ajout `GRAFANA_ADMIN_PASSWORD`.
4. `docker compose up -d postgres redis chromadb kauri_user_service kauri_chatbot_service kauri_frontend grafana`.
5. Migrations Alembic :  
   - Chatbot : `alembic upgrade head`.  
   - User : `alembic stamp head` (schéma déjà present).
6. Grafana : reset mot de passe `admin / ChangeMe2024!`.
7. Ajout du service Grafana dans `docker-compose.yml` + volume `grafana_data`.
8. Health-checks : `curl http://localhost:3201/api/v1/health`, `curl http://localhost:3202/api/v1/health`, `curl -I http://localhost`.
9. Frontend rebuild (`docker compose build kauri_frontend`) et healthcheck NGINX pointant sur `127.0.0.1`.
10. Ports 3201/3202 ouverts temporairement sur le SG pour les tests Postman/Bruno.

## 3. Services exposés

| Service | URL | Notes |
|---------|-----|-------|
| Frontend (NGINX) | `http://52.18.6.235` | SPA buildée. ⚠️ bug connu sur `/chat` si les bundles OAuth sont mis en cache (voir §7). |
| User service | `http://52.18.6.235:3201/api/v1` | Swagger `/api/v1/docs`. Port ouvert uniquement à l’IP `82.67.87.81/32`. |
| Chatbot service | `http://52.18.6.235:3202/api/v1` | Swagger `/api/v1/docs`. Même restriction. |
| ChromaDB | `http://52.18.6.235:3104` (interne) | Volume `kauri_chromadb_data` à importer. |
| Postgres | `localhost:3100` (via SSM) | Bases `kauri_users`, `kauri_chatbot`. |
| Redis | `localhost:3103` | Mot de passe `.env`. |
| Grafana | `http://52.18.6.235:3000` | Login `admin / ChangeMe2024!`. Aucun dashboard. |

> ⚠️ Revenir à un SG fermé (supprimer les règles sur 3201/3202) dès que les tests Postman sont terminés.

## 4. À terminer

- **Domaines/Cloudflare** : attendre la disponibilité du domaine (ex. `wezon.fr`). Étapes :
  1. Ajouter la zone dans Cloudflare ;
  2. Remplacer les nameservers Ionos par ceux fournis par Cloudflare ;
  3. Créer `app.wezon.fr` (ou autre) → A record vers `52.18.6.235` + proxy orange ;
  4. Mettre à jour `FRONTEND_URL`, `BACKEND_URL`, `CORS_ORIGINS`, Google OAuth et rebuild/deployer.
- **Base Chroma** : lorsque l’ingestion locale est finie, archiver `kauri_chromadb_data`, l’uploader sur S3 (`chroma/chroma_prod.tar.gz`), puis restaurer sur l’EC2 et redémarrer `chromadb` + `kauri_chatbot_service`.
- **Grafana** : ajouter une datasource (CloudWatch ou Prometheus) et changer le mot de passe admin à la première connexion.
- **Emails** : le service user génère les tokens mais ne peut pas envoyer d’e-mails (SMTP non configuré). Vérifications manuelles pour l’instant.

## 5. Connexion à l’instance et commandes utiles

- **Shell SSM** :
  ```bash
  aws ssm start-session \
    --target i-0f4e5290d3a801f3b \
    --region eu-west-1
  ```
- **Port forwarding SSM** (exposer l’API user sur ta machine) :
  ```bash
  aws ssm start-port-forwarding-session \
    --target i-0f4e5290d3a801f3b \
    --region eu-west-1 \
    --document-name AWS-StartPortForwardingSessionToRemoteHost \
    --parameters '{"host":["127.0.0.1"],"portNumber":["3201"],"localPortNumber":["13201"]}'
  ```
  → appeler ensuite `http://localhost:13201/api/v1/...`.
- **État des conteneurs** : `aws ssm send-command --document-name AWS-RunShellScript --parameters commands="cd /home/ubuntu/kauri && docker compose ps" ...`
- **Logs** : `docker logs -f <container>` depuis la session SSM.
- **Redéploiement** :
  ```bash
  git fetch origin
  git reset --hard origin/main
  docker compose build kauri_frontend
  docker compose up -d
  ```
- **Sauvegarde `.env`** : `aws s3 cp /home/ubuntu/kauri/.env s3://kauri-demo-knowledge-qvv7v/secrets/kauri.env` (ne pas laisser sur S3 plus que nécessaire).
- **Reset Grafana** : `docker exec kauri_grafana grafana-cli admin reset-admin-password <nouveau-mdp>`.

## 6. Check-list en cas d’incident

1. Vérifier l’état EC2 : `aws ec2 describe-instance-status --instance-ids i-0f4e5290d3a801f3b --region eu-west-1`.
2. Si le scheduler a arrêté la machine, `aws ec2 start-instances ...`.
3. Confirmer que l’agent SSM est `Online` (`aws ssm describe-instance-information`).
4. `docker compose ps` → tous les services doivent être `Up (healthy)`.
5. Health-checks rapides : `curl http://localhost:3201/api/v1/health`, `curl http://localhost:3202/api/v1/health`, `curl -I http://localhost`.
6. DB : `docker logs kauri_postgres` et inspection des volumes `/var/lib/docker/volumes/kauri_postgres_data/_data`.
7. Toute modification Terraform doit être validée (risque de recréer l’EC2).

## 7. Problèmes connus (11/11/2025)

1. **Frontend `/chat` → page blanche**  
   - Les bundles encore en cache rendent `OAuthButtons` alors que `VITE_ENABLE_OAUTH=false`. Comme l’endpoint `/api/v1/oauth/providers` retourne du HTML (providers non configurés), la SPA plante (`Cannot read properties of undefined`).  
   - Contournement : vider le cache navigateur ou forcer un rebuild complet (`docker compose build kauri_frontend && docker compose up -d`). Lorsque Google OAuth sera prêt (domaine HTTPS + secrets), remettre `VITE_ENABLE_OAUTH=true` et vérifier que `/api/v1/oauth/providers` renvoie du JSON avant de recompiler.
2. **Import Chroma** : pas encore réalisé. Toutes les réponses chatbot sont faites sans contexte. Prévoir le transfert de `kauri_chromadb_data`.
3. **Ports API filtrés** : seuls les IPs autorisées (actuellement `82.67.87.81/32`) peuvent appeler `:3201`/`:3202`. Ajouter votre IP au SG ou utiliser un tunnel SSM.
4. **Grafana** : pas de datasource ni TLS. Limité à l’IP autorisée mais à sécuriser/câbler avant démo.

---

Mettre à jour ce fichier dès qu’une action significative est réalisée (nouveau domaine, import Chroma, Cloudflare, etc.).
