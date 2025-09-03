'use client'
import { useState, useRef, useEffect } from 'react'

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000'

type Region = {
  type: string
  polygon: number[][]
  confidence: number
  id?: string
}

export default function Page() {
  const [imageId, setImageId] = useState<string | null>(null)
  const [regions, setRegions] = useState<Region[]>([])
  const [redactedUrl, setRedactedUrl] = useState<string | null>(null)
  const [reviewer, setReviewer] = useState<boolean>(false)
  const imgRef = useRef<HTMLImageElement | null>(null)
  const [patches, setPatches] = useState<Record<string, string>>({})

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const form = new FormData()
    form.append('file', file)
    const res = await fetch(`${API_BASE}/ingest`, { method: 'POST', body: form })
    if (!res.ok) { alert('Upload failed'); return }
    const data = await res.json()
    setImageId(data.image_id)
  setRegions(data.regions)
    setRedactedUrl(`${API_BASE}${data.redacted_url}`)
    setPatches({})
  }

  const decryptRegion = async (rid: string) => {
    if (!imageId) return
    const res = await fetch(`${API_BASE}/images/${imageId}/decrypt`, {
      method: 'POST',
      headers: reviewer ? { 'Content-Type': 'application/json', 'X-Role': 'Reviewer' } : { 'Content-Type': 'application/json' },
      body: JSON.stringify({ region_ids: [rid] } as any)
    })
    if (res.status === 403) { alert('Reviewer role required. Toggle Reviewer.'); return }
    if (!res.ok) { alert('Decrypt failed'); return }
    const data = await res.json()
    if (data[rid]?.image_base64) {
      setPatches(prev => ({ ...prev, [rid]: data[rid].image_base64 }))
    }
  }

  // Converts polygon to CSS absolute rectangle
  const polyToRect = (poly: number[][]) => {
    const xs = poly.map(p => p[0]); const ys = poly.map(p => p[1])
    const left = Math.min(...xs); const top = Math.min(...ys)
    const right = Math.max(...xs); const bottom = Math.max(...ys)
    return { left, top, width: right-left, height: bottom-top }
  }

  return (
    <main className="p-6" style={{ fontFamily: 'ui-sans-serif, system-ui' }}>
      <h1 className="text-2xl font-bold mb-4">Selective Image Encryption — PoC</h1>
      <div className="mb-4 flex items-center gap-4">
        <input type="file" accept="image/*" onChange={handleUpload} />
        <label className="flex items-center gap-2">
          <input type="checkbox" checked={reviewer} onChange={e => setReviewer(e.target.checked)} />
          Reviewer
        </label>
      </div>

      {redactedUrl && (
        <div className="relative inline-block border rounded">
          <img ref={imgRef} src={redactedUrl} alt="redacted" />
          {imgRef.current && regions.map((r, i) => {
            const rect = polyToRect(r.polygon)
            const w = imgRef.current!.naturalWidth
            const h = imgRef.current!.naturalHeight
            // Percentage positioning for responsiveness
            const style: React.CSSProperties = {
              position: 'absolute',
              left: `${(rect.left / w) * 100}%`,
              top: `${(rect.top / h) * 100}%`,
              width: `${(rect.width / w) * 100}%`,
              height: `${(rect.height / h) * 100}%`,
              border: '2px dashed #22c55e',
              boxSizing: 'border-box',
              cursor: 'pointer'
            }
            const rid = r.id
            return (
              <div key={i} style={style} title={`${r.type} (${Math.round(r.confidence*100)}%)`} onClick={() => decryptRegion(rid)}>
                {patches[rid] && (
                  <img src={patches[rid]} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                )}
              </div>
            )
          })}
        </div>
      )}

      {!redactedUrl && (
        <p className="text-gray-600">Upload an image to see auto-detected regions and redaction. Click a box to decrypt (enable Reviewer to authorize).</p>
      )}
    </main>
  )
}
