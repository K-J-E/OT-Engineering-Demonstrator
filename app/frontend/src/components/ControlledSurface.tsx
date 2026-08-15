import type { ReactNode } from 'react'

export const FIXED_SIMULATION_NOTICE = 'Simulated operation only — no real equipment control'

export function ControlledSurface({
  surfaceId,
  identityProfile,
  fixedNotice,
  children,
}: {
  surfaceId: string
  identityProfile: string
  fixedNotice: string
  children: ReactNode
}) {
  return (
    <section
      className="controlled-surface"
      data-controlled-surface={surfaceId}
      data-identity-profile={identityProfile}
      data-simulation-notice={fixedNotice}
    >
      {children}
    </section>
  )
}
