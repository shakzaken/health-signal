import { useReport } from '../hooks/useReport'

const PERIOD_OPTIONS = [
  { days: 30, label: '30 days' },
  { days: 90, label: '90 days' },
  { days: 180, label: '6 months' },
  { days: 365, label: '1 year' },
]

export default function ReportPage() {
  const { report, isLoading, periodDays, setPeriodDays, generateReport, error } = useReport()

  // Render the report: bold section headers (lines ending with :), preserve line breaks
  function renderReport(text: string) {
    return text.split('\n').map((line, i) => {
      const trimmed = line.trim()

      // Section headers: all-caps lines or lines ending with ':'
      if (trimmed.match(/^[A-Z][A-Z\s\d]+:?$/) || trimmed.match(/^#+\s/)) {
        return (
          <p key={i} className="font-semibold text-gray-900 mt-5 first:mt-0">
            {trimmed.replace(/^#+\s/, '')}
          </p>
        )
      }

      // Bullet points
      if (trimmed.startsWith('- ') || trimmed.startsWith('• ')) {
        return (
          <p key={i} className="pl-4 text-gray-700 before:content-['•'] before:mr-2 before:text-gray-400">
            {trimmed.replace(/^[-•]\s/, '')}
          </p>
        )
      }

      // Empty line → spacer
      if (!trimmed) {
        return <div key={i} className="h-1" />
      }

      return <p key={i} className="text-gray-700">{line}</p>
    })
  }

  return (
    <div className="max-w-2xl mx-auto w-full px-4 py-8 space-y-6">

      {/* Controls */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
        <h2 className="text-base font-semibold text-gray-900">Doctor Visit Report</h2>
        <p className="text-sm text-gray-500">
          Generates a structured summary of your health data for the selected period — ready to bring to an appointment.
        </p>

        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Period</label>
            <div className="flex gap-2 flex-wrap">
              {PERIOD_OPTIONS.map((opt) => (
                <button
                  key={opt.days}
                  onClick={() => setPeriodDays(opt.days)}
                  className={[
                    'px-4 py-1.5 rounded-lg text-sm font-medium border transition-colors',
                    periodDays === opt.days
                      ? 'bg-blue-600 text-white border-blue-600'
                      : 'bg-white text-gray-700 border-gray-300 hover:border-gray-400',
                  ].join(' ')}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <button
            onClick={generateReport}
            disabled={isLoading}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? 'Generating…' : 'Generate Report'}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Report output */}
      {isLoading && !report && (
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <div className="space-y-2 animate-pulse">
            {[...Array(6)].map((_, i) => (
              <div key={i} className={`h-3 bg-gray-200 rounded ${i % 3 === 0 ? 'w-1/3' : 'w-full'}`} />
            ))}
          </div>
        </div>
      )}

      {report && !isLoading && (
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-gray-900">
              Report — last {periodDays} days
            </h3>
            <span className="text-xs text-gray-400">
              {new Date().toLocaleDateString()}
            </span>
          </div>
          <div className="text-sm leading-relaxed space-y-1">
            {renderReport(report)}
          </div>
        </div>
      )}

    </div>
  )
}
