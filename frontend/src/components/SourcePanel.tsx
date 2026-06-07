import { useState } from 'react'
import type { SourceChunk } from '../types'

interface SourcePanelProps {
  sources: SourceChunk[]
}

export default function SourcePanel({ sources }: SourcePanelProps) {
  const [open, setOpen] = useState(false)

  if (sources.length === 0) return null

  return (
    <div className="border-t border-gray-200 bg-gray-50">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-4 py-2 text-xs text-gray-500 hover:text-gray-700 transition-colors"
      >
        <span className={`transition-transform ${open ? 'rotate-90' : ''}`}>▶</span>
        {sources.length} source{sources.length !== 1 ? 's' : ''} used
      </button>

      {open && (
        <div className="px-4 pb-3 space-y-2 max-h-48 overflow-y-auto">
          {sources.map((chunk, i) => (
            <div key={i} className="bg-white border border-gray-200 rounded-lg p-3 text-xs">
              <div className="flex items-center justify-between mb-1 gap-2">
                <span className="font-medium text-gray-700 truncate">{chunk.filename}</span>
                <div className="flex items-center gap-1.5 shrink-0">
                  {chunk.document_type && (
                    <span className="bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded text-[10px]">
                      {chunk.document_type}
                    </span>
                  )}
                  {chunk.source_date && (
                    <span className="text-gray-400">{chunk.source_date}</span>
                  )}
                  <span className="text-gray-400">
                    {(chunk.score * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
              <p className="text-gray-600 line-clamp-3 leading-relaxed">{chunk.text}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
