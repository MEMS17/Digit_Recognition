import { useState } from 'react';
import { ApiUnavailableError, recognizeDigit, recognizeMail } from './api/recognitionApi';
import type { RecognitionResult } from './api/types';
import { DigitCanvas } from './components/DigitCanvas';
import { MailUpload } from './components/MailUpload';
import { PredictionResult } from './components/PredictionResult';

type RequestState = 'idle' | 'loading';

export default function App() {
  const [activeTool, setActiveTool] = useState<'mail' | 'digit'>('mail');
  const [digitImage, setDigitImage] = useState<Blob | null>(null);
  const [mailImage, setMailImage] = useState<File | null>(null);
  const [result, setResult] = useState<RecognitionResult | null>(null);
  const [requestState, setRequestState] = useState<RequestState>('idle');
  const [error, setError] = useState<string | null>(null);

  const startRequest = async () => {
    const source = activeTool === 'digit' ? digitImage : mailImage;
    if (!source) { setError(activeTool === 'digit' ? 'Dessinez un chiffre avant de lancer la lecture.' : 'Ajoutez une image de courrier avant de lancer la lecture.'); return; }
    setRequestState('loading'); setError(null); setResult(null);
    try { setResult(activeTool === 'digit' ? await recognizeDigit(source) : await recognizeMail(source)); }
    catch (requestError) { setError(requestError instanceof ApiUnavailableError ? 'Le service de reconnaissance est momentanément indisponible. Réessayez dans quelques instants.' : 'La lecture n’a pas pu être réalisée. Vérifiez le fichier puis réessayez.'); }
    finally { setRequestState('idle'); }
  };
  const switchTool = (tool: 'mail' | 'digit') => { setActiveTool(tool); setResult(null); setError(null); };

  return <main className="app-shell">
    <header className="app-header">
      <div className="header-inner">
        <a className="brand" href="#workspace" aria-label="Centre de tri, poste de lecture"><span className="brand-mark">PT</span><span>Centre de tri postal</span></a>
        <div className="header-context"><span>Poste de lecture</span><span className="context-divider" /><strong>Opérateur</strong><span className="service-status"><i /> Service de démonstration</span></div>
      </div>
    </header>
    <div className="content-shell" id="workspace">
      <div className="page-title"><div><p className="breadcrumb">Opérations / Lecture assistée</p><h1>Lecture de codes postaux</h1><p>Importer un courrier ou tester la reconnaissance d’un chiffre manuscrit.</p></div><div className="page-status"><span className="status-dot" /> Prêt à traiter</div></div>
      <section className="workspace" aria-live="polite">
        <div className="work-panel panel">
          <div className="panel-heading"><div><h2>Entrée</h2><p>{activeTool === 'mail' ? 'Joindre une image de courrier pour lancer l’analyse.' : 'Tracer un chiffre pour tester la reconnaissance.'}</p></div>{result && <span className="step">NOUVELLE LECTURE</span>}</div>
          <nav className="mode-tabs" aria-label="Type de saisie"><button className={activeTool === 'mail' ? 'active' : ''} onClick={() => switchTool('mail')}>Image de courrier</button><button className={activeTool === 'digit' ? 'active' : ''} onClick={() => switchTool('digit')}>Dessin d’un chiffre</button></nav>
          {activeTool === 'mail' ? <MailUpload onFileChange={(file) => { setMailImage(file); setError(null); }} /> : <DigitCanvas onDrawingChange={(image) => { setDigitImage(image); setError(null); }} />}
          {error && <div className="alert" role="alert"><strong>Lecture non lancée</strong>{error}</div>}
          <div className="action-row"><button className="primary-button" onClick={startRequest} disabled={requestState === 'loading'}>{requestState === 'loading' ? <><span className="spinner" /> Analyse en cours</> : 'Lancer l’analyse'}</button><p className="hint">{activeTool === 'mail' ? 'Formats acceptés : PNG, JPG, WEBP · 10 Mo max.' : 'Tracez un seul chiffre, centré dans la zone.'}</p></div>
        </div>
        <PredictionResult result={result} loading={requestState === 'loading'} onCorrection={setResult} />
      </section>
      <section className="recent-panel panel" aria-labelledby="recent-title"><div className="panel-heading"><div><h2 id="recent-title">Activité récente</h2><p>Les lectures validées seront disponibles ici.</p></div></div><div className="empty-history"><span>—</span><p>Aucune lecture enregistrée dans cette session.</p><small>Les résultats s’affichent dans le panneau de droite avant validation.</small></div></section>
    </div>
  </main>;
}
