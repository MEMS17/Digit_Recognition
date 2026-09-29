import { useEffect, useRef, useState } from 'react';
interface Props { onDrawingChange: (image: Blob | null) => void; }
export function DigitCanvas({ onDrawingChange }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null); const [drawing, setDrawing] = useState(false); const [hasDrawing, setHasDrawing] = useState(false);
  const clearCanvas = () => { const canvas = canvasRef.current; if (!canvas) return; const context = canvas.getContext('2d')!; context.fillStyle = '#fffdf9'; context.fillRect(0, 0, canvas.width, canvas.height); setHasDrawing(false); onDrawingChange(null); };
  useEffect(() => { clearCanvas(); }, []);
  const point = (event: React.PointerEvent<HTMLCanvasElement>) => { const canvas = canvasRef.current!; const rect = canvas.getBoundingClientRect(); return { x: (event.clientX - rect.left) * (canvas.width / rect.width), y: (event.clientY - rect.top) * (canvas.height / rect.height) }; };
  const draw = (event: React.PointerEvent<HTMLCanvasElement>, begin = false) => { if (!drawing && !begin) return; const context = canvasRef.current!.getContext('2d')!; const p = point(event); context.lineCap = 'round'; context.lineJoin = 'round'; context.strokeStyle = '#13263d'; context.lineWidth = 18; if (begin) { context.beginPath(); context.moveTo(p.x, p.y); } else context.lineTo(p.x, p.y); context.stroke(); setHasDrawing(true); };
  const start = (event: React.PointerEvent<HTMLCanvasElement>) => { event.currentTarget.setPointerCapture(event.pointerId); setDrawing(true); draw(event, true); };
  const finish = () => { if (!drawing) return; setDrawing(false); canvasRef.current?.toBlob(onDrawingChange, 'image/png'); };
  return <div className="canvas-wrap"><canvas ref={canvasRef} width="560" height="300" onPointerDown={start} onPointerMove={draw} onPointerUp={finish} onPointerLeave={finish} aria-label="Zone de dessin pour un chiffre manuscrit" /><div className="canvas-guide">Dessinez ici</div><button className="clear-button" onClick={clearCanvas} disabled={!hasDrawing}>Effacer</button></div>;
}
