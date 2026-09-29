# Frontend

Responsable : collaborateur — interface React, TypeScript et Vite.

Lancement recommandé depuis la racine du dépôt avec Docker Compose. Le serveur de développement écoute sur `0.0.0.0:5173`. Ce conteneur sert uniquement au développement ; la construction et le service de production seront préparés dans la phase de déploiement.

Les appels navigateur à `/api/` sont transmis au backend par le proxy Vite, sans réécriture de chemin. `API_PROXY_TARGET` vaut `http://back:8000` par défaut et se configure côté serveur, sans exposer de secret au navigateur. En dehors de Docker, utiliser `API_PROXY_TARGET=http://localhost:8000`.

Commandes : `npm ci`, `npm run dev`, `npm run build`. Le build vérifie TypeScript et génère `dist/`.

L’écran actuel est une page d’initialisation. Aucun OCR, modèle, import d’image ou endpoint de prédiction n’est implémenté. Les contrats API doivent être convenus avec le responsable backend avant d’intégrer les fonctionnalités.
