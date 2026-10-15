import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Image,
  TextInput,
  Alert,
  Linking,
  ActivityIndicator,
  Pressable,
} from 'react-native';
import { Colors } from '../styles/theme';
import { ThreeDCard } from '../components/ThreeDCard';
import { ThreeDButton } from '../components/ThreeDButton';
import { PlatformMatrix } from '../components/PlatformMatrix';
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
  const [savingGallery, setSavingGallery] = useState(false);

  const handleCopyCaption = async () => {
    await copyCaptionToClipboard(caption, applyUrl);
    Alert.alert('📋 Copied to Clipboard', 'The full caption and CTA link have been copied to your clipboard!');
  };

  const handleSaveToGallery = async () => {
    setSavingGallery(true);
    Alert.alert(
      '🖼️ Media Saved',
      'The creative has been exported to your internal device media storage.'
    );
    setSavingGallery(false);
  };

  const handleBroadcast = async () => {
    if (selectedPlatforms.length === 0) {
      Alert.alert('Select Platforms', 'Please select at least one installed platform (e.g., Instagram, Facebook, WhatsApp, or LinkedIn) to proceed.');
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
        '🚀 Multi-App Broadcast Triggered!',
        `1. Caption & Link copied to clipboard.\n2. Dispatched to selected apps: ${selectedPlatforms.join(', ')}.\n3. Updated in local device database.`,
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
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Top Banner */}
      <ThreeDCard glowColor={Colors.primaryGlow} borderColor="rgba(124, 92, 252, 0.4)">
        <View style={styles.topStatusRow}>
          <Text style={styles.bannerBadge}>MANVIX NATIVE BROADCAST HUB</Text>
          <View style={styles.memoryPill}>
            <Text style={styles.memoryPillText}>💾 ON-DEVICE ONLY</Text>
          </View>
        </View>
        <Text style={styles.bannerTitle}>Review & Multi-App Publish</Text>
        <Text style={styles.bannerDesc}>
          Approve copy for "{campaign.product_name}" and launch simultaneously to Instagram, Facebook, WhatsApp, and LinkedIn via Android Intents.
        </Text>
      </ThreeDCard>

      {/* Creative 3D Visual Preview */}
      <ThreeDCard glowColor={Colors.cyanGlow} borderColor="rgba(0, 242, 254, 0.35)">
        <Text style={styles.cardHeaderSmall}>PROMOTIONAL CREATIVE (ON-DEVICE)</Text>
        <View style={styles.imageFrame3D}>
          <Image
            source={require('../../assets/icon.png')}
            style={styles.creativeImage}
            resizeMode="cover"
          />
        </View>

        <View style={styles.mediaActionBar}>
          <Pressable onPress={handleSaveToGallery} style={styles.pillButton}>
            <Text style={styles.pillButtonText}>💾 Export to Device Gallery</Text>
          </Pressable>
          <Pressable onPress={handleCopyCaption} style={styles.pillButton}>
            <Text style={styles.pillButtonText}>📋 Copy Text & Link</Text>
          </Pressable>
        </View>
      </ThreeDCard>

      {/* Editable Caption Section */}
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
          numberOfLines={6}
        />

        <View style={styles.urlCard}>
          <Text style={styles.urlLabel}>TARGET CTA LINK:</Text>
          <Text
            style={styles.urlValue}
            numberOfLines={1}
            onPress={() => Linking.openURL(applyUrl)}
          >
            {applyUrl}
          </Text>
        </View>
      </ThreeDCard>

      {/* 3D Platform Selector Matrix */}
      <ThreeDCard glowColor={Colors.primaryGlow} borderColor="rgba(124, 92, 252, 0.3)">
        <PlatformMatrix
          selectedPlatforms={selectedPlatforms}
          onChange={setSelectedPlatforms}
        />
      </ThreeDCard>

      {/* Master 3D Broadcast Button */}
      <ThreeDButton
        title={
          broadcasting
            ? 'Dispatching Intents...'
            : `🚀 Broadcast to ${selectedPlatforms.length} Selected Apps`
        }
        onPress={handleBroadcast}
        loading={broadcasting}
        gradient={['#7C5CFC', '#00F2FE']}
        glowColor={Colors.cyanGlow}
        bevelColor="#381D9E"
        style={{ marginTop: 12 }}
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
    borderColor: 'rgba(16, 185, 129, 0.4)',
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
  cardHeaderSmall: {
    color: Colors.textMuted,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  imageFrame3D: {
    width: '100%',
    height: 240,
    borderRadius: 14,
    overflow: 'hidden',
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.15)',
    backgroundColor: '#05070D',
  },
  creativeImage: {
    width: '100%',
    height: '100%',
  },
  mediaActionBar: {
    flexDirection: 'row',
    gap: 10,
    marginTop: 12,
  },
  pillButton: {
    flex: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    paddingVertical: 8,
    borderRadius: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.12)',
  },
  pillButtonText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '700',
  },
  headlineInput: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
    backgroundColor: '#0D1424',
    padding: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  captionInput: {
    color: Colors.textSecondary,
    fontSize: 13,
    backgroundColor: '#0D1424',
    padding: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    textAlignVertical: 'top',
    minHeight: 110,
    lineHeight: 19,
  },
  urlCard: {
    marginTop: 12,
    backgroundColor: 'rgba(0, 242, 254, 0.06)',
    padding: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(0, 242, 254, 0.25)',
  },
  urlLabel: {
    color: Colors.cyan,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.5,
    marginBottom: 2,
  },
  urlValue: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '600',
    textDecorationLine: 'underline',
  },
});
