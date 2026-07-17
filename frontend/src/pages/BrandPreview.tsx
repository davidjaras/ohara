import { OHARA_EMERALD, OHARA_LOGO_GEOMETRY } from '@/components/brand/geometry'
import { OharaLogo } from '@/components/brand/OharaLogo'

const SIZES = [16, 24, 32, 48, 64, 128, 256] as const
const CANDIDATES = [
  { name: 'Candidate A', description: 'Smaller opening', gapDegrees: 46 },
  { name: 'Candidate B', description: 'Balanced opening', gapDegrees: 50 },
  { name: 'Candidate C', description: 'Larger opening', gapDegrees: 54 },
] as const

function CandidateLogo({ gapDegrees }: { gapDegrees: number }) {
  const rotationDegrees = OHARA_LOGO_GEOMETRY.gapCenterDegrees + gapDegrees / 2

  return (
    <svg
      viewBox={OHARA_LOGO_GEOMETRY.viewBox}
      width="128"
      height="128"
      fill="none"
      aria-hidden="true"
    >
      <circle
        cx={OHARA_LOGO_GEOMETRY.center}
        cy={OHARA_LOGO_GEOMETRY.center}
        r={OHARA_LOGO_GEOMETRY.radius}
        stroke="currentColor"
        strokeWidth={OHARA_LOGO_GEOMETRY.strokeWidth}
        strokeLinecap="round"
        pathLength={360}
        strokeDasharray={`${360 - gapDegrees} ${gapDegrees}`}
        transform={`rotate(${rotationDegrees} ${OHARA_LOGO_GEOMETRY.center} ${OHARA_LOGO_GEOMETRY.center})`}
      />
    </svg>
  )
}

const CONTEXTS = [
  {
    label: 'Emerald on dark',
    background: '#0B0F0D',
    foreground: OHARA_EMERALD,
    border: 'rgba(245, 245, 245, 0.14)',
  },
  {
    label: 'White on dark',
    background: '#0B0F0D',
    foreground: '#F5F5F5',
    border: 'rgba(245, 245, 245, 0.14)',
  },
  {
    label: 'Emerald on light',
    background: '#F5F5F5',
    foreground: OHARA_EMERALD,
    border: 'rgba(11, 15, 13, 0.14)',
  },
  {
    label: 'Near-black on light',
    background: '#F5F5F5',
    foreground: '#0B0F0D',
    border: 'rgba(11, 15, 13, 0.14)',
  },
] as const

export function BrandPreview() {
  return (
    <main className="min-h-svh bg-[#0B0F0D] text-[#F5F5F5]">
      <header className="border-b border-white/10">
        <div className="mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-14">
          <div className="mb-8 flex size-28 items-center justify-center rounded-[22px] border border-white/10 bg-[#0B0F0D]" style={{ color: OHARA_EMERALD }}>
            <OharaLogo size={76} title="Ohara" />
          </div>
          <p className="mb-3 text-xs font-semibold uppercase" style={{ color: OHARA_EMERALD }}>
            Internal brand review
          </p>
          <h1 className="text-3xl font-semibold sm:text-4xl">ohara symbol</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-white/60 sm:text-base">
            Open circular O for continuous progress, recurring cycles, and goals.
          </p>
        </div>
      </header>

      <section className="border-b border-white/10">
        <div className="mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-14">
          <div className="mb-7 grid gap-3 sm:flex sm:items-end sm:justify-between">
            <div>
              <p className="text-xs font-medium uppercase text-white/45">Geometry study</p>
              <h2 className="mt-2 text-xl font-semibold">Gap comparison</h2>
            </div>
            <p className="text-sm text-white/45">Centered at 1:30</p>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {CANDIDATES.map((candidate) => (
              <article
                key={candidate.name}
                className="rounded-md border border-white/10 bg-white/[0.025] p-5"
              >
                <div className="flex aspect-square items-center justify-center" style={{ color: OHARA_EMERALD }}>
                  {candidate.gapDegrees === OHARA_LOGO_GEOMETRY.gapDegrees ? (
                    <OharaLogo size={128} />
                  ) : (
                    <CandidateLogo gapDegrees={candidate.gapDegrees} />
                  )}
                </div>
                <div className="mt-5 flex items-start justify-between gap-4 border-t border-white/10 pt-4">
                  <div>
                    <h3 className="text-sm font-semibold">{candidate.name}</h3>
                    <p className="mt-1 text-xs text-white/45">{candidate.description}</p>
                  </div>
                  <div className="text-right">
                    <p className="font-mono text-sm">{candidate.gapDegrees}°</p>
                    {candidate.gapDegrees === OHARA_LOGO_GEOMETRY.gapDegrees && (
                      <p className="mt-1 text-xs font-medium" style={{ color: OHARA_EMERALD }}>Selected</p>
                    )}
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="border-b border-white/10 bg-white/[0.018]">
        <div className="mx-auto grid max-w-6xl gap-8 px-5 py-10 sm:px-8 sm:py-14 md:grid-cols-[1fr_2fr]">
          <div>
            <p className="text-xs font-medium uppercase" style={{ color: OHARA_EMERALD }}>Canonical</p>
            <h2 className="mt-2 text-xl font-semibold">Candidate B</h2>
          </div>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-5 text-sm sm:grid-cols-4">
            <div>
              <dt className="text-white/45">ViewBox</dt>
              <dd className="mt-1 font-mono">64 × 64</dd>
            </div>
            <div>
              <dt className="text-white/45">Radius</dt>
              <dd className="mt-1 font-mono">20 units</dd>
            </div>
            <div>
              <dt className="text-white/45">Stroke</dt>
              <dd className="mt-1 font-mono">7 units</dd>
            </div>
            <div>
              <dt className="text-white/45">Gap</dt>
              <dd className="mt-1 font-mono">50° at 1:30</dd>
            </div>
          </dl>
        </div>
      </section>

      <section className="border-b border-white/10">
        <div className="mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-14">
          <p className="text-xs font-medium uppercase text-white/45">Scale check</p>
          <h2 className="mt-2 text-xl font-semibold">16 to 256 pixels</h2>
          <div className="mt-8 flex flex-wrap items-end gap-x-8 gap-y-10">
            {SIZES.map((size) => (
              <div key={size} className="grid shrink-0 justify-items-center gap-3">
                <div
                  className="flex items-center justify-center"
                  style={{ color: OHARA_EMERALD, width: size, height: size }}
                >
                  <OharaLogo size={size} />
                </div>
                <span className="font-mono text-xs text-white/45">{size}px</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section>
        <div className="mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-14">
          <p className="text-xs font-medium uppercase text-white/45">Color usage</p>
          <h2 className="mt-2 text-xl font-semibold">Approved contexts</h2>
          <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {CONTEXTS.map((context) => (
              <figure
                key={context.label}
                className="overflow-hidden rounded-md border"
                style={{ borderColor: context.border }}
              >
                <div
                  className="flex aspect-square items-center justify-center"
                  style={{ backgroundColor: context.background, color: context.foreground }}
                >
                  <OharaLogo size={112} title={`Ohara, ${context.label.toLowerCase()}`} />
                </div>
                <figcaption className="bg-[#151917] px-4 py-3 text-xs text-white/60">
                  {context.label}
                </figcaption>
              </figure>
            ))}
          </div>
        </div>
      </section>
    </main>
  )
}
