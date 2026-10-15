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
      `Are you sure you want to delete "${p.name}" and its local campaigns from this device?`,
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
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={Colors.cyan} />}
    >
      {/* 3D Hardware Storage Meter */}
      <ThreeDCard glowColor={Colors.emeraldGlow} borderColor="rgba(16, 185, 129, 0.35)">
        <View style={styles.hardwareBadgeRow}>
          <Text style={styles.hardwareBadgeText}>100% DEVICE HARDWARE MEMORY</Text>
          <View style={styles.securityPill}>
            <Text style={styles.securityPillText}>🔒 ZERO CLOUD LEAK</Text>
          </View>
        </View>

        <Text style={styles.metricBig}>
          {diskUsage.readableSize} <Text style={styles.metricSub}>used in sandbox</Text>
        </Text>
        <Text style={styles.storageDetail}>
          Local SQLite Database: <Text style={{ color: Colors.cyan, fontWeight: '700' }}>manvix_ai_local.db</Text>
        </Text>
        <Text style={styles.storageSubdetail}>
          Add any product, brand, or e-commerce shop. All data, custom assets, and copy are saved 100% inside your Android storage.
        </Text>
      </ThreeDCard>

      {/* 3D Stat Tiles Grid */}
      <View style={styles.statsRow}>
        <View style={styles.halfCol}>
          <ThreeDCard glowColor={Colors.primaryGlow} borderColor="rgba(124, 92, 252, 0.4)">
            <Text style={styles.statLabel}>MY PRODUCTS</Text>
            <Text style={styles.statNumber}>{stats.totalProducts}</Text>
            <Text style={styles.statCaption}>Added to vault</Text>
          </ThreeDCard>
        </View>

        <View style={styles.halfCol}>
          <ThreeDCard glowColor={Colors.cyanGlow} borderColor="rgba(0, 242, 254, 0.4)">
            <Text style={styles.statLabel}>BROADCASTS</Text>
            <Text style={styles.statNumber}>{stats.totalPublished}</Text>
            <Text style={styles.statCaption}>Multi-app posts</Text>
          </ThreeDCard>
        </View>
      </View>

      {/* Products Carousel / Selector */}
      <View style={styles.sectionHeaderRow}>
        <View>
          <Text style={styles.sectionHeader}>Your Products & Brands</Text>
          <Text style={styles.sectionSubtitle}>Select or add any business/service to promote</Text>
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
                styles.productChip,
                isSelected && styles.selectedProductChip,
              ]}
            >
              <Text style={styles.chipIcon}>{p.logo_icon || '🚀'}</Text>
              <View>
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
            </Pressable>
          );
        })}
      </ScrollView>

      {/* Active Product Showcase */}
      {currentProduct && (
        <ThreeDCard glowColor={Colors.cyanGlow} borderColor="rgba(0, 242, 254, 0.35)">
          <View style={styles.brandHeader}>
            <View style={styles.brandTitleWrap}>
              <View style={styles.activeTagRow}>
                <Text style={styles.brandBadge}>ACTIVE PRODUCT</Text>
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

          <View style={styles.benefitList}>
            {(currentProduct.key_benefits || []).map((b, i) => (
              <View key={i} style={styles.benefitItem}>
                <Text style={styles.bulletCheck}>✓</Text>
                <Text style={styles.benefitText}>{b}</Text>
              </View>
            ))}
          </View>

          <View style={styles.ctaPreviewBar}>
            <Text style={styles.ctaLabel}>CALL TO ACTION:</Text>
            <Text style={styles.ctaVal}>{currentProduct.cta_text} → {currentProduct.cta_url}</Text>
          </View>

          <ThreeDButton
            title={`✨ Generate AI Post for ${currentProduct.name}`}
            onPress={() => {
              if (onSelectProductForStudio) {
                onSelectProductForStudio(currentProduct);
              }
              onNavigate('studio');
            }}
            gradient={['#7C5CFC', '#00F2FE']}
            glowColor={Colors.cyanGlow}
            bevelColor="#381D9E"
            style={{ marginTop: 14 }}
          />
        </ThreeDCard>
      )}

      {/* Stored Campaigns Header */}
      <View style={styles.campaignsHeaderRow}>
        <Text style={styles.sectionHeader}>Saved In Device Memory</Text>
        <Text style={styles.viewAllText} onPress={() => onNavigate('vault')}>
          Open Vault →
        </Text>
      </View>

      {campaigns.length === 0 ? (
        <ThreeDCard>
          <Text style={styles.emptyNotice}>No campaigns created yet. Tap below to generate one!</Text>
        </ThreeDCard>
      ) : (
        campaigns.slice(0, 3).map((camp) => (
          <ThreeDCard key={camp.id} glowColor="rgba(255, 255, 255, 0.15)">
            <View style={styles.campTopRow}>
              <View style={styles.statusBadge}>
                <Text style={styles.statusText}>{camp.status.toUpperCase()}</Text>
              </View>
              <Text style={styles.campDate}>{new Date(camp.created_at).toLocaleDateString()}</Text>
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
                title="Post Now 🚀"
                height={40}
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
        onProductSaved={(newProd) => {
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
    paddingBottom: 36,
  },
  hardwareBadgeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
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
    fontSize: 28,
    fontWeight: '900',
    color: '#FFFFFF',
    letterSpacing: -0.5,
  },
  metricSub: {
    fontSize: 14,
    color: Colors.textSecondary,
    fontWeight: '500',
  },
  storageDetail: {
    color: Colors.textSecondary,
    fontSize: 12,
    marginTop: 6,
  },
  storageSubdetail: {
    color: Colors.textMuted,
    fontSize: 11,
    marginTop: 4,
    lineHeight: 16,
  },
  statsRow: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 4,
  },
  halfCol: {
    flex: 1,
  },
  statLabel: {
    color: Colors.textMuted,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
  statNumber: {
    fontSize: 28,
    fontWeight: '900',
    color: '#FFFFFF',
    marginVertical: 4,
  },
  statCaption: {
    color: Colors.textSecondary,
    fontSize: 11,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 18,
    marginBottom: 8,
  },
  sectionHeader: {
    fontSize: 16,
    fontWeight: '800',
    color: '#FFFFFF',
    letterSpacing: 0.5,
  },
  sectionSubtitle: {
    fontSize: 11,
    color: Colors.textMuted,
    marginTop: 2,
  },
  addBrandBtn: {
    backgroundColor: 'rgba(0, 242, 254, 0.15)',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: Colors.cyan,
  },
  addBrandBtnText: {
    color: Colors.cyan,
    fontSize: 12,
    fontWeight: '800',
  },
  productSlider: {
    flexDirection: 'row',
    marginVertical: 8,
  },
  productChip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0D1424',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 14,
    marginRight: 10,
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    gap: 8,
  },
  selectedProductChip: {
    borderColor: Colors.cyan,
    backgroundColor: 'rgba(0, 242, 254, 0.12)',
  },
  chipIcon: {
    fontSize: 20,
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
    width: 52,
    height: 52,
    borderRadius: 26,
    backgroundColor: '#172238',
    borderWidth: 1.5,
    borderColor: Colors.cyan,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarEmoji: {
    fontSize: 24,
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
    fontSize: 10,
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
    fontSize: 13,
    fontWeight: '700',
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
    backgroundColor: 'rgba(124, 92, 252, 0.25)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: Colors.primary,
  },
  statusText: {
    color: Colors.cyan,
    fontSize: 10,
    fontWeight: '800',
  },
  campDate: {
    color: Colors.textMuted,
    fontSize: 11,
  },
  campHeadline: {
    fontSize: 15,
    fontWeight: '700',
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
