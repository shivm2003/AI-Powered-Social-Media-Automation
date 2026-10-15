import React from 'react';
import { View, StyleSheet, ViewStyle, StyleProp } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors } from '../styles/theme';

interface ThreeDCardProps {
  children: React.ReactNode;
  style?: StyleProp<ViewStyle>;
  glowColor?: string;
  borderColor?: string;
  gradientColors?: readonly [string, string, ...string[]];
  depth?: number;
}

export const ThreeDCard: React.FC<ThreeDCardProps> = ({
  children,
  style,
  glowColor = Colors.cyanGlow,
  borderColor = 'rgba(255, 255, 255, 0.1)',
  gradientColors = Colors.gradientCard,
  depth = 4,
}) => {
  return (
    <View
      style={[
        styles.outerContainer,
        {
          shadowColor: glowColor,
          borderBottomWidth: depth,
          borderBottomColor: 'rgba(0, 0, 0, 0.7)',
        },
        style,
      ]}
    >
      <LinearGradient
        colors={gradientColors}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={[
          styles.innerCard,
          {
            borderColor: borderColor,
          },
        ]}
      >
        {/* Subtle Top Specular Glass Reflection */}
        <View style={styles.specularHighlight} />
        {children}
      </LinearGradient>
    </View>
  );
};

const styles = StyleSheet.create({
  outerContainer: {
    borderRadius: 22,
    backgroundColor: '#050811',
    marginVertical: 8,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.35,
    shadowRadius: 12,
    elevation: 8,
    position: 'relative',
  },
  innerCard: {
    borderRadius: 22,
    padding: 16,
    borderWidth: 1.5,
    overflow: 'hidden',
    position: 'relative',
  },
  specularHighlight: {
    position: 'absolute',
    top: 0,
    left: 24,
    right: 24,
    height: 1.5,
    backgroundColor: 'rgba(255, 255, 255, 0.35)',
    borderRadius: 1,
  },
});
