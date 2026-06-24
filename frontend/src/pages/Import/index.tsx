import { useState, type FormEvent, useRef } from 'react'
import {
  Upload,
  FileSpreadsheet,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
} from 'lucide-react'
import { api, ApiError, type ImportResult } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

const MAX_SIZE = 10 * 1024 * 1024
const ACCEPTED = '.xlsx,.xls,.csv'

export function ImportPage() {
  const inputRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const [result, setResult] = useState<ImportResult | null>(null)
  const [history, setHistory] = useState<ImportResult[]>([])

  const validateFile = (f: File): string | null => {
    const ext = '.' + f.name.split('.').pop()?.toLowerCase()
    if (!ACCEPTED.includes(ext)) return 'Format non accepté. Utilisez .xlsx, .xls ou .csv.'
    if (f.size > MAX_SIZE) return 'Fichier trop volumineux (max 10 Mo).'
    return null
  }

  const handleFile = (f: File) => {
    setErrorMsg(null)
    setResult(null)
    const err = validateFile(f)
    if (err) {
      setErrorMsg(err)
      setFile(null)
    } else {
      setFile(f)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }

  const handleDragLeave = () => setDragOver(false)

  const handleClick = () => inputRef.current?.click()

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) handleFile(f)
  }

  const handleUpload = async (e: FormEvent) => {
    e.preventDefault()
    if (!file) return
    setUploading(true)
    setErrorMsg(null)
    setResult(null)

    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await api.upload<ImportResult>('/imports', formData)
      setResult(res)
      setHistory((prev) => [res, ...prev])
      setFile(null)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Erreur lors de l\'import.'
      setErrorMsg(msg)
    } finally {
      setUploading(false)
    }
  }

  const isDragActive = dragOver ? 'border-primary bg-primary/5' : 'border-muted-foreground/25'

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Import de cours</h2>
        <p className="text-sm text-muted-foreground">
          Importez un fichier Excel ou CSV pour ajouter des cours au catalogue
        </p>
      </div>

      <Card>
        <CardContent className="p-6">
          <form onSubmit={(e) => void handleUpload(e)} className="space-y-4">
            <div
              role="button"
              tabIndex={0}
              className={cn(
                'flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed p-12 text-center transition-colors',
                isDragActive,
              )}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={handleClick}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') handleClick()
              }}
            >
              <input
                ref={inputRef}
                type="file"
                accept={ACCEPTED}
                className="hidden"
                onChange={handleInputChange}
              />
              {file ? (
                <>
                  <FileSpreadsheet className="h-10 w-10 text-primary" />
                  <div>
                    <p className="font-medium">{file.name}</p>
                    <p className="text-sm text-muted-foreground">
                      {(file.size / 1024).toFixed(1)} Ko
                    </p>
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation()
                      setFile(null)
                      setErrorMsg(null)
                    }}
                  >
                    Changer de fichier
                  </Button>
                </>
              ) : (
                <>
                  <Upload className="h-10 w-10 text-muted-foreground/40" />
                  <div>
                    <p className="font-medium text-muted-foreground">
                      Déposez un fichier ici ou cliquez pour parcourir
                    </p>
                    <p className="text-sm text-muted-foreground/70">
                      {ACCEPTED} — max 10 Mo
                    </p>
                  </div>
                </>
              )}
            </div>

            {errorMsg && (
              <div className="flex items-center gap-2 rounded-md bg-destructive/15 px-4 py-3 text-sm text-destructive-foreground">
                <AlertCircle className="h-4 w-4 shrink-0" />
                {errorMsg}
              </div>
            )}

            <Button type="submit" disabled={!file || uploading} className="w-full sm:w-auto">
              {uploading ? (
                <>
                  <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  Import en cours...
                </>
              ) : (
                <>
                  <Upload className="mr-2 h-4 w-4" />
                  Importer
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {result && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <CheckCircle className="h-5 w-5 text-green-400" />
              Import terminé
            </CardTitle>
            <CardDescription>
              Résultat pour <span className="font-medium">{result.filename}</span>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm">
              <span className="font-medium text-green-400">{result.inserted}</span> cours insérés
            </p>
            {result.errors.length > 0 && (
              <div className="space-y-1">
                <p className="text-sm font-medium text-destructive">
                  {result.errors.length} erreur{result.errors.length > 1 ? 's' : ''}:
                </p>
                <ul className="space-y-1">
                  {result.errors.map((err, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 rounded-md bg-destructive/10 px-3 py-2 text-xs text-destructive-foreground"
                    >
                      <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
                      {err}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {history.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Imports récents</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="divide-y divide-border">
              {history.map((h, i) => (
                <div key={i} className="flex items-center justify-between py-2 text-sm">
                  <div className="flex items-center gap-2">
                    <FileSpreadsheet className="h-4 w-4 text-muted-foreground" />
                    <span className="font-medium">{h.filename}</span>
                    <span className="text-muted-foreground">
                      — {h.inserted} cours
                    </span>
                  </div>
                  {h.errors.length > 0 && (
                    <span className="text-xs text-destructive">
                      {h.errors.length} erreur{h.errors.length > 1 ? 's' : ''}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
