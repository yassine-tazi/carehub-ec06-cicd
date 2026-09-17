# CareHub — EC06 CI/CD

> Rendu anonyme — aucune donnée personnelle, aucun secret réel et aucune URL de dépôt personnelle ne doivent être ajoutés à cette archive.

## 1. Objet

Cette solution industrialise le déploiement du portail de prise de rendez-vous CareHub avec :

- une application conteneurisée et configurable sans valeur d'environnement figée dans l'image ;
- une base PostgreSQL persistante ;
- des contrôles de santé et des dépendances basées sur l'état de santé ;
- des limites CPU/RAM explicites ;
- une chaîne GitHub Actions couvrant tests, lint, sécurité, conformité, build, publication et déploiement ;
- un contrôle de conformité bloquant sur les fichiers d'infrastructure ;
- une gestion des secrets sans valeur sensible dans le dépôt, les images ou les journaux ;
- une stratégie de mise à l'échelle et de retour arrière ;
- une supervision Prometheus/Grafana et un tableau DORA à alimenter avec les exécutions réelles.

## 2. Démarrage en une commande

Prérequis : Docker Engine et Docker Compose v2.

```bash
cp 02_conteneurisation/.env.dev.example 02_conteneurisation/.env.dev
cd 02_conteneurisation
docker compose --env-file .env.dev up -d --build
```

Vérification :

```bash
curl -fsS http://localhost:8080/health
```

Arrêt :

```bash
docker compose --env-file .env.dev down
```

### Démo locale rapide sous Windows

Depuis la racine du dossier :

```powershell
powershell -ExecutionPolicy Bypass -File .\01_pipeline\scripts\demo_local_windows.ps1
```

Le script démarre CareHub, teste la base, crée un rendez-vous, affiche les ressources, passe à 3 réplicas et montre les instances servies par Nginx.

### Dépôt GitHub d'exécution

Les workflows sont livrés dans `01_pipeline/.github/workflows/` car c'est l'arborescence demandée dans l'archive d'examen. Pour les exécuter sur GitHub, ils doivent aussi être placés à la racine du dépôt sous `.github/workflows/`. Le script `01_pipeline/scripts/prepare_execution_repo.ps1` prépare automatiquement un dossier de dépôt d'exécution avec cette structure, sans modifier l'arborescence du ZIP final.

## 3. Environnements dev / recette / production

Le même `Dockerfile` et le même `compose.yml` sont utilisés dans les trois environnements. Seuls les paramètres externes changent :

| Paramètre | Dev | Recette | Production |
|---|---|---|---|
| `APP_ENV` | `development` | `staging` | `production` |
| `APP_IMAGE` | build local | image immuable du registre | image immuable du registre |
| `APP_PORT` | 8080 | 8080 | 8080 |
| `APP_REPLICAS` | 1 | 2 | 3 minimum |
| Secrets DB | local non committé | secret CI/CD / hôte | secret CI/CD / hôte |

Aucune valeur propre à un environnement n'est copiée dans l'image. Les exemples `.env.*.example` ne contiennent que des espaces réservés.

## 4. Architecture

```text
Utilisateur
    |
    v
Nginx reverse proxy :8080
    |
    +------> app:8000  (1 à N réplicas)
                  |
                  v
             PostgreSQL
             volume nommé

Git commit / PR
    |
    +--> tests + couverture >= 70 %
    +--> lint / pre-commit
    +--> gitleaks + Trivy
    +--> contrôle conformité personnalisé (bloquant)
    +--> build image + SBOM/provenance
    +--> scan image HIGH/CRITICAL
    +--> push GHCR + signature cosign OIDC
    +--> déploiement VPS + smoke test
    +--> rollback automatique si smoke test KO
```

## 5. Partie A — chaîne remobilisée

### Protections prévues

- branche `main` protégée : PR obligatoire, checks CI obligatoires, branche à jour avant fusion ;
- matrice Python 3.10 / 3.11 / 3.12 ;
- couverture minimale : 70 % ;
- hooks `pre-commit` : hygiène fichiers, Ruff, détection de clé privée ;
- détection de secrets avec Gitleaks ;
- scan Trivy du système de fichiers puis de l'image ;
- image Docker multi-stage, exécution non-root, `HEALTHCHECK` ;
- SBOM/provenance produits lors du build ;
- signature d'image avec Cosign en OIDC keyless ;
- déploiement sur runner self-hosted étiqueté `linux,docker` ;
- rollback automatique vers la dernière image saine si le smoke test échoue.

> La capture de la protection de branche doit être ajoutée dans `03_preuves_execution/` après vérification dans les paramètres du dépôt. Une protection uniquement décrite ici n'est pas considérée comme une preuve d'exécution.

### Deux faiblesses identifiées

1. **Hôte VPS unique** : la réplication applicative protège contre la panne d'un conteneur mais pas contre la perte complète du VPS. Une évolution vers deux nœuds ou un orchestrateur multi-hôte supprimerait ce point de défaillance unique.
2. **Runner self-hosted avec accès Docker** : le runner de déploiement possède des droits puissants sur l'hôte. Le risque est réduit par un compte dédié, des labels de runner, des jobs limités à la branche protégée, un nettoyage après exécution et des permissions GitHub minimales. À terme, un runner éphémère isolé serait préférable.

