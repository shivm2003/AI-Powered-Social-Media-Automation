import React from 'react';
import { View, Text, StyleSheet, Pressable } from 'react-native';
import { Colors } from '../styles/theme';
import { SupportedPlatform, PLATFORMS_CONFIG } from '../native/intentSharing';

interface PlatformMatrixProps {
  selectedPlatforms: SupportedPlatform[];
  onChange: (platforms: SupportedPlatform[]) => void;
}

export const PlatformMatrix: React.FC<PlatformMatrixProps> = ({
  selectedPlatforms,
  onChange,
}) => {
  const allPlatforms: SupportedPlatform[] = ['facebook', 'instagram', 'whatsapp', 'linkedin'];

  const togglePlatform = (plat: SupportedPlatform) => {
    if (selectedPlatforms.includes(plat)) {
      onChange(selectedPlatforms.filter((p) => p !== plat));
    } else {
      onChange([...selectedPlatforms, plat]);
    }
  };

  const selectAll = () => {
    onChange([...allPlatforms]);
  };

  const clearAll = () => {
    onChange([]);
  };

  return (
    <View style={styles.container}>
      {/* Quick Select Bar */}
      <View style={styles.quickBar}>
        <Text style={styles.sectionTitle}>Target Installed Apps</Text>
        <View style={styles.quickButtons}>
          <Pressable onPress={selectAll} style={styles.pillAction}>
            <Text style={styles.pillText}>Select All</Text>
          </Pressable>
          <Pressable onPress={clearAll} style={[styles.pillAction, styles.pillClear]}>
            <Text style={styles.pillTextMuted}>Clear</Text>
          </Pressable>
        </View>
      </View>

      {/* 2x2 Platform Grid */}
      <View style={styles.grid}>
        {allPlatforms.map((plat) => {
          const config = PLATFORMS_CONFIG[plat];
          const isSelected = selectedPlatforms.includes(plat);

          return (
            <Pressable
              key={plat}
              onPress={() => togglePlatform(plat)}
              style={({ pressed }) => [
                styles.platformCard,
                {
                  borderColor: isSelected ? config.color : 'rgba(255, 255, 255, 0.1)',
                  shadowColor: isSelected ? config.glowColor : 'transparent',
                  transform: [{ translateY: pressed ? 2 : 0 }],
                },
              ]}
            >
              {/* 3D Bottom Bevel Edge */}
              <View
                style={[
                  styles.cardBevel,
                  {
                    backgroundColor: isSelected ? config.color : '#0A0E17',
                    opacity: isSelected ? 0.35 : 0.8,
                  },
                ]}
              />

              <View style={styles.cardHeader}>
                <Text style={styles.platformIcon}>{config.iconText}</Text>
                <View
                  style={[
                    styles.checkbox,
                    {
                      borderColor: isSelected ? config.color : 'rgba(255, 255, 255, 0.25)',
                      backgroundColor: isSelected ? config.color : 'transparent',
                    },
                  ]}
                >
                  {isSelected && <Text style={styles.checkmark}>✓</Text>}
                </View>
              </View>

              <Text
                style={[
                  styles.platformName,
                  {
                    color: isSelected ? '#FFFFFF' : Colors.textSecondary,
                    fontWeight: isSelected ? '700' : '500',
                  },
                ]}
              >
                {config.name}
              </Text>
              <Text style={styles.appStateBadge}>
                {isSelected ? 'Ready to post' : 'Tap to enable'}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: 10,
  },
  quickBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  quickButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  pillAction: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    backgroundColor: 'rgba(124, 92, 252, 0.15)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(124, 92, 252, 0.3)',
  },
  pillClear: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  pillText: {
    color: Colors.cyan,
    fontSize: 11,
    fontWeight: '600',
  },
  pillTextMuted: {
    color: Colors.textMuted,
    fontSize: 11,
    fontWeight: '600',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  platformCard: {
    width: '48%',
    backgroundColor: '#0D1424',
    borderRadius: 16,
    padding: 14,
    borderWidth: 1.5,
    position: 'relative',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.45,
    shadowRadius: 10,
    elevation: 6,
  },
  cardBevel: {
    position: 'absolute',
    bottom: -4,
    left: 4,
    right: 4,
    height: 8,
    borderRadius: 10,
    zIndex: -1,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  platformIcon: {
    fontSize: 22,
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 6,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  checkmark: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '900',
  },
  platformName: {
    fontSize: 15,
    marginBottom: 2,
  },
  appStateBadge: {
    color: Colors.textMuted,
    fontSize: 11,
  },
});
