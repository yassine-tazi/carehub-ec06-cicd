# Protection de branche — preuve à fournir

Configuration à appliquer sur `main` :

- Require a pull request before merging ;
- au moins 1 approbation ;
- Require status checks to pass ;
- checks obligatoires : tests, precommit, compliance, secret-scan, trivy-fs ;
- Require branches to be up to date before merging ;
- désactiver le force-push ;
- désactiver la suppression de la branche protégée.

Ajouter dans `03_preuves_execution/` une capture anonymisée montrant la règle réellement active.