## 6. Partie B — correspondance avec la grille

| Critère | Réponse apportée | Preuve attendue |
|---|---|---|
| C12.1 | même image et même composition, configuration externalisée | `compose.yml`, `.env.*.example`, capture des 3 environnements |
| C13.1 | limites CPU/RAM sur app, DB et proxy | `compose.yml`, `docker stats` |
| C13.2 | réplication de l'app derrière Nginx, minimum 2 réplicas avant mise à jour, smoke test et rollback | capture `docker compose ps`, test pendant mise à jour |
| C14.1 | `check_compliance.py` bloque une configuration non conforme et indique la règle violée | logs échec + succès fournis dans `03_preuves_execution/` |
| C14.2 | secrets GitHub/variables d'hôte, injection à l'exécution, aucune valeur réelle dans l'archive | `04_securite_secrets.md` + paramètres du dépôt anonymisés |

## 7. Ressources et charge retenue

Hypothèse de dimensionnement explicitement posée pour l'épreuve : portail de rendez-vous avec une charge moyenne faible à modérée et des pointes lors de l'ouverture des créneaux. Le point de départ retenu est :

- `app` : 0,50 CPU / 384 MiB par réplica ;
- `db` : 0,75 CPU / 768 MiB ;
- `proxy` : 0,25 CPU / 128 MiB.

La production démarre avec **3 réplicas applicatifs**. La règle opérationnelle est : augmenter d'un réplica lorsque la charge CPU applicative dépasse 70 % pendant 5 minutes ou lorsque la latence p95 dépasse 500 ms pendant 5 minutes ; réduire après 15 minutes sous 35 %, sans descendre sous 2 réplicas en production. Sur Docker Compose, cette décision est exécutée par `docker compose up -d --scale app=N` et documentée ; l'autoscaling natif nécessiterait un orchestrateur dédié.

## 8. Mise à jour sans interruption et retour arrière

Avant une livraison en journée :

1. conserver au moins deux réplicas sains derrière Nginx ;
2. tirer l'image immuable identifiée par le SHA du commit ;
3. lancer/recréer les réplicas avec la nouvelle image ;
4. attendre les healthchecks ;
5. exécuter `curl -fsS /health` ;
6. en cas d'échec, relancer immédiatement la valeur `LAST_GOOD_IMAGE` enregistrée par le job de déploiement.

La limite est clairement documentée : Docker Compose sur un VPS n'offre pas les garanties de rolling update d'un orchestrateur comme Kubernetes/Swarm. Pour l'épreuve, la disponibilité est maintenue par plusieurs réplicas derrière le proxy et par le rollback automatisé ; pour une cible hospitalière haute disponibilité, le VPS unique doit être remplacé par une architecture multi-nœuds.

## 9. Preuves d'exécution

Les commandes et scénarios de preuve sont préparés dans `03_preuves_execution/`, mais les captures finales doivent provenir de vos exécutions réelles. Le scénario GitHub rouge/vert peut être déclenché sans casser la configuration réelle grâce à l'entrée `demo_failure` du workflow `Security and compliance`. Voir `03_preuves_execution/README.md`.

## 10. Déclaration obligatoire d'utilisation de l'IA

### Outil utilisé

- **ChatGPT — modèle GPT-5.6 Sol — interface Web**.

### Périmètre d'utilisation

L'IA a été utilisée pour assister la structuration du dossier EC06, proposer les fichiers Docker/Compose, les workflows GitHub Actions, le contrôle de conformité, la documentation de la gestion des secrets, la stratégie de mise à l'échelle/rollback et le squelette d'observabilité.

### Prompts majeurs / démarche de contexte

1. Analyse du sujet EC06 CareHub et transformation des exigences C12.1, C13.1, C13.2, C14.1 et C14.2 en fichiers livrables vérifiables.
2. Génération d'une chaîne CI/CD simple et complète : tests, lint, sécurité, conformité, build, scan, publication, signature, déploiement et rollback.
3. Vérification de l'anonymat et suppression de toute valeur sensible ; remplacement des informations d'infrastructure par des variables ou secrets.
4. Construction d'un contrôle personnalisé qui refuse les images `latest`, les services critiques sans healthcheck, les conteneurs privilégiés et les services sans limites de ressources.

### Audit des réponses IA

Les propositions ont été relues au regard des contraintes de l'épreuve. Les éléments conservés sont ceux qui respectent la reproductibilité, les tags d'images explicites, l'exécution non-root, les healthchecks, les volumes nommés, les limites de ressources, les secrets externalisés et les contrôles de sécurité bloquants. Les preuves dépendant d'un compte GitHub ou d'un VPS n'ont pas été inventées : les emplacements sont fournis pour y placer les captures et sorties obtenues réellement. La stratégie de mise à l'échelle précise également la limite de Docker Compose : l'absence d'autoscaling natif est assumée et documentée au lieu d'être présentée comme une capacité existante.
