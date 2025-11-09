# KAURI – Notes de Déploiement (AWS)

Ce document rassemble toutes les étapes réalisées pour déployer KAURI sur AWS et les points importants à connaître avant de reprendre l’exploitation ou les évolutions du projet.

## 1. Infrastructure AWS

- **Terraform** : toutes les ressources vivent dans `infrastructure/aws/kauri`. Le dernier `terraform apply` (09/11/2025) crée :
  - VPC dédié (`10.42.0.0/20`), sous-réseau public `10.42.1.0/24`, IGW, route table.
  - Instance EC2 `m7i-flex.large` (ID `i-0f4e5290d3a801f3b`) avec EIP `52.18.6.235`. L’agent SSM est actif.
  - Security Group `kauri-demo-sg` : 22/80/443/3000 ouverts selon IP autorisées. Ports 3201/3202 temporairement exposés à `82.67.87.81/32` pour les tests.
  - IAM (role EC2 + inline policy S3/SSM/CloudWatch + instance profile).
  - Bucket S3 `kauri-demo-knowledge-qvv7v` (versionning, lifecycle, dossier `secrets/` pour `.env`).
  - SNS `kauri-alerts`, budgets globaux/taggués, alarmes CloudWatch CPU/Status, scheduler EventBridge (start 07h / stop 21h CET).
  - Paramètres SSM `/kauri/OPENAI_API_KEY` et `/kauri/DEEPSEEK_API_KEY`.

## 2. Provisionnement de l’instance

Toutes les commandes ont été exécutées via **AWS SSM** (voir historique des `send-command` si besoin) :

1. Installation Docker CE + compose plugin, AWS CLI, git.
2. Clonage du repo `https://github.com/henribesnard/kauri.git` dans `/home/ubuntu/kauri`.
3. Synchronisation du `.env` (copié sur S3 puis téléchargé côté EC2) et mise à jour pour inclure `GRAFANA_ADMIN_PASSWORD`.
4. Lancement des services Docker (`docker compose up -d postgres redis chromadb kauri_user_service kauri_chatbot_service kauri_frontend grafana`).
5. Exécution des migrations Alembic :
   - `kauri_chatbot_service` : `alembic upgrade head` (DB `kauri_chatbot`).
   - `kauri_user_service` : schéma déjà présent, donc `alembic stamp head` pour aligner la révision.
6. Mise en place de Grafana : reset du mot de passe admin via `grafana-cli admin reset-admin-password ChangeMe2024!`.
7. Ajout du service Grafana et de son volume dans `docker-compose.yml` (port 3000 interne, exposé partiellement via SG).
8. Health-checks vérifiés : `curl http://localhost:3201/api/v1/health`, `curl http://localhost:3202/api/v1/health`, `curl -I http://localhost`.
9. Frontend reconstruit (`docker compose build kauri_frontend`) et healthcheck modifié pour pointer `127.0.0.1`.
10. Ports 3201/3202 temporairement ouverts sur le Security Group pour permettre les tests Postman/Bruno depuis `82.67.87.81`.

## 3. Services disponibles

| Service                  | URL/Port                                              | Notes |
|--------------------------|-------------------------------------------------------|-------|
| Frontend (NGINX)         | `http://52.18.6.235` (port 80)                        | Sert la SPA buildée. Healthcheck OK. |
| User Service (FastAPI)   | `http://52.18.6.235:3201`                             | Swagger disponible via `/api/v1/docs`. |
| Chatbot Service (FastAPI)| `http://52.18.6.235:3202`                             | Swagger via `/api/v1/docs`. |
| ChromaDB                 | `http://52.18.6.235:3104` (non exposé publiquement)   | Volume `kauri_chromadb_data`. En attente de l’import final. |
| Postgres                 | `localhost:3100` sur l’EC2                            | Deux bases : `kauri_users`, `kauri_chatbot`. |
| Redis                    | `localhost:3103`                                      | Mot de passe depuis `.env`. |
| Grafana                  | `http://52.18.6.235:3000`                             | Login `admin / ChangeMe2024!`. Aucun dashboard préconfiguré. |

> ⚠️ Les ports 3201/3202 sont ouverts uniquement pour l’IP `82.67.87.81`. Revenir au verrouillage initial dès que les tests sont terminés (`aws ec2 revoke-security-group-ingress ...`).

## 4. Points à finaliser

- **Cloudflare / DNS / TLS** : en attente d’un sous-domaine et d’un token DNS (gratuit). Dès que les infos sont fournies, configurer l’enregistrement, activer le proxy et ajuster `FRONTEND_URL`, `BACKEND_URL`, `CORS_ORIGINS` + URI OAuth Google.
- **Import Chroma** : l’ingestion se termine en local. Il faudra archiver le volume (`tar -czf chroma_prod.tar.gz`), l’envoyer sur S3 (`s3://kauri-demo-knowledge-qvv7v/chroma/`) puis restaurer sur l’EC2 (`docker volume create kauri_chromadb_data && tar -xzf ...`). Relancer `chromadb` et `kauri_chatbot_service` ensuite.
- **Grafana dashboards** : aucun datasource n’est défini. Ajouter au minimum une datasource CloudWatch (ou installer Prometheus/cAdvisor si nécessaire). Changer le mot de passe admin dès la première connexion.
- **Cloudflare tunnel** (optionnel) : si aucun domaine n’est fourni, on peut utiliser `cloudflared` pour générer une URL `*.trycloudflare.com`, mais elle changera à chaque redémarrage et doit tourner en permanence.
- **Documentation OAuth** : mettre à jour la console Google avec la nouvelle URI `https://<domaine>/api/v1/oauth/callback/google` dès que le DNS est en place.

## 5. Commandes utiles

- **Voir l’état des conteneurs** : `aws ssm send-command --document-name AWS-RunShellScript --parameters commands="cd /home/ubuntu/kauri && docker compose ps" ...`
- **Consulter les logs d’un service** : `docker logs -f kauri_user_service` (via SSM).
- **Redéployer** : `docker compose pull && docker compose up -d` après un `git fetch && git reset --hard origin/main`.
- **Sauvegarder le `.env`** : `aws s3 cp /home/ubuntu/kauri/.env s3://kauri-demo-knowledge-qvv7v/secrets/kauri.env` (ne laisser le fichier sur S3 que temporairement).
- **Reset Grafana** : `docker exec kauri_grafana grafana-cli admin reset-admin-password <mdp>`.

## 6. Check-list reprise / incident

1. Vérifier l’état EC2 (`aws ec2 describe-instance-status ...`).
2. Si l’instance est stoppée par le scheduler, la démarrer (`aws ec2 start-instances`).
3. Tester l’accès SSM (`aws ssm describe-instance-information` → `Online`).
4. `docker compose ps` pour s’assurer que tous les services sont `Up (healthy)`.
5. Vérifier `curl http://localhost:3201/api/v1/health`, `curl http://localhost:3202/api/v1/health`, `curl -I http://localhost`.
6. En cas de problème DB, consulter `docker logs kauri_postgres` et vérifier les volumes `/var/lib/docker/volumes/kauri_postgres_data/_data`.
7. Contacter l’équipe ops avant toute modification Terraform (risque de recréer l’EC2).

---
Ces notes peuvent servir de référence pour tout développeur amené à poursuivre le déploiement ou l’exploitation de KAURI sur AWS. Mettre à jour ce fichier à chaque itération majeure (nouvelles ressources, changement de DNS, etc.).
