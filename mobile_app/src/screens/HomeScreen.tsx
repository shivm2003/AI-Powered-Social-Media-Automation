import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  Pressable,
  RefreshControl,
  Alert,
} from 'react-native';
import { Colors } from '../styles/theme';
import { ThreeDCard } from '../components/ThreeDCard';
import { ThreeDButton } from '../components/ThreeDButton';
import { ProductModal } from '../components/ProductModal';
import {
  getAllCampaigns,
  getAllProducts,
  getStorageStats,
  deleteProduct,
  Campaign,
  Product,
  StorageStats,
} from '../db/database';
import { getInternalStorageUsage } from '../storage/mediaStorage';

interface HomeScreenProps {
  onNavigate: (tab: 'home' | 'studio' | 'approval' | 'vault') => void;
  onSelectCampaignForBroadcast?: (campaign: Campaign) => void;
  onSelectProductForStudio?: (product: Product) => void;
}

export const HomeScreen: React.FC<HomeScreenProps> = ({
  onNavigate,
  onSelectCampaignForBroadcast,
  onSelectProductForStudio,
}) => {
  const [stats, setStats] = useState<StorageStats>({
    totalCampaigns: 0,
    totalPublished: 0,
    totalProducts: 0,
    storageMode: 'On-Device SQLite',
  });
  const [diskUsage, setDiskUsage] = useState({ readableSize: '0 KB', fileCount: 0 });
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [activeProductIndex, setActiveProductIndex] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [isModalVisible, setIsModalVisible] = useState(false);

  const loadData = async () => {
    try {
      const s = getStorageStats();
      const c = getAllCampaigns();
      const p = getAllProducts();
      const d = await getInternalStorageUsage();
      setStats(s);
      setCampaigns(c);
      setProducts(p);
      setDiskUsage({ readableSize: d.readableSize, fileCount: d.fileCount });
    } catch (e) {
      console.error('Failed to load home data:', e);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const onRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const currentProduct = products[activeProductIndex] || products[0];

  const handleDeleteProduct = (p: Product) => {
    Alert.alert(
      'Delete Product',
      `Delete "${p.name}" and all its campaigns from your device storage?`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            deleteProduct(p.id);
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
      {/* 3D Hardware Vault Meter */}
      <ThreeDCard glowColor={Colors.emeraldGlow} borderColor="rgba(16, 185, 129, 0.35)">
        <View style={styles.hardwareBadgeRow}>
          <View style={styles.statusDotRow}>
            <View style={styles.liveGreenDot} />
            <Text style={styles.hardwareBadgeText}>100% ON-DEVICE HARDWARE MEMORY</Text>
          </View>
          <View style={styles.securityPill}>
            <Text style={styles.securityPillText}>🔒 ZERO CLOUD LEAK</Text>
          </View>
        </View>

        <Text style={styles.metricBig}>
          {diskUsage.readableSize} <Text style={styles.metricSub}>encrypted storage used</Text>
        </Text>

        {/* Storage Visual Gauge Bar */}
        <View style={styles.storageGaugeBg}>
          <View style={styles.storageGaugeFill} />
        </View>

        <View style={styles.storageFooterRow}>
          <Text style={styles.storageDbLabel}>
            Database: <Text style={{ color: Colors.cyan, fontWeight: '700' }}>manvix_ai_local.db</Text>
          </Text>
          <Text style={styles.storageDbSub}>SQLite v3 (WAL)</Text>
        </View>
      </ThreeDCard>

      {/* Quick Metrics Bar */}
      <View style={styles.statsRow}>
        <View style={styles.statTile}>
          <Text style={styles.statNumber}>{stats.totalProducts}</Text>
          <Text style={styles.statLabel}>Products</Text>
        </View>
        <View style={styles.statDivider} />
        <View style={styles.statTile}>
          <Text style={[styles.statNumber, { color: Colors.cyan }]}>{stats.totalCampaigns}</Text>
          <Text style={styles.statLabel}>Campaigns</Text>
        </View>
        <View style={styles.statDivider} />
        <View style={styles.statTile}>
          <Text style={[styles.statNumber, { color: Colors.emerald }]}>{stats.totalPublished}</Text>
          <Text style={styles.statLabel}>Broadcasts</Text>
        </View>
      </View>

      {/* Product Selection Carousel */}
      <View style={styles.sectionHeaderRow}>
        <View>
          <Text style={styles.sectionHeader}>Your Products & Brands</Text>
          <Text style={styles.sectionSubtitle}>Select active product or tap + to add your own</Text>
        </View>
        <Pressable onPress={() => setIsModalVisible(true)} style={styles.addBrandBtn}>
          <Text style={styles.addBrandBtnText}>+ Add Product</Text>
        </Pressable>
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.productSlider}>
        {products.map((p, idx) => {
          const isSelected = idx === activeProductIndex;
          return (
            <Pressable
              key={p.id}
              onPress={() => setActiveProductIndex(idx)}
              style={[
                styles.productCardPill,
                isSelected && styles.selectedProductCardPill,
              ]}
            >
              <View style={styles.chipAvatarBox}>
                <Text style={styles.chipIcon}>{p.logo_icon || '🚀'}</Text>
              </View>
              <View style={styles.chipTextWrap}>
                <Text
                  style={[
                    styles.chipName,
                    isSelected && { color: '#FFFFFF', fontWeight: '800' },
                  ]}
                  numberOfLines={1}
                >
                  {p.name}
                </Text>
                <Text style={styles.chipCategory} numberOfLines={1}>
                  {p.category}
                </Text>
              </View>
              {isSelected && <View style={styles.activeCheckDot} />}
            </Pressable>
          );
        })}

        {/* Plus card inside slider */}
        <Pressable
          onPress={() => setIsModalVisible(true)}
          style={styles.addMoreCard}
        >
          <Text style={styles.addMoreIcon}>+</Text>
          <Text style={styles.addMoreText}>New Brand</Text>
        </Pressable>
      </ScrollView>

      {/* Active Product Hero Showcase */}
      {currentProduct && (
        <ThreeDCard glowColor={Colors.cyanGlow} borderColor="rgba(0, 242, 254, 0.35)">
          <View style={styles.brandHeader}>
            <View style={styles.brandTitleWrap}>
              <View style={styles.activeTagRow}>
                <Text style={styles.brandBadge}>ACTIVE PROFILE</Text>
                <Pressable onPress={() => handleDeleteProduct(currentProduct)}>
                  <Text style={styles.deleteLink}>Delete</Text>
                </Pressable>
              </View>
              <Text style={styles.brandName}>{currentProduct.name}</Text>
              <Text style={styles.brandCategory}>{currentProduct.category}</Text>
            </View>
            <View style={styles.avatarCircle}>
              <Text style={styles.avatarEmoji}>{currentProduct.logo_icon || '🚀'}</Text>
            </View>
          </View>

          <Text style={styles.brandDesc}>{currentProduct.description}</Text>

          {/* Benefits checklist */}
          <View style={styles.benefitList}>
            {(currentProduct.key_benefits || []).slice(0, 3).map((b, i) => (
              <View key={i} style={styles.benefitItem}>
                <Text style={styles.bulletCheck}>✓</Text>
                <Text style={styles.benefitText}>{b}</Text>
              </View>
            ))}
          </View>

          {/* CTA Preview */}
          <View style={styles.ctaPreviewBar}>
            <Text style={styles.ctaLabel}>STORE / CTA LINK:</Text>
            <Text style={styles.ctaVal} numberOfLines={1}>
              {currentProduct.cta_text} → {currentProduct.cta_url}
            </Text>
          </View>

          <ThreeDButton
            title={`✨ Launch AI Studio for ${currentProduct.name}`}
            onPress={() => {
              if (onSelectProductForStudio) {
                onSelectProductForStudio(currentProduct);
              }
              onNavigate('studio');
            }}
            gradient={Colors.gradientCosmic}
            glowColor={Colors.cyanGlow}
            bevelColor="#381D9E"
            style={{ marginTop: 14 }}
          />
        </ThreeDCard>
      )}

      {/* Saved Campaigns Stream */}
      <View style={styles.campaignsHeaderRow}>
        <View>
          <Text style={styles.sectionHeader}>Saved In Device Memory</Text>
          <Text style={styles.sectionSubtitle}>Recent campaigns ready for multi-app broadcast</Text>
        </View>
        <Text style={styles.viewAllText} onPress={() => onNavigate('vault')}>
          Open Vault →
        </Text>
      </View>

      {campaigns.length === 0 ? (
        <ThreeDCard>
          <Text style={styles.emptyNotice}>No campaigns created yet. Tap above to synthesize one!</Text>
        </ThreeDCard>
      ) : (
        campaigns.slice(0, 3).map((camp) => (
          <ThreeDCard key={camp.id} glowColor="rgba(255, 255, 255, 0.12)">
            <View style={styles.campTopRow}>
              <View style={styles.statusBadge}>
                <Text style={styles.statusText}>{camp.status.toUpperCase()}</Text>
              </View>
              <Text style={styles.campDate}>
                {new Date(camp.created_at).toLocaleDateString()}
              </Text>
            </View>

            <Text style={styles.campProductBadge}>{camp.product_name}</Text>
            <Text style={styles.campHeadline} numberOfLines={2}>
              {camp.headline}
            </Text>
            <Text style={styles.campCaption} numberOfLines={3}>
              {camp.caption}
            </Text>

            <View style={styles.campBottomBar}>
              <Text style={styles.platformsBadge}>
                Target Apps: {camp.platforms.join(', ') || 'instagram, facebook'}
              </Text>
              <ThreeDButton
                title="Broadcast 🚀"
                height={38}
                onPress={() => {
                  if (onSelectCampaignForBroadcast) {
                    onSelectCampaignForBroadcast(camp);
                  }
                  onNavigate('approval');
                }}
                style={{ marginVertical: 0, minWidth: 120 }}
              />
            </View>
          </ThreeDCard>
        ))
      )}

      {/* Add Product Modal */}
      <ProductModal
        visible={isModalVisible}
        onClose={() => setIsModalVisible(false)}
        onProductSaved={() => {
          loadData();
          setActiveProductIndex(0);
        }}
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
  hardwareBadgeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  statusDotRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  liveGreenDot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
    backgroundColor: Colors.emerald,
  },
  hardwareBadgeText: {
    color: Colors.emerald,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8,
  },
  securityPill: {
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.4)',
  },
  securityPillText: {
    color: Colors.emerald,
    fontSize: 9,
    fontWeight: '800',
  },
  metricBig: {
    fontSize: 26,
    fontWeight: '900',
    color: '#FFFFFF',
    letterSpacing: -0.5,
  },
  metricSub: {
    fontSize: 13,
    color: Colors.textSecondary,
    fontWeight: '500',
  },
  storageGaugeBg: {
    height: 6,
    borderRadius: 3,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    marginVertical: 10,
    overflow: 'hidden',
  },
  storageGaugeFill: {
    width: '18%',
    height: '100%',
    borderRadius: 3,
    backgroundColor: Colors.cyan,
  },
  storageFooterRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 2,
  },
  storageDbLabel: {
    color: Colors.textMuted,
    fontSize: 11,
  },
  storageDbSub: {
    color: Colors.textMuted,
    fontSize: 10,
    fontWeight: '600',
  },
  statsRow: {
    flexDirection: 'row',
    backgroundColor: '#090E1D',
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    paddingVertical: 12,
    marginVertical: 8,
    alignItems: 'center',
    justifyContent: 'space-around',
  },
  statTile: {
    alignItems: 'center',
    flex: 1,
  },
  statNumber: {
    fontSize: 22,
    fontWeight: '900',
    color: '#FFFFFF',
  },
  statLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: Colors.textMuted,
    textTransform: 'uppercase',
    marginTop: 2,
  },
  statDivider: {
    width: 1,
    height: 24,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 16,
    marginBottom: 8,
  },
  sectionHeader: {
    fontSize: 16,
    fontWeight: '800',
    color: '#FFFFFF',
    letterSpacing: 0.3,
  },
  sectionSubtitle: {
    fontSize: 11,
    color: Colors.textMuted,
    marginTop: 2,
  },
  addBrandBtn: {
    backgroundColor: 'rgba(0, 242, 254, 0.12)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: Colors.cyan,
  },
  addBrandBtnText: {
    color: Colors.cyan,
    fontSize: 11,
    fontWeight: '800',
  },
  productSlider: {
    flexDirection: 'row',
    marginVertical: 8,
  },
  productCardPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0A0F1F',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 16,
    marginRight: 10,
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    gap: 10,
    minWidth: 160,
    position: 'relative',
  },
  selectedProductCardPill: {
    borderColor: Colors.cyan,
    backgroundColor: 'rgba(0, 242, 254, 0.1)',
  },
  chipAvatarBox: {
    width: 34,
    height: 34,
    borderRadius: 10,
    backgroundColor: '#121A2E',
    alignItems: 'center',
    justifyContent: 'center',
  },
  chipIcon: {
    fontSize: 18,
  },
  chipTextWrap: {
    flex: 1,
  },
  chipName: {
    color: Colors.textSecondary,
    fontSize: 13,
    fontWeight: '700',
  },
  chipCategory: {
    color: Colors.textMuted,
    fontSize: 10,
  },
  activeCheckDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.cyan,
    position: 'absolute',
    top: 6,
    right: 8,
  },
  addMoreCard: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderStyle: 'dashed',
    paddingHorizontal: 16,
    paddingVertical: 10,
    minWidth: 90,
  },
  addMoreIcon: {
    color: Colors.cyan,
    fontSize: 18,
    fontWeight: '800',
  },
  addMoreText: {
    color: Colors.textMuted,
    fontSize: 10,
    fontWeight: '700',
    marginTop: 2,
  },
  brandHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  brandTitleWrap: {
    flex: 1,
  },
  activeTagRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  brandBadge: {
    color: Colors.cyan,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8,
  },
  deleteLink: {
    color: Colors.rose,
    fontSize: 11,
    fontWeight: '600',
  },
  brandName: {
    fontSize: 20,
    fontWeight: '900',
    color: '#FFFFFF',
    marginTop: 2,
  },
  brandCategory: {
    fontSize: 12,
    color: Colors.textSecondary,
  },
  avatarCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#16223D',
    borderWidth: 1.5,
    borderColor: Colors.cyan,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarEmoji: {
    fontSize: 22,
  },
  brandDesc: {
    color: Colors.textSecondary,
    fontSize: 12,
    lineHeight: 18,
    marginTop: 10,
  },
  benefitList: {
    marginTop: 10,
    gap: 6,
  },
  benefitItem: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  bulletCheck: {
    color: Colors.emerald,
    fontSize: 13,
    fontWeight: '800',
    marginRight: 6,
  },
  benefitText: {
    color: '#E2E8F0',
    fontSize: 12,
  },
  ctaPreviewBar: {
    marginTop: 12,
    padding: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.04)',
    borderRadius: 8,
  },
  ctaLabel: {
    color: Colors.gold,
    fontSize: 9,
    fontWeight: '800',
  },
  ctaVal: {
    color: '#FFFFFF',
    fontSize: 11,
    marginTop: 2,
  },
  campaignsHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 18,
    marginBottom: 8,
  },
  viewAllText: {
    color: Colors.cyan,
    fontSize: 12,
    fontWeight: '800',
  },
  campTopRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  campProductBadge: {
    color: Colors.cyan,
    fontSize: 11,
    fontWeight: '700',
    marginBottom: 2,
  },
  statusBadge: {
    backgroundColor: 'rgba(139, 92, 246, 0.25)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: Colors.primary,
  },
  statusText: {
    color: Colors.cyan,
    fontSize: 9,
    fontWeight: '800',
  },
  campDate: {
    color: Colors.textMuted,
    fontSize: 10,
  },
  campHeadline: {
    fontSize: 14,
    fontWeight: '800',
    color: '#FFFFFF',
    marginBottom: 4,
  },
  campCaption: {
    fontSize: 12,
    color: Colors.textSecondary,
    lineHeight: 18,
  },
  campBottomBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.08)',
  },
  platformsBadge: {
    color: Colors.textMuted,
    fontSize: 11,
    fontWeight: '600',
    textTransform: 'capitalize',
  },
  emptyNotice: {
    color: Colors.textMuted,
    textAlign: 'center',
    paddingVertical: 14,
    fontSize: 13,
  },
});
