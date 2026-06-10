import { useState, useRef, type ReactNode } from 'react'
import { uploadDocument, getDocumentStatus } from '../api/backend'
import type { DocumentUploadResponse } from '../api/backend'
import { UploadIcon, SearchIcon, ArrowDownIcon, FileIcon, CheckIcon, SparkIcon } from '../components/Icons'

// ── Reusable card primitives ─────────────────────────────────────────────────

function Card({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        boxShadow: '0 1px 2px rgba(20,30,50,.04)',
      }}
    >
      {children}
    </div>
  )
}

function CardHead({ icon, title, sub }: { icon: ReactNode; title: string; sub?: string }) {
  return (
    <div style={{ display: 'flex', gap: 12, padding: '22px 22px 0' }}>
      <div
        style={{
          flexShrink: 0,
          width: 34,
          height: 34,
          borderRadius: 9,
          background: 'var(--accent-soft)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {icon}
      </div>
      <div>
        <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--ink)' }}>{title}</div>
        {sub && <div style={{ fontSize: 13, color: 'var(--sub)', marginTop: 3, lineHeight: 1.5 }}>{sub}</div>}
      </div>
    </div>
  )
}

function Label({ children, opt }: { children: ReactNode; opt?: boolean }) {
  return (
    <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--ink)', marginBottom: 8 }}>
      {children}
      {opt && <span style={{ color: 'var(--faint)', fontWeight: 400 }}> (optional)</span>}
    </div>
  )
}

function StatusDot({ status }: { status: string }) {
  const color = status === 'completed' ? 'var(--good)' : status === 'failed' ? '#A23E3E' : 'var(--warn)'
  const bg = status === 'completed' ? '#EAF6F0' : status === 'failed' ? '#FBEAEA' : '#FBF1E3'
  const text = status === 'completed' ? 'Completed' : status === 'failed' ? 'Failed' : 'Processing'
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        fontSize: 12,
        fontWeight: 600,
        color,
        background: bg,
        padding: '3px 9px',
        borderRadius: 20,
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: color }} />
      {text}
    </span>
  )
}

const btnPrimary: React.CSSProperties = {
  border: 'none',
  background: 'var(--accent)',
  color: '#fff',
  fontWeight: 600,
  fontSize: 13.5,
  padding: '10px 18px',
  borderRadius: 'calc(var(--radius) * 0.7)',
  cursor: 'pointer',
  fontFamily: 'inherit',
  transition: 'filter .15s',
  display: 'inline-flex',
  alignItems: 'center',
  gap: 7,
}

const inputStyle: React.CSSProperties = {
  border: '1px solid var(--border-strong)',
  borderRadius: 'calc(var(--radius) * 0.7)',
  padding: '10px 12px',
  fontSize: 13.5,
  color: 'var(--ink)',
  background: 'var(--surface)',
  outline: 'none',
  fontFamily: 'inherit',
  width: '100%',
}

// ── Upload section ────────────────────────────────────────────────────────────

