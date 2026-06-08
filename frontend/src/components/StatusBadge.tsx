interface StatusBadgeProps {
  status: string
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  let color = 'var(--sub)'
  let bg = 'var(--surface-2)'

  if (status === 'completed') {
    color = 'var(--good)'
    bg = '#EAF6F0'
  } else if (status === 'failed') {
    color = '#A23E3E'
    bg = '#FBEAEA'
  } else if (status === 'processing' || status === 'pending') {
    color = 'var(--warn)'
    bg = '#FBF1E3'
  }

  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        fontSize: 11.5,
        fontWeight: 600,
        color,
        background: bg,
        padding: '3px 9px',
        borderRadius: 20,
        textTransform: 'capitalize',
      }}
    >
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: color }} />
      {status}
    </span>
  )
}
