# Durcissement du runner self-hosted

Le runner de déploiement est dédié aux jobs de production et étiqueté `self-hosted, linux, docker`.

Mesures : compte système dédié, aucun usage interactif, accès entrant non requis, mises à jour régulières, permissions GitHub minimales, jobs de production limités à la branche protégée, environnement GitHub `production` avec approbation, nettoyage des espaces de travail et des images inutiles, journalisation des exécutions.

Le montage du socket Docker donne des privilèges élevés. Il est donc traité comme un risque connu. L'évolution recommandée est un runner éphémère dédié à chaque déploiement ou un mécanisme de déploiement distant avec permissions plus fines.
