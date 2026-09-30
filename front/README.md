# Frontend

## Développement hors Docker

Depuis `front/` :

```sh
npm ci
npm run dev
npm run build
```

Le build vérifie TypeScript et génère `dist/`.
Pour joindre Django localement, définir `API_PROXY_TARGET=http://localhost:8000`
dans l'environnement du serveur Vite ; dans Docker, la cible est `http://back:8000`.

`VITE_API_BASE_URL` définit la base publique de l'API, avec `/api` par défaut.
`VITE_USE_MOCKS=true` active les données de démonstration ; la production utilise `false`.
Aucun secret ne doit être placé dans une variable `VITE_*`, intégrée au JavaScript public.

La configuration Vercel est décrite dans [Déploiement](../docs/DEPLOYMENT.md).
