interface IconProps {
  size?: number
  color?: string
  sw?: number
}

function mk(paths: string[], fill?: boolean) {
  return function Icon({ size = 18, color = 'currentColor', sw = 1.7 }: IconProps) {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" fill={fill ? color : 'none'}>
        {paths.map((d, i) => (
          <path key={i} d={d} stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round" />
        ))}
      </svg>
    )
  }
}

export const PulseIcon = mk(['M2 13h4l2.5-7 4 14 2.5-9 2 2h5'])
export const ChatIcon = mk(['M4 5h16v11H9l-4 3v-3H4V5z'])
export const UploadIcon = mk(['M12 16V5', 'M8 9l4-4 4 4', 'M5 19h14'])
export const ReportIcon = mk(['M7 3h8l4 4v14H7z', 'M9 12h6', 'M9 16h4', 'M14 3v4h4'])
export const PlusIcon = mk(['M12 5v14', 'M5 12h14'])
export const SendIcon = mk(['M5 12l14-7-6 16-3-7-5-2z'])
export const ChevronIcon = mk(['M6 9l6 6 6-6'])
export const SearchIcon = mk(['M11 19a8 8 0 100-16 8 8 0 000 16z', 'M21 21l-4.3-4.3'])
export const FileIcon = mk(['M7 3h8l4 4v14H7z', 'M14 3v4h4'])
export const CheckIcon = mk(['M5 13l4 4L19 7'])
export const SparkIcon = mk(['M12 3v4', 'M12 17v4', 'M3 12h4', 'M17 12h4', 'M6 6l2.5 2.5', 'M15.5 15.5L18 18', 'M18 6l-2.5 2.5', 'M8.5 15.5L6 18'])
export const FilterIcon = mk(['M3 5h18', 'M6 12h12', 'M10 19h4'])
export const CopyIcon = mk(['M9 9h10v10H9z', 'M5 15V5h10'])
export const ArrowDownIcon = mk(['M12 5v14', 'M19 12l-7 7-7-7'])
export const TrendIcon = mk(['M3 17l6-6 4 4 7-7', 'M21 8v4h-4'])
export const XIcon = mk(['M6 6l12 12', 'M18 6L6 18'])
export const PillIcon = mk(['M10.5 13.5l3-3', 'M8 16a4 4 0 010-6l3-3a4 4 0 016 6l-3 3a4 4 0 01-6 0z'])
