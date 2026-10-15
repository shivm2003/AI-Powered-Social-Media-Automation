import React from 'react';
import { View, Text, StyleSheet, Image, Platform, StatusBar as RNStatusBar } from 'react-native';
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

        {/* Compact On-Device Vault Pill */}
        <View style={styles.vaultCapsule}>
          <View style={styles.vaultDot} />
          <Text style={styles.vaultText}>100% OFFLINE</Text>
        </View>
      </View>
    </View>
  );
};

const topInset = Platform.OS === 'android' ? (RNStatusBar.currentHeight || 28) + 8 : 48;

const styles = StyleSheet.create({
  headerContainer: {
    paddingHorizontal: 16,
    paddingTop: topInset,
    paddingBottom: 12,
    backgroundColor: '#040711',
    borderBottomWidth: 1.5,
    borderBottomColor: 'rgba(255, 255, 255, 0.08)',
  },
  brandingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  logoFrame3D: {
    width: 44,
    height: 44,
    borderRadius: 14,
    overflow: 'hidden',
    borderWidth: 1.5,
    borderColor: Colors.cyan,
    shadowColor: Colors.cyanGlow,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.6,
    shadowRadius: 8,
    elevation: 8,
    backgroundColor: '#0A0F1D',
  },
  logoImage: {
    width: '100%',
    height: '100%',
  },
  titleColumn: {
    marginLeft: 10,
    flex: 1,
  },
  nameRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  brandTitle: {
    fontSize: 20,
    fontWeight: '900',
    color: '#FFFFFF',
    letterSpacing: 1,
  },
  badge3D: {
    marginLeft: 6,
    backgroundColor: 'rgba(139, 92, 246, 0.25)',
    borderWidth: 1,
    borderColor: Colors.primary,
    borderRadius: 6,
    paddingHorizontal: 5,
    paddingVertical: 1,
  },
  badgeText: {
    color: Colors.cyan,
    fontSize: 8,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  tagline: {
    color: Colors.textMuted,
    fontSize: 10,
    fontWeight: '600',
    marginTop: 1,
  },
  vaultCapsule: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(16, 185, 129, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.35)',
    borderRadius: 10,
    paddingHorizontal: 8,
    paddingVertical: 4,
    gap: 6,
  },
  vaultDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.emerald,
    shadowColor: Colors.emeraldGlow,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.8,
    shadowRadius: 4,
    elevation: 4,
  },
  vaultText: {
    color: Colors.emerald,
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
});
