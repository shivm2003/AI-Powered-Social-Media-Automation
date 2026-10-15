import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  Image,
  Pressable,
  Linking,
  Alert,
} from 'react-native';
import { Colors } from '../styles/theme';
import { copyCaptionToClipboard } from '../native/intentSharing';

interface SocialPreviewMockupProps {
  productName: string;
  avatarIcon?: string;
  headline: string;
  caption: string;
  hashtags: string[];
  applyUrl?: string;
  ctaText?: string;
}

export const SocialPreviewMockup: React.FC<SocialPreviewMockupProps> = ({
  productName,
  avatarIcon = '🚀',
  headline,
  caption,
  hashtags,
  applyUrl,
  ctaText = 'Shop Now',
}) => {
  const [liked, setLiked] = useState(false);
  const [likeCount, setLikeCount] = useState(1284);
  const [expanded, setExpanded] = useState(false);

  const toggleLike = () => {
    if (liked) {
      setLiked(false);
      setLikeCount((prev) => prev - 1);
    } else {
      setLiked(true);
      setLikeCount((prev) => prev + 1);
    }
  };

  const handleCopy = async () => {
    await copyCaptionToClipboard(caption, applyUrl);
    Alert.alert('📋 Copied!', 'Post caption and CTA link copied to clipboard.');
  };

  return (
    <View style={styles.cardContainer}>
      {/* Feed Card Header */}
      <View style={styles.headerRow}>
        <View style={styles.authorRow}>
          <View style={styles.avatarCircle}>
            <Text style={styles.avatarEmoji}>{avatarIcon}</Text>
          </View>
          <View style={styles.authorTextCol}>
            <View style={styles.nameBadgeRow}>
              <Text style={styles.authorName} numberOfLines={1}>
                {productName}
              </Text>
              <Text style={styles.verifiedBadge}>✓</Text>
            </View>
            <Text style={styles.postMeta}>Sponsored • Universal Feed</Text>
          </View>
        </View>

        <Pressable onPress={handleCopy} style={styles.copyPill}>
          <Text style={styles.copyPillText}>📋 Copy Text</Text>
        </Pressable>
      </View>

      {/* Main Visual Creative Frame */}
      <View style={styles.creativeFrame}>
        <Image
          source={require('../../assets/icon.png')}
          style={styles.creativeImage}
          resizeMode="cover"
        />

        {/* CTA Floating Banner */}
        {applyUrl ? (
          <Pressable
            style={styles.ctaBanner}
            onPress={() => Linking.openURL(applyUrl)}
          >
            <Text style={styles.ctaBannerText}>
              👉 {ctaText} — {applyUrl.replace('https://', '')}
            </Text>
            <Text style={styles.ctaArrow}>→</Text>
          </Pressable>
        ) : null}
      </View>

      {/* Social Engagement Bar */}
      <View style={styles.engagementBar}>
        <View style={styles.leftActions}>
          <Pressable onPress={toggleLike} style={styles.actionBtn}>
            <Text style={styles.actionIcon}>{liked ? '❤️' : '🤍'}</Text>
            <Text style={[styles.actionCount, liked && { color: Colors.rose }]}>
              {likeCount.toLocaleString()}
            </Text>
          </Pressable>

          <View style={styles.actionBtn}>
            <Text style={styles.actionIcon}>💬</Text>
            <Text style={styles.actionCount}>86</Text>
          </View>

          <View style={styles.actionBtn}>
            <Text style={styles.actionIcon}>🚀</Text>
            <Text style={styles.actionCount}>240</Text>
          </View>
        </View>

        <View style={styles.actionBtn}>
          <Text style={styles.actionIcon}>🔖</Text>
        </View>
      </View>

      {/* Caption Content */}
      <View style={styles.captionBox}>
        <Text style={styles.headlineText}>{headline}</Text>

        <Text
          style={styles.bodyCaptionText}
          numberOfLines={expanded ? undefined : 3}
        >
          {caption}
        </Text>

        {caption.length > 100 && (
          <Pressable onPress={() => setExpanded(!expanded)}>
            <Text style={styles.expandText}>
              {expanded ? 'Show Less ▴' : '...more ▾'}
            </Text>
          </Pressable>
        )}

        {/* Hashtags Cloud */}
        <View style={styles.hashtagsRow}>
          {hashtags.map((tag, i) => (
            <Text key={i} style={styles.hashtagPill}>
              {tag}
            </Text>
          ))}
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  cardContainer: {
    backgroundColor: '#0A0F1D',
    borderRadius: 22,
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.12)',
    overflow: 'hidden',
    marginVertical: 10,
    shadowColor: Colors.cyanGlow,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.35,
    shadowRadius: 14,
    elevation: 8,
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  authorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  avatarCircle: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: '#16223D',
    borderWidth: 1.5,
    borderColor: Colors.cyan,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarEmoji: {
    fontSize: 18,
  },
  authorTextCol: {
    marginLeft: 10,
    flex: 1,
  },
  nameBadgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  authorName: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '800',
  },
  verifiedBadge: {
    color: '#00F2FE',
    fontSize: 11,
    fontWeight: '900',
  },
  postMeta: {
    color: Colors.textMuted,
    fontSize: 11,
  },
  copyPill: {
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.14)',
  },
  copyPillText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '700',
  },
  creativeFrame: {
    width: '100%',
    height: 280,
    backgroundColor: '#040711',
    position: 'relative',
  },
  creativeImage: {
    width: '100%',
    height: '100%',
  },
  ctaBanner: {
    position: 'absolute',
    bottom: 12,
    left: 12,
    right: 12,
    backgroundColor: 'rgba(10, 15, 29, 0.92)',
    borderWidth: 1.5,
    borderColor: Colors.cyan,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  ctaBannerText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '800',
    flex: 1,
  },
  ctaArrow: {
    color: Colors.cyan,
    fontSize: 16,
    fontWeight: '900',
    marginLeft: 8,
  },
  engagementBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.06)',
  },
  leftActions: {
    flexDirection: 'row',
    gap: 16,
    alignItems: 'center',
  },
  actionBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  actionIcon: {
    fontSize: 18,
  },
  actionCount: {
    color: Colors.textSecondary,
    fontSize: 12,
    fontWeight: '700',
  },
  captionBox: {
    padding: 14,
  },
  headlineText: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '800',
    marginBottom: 6,
    lineHeight: 20,
  },
  bodyCaptionText: {
    color: '#CBD5E1',
    fontSize: 13,
    lineHeight: 19,
  },
  expandText: {
    color: Colors.cyan,
    fontSize: 12,
    fontWeight: '700',
    marginTop: 4,
  },
  hashtagsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 10,
  },
  hashtagPill: {
    color: Colors.cyan,
    fontSize: 11,
    fontWeight: '600',
    backgroundColor: 'rgba(0, 242, 254, 0.08)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
});
