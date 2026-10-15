/**
 * MANVIX AI 3D Luxury Design Tokens & Theme
 * Crafted with custom 3D bevels, holographic glass, and neon cyberpunk glows.
 */
export const Colors = {
  // Deep space obsidian canvas
  background: '#070A12',
  backgroundSecondary: '#0B0F19',
  surface: '#121826',
  surfaceElevated: '#1A2338',
  surfaceGlass: 'rgba(255, 255, 255, 0.05)',
  surfaceGlassBorder: 'rgba(255, 255, 255, 0.12)',

  // 3D Neon Accents
  primary: '#7C5CFC',
  primaryGlow: 'rgba(124, 92, 252, 0.45)',
  cyan: '#00F2FE',
  cyanGlow: 'rgba(0, 242, 254, 0.45)',
  gold: '#FFB347',
  goldGlow: 'rgba(255, 179, 71, 0.45)',
  emerald: '#10B981',
  emeraldGlow: 'rgba(16, 185, 129, 0.45)',
  rose: '#F43F5E',

  // Social Platform Official Hues
  facebook: '#1877F2',
  instagram: '#E4405F',
  whatsapp: '#25D366',
  linkedin: '#0A66C2',

  // Text Hierarchy
  textPrimary: '#FFFFFF',
  textSecondary: '#94A3B8',
  textMuted: '#64748B',

  // Gradients
  gradientPrimary: ['#7C5CFC', '#9061F9'] as const,
  gradientCyber: ['#00F2FE', '#4FACFE'] as const,
  gradient3DCard: ['#141C2E', '#0B0F19'] as const,
  gradientSuccess: ['#10B981', '#059669'] as const,
};

export const Shadows3D = {
  // 3D elevated tile
  card: {
    shadowColor: '#00F2FE',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.18,
    shadowRadius: 12,
    elevation: 8,
  },
  // 3D button with bevel edge
  button: {
    shadowColor: '#7C5CFC',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.4,
    shadowRadius: 16,
    elevation: 10,
  },
  glowPrimary: {
    shadowColor: '#7C5CFC',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.65,
    shadowRadius: 14,
    elevation: 10,
  },
  glowCyan: {
    shadowColor: '#00F2FE',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.65,
    shadowRadius: 14,
    elevation: 10,
  },
  glowEmerald: {
    shadowColor: '#10B981',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.65,
    shadowRadius: 14,
    elevation: 10,
  },
};
