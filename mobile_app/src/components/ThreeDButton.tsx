import React, { useState } from 'react';
import {
  Pressable,
  Text,
  StyleSheet,
  View,
  ViewStyle,
  TextStyle,
  StyleProp,
  ActivityIndicator,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Colors } from '../styles/theme';

interface ThreeDButtonProps {
  title: string;
  onPress: () => void;
  gradient?: readonly [string, string, ...string[]];
  bevelColor?: string;
  glowColor?: string;
  icon?: React.ReactNode;
  loading?: boolean;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  titleStyle?: StyleProp<TextStyle>;
  height?: number;
}

export const ThreeDButton: React.FC<ThreeDButtonProps> = ({
  title,
  onPress,
  gradient = Colors.gradientCosmic,
  bevelColor = '#3A1E8A',
  glowColor = Colors.primaryGlow,
  icon,
  loading = false,
  disabled = false,
  style,
  titleStyle,
  height = 54,
}) => {
  const [isPressed, setIsPressed] = useState(false);

  return (
    <Pressable
      onPress={onPress}
      onPressIn={() => setIsPressed(true)}
      onPressOut={() => setIsPressed(false)}
      disabled={disabled || loading}
      style={({ pressed }) => [
        styles.outerContainer,
        {
          height,
          shadowColor: glowColor,
          opacity: disabled ? 0.6 : 1,
          transform: [{ translateY: isPressed ? 4 : 0 }],
        },
        style,
      ]}
    >
      {/* 3D Bevel Underside Lip */}
      <View
        style={[
          styles.bevelUnderside,
          {
            backgroundColor: bevelColor,
            bottom: isPressed ? 0 : -5,
          },
        ]}
      />

      {/* Surface Gradient */}
      <LinearGradient
        colors={gradient}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 0 }}
        style={[
          styles.buttonSurface,
          {
            height: height - 4,
          },
        ]}
      >
        {/* Specular highlight */}
        <View style={styles.topGloss} />

        {loading ? (
          <ActivityIndicator color="#FFFFFF" size="small" />
        ) : (
          <View style={styles.contentRow}>
            {icon && <View style={styles.iconWrapper}>{icon}</View>}
            <Text style={[styles.title, titleStyle]}>{title}</Text>
          </View>
        )}
      </LinearGradient>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  outerContainer: {
    marginVertical: 8,
    position: 'relative',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.5,
    shadowRadius: 14,
    elevation: 8,
  },
  bevelUnderside: {
    position: 'absolute',
    left: 2,
    right: 2,
    height: 14,
    borderRadius: 16,
    zIndex: 1,
  },
  buttonSurface: {
    borderRadius: 16,
    zIndex: 2,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.28)',
    overflow: 'hidden',
    paddingHorizontal: 20,
  },
  topGloss: {
    position: 'absolute',
    top: 0,
    left: 12,
    right: 12,
    height: 1.5,
    backgroundColor: 'rgba(255, 255, 255, 0.5)',
    borderRadius: 2,
  },
  contentRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconWrapper: {
    marginRight: 10,
  },
  title: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '800',
    letterSpacing: 0.6,
    textTransform: 'uppercase',
  },
});