function UploadSection() {
  const [file, setFile] = useState<File | null>(null)
  const [sourceDate, setSourceDate] = useState('')
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState<DocumentUploadResponse | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [drag, setDrag] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function pickFile(f: File | null | undefined) {
    if (!f) return
    setFile(f)
    setUploadResult(null)
    setUploadError(null)
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDrag(false)
    pickFile(e.dataTransfer.files?.[0])
  }

  function reset() {
    setFile(null)
    setSourceDate('')
    setUploadResult(null)
    setUploadError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  async function handleUpload() {
    if (!file || uploading) return
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

  return (
    <Card>
      <CardHead
        icon={<UploadIcon size={18} color="var(--accent)" />}
        title="Upload a document"
        sub="Supported formats: PDF, TXT · up to 20 MB"
      />
      <div style={{ padding: 22 }}>
        {uploadResult ? (
          /* Success state */
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: '14px 16px',
                background: '#EAF6F0',
                border: '1px solid #CDEADB',
                borderRadius: 'calc(var(--radius) * 0.8)',
              }}
            >
              <div
                style={{
                  width: 30,
                  height: 30,
                  borderRadius: '50%',
                  background: 'var(--good)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <CheckIcon size={17} color="#fff" sw={2.4} />
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600, color: '#15663F' }}>
                  Document ingested successfully
                </div>
                <div style={{ fontSize: 12.5, color: '#3C7458', marginTop: 1 }}>
                  Ready to reference in Chat and Doctor Report.
                </div>
              </div>
            </div>

            <div
              style={{
                border: '1px solid var(--border)',
                borderRadius: 'calc(var(--radius) * 0.8)',
                overflow: 'hidden',
              }}
            >
              {[
                ['Document ID', uploadResult.id, true],
                ['Filename', uploadResult.filename, false],
                ['Detected type', uploadResult.document_type, false],
                ['Status', null, false],
              ].map(([k, v, mono], i) => (
                <div
                  key={i as number}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    padding: '11px 14px',
                    borderTop: i ? '1px solid var(--border)' : 'none',
                  }}
                >
                  <span style={{ fontSize: 13, color: 'var(--sub)', width: 130, flexShrink: 0 }}>{k}</span>
                  {k === 'Status' ? (
                    <StatusDot status={uploadResult.processing_status} />
                  ) : (
                    <span
                      style={{
                        fontSize: 13.5,
                        fontWeight: 600,
                        color: 'var(--ink)',
                        fontFamily: mono ? 'var(--mono)' : 'inherit',
                        wordBreak: 'break-all',
                      }}
                    >
                      {v as string}
                    </span>
                  )}
                </div>
              ))}
            </div>

            <div>
              <button onClick={reset} style={btnPrimary}>
                Upload another
              </button>
            </div>
          </div>
        ) : (
          /* Upload form */
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <div>
              <Label>File</Label>
              <div
                onDragOver={(e) => { e.preventDefault(); setDrag(true) }}
                onDragLeave={() => setDrag(false)}
                onDrop={onDrop}
                onClick={() => fileInputRef.current?.click()}
                style={{
                  border: `1.5px dashed ${drag ? 'var(--accent)' : 'var(--border-strong)'}`,
                  background: drag ? 'var(--accent-soft)' : 'var(--surface-2)',
                  borderRadius: 'calc(var(--radius) * 0.8)',
                  padding: '24px 20px',
                  textAlign: 'center',
                  cursor: 'pointer',
                  transition: 'border-color .15s, background .15s',
                }}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.txt"
                  style={{ display: 'none' }}
                  onChange={(e) => pickFile(e.target.files?.[0])}
                />
                {file ? (
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 11 }}>
                    <div
                      style={{
                        width: 34,
                        height: 40,
                        borderRadius: 6,
                        background: 'var(--surface)',
                        border: '1px solid var(--border)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        flexShrink: 0,
                      }}
                    >
                      <FileIcon size={18} color="var(--accent)" />
                    </div>
                    <div style={{ textAlign: 'left' }}>
                      <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--ink)' }}>{file.name}</div>
                      <div style={{ fontSize: 12, color: 'var(--faint)' }}>
                        {(file.size / 1024).toFixed(0)} KB · click to replace
                      </div>
                    </div>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                    <div
                      style={{
                        width: 38,
                        height: 38,
                        borderRadius: '50%',
                        background: 'var(--accent-soft)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                    >
                      <ArrowDownIcon size={18} color="var(--accent)" />
                    </div>
                    <div style={{ fontSize: 13.5, color: 'var(--ink)', fontWeight: 500 }}>
                      Drop a file here, or{' '}
                      <span style={{ color: 'var(--accent)' }}>browse</span>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--faint)' }}>PDF or TXT</div>
                  </div>
                )}
              </div>
            </div>

            <div style={{ maxWidth: 220 }}>
              <Label opt>Source date</Label>
              <input
                type="date"
                value={sourceDate}
                onChange={(e) => setSourceDate(e.target.value)}
                style={inputStyle}
              />
            </div>

            {uploading && (
              <div
                style={{
                  background: 'var(--surface-2)',
                  border: '1px solid var(--border)',
                  borderRadius: 'calc(var(--radius) * 0.8)',
                  padding: '14px 16px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10 }}>
                  <div style={{ animation: 'hsspin 1s linear infinite', display: 'flex' }}>
                    <SparkIcon size={14} color="var(--accent)" />
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--ink)' }}>
                    Uploading & indexing…
                  </span>
                </div>
                <div
                  style={{
                    height: 6,
                    borderRadius: 6,
                    background: 'var(--border)',
                    overflow: 'hidden',
                  }}
                >
                  <div
                    style={{
                      height: '100%',
                      width: '35%',
                      background: 'var(--accent)',
                      borderRadius: 6,
                      animation: 'hsslide 1.4s ease-in-out infinite',
                    }}
                  />
                </div>
              </div>
            )}

            {uploadError && (
              <div
                style={{
                  padding: '10px 14px',
                  background: '#FBEAEA',
                  border: '1px solid #F0CECE',
                  borderRadius: 'calc(var(--radius) * 0.7)',
                  fontSize: 13,
                  color: '#A23E3E',
                }}
              >
                {uploadError}
              </div>
            )}

            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <button
                onClick={handleUpload}
                disabled={!file || uploading}
                style={{
                  ...btnPrimary,
                  opacity: file && !uploading ? 1 : 0.5,
                  cursor: file && !uploading ? 'pointer' : 'default',
                }}
              >
                {uploading ? 'Ingesting…' : 'Upload & ingest'}
              </button>
              {file && !uploading && (
                <button
                  onClick={reset}
                  style={{
                    border: 'none',
                    background: 'transparent',
                    color: 'var(--sub)',
                    fontSize: 13,
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    textDecoration: 'underline',
                  }}
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        )}
      </div>
    </Card>
  )
}

