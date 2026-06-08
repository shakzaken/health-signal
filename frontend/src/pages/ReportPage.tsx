import { useReport } from '../hooks/useReport'
import { ReportIcon, SparkIcon, CopyIcon, PulseIcon } from '../components/Icons'

const PERIOD_OPTIONS = [
  { days: 30, label: '30 days', key: '30d' },
  { days: 90, label: '90 days', key: '90d' },
  { days: 180, label: '6 months', key: '6mo' },
  { days: 365, label: '1 year', key: '1yr' },
]

// Render the LLM-generated report text with visual hierarchy
function renderReport(text: string) {
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []
  let key = 0

  for (const line of lines) {
    const trimmed = line.trim()
    if (!trimmed) {
      elements.push(<div key={key++} style={{ height: 8 }} />)
      continue
    }

    // Section headers (Markdown ## or ALL CAPS or ends with :)
    if (trimmed.match(/^#{1,3}\s/) || trimmed.match(/^[A-Z][A-Z\s\d–-]+:?\s*$/)) {
      const text = trimmed.replace(/^#{1,3}\s/, '').replace(/:$/, '')
      elements.push(
        <div
          key={key++}
          style={{
            fontSize: 15,
            fontWeight: 700,
            color: 'var(--ink)',
            marginTop: 4,
            paddingBottom: 8,
            borderBottom: '1px solid var(--border)',
          }}
        >
          {text}
        </div>
      )
      continue
    }

    // Bullet points
    if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
      const content = trimmed.replace(/^[-•]\s/, '')
      elements.push(
        <div key={key++} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
          <span
            style={{
              marginTop: 7,
              width: 5,
              height: 5,
              borderRadius: '50%',
              flexShrink: 0,
              background: 'var(--accent)',
            }}
          />
          <span style={{ fontSize: 14, color: 'var(--ink)', lineHeight: 1.6 }}>{content}</span>
        </div>
      )
      continue
    }

    // Regular paragraph
    elements.push(
      <p key={key++} style={{ margin: 0, fontSize: 14, color: '#27313F', lineHeight: 1.65 }}>
        {line}
      </p>
    )
  }

  return elements
}

export default function ReportPage() {
  const { report, isLoading, periodDays, setPeriodDays, generateReport, error } = useReport()

  const currentPeriod = PERIOD_OPTIONS.find((o) => o.days === periodDays)!
  const today = new Date().toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })

  function copyReport() {
    if (report) navigator.clipboard.writeText(report).catch(() => {})
  }

  return (
    <div style={{ overflowY: 'auto', height: '100%' }}>
      <div
        style={{
          maxWidth: 760,
          margin: '0 auto',
          padding: '34px 28px 60px',
          display: 'flex',
          flexDirection: 'column',
          gap: 22,
        }}
      >
        {/* Page title */}
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
            Doctor visit report
          </h1>
          <p style={{ margin: '6px 0 0', fontSize: 14, color: 'var(--sub)' }}>
            A structured summary of your health data, ready to bring to an appointment.
          </p>
        </div>

        {/* Controls card */}
        <div
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: 22,
            boxShadow: '0 1px 2px rgba(20,30,50,.04)',
          }}
        >
          <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--ink)', marginBottom: 10 }}>
            Reporting period
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {PERIOD_OPTIONS.map((opt) => {
              const active = periodDays === opt.days
              return (
                <button
                  key={opt.days}
                  onClick={() => setPeriodDays(opt.days)}
                  style={{
                    padding: '9px 18px',
                    borderRadius: 'calc(var(--radius) * 0.7)',
                    border: `1px solid ${active ? 'var(--accent)' : 'var(--border-strong)'}`,
                    background: active ? 'var(--accent)' : 'var(--surface)',
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    fontSize: 13.5,
                    fontWeight: 600,
                    color: active ? '#fff' : 'var(--ink)',
                    transition: 'all .12s',
                  }}
                >
                  {opt.label}
                </button>
              )
            })}
          </div>

          <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', gap: 12 }}>
            <button
              onClick={generateReport}
              disabled={isLoading}
              style={{
                border: 'none',
                background: 'var(--accent)',
                color: '#fff',
                fontWeight: 600,
                fontSize: 13.5,
                padding: '11px 20px',
                borderRadius: 'calc(var(--radius) * 0.7)',
                cursor: isLoading ? 'default' : 'pointer',
                fontFamily: 'inherit',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 8,
                transition: 'filter .15s',
                opacity: isLoading ? 0.7 : 1,
              }}
            >
              {isLoading ? (
                <>
                  <SparkIcon size={15} color="#fff" />
                  Generating…
                </>
              ) : (
                <>
                  <ReportIcon size={15} color="#fff" />
                  {report ? 'Regenerate report' : 'Generate report'}
                </>
              )}
            </button>

            {report && !isLoading && (
              <button
                onClick={copyReport}
                style={{
                  border: '1px solid var(--border-strong)',
                  background: 'var(--surface)',
                  color: 'var(--sub)',
                  fontSize: 13,
                  padding: '10px 15px',
                  borderRadius: 'calc(var(--radius) * 0.7)',
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 7,
                }}
              >
                <CopyIcon size={14} color="var(--sub)" />
                Copy
              </button>
            )}
          </div>
        </div>

        {/* Error */}
        {error && (
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
            {error}
          </div>
        )}

        {/* Skeleton loader */}
        {isLoading && !report && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                style={{
                  height: i === 0 ? 120 : 80,
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius)',
                  animation: `hspulse 1.3s ${i * 0.12}s infinite`,
                }}
              />
            ))}
          </div>
        )}

        {/* Report output */}
        {report && !isLoading && (
          <div
            style={{
              background: 'var(--surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              overflow: 'hidden',
              boxShadow: '0 1px 3px rgba(20,30,50,.05)',
            }}
          >
            {/* Report header */}
            <div
              style={{
                padding: '20px 26px',
                borderBottom: '1px solid var(--border)',
                display: 'flex',
                alignItems: 'center',
                gap: 13,
                background: 'var(--surface-2)',
              }}
            >
              <div
                style={{
                  width: 38,
                  height: 38,
                  borderRadius: 10,
                  background: 'var(--accent)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0,
                }}
              >
                <PulseIcon size={20} color="#fff" sw={2.2} />
              </div>
              <div>
                <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--ink)' }}>
                  Health summary
                </div>
                <div style={{ fontSize: 12.5, color: 'var(--sub)', marginTop: 1 }}>
                  Covering {currentPeriod.label.toLowerCase()} · generated {today}
                </div>
              </div>
            </div>

            {/* Report body */}
            <div
              style={{
                padding: '26px',
                display: 'flex',
                flexDirection: 'column',
                gap: 12,
              }}
            >
              {renderReport(report)}

              <div
                style={{
                  fontSize: 11.5,
                  color: 'var(--faint)',
                  borderTop: '1px solid var(--border)',
                  paddingTop: 16,
                  marginTop: 4,
                  lineHeight: 1.5,
                }}
              >
                This summary is generated from your uploaded documents to support — not replace — a
                conversation with your healthcare provider. Always confirm findings with a clinician.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
