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
  const allPlatforms: SupportedPlatform[] = ['instagram', 'facebook', 'whatsapp', 'linkedin'];

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
        <View>
          <Text style={styles.sectionTitle}>TARGET SOCIAL NETWORKS</Text>
          <Text style={styles.sectionSubtitle}>
            {selectedPlatforms.length} of {allPlatforms.length} apps selected for instant broadcast
          </Text>
        </View>
        <View style={styles.quickButtons}>
          <Pressable onPress={selectAll} style={styles.pillAction}>
            <Text style={styles.pillText}>All</Text>
          </Pressable>
          <Pressable onPress={clearAll} style={[styles.pillAction, styles.pillClear]}>
            <Text style={styles.pillTextMuted}>None</Text>
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
                  borderColor: isSelected ? config.color : 'rgba(255, 255, 255, 0.08)',
                  backgroundColor: isSelected ? 'rgba(14, 21, 38, 0.95)' : '#070C18',
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
                    backgroundColor: isSelected ? config.color : '#050811',
                    opacity: isSelected ? 0.4 : 0.8,
                  },
                ]}
              />

              <View style={styles.cardHeader}>
                <Text style={styles.platformIcon}>{config.iconText}</Text>
                <View
                  style={[
                    styles.checkbox,
                    {
                      borderColor: isSelected ? config.color : 'rgba(255, 255, 255, 0.2)',
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
                    fontWeight: isSelected ? '800' : '600',
                  },
                ]}
              >
                {config.name}
              </Text>
              <Text
                style={[
                  styles.appStateBadge,
                  isSelected && { color: config.color, fontWeight: '700' },
                ]}
              >
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
    marginVertical: 4,
  },
  quickBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  sectionTitle: {
    color: Colors.cyan,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.8,
  },
  sectionSubtitle: {
    color: Colors.textMuted,
    fontSize: 11,
    marginTop: 2,
  },
  quickButtons: {
    flexDirection: 'row',
    gap: 6,
  },
  pillAction: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    backgroundColor: 'rgba(0, 242, 254, 0.12)',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(0, 242, 254, 0.3)',
  },
  pillClear: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  pillText: {
    color: Colors.cyan,
    fontSize: 11,
    fontWeight: '700',
  },
  pillTextMuted: {
    color: Colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'space-between',
    rowGap: 10,
  },
  platformCard: {
    width: '48%',
    borderRadius: 16,
    padding: 12,
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
    fontSize: 20,
  },
  checkbox: {
    width: 22,
    height: 22,
    borderRadius: 7,
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
    fontSize: 14,
    marginBottom: 2,
  },
  appStateBadge: {
    color: Colors.textMuted,
    fontSize: 10,
  },
});
