export default function App() {
  return (
    <main>
      <p className="eyebrow">Projet annuel · Reconnaissance de chiffres</p>
      <h1>Lire les codes postaux manuscrits.</h1>
      <p className="intro">
        Une application pour identifier les codes postaux sur les courriers,
        avec une vérification humaine des lectures incertaines.
      </p>
      <section aria-labelledby="status-title">
        <span className="badge">Initialisation du projet</span>
        <h2 id="status-title">Le socle de l’application est prêt.</h2>
        <p>
          L’import d’un courrier et la reconnaissance seront ajoutés lors des prochaines étapes.
          Aucun modèle de reconnaissance n’est encore intégré.
        </p>
      </section>
    </main>
  );
}
