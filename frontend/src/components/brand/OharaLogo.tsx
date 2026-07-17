import { useId, type SVGProps } from 'react'
import { OHARA_LOGO_GEOMETRY } from '@/components/brand/geometry'

export interface OharaLogoProps extends SVGProps<SVGSVGElement> {
  size?: number | string
  title?: string
}

export function OharaLogo({
  size = 32,
  title,
  className,
  role,
  'aria-label': ariaLabel,
  'aria-labelledby': ariaLabelledBy,
  ...svgProps
}: OharaLogoProps) {
  const titleId = useId()
  const hasAccessibleLabel = Boolean(title || ariaLabel || ariaLabelledBy)
  const labelledBy = title
    ? [titleId, ariaLabelledBy].filter(Boolean).join(' ')
    : ariaLabelledBy

  return (
    <svg
      {...svgProps}
      xmlns="http://www.w3.org/2000/svg"
      viewBox={OHARA_LOGO_GEOMETRY.viewBox}
      width={size}
      height={size}
      fill="none"
      className={className}
      role={role ?? (hasAccessibleLabel ? 'img' : undefined)}
      aria-label={ariaLabel}
      aria-labelledby={labelledBy || undefined}
      aria-hidden={hasAccessibleLabel ? undefined : true}
    >
      {title && <title id={titleId}>{title}</title>}
      <circle
        cx={OHARA_LOGO_GEOMETRY.center}
        cy={OHARA_LOGO_GEOMETRY.center}
        r={OHARA_LOGO_GEOMETRY.radius}
        stroke="currentColor"
        strokeWidth={OHARA_LOGO_GEOMETRY.strokeWidth}
        strokeLinecap="round"
        pathLength={360}
        strokeDasharray={`${360 - OHARA_LOGO_GEOMETRY.gapDegrees} ${OHARA_LOGO_GEOMETRY.gapDegrees}`}
        transform={`rotate(${OHARA_LOGO_GEOMETRY.rotationDegrees} ${OHARA_LOGO_GEOMETRY.center} ${OHARA_LOGO_GEOMETRY.center})`}
      />
    </svg>
  )
}
