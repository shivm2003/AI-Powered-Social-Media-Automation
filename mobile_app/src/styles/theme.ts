/**
 * MANVIX AI — Ultra-Premium 3D Design System & Tokens
 * Futuristic Obsidian Glass, Neon Cyberpunk Accents & Tactile 3D Controls
 */
export const Colors = {
  // Deep space canvas
  background: '#040711',
  backgroundSecondary: '#080D1A',
  surface: '#0E1526',
  surfaceElevated: '#151F36',
  surfaceGlass: 'rgba(255, 255, 255, 0.04)',
  surfaceGlassBorder: 'rgba(255, 255, 255, 0.1)',

  // Vibrant Neon Spectrum
  primary: '#8B5CF6',
  primaryGlow: 'rgba(139, 92, 246, 0.45)',
  cyan: '#00F2FE',
  cyanGlow: 'rgba(0, 242, 254, 0.45)',
  gold: '#F59E0B',
  goldGlow: 'rgba(245, 158, 11, 0.45)',
  emerald: '#10B981',
  emeraldGlow: 'rgba(16, 185, 129, 0.45)',
  rose: '#F43F5E',
  roseGlow: 'rgba(244, 63, 94, 0.45)',
  indigo: '#6366F1',

  // Social Platform Official Hues
  facebook: '#1877F2',
  facebookGlow: 'rgba(24, 119, 242, 0.4)',
  instagram: '#E4405F',
  instagramGlow: 'rgba(228, 64, 95, 0.4)',
  whatsapp: '#25D366',
  whatsappGlow: 'rgba(37, 211, 102, 0.4)',
  linkedin: '#0A66C2',
  linkedinGlow: 'rgba(10, 102, 194, 0.4)',

  // Text Hierarchy
  textPrimary: '#FFFFFF',
  textSecondary: '#94A3B8',
  textMuted: '#64748B',
  textSubtle: '#475569',

  // Gradients
  gradientPrimary: ['#8B5CF6', '#6366F1'] as const,
  gradientCyan: ['#00F2FE', '#4FACFE'] as const,
  gradientCosmic: ['#8B5CF6', '#00F2FE'] as const,
  gradientFire: ['#FF6B6B', '#FF8E53'] as const,
  gradientCard: ['#121B2F', '#090E1C'] as const,
  gradientCardActive: ['#1A2540', '#0D1426'] as const,
  gradientSuccess: ['#10B981', '#059669'] as const,
  gradientGlass: ['rgba(255, 255, 255, 0.08)', 'rgba(255, 255, 255, 0.02)'] as const,
};

export const Shadows3D = {
  card: {
    shadowColor: '#00F2FE',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.22,
    shadowRadius: 14,
    elevation: 8,
  },
  button: {
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.45,
    shadowRadius: 16,
    elevation: 10,
  },
  glowCyan: {
    shadowColor: '#00F2FE',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.7,
    shadowRadius: 12,
    elevation: 8,
  },
  glowPrimary: {
    shadowColor: '#8B5CF6',
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.7,
    shadowRadius: 12,
    elevation: 8,
  },
};
