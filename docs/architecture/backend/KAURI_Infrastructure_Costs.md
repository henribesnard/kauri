# KAURI - Estimation des Coûts Infrastructure

> **Document de référence pour les coûts d'infrastructure**
> **Date**: 2025-11-04
> **Version**: 1.0
> **Statut**: Estimations basées sur tarifs publics (à valider avec quotes)

---

## 📋 Table des Matières

1. [Vue d'Ensemble](#1-vue-densemble)
2. [Coûts Infrastructure Cloud](#2-coûts-infrastructure-cloud)
3. [Coûts Services Managés](#3-coûts-services-managés)
4. [Coûts Développement et Personnel](#4-coûts-développement-et-personnel)
5. [Scénarios de Coûts](#5-scénarios-de-coûts)
6. [Optimisations Possibles](#6-optimisations-possibles)
7. [Recommandations](#7-recommandations)

---

## 1. Vue d'Ensemble

### 1.1 Périmètre

Cette estimation couvre l'infrastructure nécessaire pour :
- **3 microservices backend** (Chatbot API, RAG Engine, Knowledge Base)
- **1 application frontend** (React SPA)
- **Bases de données** (PostgreSQL, Vector DB, Redis)
- **Message Bus** (Kafka)
- **Monitoring** (ELK, Prometheus, Grafana, Jaeger)
- **CI/CD** (GitHub Actions, Container Registry)

### 1.2 Hypothèses

- **Charge** : 1000-5000 utilisateurs actifs
- **Trafic** : 10-100 requêtes/seconde
- **Disponibilité** : 99.9% (SLA)
- **Région** : Europe de l'Ouest (pour GDPR/OHADA)
- **Environnements** : Production + Staging

---

## 2. Coûts Infrastructure Cloud

### 2.1 Kubernetes (EKS/GKE/AKS)

#### AWS EKS (Elastic Kubernetes Service)

| Composant | Spec | Coût Mensuel |
|-----------|------|--------------|
| **Control Plane** | Cluster managé | $73/mois |
| **Worker Nodes** | 3x t3.large (2 vCPU, 8GB RAM) | $150/mois |
| **Load Balancer** | Network Load Balancer | $25/mois |
| **EBS Storage** | 100 GB SSD (gp3) | $8/mois |
| **Data Transfer** | ~500 GB/mois | $45/mois |
| **Total EKS** | | **~$301/mois** |

#### GCP GKE (Google Kubernetes Engine)

| Composant | Spec | Coût Mensuel |
|-----------|------|--------------|
| **Control Plane** | Standard (gratuit <1000 nodes) | $0/mois |
| **Worker Nodes** | 3x e2-standard-2 (2 vCPU, 8GB RAM) | $130/mois |
| **Load Balancer** | HTTP(S) Load Balancer | $18/mois |
| **Persistent Disk** | 100 GB SSD | $17/mois |
| **Egress Traffic** | ~500 GB/mois | $50/mois |
| **Total GKE** | | **~$215/mois** |

**Recommandation** : GKE pour le coût (−$86/mois vs EKS)

---

### 2.2 Base de Données PostgreSQL

#### AWS RDS PostgreSQL

| Configuration | Spec | Coût Mensuel |
|---------------|------|--------------|
| **Instance Type** | db.t3.medium (2 vCPU, 4GB RAM) | $62/mois |
| **Multi-AZ** | Réplication automatique | +$62/mois |
| **Storage** | 100 GB SSD (gp3) | $12/mois |
| **Backup** | 7 jours automatique | Inclus |
| **Total RDS** | | **~$136/mois** |

#### GCP Cloud SQL PostgreSQL

| Configuration | Spec | Coût Mensuel |
|---------------|------|--------------|
| **Instance Type** | db-custom-2-7680 (2 vCPU, 7.5GB RAM) | $90/mois |
| **High Availability** | Réplication régionale | +$90/mois |
| **Storage** | 100 GB SSD | $17/mois |
| **Backup** | 7 jours automatique | Inclus |
| **Total Cloud SQL** | | **~$197/mois** |

#### Managed PostgreSQL alternatifs

| Service | Spec | Coût Mensuel |
|---------|------|--------------|
| **Supabase** (managed) | 8 GB RAM, 50 GB storage | $25/mois |
| **Neon** (serverless) | 4 GB RAM, auto-scale | $19/mois |
| **Railway** | 8 GB RAM, 100 GB storage | $20/mois |

**Recommandation** :
- **Production critique** : AWS RDS ($136/mois) - fiabilité éprouvée
- **Budget serré** : Supabase ($25/mois) - bon rapport qualité/prix

---

### 2.3 Vector Database (Embeddings)

#### Pinecone (Managed Cloud)

| Tier | Spec | Coût Mensuel |
|------|------|--------------|
| **Starter** | 1 pod, 1M vecteurs, 100 req/s | $70/mois |
| **Standard** | 1 pod, 5M vecteurs, 200 req/s | $150/mois |
| **Enterprise** | Custom, SLA 99.9% | $500+/mois |

**Pour KAURI** : Starter tier ($70/mois) suffit pour MVP

#### Alternatives

| Service | Spec | Coût Mensuel |
|---------|------|--------------|
| **Qdrant Cloud** | 1 node, 1M vecteurs | $25/mois |
| **Weaviate Cloud** | 1 node, 1M vecteurs | $60/mois |
| **Milvus (self-hosted)** | Sur K8s, coût infra | ~$50/mois |

**Recommandation** :
- **Simplicité** : Pinecone ($70/mois) - zero ops
- **Économie** : Qdrant Cloud ($25/mois) - bon compromis
- **Contrôle** : Milvus self-hosted ($50/mois infra) - flexibilité max

---

### 2.4 Cache Redis

#### AWS ElastiCache

| Configuration | Spec | Coût Mensuel |
|---------------|------|--------------|
| **Instance Type** | cache.t3.medium (2 vCPU, 3.09GB RAM) | $43/mois |
| **Multi-AZ** | 1 replica | +$43/mois |
| **Total ElastiCache** | | **~$86/mois** |

#### GCP Memorystore

| Configuration | Spec | Coût Mensuel |
|---------------|------|--------------|
| **Basic Tier** | M2 (4 GB RAM) | $50/mois |
| **Standard Tier** | M2 (4 GB RAM) + HA | $100/mois |
| **Total Memorystore** | | **~$100/mois** |

#### Alternatives

| Service | Spec | Coût Mensuel |
|---------|------|--------------|
| **Upstash Redis** | Serverless, 500K req/mois | $0 (free tier) |
| **Redis Cloud** | 500 MB RAM | $5/mois |
| **Redis self-hosted** | Sur K8s | Inclus dans K8s |

**Recommandation** :
- **Production** : AWS ElastiCache ($86/mois) - fiabilité
- **MVP/Staging** : Upstash gratuit ou Redis Cloud ($5/mois)

---

### 2.5 Message Bus (Kafka)

#### AWS MSK (Managed Streaming for Kafka)

| Configuration | Spec | Coût Mensuel |
|---------------|------|--------------|
| **2 brokers** | kafka.t3.small (2 vCPU, 2GB RAM each) | $87/mois |
| **Storage** | 100 GB per broker | $20/mois |
| **Total MSK** | | **~$107/mois** |

#### Confluent Cloud (Kafka as a Service)

| Tier | Spec | Coût Mensuel |
|------|------|--------------|
| **Basic** | 1 cluster, shared | $0 + usage |
| **Standard** | Dedicated, 99.95% SLA | $600/mois |
| **Usage** | $0.11/GB ingress + $0.09/GB egress | ~$50/mois |

**Pour KAURI** : Basic + usage = $50/mois

#### Alternatives

| Service | Spec | Coût Mensuel |
|---------|------|--------------|
| **RabbitMQ (self-hosted)** | Sur K8s | Inclus dans K8s |
| **Redis Streams** | Via Redis existant | $0 (déjà payé) |
| **NATS** (self-hosted) | Sur K8s | Inclus dans K8s |

**Recommandation** :
- **Event-driven important** : Confluent Cloud Basic ($50/mois)
- **Budget limité** : Redis Streams ($0) ou RabbitMQ self-hosted

---

## 3. Coûts Services Managés

### 3.1 Monitoring et Observabilité

#### ELK Stack (Elastic Cloud)

| Tier | Spec | Coût Mensuel |
|------|------|--------------|
| **Standard** | 4 GB RAM, 30 jours retention | $95/mois |
| **Gold** | 8 GB RAM, HA, SAML auth | $200/mois |

#### Alternatives Open Source (Self-Hosted)

| Service | Spec | Coût Mensuel |
|---------|------|--------------|
| **ELK sur K8s** | 2 nodes, 8 GB RAM total | ~$50/mois (infra) |
| **Loki + Grafana** | Léger, storage S3 | ~$30/mois |
| **Datadog** | APM + logs + metrics | $15/host = $45/mois |

**Recommandation** :
- **Production** : Elastic Cloud Standard ($95/mois) - complet
- **Budget serré** : Loki + Grafana ($30/mois) - efficace

---

#### Prometheus + Grafana

| Déploiement | Spec | Coût Mensuel |
|-------------|------|--------------|
| **Self-hosted sur K8s** | Inclus dans cluster | $0 (déjà payé) |
| **Grafana Cloud** | Free tier (10K séries) | $0 |
| **Grafana Cloud Pro** | 50K séries, alerting | $49/mois |

**Recommandation** : Grafana Cloud Free tier ($0)

---

#### Distributed Tracing (Jaeger)

| Déploiement | Spec | Coût Mensuel |
|-------------|------|--------------|
| **Jaeger sur K8s** | Self-hosted | $0 (déjà payé) |
| **New Relic** | APM + tracing | $99/mois |
| **Datadog APM** | Inclus dans plan | Voir ci-dessus |

**Recommandation** : Jaeger self-hosted ($0)

---

### 3.2 CI/CD et Registry

#### GitHub Actions

| Usage | Spec | Coût Mensuel |
|-------|------|--------------|
| **Free tier** | 2000 minutes/mois (repo public) | $0 |
| **Team** | 3000 minutes + storage | $4/user = $40/mois |
| **Usage additionnel** | $0.008/minute Linux | ~$20/mois |

**Recommandation** : GitHub Free + quelques minutes payées ($10-20/mois)

---

#### Container Registry

| Service | Spec | Coût Mensuel |
|---------|------|--------------|
| **Docker Hub** | Unlimited public, 1 private repo | $0 |
| **AWS ECR** | 10 GB storage, 50 GB transfer | $5/mois |
| **GCP Artifact Registry** | 10 GB storage | $2/mois |
| **GitHub Container Registry** | Illimité (repo public) | $0 |

**Recommandation** : GitHub Container Registry ($0)

---

### 3.3 Object Storage (Documents)

#### AWS S3

| Usage | Spec | Coût Mensuel |
|-------|------|--------------|
| **Standard Storage** | 100 GB | $2.30/mois |
| **Requests** | 1M PUT, 10M GET | $5/mois |
| **Data Transfer** | 100 GB out | $9/mois |
| **Total S3** | | **~$16/mois** |

#### Alternatives

| Service | Spec | Coût Mensuel |
|---------|------|--------------|
| **GCP Cloud Storage** | 100 GB, multi-region | $20/mois |
| **Cloudflare R2** | 100 GB, 0€ egress | $1.50/mois |
| **Backblaze B2** | 100 GB, free 3x download | $6/mois |

**Recommandation** : Cloudflare R2 ($1.50/mois) - zéro frais de sortie !

---

## 4. Coûts Développement et Personnel

### 4.1 One-Time (Migration/Setup)

| Poste | Durée | Coût |
|-------|-------|------|
| **2 Développeurs Backend** | 12 semaines @ $5000/mois | $60,000 |
| **1 DevOps Engineer** | 4 semaines @ $6000/mois | $24,000 |
| **1 Frontend Developer** | 8 semaines @ $4500/mois | $36,000 |
| **Architecture Review** | 1 semaine @ $8000/sem | $8,000 |
| **Total One-Time** | | **$128,000** |

---

### 4.2 Récurrent (Maintenance)

| Poste | Allocation | Coût Mensuel |
|-------|------------|--------------|
| **Backend Engineer** | 50% FTE | $2,500/mois |
| **DevOps Engineer** | 25% FTE | $1,500/mois |
| **Frontend Engineer** | 25% FTE | $1,125/mois |
| **Total Récurrent** | | **$5,125/mois** |

---

## 5. Scénarios de Coûts

### 5.1 Scénario MVP (Budget Minimal)

**Objectif** : Lancer rapidement avec coûts minimum

| Service | Choix | Coût Mensuel |
|---------|-------|--------------|
| **Kubernetes** | GKE Autopilot (2 nodes) | $120/mois |
| **PostgreSQL** | Supabase managed | $25/mois |
| **Vector DB** | Qdrant Cloud | $25/mois |
| **Redis** | Upstash free tier | $0/mois |
| **Message Bus** | Redis Streams (no Kafka) | $0/mois |
| **Monitoring** | Loki + Grafana Cloud free | $0/mois |
| **Storage** | Cloudflare R2 | $2/mois |
| **CI/CD** | GitHub Actions free | $0/mois |
| **Total Infrastructure** | | **$172/mois** |
| **Personnel (25% DevOps)** | | $1,500/mois |
| **Total MVP** | | **~$175/mois infra + $1.5K personnel** |

**Capacité** : 500-1000 utilisateurs, 10-20 req/s

---

### 5.2 Scénario Production (Recommandé)

**Objectif** : Production-ready avec HA et scalabilité

| Service | Choix | Coût Mensuel |
|---------|-------|--------------|
| **Kubernetes** | GKE Standard (3 nodes) | $215/mois |
| **PostgreSQL** | AWS RDS Multi-AZ | $136/mois |
| **Vector DB** | Pinecone Starter | $70/mois |
| **Redis** | AWS ElastiCache Multi-AZ | $86/mois |
| **Message Bus** | Confluent Cloud Basic | $50/mois |
| **Monitoring** | Elastic Cloud Standard | $95/mois |
| **Storage** | AWS S3 | $16/mois |
| **CI/CD** | GitHub Actions | $20/mois |
| **Total Infrastructure** | | **$688/mois** |
| **Personnel (75% temps)** | | $5,125/mois |
| **Total Production** | | **~$690/mois infra + $5.1K personnel** |

**Capacité** : 5000-10000 utilisateurs, 100 req/s, 99.9% uptime

---

### 5.3 Scénario Enterprise (Haute Disponibilité)

**Objectif** : Multi-région, SLA 99.95%

| Service | Choix | Coût Mensuel |
|---------|-------|--------------|
| **Kubernetes** | EKS Multi-AZ (6 nodes) | $600/mois |
| **PostgreSQL** | RDS Aurora Global Database | $400/mois |
| **Vector DB** | Pinecone Enterprise | $500/mois |
| **Redis** | ElastiCache Cluster Mode | $300/mois |
| **Message Bus** | MSK Multi-AZ | $200/mois |
| **Monitoring** | Datadog Pro | $150/mois |
| **CDN** | CloudFront | $100/mois |
| **WAF** | AWS WAF + Shield | $50/mois |
| **Total Infrastructure** | | **$2,300/mois** |
| **Personnel (2 DevOps FTE)** | | $12,000/mois |
| **Total Enterprise** | | **~$2.3K infra + $12K personnel** |

**Capacité** : 50K+ utilisateurs, 1000+ req/s, multi-région

---

## 6. Optimisations Possibles

### 6.1 Réduction des Coûts Infrastructure

1. **Utiliser Reserved Instances** (AWS/GCP)
   - Économies : 30-40% sur compute
   - Exemple : K8s nodes @ -$60/mois

2. **Spot Instances** pour jobs non-critiques
   - Économies : 60-80% sur compute
   - Exemple : Celery workers @ -$40/mois

3. **Auto-scaling agressif**
   - Scale down hors heures de pointe
   - Économies : 20-30% sur compute
   - Exemple : -$50/mois la nuit/weekend

4. **Consolidation des services**
   - Redis Streams au lieu de Kafka → -$50/mois
   - Self-host monitoring → -$95/mois

5. **Optimisation stockage**
   - Cloudflare R2 au lieu S3 → -$14/mois
   - Lifecycle policies (archives) → -$5/mois

**Total économies potentielles** : **$200-300/mois**

---

### 6.2 Alternatives Open Source

| Service Managé | Alternative Open Source | Économie |
|----------------|-------------------------|----------|
| Pinecone ($70) | Milvus self-hosted | -$70/mois |
| Elastic Cloud ($95) | ELK sur K8s | -$95/mois |
| AWS MSK ($107) | RabbitMQ | -$107/mois |
| ElastiCache ($86) | Redis sur K8s | -$86/mois |

**Économies totales** : **−$358/mois**

**Trade-off** : +50% effort DevOps (monitoring, maintenance, backup)

---

## 7. Recommandations

### 7.1 Recommandation Globale

Pour KAURI, nous recommandons le **Scénario Production** :

**Coûts** :
- Infrastructure : **~$690/mois**
- Personnel : **~$5,125/mois**
- **Total : ~$5,815/mois**

**Justification** :
- ✅ Production-ready avec HA
- ✅ Scalable jusqu'à 10K utilisateurs
- ✅ SLA 99.9%
- ✅ Backup automatique
- ✅ Monitoring complet

---

### 7.2 Roadmap Budgétaire

#### Phase 1 : MVP (Mois 1-3)
- Scénario MVP : **$175/mois infra**
- Développement : **$128K one-time**
- Personnel : **$1,500/mois**

#### Phase 2 : Production (Mois 4-6)
- Migration vers Scénario Production
- Infra : **$690/mois**
- Personnel : **$5,125/mois**

#### Phase 3 : Optimisation (Mois 7-12)
- Optimisations appliquées : **-$200/mois**
- Infra : **$490/mois**
- Personnel : **$5,125/mois**

---

### 7.3 Validation et Prochaines Étapes

**À faire avant engagement** :

1. **Demander des quotes officiels**
   - AWS : RDS, ElastiCache, EKS
   - GCP : Cloud SQL, GKE
   - Pinecone : Starter tier
   - Confluent : Basic tier

2. **POC sur Free Tiers**
   - Valider architecture sur gratuits
   - Mesurer usage réel (req/s, storage)
   - Ajuster estimations

3. **Négocier avec vendors**
   - Startup credits (AWS, GCP)
   - Discounts pour engagement 1 an
   - Possibilité réduction 15-20%

4. **Comparer alternatives**
   - Tester Qdrant vs Pinecone
   - Benchmark RDS vs Supabase
   - Évaluer Loki vs Elastic

---

## 📊 Tableau Récapitulatif

| Scénario | Infra/mois | Personnel/mois | Total/mois | Capacité |
|----------|------------|----------------|------------|----------|
| **MVP** | $175 | $1,500 | **$1,675** | 1K users, 20 req/s |
| **Production** ⭐ | $690 | $5,125 | **$5,815** | 10K users, 100 req/s |
| **Enterprise** | $2,300 | $12,000 | **$14,300** | 50K+ users, 1K req/s |

---

**Recommandation finale** : **Scénario Production** à **~$5,815/mois**

**Avec optimisations** : **~$5,615/mois** (−$200)

**Avec Reserved Instances (1 an)** : **~$5,200/mois** (−$615)

---

**Document créé par** : Architecture Team
**Date** : 2025-11-04
**Version** : 1.0
**Statut** : Estimations - À valider avec quotes officiels
**Prochaine revue** : 2025-11-15
