import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  RefreshControl,
  Alert,
  TextInput,
} from 'react-native';
import { Colors } from '../styles/theme';
import { ThreeDCard } from '../components/ThreeDCard';
import { ThreeDButton } from '../components/ThreeDButton';
import { getAllCampaigns, deleteCampaign, Campaign } from '../db/database';
import { copyCaptionToClipboard } from '../native/intentSharing';

interface VaultScreenProps {
  onSelectCampaignForBroadcast: (campaign: Campaign) => void;
  onNavigate: (tab: 'home' | 'studio' | 'approval' | 'vault') => void;
}

export const VaultScreen: React.FC<VaultScreenProps> = ({
  onSelectCampaignForBroadcast,
  onNavigate,
}) => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<'all' | 'approved' | 'posted'>('all');
  const [refreshing, setRefreshing] = useState(false);

  const loadData = () => {
    try {
      const all = getAllCampaigns();
      setCampaigns(all);
    } catch (e) {
      console.error('Error loading vault campaigns:', e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
    setRefreshing(false);
  };

  const filteredList = campaigns.filter((c) => {
    if (filter !== 'all' && c.status !== filter) return false;
    if (searchQuery.trim().length > 0) {
      const q = searchQuery.toLowerCase();
      const inName = (c.product_name || '').toLowerCase().includes(q);
      const inHead = (c.headline || '').toLowerCase().includes(q);
      const inCap = (c.caption || '').toLowerCase().includes(q);
      return inName || inHead || inCap;
    }
    return true;
  });

  const handleCopyCaption = async (c: Campaign) => {
    await copyCaptionToClipboard(c.caption, c.apply_url);
    Alert.alert('📋 Copied!', 'Caption and CTA URL copied to clipboard.');
  };

  const handleDeleteCampaign = (c: Campaign) => {
    Alert.alert(
      'Delete Campaign',
      'Remove this campaign permanently from your on-device storage?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            deleteCampaign(c.id);
            loadData();
          },
        },
      ]
    );
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.cyan} />}
    >
      {/* Vault Info Header */}
      <ThreeDCard glowColor={Colors.emeraldGlow} borderColor="rgba(16, 185, 129, 0.35)">
        <View style={styles.vaultHeaderRow}>
          <Text style={styles.vaultBadge}>100% OFFLINE SQLITE REPOSITORY</Text>
          <View style={styles.lockPill}>
            <Text style={styles.lockText}>🔐 SECURE HARDWARE</Text>
          </View>
        </View>
        <Text style={styles.vaultTitle}>On-Device Campaign Vault</Text>
        <Text style={styles.vaultDesc}>
          All campaigns, custom angles, and published history are encrypted in SQLite internal memory on your Android phone. Zero cloud servers.
        </Text>
      </ThreeDCard>

      {/* Search Bar */}
      <View style={styles.searchBarContainer}>
        <Text style={styles.searchIcon}>🔍</Text>
        <TextInput
          style={styles.searchInput}
          placeholder="Search campaigns, brands, or copy..."
          placeholderTextColor={Colors.textMuted}
          value={searchQuery}
          onChangeText={setSearchQuery}
        />
        {searchQuery.length > 0 && (
          <Pressable onPress={() => setSearchQuery('')}>
            <Text style={styles.clearSearch}>✕</Text>
          </Pressable>
        )}
      </View>

      {/* Filter Tabs */}
      <View style={styles.filterRow}>
        {(['all', 'approved', 'posted'] as const).map((tab) => {
          const isSelected = filter === tab;
          const count = campaigns.filter((c) => (tab === 'all' ? true : c.status === tab)).length;
          return (
            <Pressable
              key={tab}
              onPress={() => setFilter(tab)}
              style={[
                styles.filterTab,
                {
                  backgroundColor: isSelected ? 'rgba(0, 242, 254, 0.12)' : '#0A0F1D',
                  borderColor: isSelected ? Colors.cyan : 'rgba(255, 255, 255, 0.08)',
                },
              ]}
            >
              <Text
                style={[
                  styles.filterTabText,
                  { color: isSelected ? Colors.cyan : Colors.textSecondary },
                ]}
              >
                {tab.toUpperCase()} ({count})
              </Text>
            </Pressable>
          );
        })}
      </View>

      {/* List of Stored Campaigns */}
      {filteredList.length === 0 ? (
        <ThreeDCard>
          <Text style={styles.emptyText}>No campaigns match your search or filter.</Text>
        </ThreeDCard>
      ) : (
        filteredList.map((c) => (
          <ThreeDCard key={c.id} glowColor="rgba(255, 255, 255, 0.12)">
            <View style={styles.cardHeader}>
              <View style={styles.headerLeft}>
                <View
                  style={[
                    styles.statusTag,
                    {
                      borderColor:
                        c.status === 'posted'
                          ? Colors.emerald
                          : Colors.primary,
                      backgroundColor:
                        c.status === 'posted'
                          ? 'rgba(16, 185, 129, 0.12)'
                          : 'rgba(139, 92, 246, 0.15)',
                    },
                  ]}
                >
                  <Text
                    style={[
                      styles.statusTagText,
                      {
                        color:
                          c.status === 'posted'
                            ? Colors.emerald
                            : Colors.cyan,
                      },
                    ]}
                  >
                    {c.status.toUpperCase()}
                  </Text>
                </View>
                <Text style={styles.prodTag}>{c.product_name}</Text>
              </View>

              <View style={styles.headerRight}>
                <Text style={styles.dateStamp}>
                  {c.posted_at
                    ? `Posted: ${new Date(c.posted_at).toLocaleTimeString()}`
                    : `Created: ${new Date(c.created_at).toLocaleDateString()}`}
                </Text>
                <Pressable onPress={() => handleDeleteCampaign(c)} style={styles.deleteBtn}>
                  <Text style={styles.deleteBtnText}>🗑️</Text>
                </Pressable>
              </View>
            </View>

            <Text style={styles.campaignHeadline}>{c.headline}</Text>
            <Text style={styles.campaignCaption} numberOfLines={3}>
              {c.caption}
            </Text>

            <View style={styles.tagsContainer}>
              {c.hashtags.slice(0, 4).map((tag, i) => (
                <Text key={i} style={styles.tagText}>
                  {tag}
                </Text>
              ))}
            </View>

            <View style={styles.actionsBar}>
              <Pressable
                onPress={() => handleCopyCaption(c)}
                style={styles.secondaryAction}
              >
                <Text style={styles.secondaryActionText}>📋 Copy Text</Text>
              </Pressable>

              <ThreeDButton
                title="Broadcast 🚀"
                height={38}
                onPress={() => {
                  onSelectCampaignForBroadcast(c);
                  onNavigate('approval');
                }}
                style={{ marginVertical: 0, minWidth: 130 }}
              />
            </View>
          </ThreeDCard>
        ))
      )}

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
  vaultHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  vaultBadge: {
    color: Colors.emerald,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8,
  },
  lockPill: {
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.35)',
  },
  lockText: {
    color: Colors.emerald,
    fontSize: 9,
    fontWeight: '800',
  },
  vaultTitle: {
    fontSize: 20,
    fontWeight: '900',
    color: '#FFFFFF',
  },
  vaultDesc: {
    color: Colors.textSecondary,
    fontSize: 12,
    lineHeight: 18,
    marginTop: 4,
  },
  searchBarContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0A0F1D',
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 14,
    paddingHorizontal: 12,
    paddingVertical: 8,
    marginTop: 12,
  },
  searchIcon: {
    fontSize: 16,
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    color: '#FFFFFF',
    fontSize: 13,
  },
  clearSearch: {
    color: Colors.textMuted,
    fontSize: 14,
    paddingHorizontal: 6,
  },
  filterRow: {
    flexDirection: 'row',
    gap: 8,
    marginVertical: 12,
  },
  filterTab: {
    flex: 1,
    paddingVertical: 9,
    borderRadius: 12,
    alignItems: 'center',
    borderWidth: 1,
  },
  filterTabText: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  headerRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusTag: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    borderWidth: 1,
  },
  statusTagText: {
    fontSize: 10,
    fontWeight: '800',
  },
  prodTag: {
    color: Colors.cyan,
    fontSize: 11,
    fontWeight: '700',
  },
  dateStamp: {
    color: Colors.textMuted,
    fontSize: 10,
  },
  deleteBtn: {
    padding: 4,
  },
  deleteBtnText: {
    fontSize: 13,
  },
  campaignHeadline: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '800',
    marginBottom: 4,
  },
  campaignCaption: {
    color: Colors.textSecondary,
    fontSize: 12,
    lineHeight: 18,
  },
  tagsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 8,
  },
  tagText: {
    color: Colors.cyan,
    fontSize: 11,
  },
  actionsBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.08)',
  },
  secondaryAction: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  secondaryActionText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '700',
  },
  emptyText: {
    color: Colors.textMuted,
    textAlign: 'center',
    paddingVertical: 20,
    fontSize: 13,
  },
});