// ── Status checker ────────────────────────────────────────────────────────────

function StatusChecker() {
  const [checkId, setCheckId] = useState('')
  const [checking, setChecking] = useState(false)
  const [checkResult, setCheckResult] = useState<{
    id: string
    filename: string
    processing_status: string
    document_type: string
  } | null>(null)
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
    <Card>
      <CardHead
        icon={<SearchIcon size={17} color="var(--accent)" />}
        title="Check document status"
        sub="Look up the processing status of a previously uploaded document by ID."
      />
      <div style={{ padding: 22 }}>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            value={checkId}
            onChange={(e) => setCheckId(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCheck()}
            placeholder="Document ID"
            style={{ ...inputStyle, flex: 1, fontFamily: 'var(--mono)', fontSize: 13 }}
          />
          <button
            onClick={handleCheck}
            disabled={!checkId.trim() || checking}
            style={{
              ...btnPrimary,
              opacity: checkId.trim() && !checking ? 1 : 0.5,
              cursor: checkId.trim() && !checking ? 'pointer' : 'default',
              flexShrink: 0,
            }}
          >
            {checking ? 'Checking…' : 'Check'}
          </button>
        </div>

        {checkResult && (
          <div
            style={{
              marginTop: 14,
              border: '1px solid var(--border)',
              borderRadius: 'calc(var(--radius) * 0.8)',
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '12px 14px',
                background: 'var(--surface-2)',
                borderBottom: '1px solid var(--border)',
              }}
            >
              <span
                style={{
                  fontFamily: 'var(--mono)',
                  fontSize: 12.5,
                  color: 'var(--ink)',
                  fontWeight: 600,
                  wordBreak: 'break-all',
                }}
              >
                {checkResult.id}
              </span>
              <span style={{ marginLeft: 'auto', flexShrink: 0 }}>
                <StatusDot status={checkResult.processing_status} />
              </span>
            </div>
            {[
              ['Document', checkResult.filename],
              ['Type', checkResult.document_type],
            ].map(([k, v], i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  padding: '10px 14px',
                  borderTop: i ? '1px solid var(--border)' : 'none',
                }}
              >
                <span style={{ fontSize: 13, color: 'var(--sub)', width: 130, flexShrink: 0 }}>{k}</span>
                <span style={{ fontSize: 13.5, fontWeight: 500, color: 'var(--ink)' }}>{v}</span>
              </div>
            ))}
          </div>
        )}

        {checkError && (
          <div
            style={{
              marginTop: 12,
              padding: '10px 14px',
              background: '#FBEAEA',
              border: '1px solid #F0CECE',
              borderRadius: 'calc(var(--radius) * 0.7)',
              fontSize: 13,
              color: '#A23E3E',
            }}
          >
            {checkError}
          </div>
        )}
      </div>
    </Card>
  )
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function UploadPage() {
  return (
    <div style={{ overflowY: 'auto', height: '100%' }}>
      <div
        style={{
          maxWidth: 680,
          margin: '0 auto',
          padding: '34px 28px 60px',
          display: 'flex',
          flexDirection: 'column',
          gap: 22,
        }}
      >
        <div>
          <h1
            style={{
              margin: 0,
              fontSize: 22,
              fontWeight: 700,
              color: 'var(--ink)',
              letterSpacing: '-0.01em',
            }}
          >
            Upload health documents
          </h1>
          <p style={{ margin: '6px 0 0', fontSize: 14, color: 'var(--sub)' }}>
            Add blood tests, symptom logs or supplement records. We classify and index them automatically
            so the assistant can reference them.
          </p>
        </div>

        <UploadSection />
        <StatusChecker />
      </div>
    </div>
  )
}
