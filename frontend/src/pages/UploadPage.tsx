import { useState, useRef } from 'react'
import { uploadDocument, getDocumentStatus } from '../api/backend'
import type { DocumentUploadResponse } from '../api/backend'
import StatusBadge from '../components/StatusBadge'

export default function UploadPage() {
  // ── Upload section ──────────────────────────────────────────────────────────
  const [file, setFile] = useState<File | null>(null)
  const [sourceDate, setSourceDate] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<DocumentUploadResponse | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  async function handleUpload() {
    if (!file) return
    setUploading(true)
    setUploadResult(null)
    setUploadError(null)
    try {
      const result = await uploadDocument(file, sourceDate || undefined)
      setUploadResult(result)
      setFile(null)
      setSourceDate('')
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  // ── Status check section ────────────────────────────────────────────────────
  const [checkId, setCheckId] = useState('')
  const [checking, setChecking] = useState(false)
  const [checkResult, setCheckResult] = useState<{ id: string; filename: string; processing_status: string; document_type: string } | null>(null)
  const [checkError, setCheckError] = useState<string | null>(null)

  async function handleCheck() {
    if (!checkId.trim()) return
    setChecking(true)
    setCheckResult(null)
    setCheckError(null)
    try {
      const result = await getDocumentStatus(checkId.trim())
      setCheckResult(result)
    } catch (err) {
      setCheckError(err instanceof Error ? err.message : 'Not found')
    } finally {
      setChecking(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto w-full px-4 py-8 space-y-8">

      {/* Upload a document */}
      <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
        <h2 className="text-base font-semibold text-gray-900">Upload a Document</h2>
        <p className="text-sm text-gray-500">
          Supported formats: PDF, TXT. The system will automatically classify and extract data.
        </p>

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">File</label>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.txt"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="block w-full text-sm text-gray-700 file:mr-3 file:py-1.5 file:px-3 file:rounded-lg file:border file:border-gray-300 file:text-sm file:font-medium file:bg-gray-50 file:text-gray-700 hover:file:bg-gray-100 cursor-pointer"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Source Date <span className="text-gray-400 font-normal">(optional)</span>
            </label>
            <input
              type="date"
              value={sourceDate}
              onChange={(e) => setSourceDate(e.target.value)}
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {uploading ? 'Uploading…' : 'Upload & Ingest'}
          </button>
        </div>

        {uploadResult && (
          <div className="mt-3 p-3 bg-green-50 border border-green-200 rounded-lg text-sm space-y-1">
            <div className="font-medium text-green-800">Uploaded successfully</div>
            <div className="text-green-700">
              <span className="font-mono text-xs text-green-600">{uploadResult.id}</span>
            </div>
            <div className="flex items-center gap-2 text-green-700">
              {uploadResult.filename}
              <StatusBadge status={uploadResult.processing_status} />
            </div>
          </div>
        )}

        {uploadError && (
          <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {uploadError}
          </div>
        )}
      </section>

      {/* Check document status */}
      <section className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
        <h2 className="text-base font-semibold text-gray-900">Check Document Status</h2>

        <div className="flex gap-2">
          <input
            type="text"
            value={checkId}
            onChange={(e) => setCheckId(e.target.value)}
            placeholder="Document ID"
            onKeyDown={(e) => e.key === 'Enter' && handleCheck()}
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <button
            onClick={handleCheck}
            disabled={!checkId.trim() || checking}
            className="px-4 py-2 bg-gray-800 text-white text-sm font-medium rounded-lg hover:bg-gray-900 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {checking ? 'Checking…' : 'Check'}
          </button>
        </div>

        {checkResult && (
          <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg text-sm space-y-1">
            <div className="font-medium text-gray-800">{checkResult.filename}</div>
            <div className="flex items-center gap-2 text-gray-600">
              <span>{checkResult.document_type}</span>
              <StatusBadge status={checkResult.processing_status} />
            </div>
          </div>
        )}

        {checkError && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {checkError}
          </div>
        )}
      </section>

    </div>
  )
}
