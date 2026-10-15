import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  Alert,
  Linking,
  Pressable,
} from 'react-native';
import { Colors } from '../styles/theme';
import { ThreeDCard } from '../components/ThreeDCard';
import { ThreeDButton } from '../components/ThreeDButton';
import { PlatformMatrix } from '../components/PlatformMatrix';
import { SocialPreviewMockup } from '../components/SocialPreviewMockup';
import {
  SupportedPlatform,
  broadcastToMultiplePlatforms,
  copyCaptionToClipboard,
} from '../native/intentSharing';
import { exportToDeviceGallery } from '../storage/mediaStorage';
import { Campaign, markCampaignPosted, saveCampaign } from '../db/database';

interface ApprovalScreenProps {
  campaign: Campaign;
  onCampaignUpdated?: (campaign: Campaign) => void;
  onNavigateToVault?: () => void;
}

export const ApprovalScreen: React.FC<ApprovalScreenProps> = ({
  campaign,
  onCampaignUpdated,
  onNavigateToVault,
}) => {
  const [selectedPlatforms, setSelectedPlatforms] = useState<SupportedPlatform[]>(
    (campaign.platforms as SupportedPlatform[]) || ['instagram', 'facebook']
  );
  const [headline, setHeadline] = useState(campaign.headline);
  const [caption, setCaption] = useState(campaign.caption);
  const [applyUrl, setApplyUrl] = useState(campaign.apply_url || 'https://mybrand.com');
  const [broadcasting, setBroadcasting] = useState(false);
  const [editMode, setEditMode] = useState(false);

  const handleCopyCaption = async () => {
    await copyCaptionToClipboard(caption, applyUrl);
    Alert.alert('📋 Copied!', 'The full caption and CTA link have been copied to your clipboard!');
  };

  const handleExportMedia = async () => {
    const success = await exportToDeviceGallery(campaign.local_image_uri);
    if (success) {
      Alert.alert('🖼️ Media Exported', 'The creative has been shared/saved.');
    }
  };

  const handleBroadcast = async () => {
    if (selectedPlatforms.length === 0) {
      Alert.alert('Select Target Apps', 'Please select at least one social app (Instagram, Facebook, WhatsApp, or LinkedIn) to proceed.');
      return;
    }

    setBroadcasting(true);

    try {
      // 1. Copy caption to clipboard so user can immediately paste in social media composer
      await copyCaptionToClipboard(caption, applyUrl);

      // 2. Launch Android multi-platform broadcast
      await broadcastToMultiplePlatforms(
        selectedPlatforms,
        campaign.local_image_uri,
        caption,
        applyUrl
      );

      // 3. Mark campaign as posted in on-device SQLite database
      markCampaignPosted(campaign.id, selectedPlatforms);

      // 4. Update memory object
      const updated: Campaign = {
        ...campaign,
        headline,
        caption,
        apply_url: applyUrl,
        platforms: selectedPlatforms,
        status: 'posted',
        posted_at: Date.now(),
      };
      saveCampaign(updated);

      if (onCampaignUpdated) {
        onCampaignUpdated(updated);
      }

      Alert.alert(
        '🚀 Multi-App Broadcast Launched!',
        `1. Caption & CTA link copied to clipboard.\n2. Dispatched to selected apps: ${selectedPlatforms.join(', ')}.\n3. Updated in local device database.`,
        [
          { text: 'View Vault History', onPress: onNavigateToVault },
          { text: 'Done', style: 'default' },
        ]
      );
    } catch (e: any) {
      Alert.alert('Broadcast Notice', e.message || 'Share operation initiated.');
    } finally {
      setBroadcasting(false);
    }
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      {/* Top Banner */}
      <ThreeDCard glowColor={Colors.primaryGlow} borderColor="rgba(139, 92, 246, 0.4)">
        <View style={styles.topStatusRow}>
          <Text style={styles.bannerBadge}>DIRECT NATIVE DISPATCH HUB</Text>
          <View style={styles.memoryPill}>
            <Text style={styles.memoryPillText}>💾 100% OFFLINE</Text>
          </View>
        </View>
        <Text style={styles.bannerTitle}>Review & Multi-App Publish</Text>
        <Text style={styles.bannerDesc}>
          Approve copy for "{campaign.product_name}" and launch simultaneously to Instagram, Facebook, WhatsApp, and LinkedIn via Android Intents.
        </Text>
      </ThreeDCard>

      {/* Realistic Social Feed Mockup Card */}
      <SocialPreviewMockup
        productName={campaign.product_name}
        headline={headline}
        caption={caption}
        hashtags={campaign.hashtags}
        applyUrl={applyUrl}
        ctaText="Shop Now"
      />

      {/* Quick Action Toolbar */}
      <View style={styles.quickActionRow}>
        <Pressable onPress={handleCopyCaption} style={styles.actionPill}>
          <Text style={styles.actionPillIcon}>📋</Text>
          <Text style={styles.actionPillText}>Copy Text</Text>
        </Pressable>

        <Pressable onPress={() => setEditMode(!editMode)} style={styles.actionPill}>
          <Text style={styles.actionPillIcon}>✏️</Text>
          <Text style={styles.actionPillText}>{editMode ? 'Close Edit' : 'Edit Copy'}</Text>
        </Pressable>

        <Pressable onPress={handleExportMedia} style={styles.actionPill}>
          <Text style={styles.actionPillIcon}>💾</Text>
          <Text style={styles.actionPillText}>Save Image</Text>
        </Pressable>
      </View>

      {/* Inline Editor Drawer (if enabled) */}
      {editMode && (
        <ThreeDCard glowColor="rgba(255, 255, 255, 0.15)">
          <Text style={styles.cardHeaderSmall}>HEADLINE (CLICK TO EDIT)</Text>
          <TextInput
            style={styles.headlineInput}
            value={headline}
            onChangeText={setHeadline}
            multiline
          />

          <Text style={[styles.cardHeaderSmall, { marginTop: 14 }]}>MARKETING CAPTION (CLICK TO EDIT)</Text>
          <TextInput
            style={styles.captionInput}
            value={caption}
            onChangeText={setCaption}
            multiline
            numberOfLines={5}
          />

          <Text style={[styles.cardHeaderSmall, { marginTop: 14 }]}>CTA / STORE URL</Text>
          <TextInput
            style={styles.headlineInput}
            value={applyUrl}
            onChangeText={setApplyUrl}
            autoCapitalize="none"
          />
        </ThreeDCard>
      )}

      {/* 3D Platform Selector Matrix */}
      <ThreeDCard glowColor={Colors.primaryGlow} borderColor="rgba(139, 92, 246, 0.3)">
        <PlatformMatrix
          selectedPlatforms={selectedPlatforms}
          onChange={setSelectedPlatforms}
        />
      </ThreeDCard>

      {/* Master 3D Broadcast Button */}
      <ThreeDButton
        title={
          broadcasting
            ? 'Dispatching Android Intents...'
            : `🚀 Broadcast to ${selectedPlatforms.length} Selected Apps`
        }
        onPress={handleBroadcast}
        loading={broadcasting}
        gradient={Colors.gradientCosmic}
        glowColor={Colors.cyanGlow}
        bevelColor="#381D9E"
        style={{ marginTop: 14 }}
      />

      <View style={{ height: 40 }} />
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  content: {
    padding: 16,
    paddingBottom: 40,
  },
  topStatusRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  bannerBadge: {
    color: Colors.cyan,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8,
  },
  memoryPill: {
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.35)',
  },
  memoryPillText: {
    color: Colors.emerald,
    fontSize: 9,
    fontWeight: '800',
  },
  bannerTitle: {
    fontSize: 20,
    fontWeight: '900',
    color: '#FFFFFF',
  },
  bannerDesc: {
    color: Colors.textSecondary,
    fontSize: 12,
    lineHeight: 18,
    marginTop: 4,
  },
  quickActionRow: {
    flexDirection: 'row',
    gap: 8,
    marginVertical: 4,
  },
  actionPill: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0A0F1D',
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
    paddingVertical: 10,
    gap: 6,
  },
  actionPillIcon: {
    fontSize: 14,
  },
  actionPillText: {
    color: '#E2E8F0',
    fontSize: 12,
    fontWeight: '700',
  },
  cardHeaderSmall: {
    color: Colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8,
    marginBottom: 8,
  },
  headlineInput: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '700',
    backgroundColor: '#070A12',
    padding: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  captionInput: {
    color: Colors.textSecondary,
    fontSize: 13,
    backgroundColor: '#070A12',
    padding: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    textAlignVertical: 'top',
    minHeight: 100,
    lineHeight: 19,
  },
});
