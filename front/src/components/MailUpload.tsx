import { useEffect, useState } from 'react';
interface Props { onFileChange: (file: File | null) => void; }
const ACCEPTED_TYPES = ['image/jpeg', 'image/png'];
export function MailUpload({ onFileChange }: Props) {
  const [file, setFile] = useState<File | null>(null); const [preview, setPreview] = useState<string | null>(null); const [message, setMessage] = useState<string | null>(null);
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);
  const selectFile = (selected: File | undefined) => { if (!selected) return; if (!ACCEPTED_TYPES.includes(selected.type) || selected.size > 5 * 1024 * 1024) { setMessage('Choisissez une image PNG ou JPEG de moins de 5 MiB.'); return; } if (preview) URL.revokeObjectURL(preview); setFile(selected); setPreview(URL.createObjectURL(selected)); setMessage(null); onFileChange(selected); };
  const remove = () => { if (preview) URL.revokeObjectURL(preview); setPreview(null); setFile(null); onFileChange(null); };
  return <div>{preview ? <div className="mail-preview"><img src={preview} alt="Aperçu de la zone postale recadrée importée" /><button onClick={remove}>Retirer l’image</button></div> : <label className="dropzone" onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); selectFile(event.dataTransfer.files[0]); }}><input type="file" accept="image/png,image/jpeg" onChange={(event) => selectFile(event.target.files?.[0])} /><span className="upload-icon">↥</span><strong>Déposez une zone postale recadrée</strong><small>PNG ou JPEG · maximum 5 MiB</small></label>}{message && <p className="input-error">{message}</p>}{file && <p className="file-name">✓ {file.name}</p>}</div>;
}
