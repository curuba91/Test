/** Absolute pressure in bar at a given depth (metres) in seawater (1 bar per 10 m). */
export function absolutePressure(depthM: number, surfaceBar = 1.013): number {
  return surfaceBar + depthM / 10
}

/** Partial pressure of a gas fraction at depth. */
export function partialPressure(fraction: number, depthM: number): number {
  return fraction * absolutePressure(depthM, 1)
}

/** Maximum Operating Depth for a given O2 fraction (0–1) and ppO2 limit. */
export function mod(fO2: number, ppO2Max: number): number {
  return (ppO2Max / fO2 - 1) * 10
}

/** Equivalent Air Depth for a nitrox mix. */
export function ead(fO2: number, depthM: number): number {
  const fN2 = 1 - fO2
  return ((fN2 * (depthM + 10)) / 0.79) - 10
}

/** Best mix (O2 fraction) for a target depth and ppO2 limit. */
export function bestMix(depthM: number, ppO2Max: number): number {
  return ppO2Max / absolutePressure(depthM, 1)
}

/** Surface air consumption (bar/min at surface) from a dive segment. */
export function sacBarPerMin(startBar: number, endBar: number, minutes: number, avgDepthM: number): number {
  const used = startBar - endBar
  return used / minutes / absolutePressure(avgDepthM, 1)
}

/** Respiratory minute volume in litres/min from SAC and cylinder size. */
export function rmv(sacBar: number, cylinderLitres: number): number {
  return sacBar * cylinderLitres
}

/** Gas duration in minutes at depth with a reserve. */
export function gasDuration(
  rmvLpm: number,
  cylinderLitres: number,
  startBar: number,
  reserveBar: number,
  depthM: number,
): number {
  const usable = (startBar - reserveBar) * cylinderLitres
  const consumption = rmvLpm * absolutePressure(depthM, 1)
  return usable / consumption
}

/** Boyle's law: volume at depth from surface volume. */
export function volumeAtDepth(surfaceVolume: number, depthM: number): number {
  return surfaceVolume / absolutePressure(depthM, 1)
}

/**
 * Simplified recreational no‑decompression limits (minutes) per depth in metres.
 * Educational values approximating common recreational tables. NOT for real dive planning.
 */
export const NDL_TABLE: Record<number, number> = {
  10: 219,
  12: 147,
  14: 98,
  16: 72,
  18: 56,
  20: 45,
  22: 37,
  25: 29,
  30: 20,
  35: 14,
  40: 9,
}

export function ndlForDepth(depthM: number): number | null {
  const depths = Object.keys(NDL_TABLE).map(Number).sort((a, b) => a - b)
  if (depthM > depths[depths.length - 1]) return null
  for (const d of depths) {
    if (depthM <= d) return NDL_TABLE[d]
  }
  return null
}

/** Rough weight estimation in kg (very simplified rule of thumb). */
export function estimateWeight(bodyKg: number, suit: 'none' | 'shorty' | '3mm' | '5mm' | '7mm' | 'dry', saltwater: boolean, aluCylinder: boolean): number {
  const base: Record<typeof suit, number> = { none: 0.02, shorty: 0.05, '3mm': 0.07, '5mm': 0.09, '7mm': 0.11, dry: 0.13 }
  let w = bodyKg * base[suit]
  if (saltwater) w += 2
  if (aluCylinder) w += 1.5
  return Math.round(w * 2) / 2
}

export function round(n: number, digits = 1): number {
  const p = Math.pow(10, digits)
  return Math.round(n * p) / p
}
