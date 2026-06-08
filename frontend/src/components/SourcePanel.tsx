import { useState } from 'react'
import type { SourceChunk } from '../types'
import { ChevronIcon, FileIcon } from './Icons'

interface SourcePanelProps {
  sources: SourceChunk[]
}

export default function SourcePanel({ sources }: SourcePanelProps) {
  const [open, setOpen] = useState(false)

  if (sources.length === 0) return null

  // Indent to align with assistant bubble text (30px avatar + 11px gap = 41px)
  return (
    <div style={{ marginLeft: 41, marginTop: 8 }}>
      <div
        style={{
          border: '1px solid var(--border)',
          borderRadius: 'calc(var(--radius) * 0.8)',
          background: 'var(--surface-2)',
          overflow: 'hidden',
        }}
      >
        <button
          onClick={() => setOpen((v) => !v)}
          style={{
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 8,
            padding: '9px 12px',
            cursor: 'pointer',
            border: 'none',
            background: 'transparent',
            fontFamily: 'inherit',
            textAlign: 'left',
          }}
        >
          <span
            style={{
              display: 'flex',
              transition: 'transform .2s',
              transform: open ? 'rotate(-90deg)' : 'none',
            }}
          >
            <ChevronIcon size={13} color="var(--faint)" sw={2} />
          </span>
          <FileIcon size={13} color="var(--faint)" />
          <span style={{ fontSize: 12.5, fontWeight: 500, color: 'var(--sub)' }}>
            {sources.length} source{sources.length !== 1 ? 's' : ''} used
          </span>
        </button>

        {open && (
          <div
            style={{
              borderTop: '1px solid var(--border)',
              padding: '10px 12px',
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            {sources.map((s, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 10,
                  padding: '8px 10px',
                  border: '1px solid var(--border)',
                  borderRadius: 'calc(var(--radius) * 0.6)',
                  background: 'var(--surface)',
                }}
              >
                <span
                  style={{
                    flexShrink: 0,
                    fontSize: 9.5,
                    fontWeight: 600,
                    fontFamily: 'var(--mono)',
                    color: 'var(--accent-ink)',
                    background: 'var(--accent-soft)',
                    padding: '3px 6px',
                    borderRadius: 5,
                    marginTop: 1,
                    textTransform: 'uppercase',
                  }}
                >
                  {s.document_type || 'doc'}
                </span>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--ink)' }}>
                      {s.filename}
                    </span>
                    <span
                      style={{
                        fontSize: 10.5,
                        color: 'var(--faint)',
                        fontFamily: 'var(--mono)',
                      }}
                    >
                      {Math.round(s.score * 100)}% match
                    </span>
                    {s.source_date && (
                      <span
                        style={{
                          fontSize: 10.5,
                          color: 'var(--faint)',
                          fontFamily: 'var(--mono)',
                        }}
                      >
                        {s.source_date}
                      </span>
                    )}
                  </div>
                  <div
                    style={{
                      fontSize: 12,
                      color: 'var(--sub)',
                      marginTop: 3,
                      lineHeight: 1.45,
                      display: '-webkit-box',
                      WebkitLineClamp: 3,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}
                  >
                    {s.text}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
