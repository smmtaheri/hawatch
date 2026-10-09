export type GammaChannel = {
  amplitude: number;
  exponent: number;
  offset: number;
};

// Shared by the live route background SVG filters and generated share images.
export const ROUTE_NIGHT_TONE: Record<"desktop" | "mobile", GammaChannel[]> = {
  desktop: [
    { amplitude: 0.5152, exponent: 2.01, offset: 0.0014 },
    { amplitude: 0.4622, exponent: 2.58, offset: 0.1378 },
    { amplitude: 0.4754, exponent: 4, offset: 0.2391 },
  ],
  mobile: [
    { amplitude: 0.5109, exponent: 2.28, offset: 0.0095 },
    { amplitude: 0.5205, exponent: 2.4, offset: 0.1123 },
    { amplitude: 0.498, exponent: 2.61, offset: 0.1995 },
  ],
};
