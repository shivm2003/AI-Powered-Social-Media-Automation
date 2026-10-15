import React from 'react';
import { View, Text, StyleSheet, Image } from 'react-native';
import { Colors } from '../styles/theme';

interface AppHeaderProps {
  memoryUsage?: string;
  totalCampaigns?: number;
}

export const AppHeader: React.FC<AppHeaderProps> = ({
  memoryUsage = '100% On-Device',
  totalCampaigns = 0,
}) => {
  return (
    <View style={styles.headerContainer}>
      {/* 3D App Icon + Title */}
      <View style={styles.brandingRow}>
        <View style={styles.logoFrame3D}>
          <Image
            source={require('../../assets/icon.png')}
            style={styles.logoImage}
            resizeMode="cover"
          />
        </View>

        <View style={styles.titleColumn}>
          <View style={styles.nameRow}>
            <Text style={styles.brandTitle}>MANVIX</Text>
            <Text style={[styles.brandTitle, { color: Colors.cyan }]}> AI</Text>
            <View style={styles.badge3D}>
              <Text style={styles.badgeText}>3D PRO</Text>
            </View>
          </View>
          <Text style={styles.tagline}>Your Social Media, Supercharged by AI</Text>
        </View>
      </View>

      {/* Internal Device Storage Status Capsule */}
      <View style={styles.memoryCapsule}>
        <View style={styles.memoryIndicatorDot} />
        <View style={styles.memoryTextRow}>
          <Text style={styles.memoryLabel}>LOCAL HARDWARE VAULT:</Text>
          <Text style={styles.memoryValue}>
            💾 {memoryUsage} ({totalCampaigns} Saved)
          </Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  headerContainer: {
    paddingHorizontal: 16,
    paddingTop: 48,
    paddingBottom: 14,
    backgroundColor: '#070A12',
    borderBottomWidth: 1.5,
    borderBottomColor: 'rgba(255, 255, 255, 0.08)',
  },
  brandingRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  logoFrame3D: {
    width: 52,
    height: 52,
    borderRadius: 16,
    overflow: 'hidden',
    borderWidth: 1.5,
    borderColor: Colors.cyan,
    shadowColor: Colors.cyanGlow,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.7,
    shadowRadius: 10,
    elevation: 8,
    backgroundColor: '#0D1424',
  },
  logoImage: {
    width: '100%',
    height: '100%',
  },
  titleColumn: {
    marginLeft: 12,
    flex: 1,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  brandTitle: {
    fontSize: 22,
    fontWeight: '900',
    color: '#FFFFFF',
    letterSpacing: 1.2,
  },
  badge3D: {
    marginLeft: 8,
    backgroundColor: 'rgba(124, 92, 252, 0.25)',
    borderWidth: 1,
    borderColor: Colors.primary,
    borderRadius: 6,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  badgeText: {
    color: Colors.cyan,
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  tagline: {
    color: Colors.textSecondary,
    fontSize: 11,
    fontWeight: '600',
    marginTop: 2,
  },
  memoryCapsule: {
    marginTop: 10,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(16, 185, 129, 0.08)',
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.3)',
    borderRadius: 12,
    paddingHorizontal: 12,
    paddingVertical: 6,
    gap: 8,
  },
  memoryIndicatorDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: Colors.emerald,
    shadowColor: Colors.emeraldGlow,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 6,
    elevation: 4,
  },
  memoryTextRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    flexWrap: 'wrap',
  },
  memoryLabel: {
    color: Colors.emerald,
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 0.8,
  },
  memoryValue: {
    color: '#E2E8F0',
    fontSize: 11,
    fontWeight: '600',
  },
});
