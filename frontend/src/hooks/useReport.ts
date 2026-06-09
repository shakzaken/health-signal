import { useState, useCallback } from 'react'
import { generateReport } from '../api/backend'

export function useReport() {
  const [report, setReport] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [periodDays, setPeriodDays] = useState(90)
  const [error, setError] = useState<string | null>(null)

  const generate = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    setReport('')

    try {
      const result = await generateReport(periodDays)
      setReport(result.report)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to generate report')
    } finally {
      setIsLoading(false)
    }
  }, [periodDays])

  return { report, isLoading, periodDays, setPeriodDays, generateReport: generate, error }
}
