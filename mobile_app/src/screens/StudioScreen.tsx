import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  Pressable,
  Alert,
} from 'react-native';
import { Colors } from '../styles/theme';
import { ThreeDCard } from '../components/ThreeDCard';
import { ThreeDButton } from '../components/ThreeDButton';
import { ProductModal } from '../components/ProductModal';
import { getAllProducts, saveCampaign, Campaign, Product } from '../db/database';

interface StudioScreenProps {
  onCampaignCreated: (campaign: Campaign) => void;
  onNavigate: (tab: 'home' | 'studio' | 'approval' | 'vault') => void;
  selectedProduct?: Product | null;
}

const CAMPAIGN_GOALS = [
  { id: 'launch', label: '🚀 Product Launch', sub: 'Announce new release' },
  { id: 'sale', label: '🔥 Flash Sale & Discount', sub: 'Urgency & conversions' },
  { id: 'value', label: '💡 Problem & Solution', sub: 'Highlight key benefits' },
  { id: 'viral', label: '✨ Trend & Lifestyle', sub: 'High social engagement' },
];

const TONES = [
  { id: 'energetic', label: '🔥 High Energy' },
  { id: 'luxury', label: '💎 Sleek & Luxury' },
  { id: 'trust', label: '🤝 Trusted & Friendly' },
  { id: 'witty', label: '⚡ Bold & Modern' },
];

export const StudioScreen: React.FC<StudioScreenProps> = ({
  onCampaignCreated,
  onNavigate,
  selectedProduct: propProduct,
}) => {
  const [products, setProducts] = useState<Product[]>([]);
  const [activeProduct, setActiveProduct] = useState<Product | null>(null);
  const [selectedGoal, setSelectedGoal] = useState('launch');
  const [selectedTone, setSelectedTone] = useState('energetic');
  const [customAngle, setCustomAngle] = useState('');
  const [generating, setGenerating] = useState(false);
  const [generatedResult, setGeneratedResult] = useState<Campaign | null>(null);
  const [showProductModal, setShowProductModal] = useState(false);

  const loadProducts = () => {
    const all = getAllProducts();
    setProducts(all);
    if (propProduct) {
      setActiveProduct(propProduct);
    } else if (all.length > 0 && !activeProduct) {
      setActiveProduct(all[0]);
    }
  };

  useEffect(() => {
    loadProducts();
  }, [propProduct]);

  const handleGenerate = () => {
    if (!activeProduct) {
      Alert.alert('No Product Selected', 'Please add or select a product first.');
      return;
    }

    setGenerating(true);

    setTimeout(() => {
      const prodName = activeProduct.name;
      const benefits = activeProduct.key_benefits || [];
      const cta = activeProduct.cta_text || 'Learn More';
      const url = activeProduct.cta_url || 'https://mybrand.com';
      const cleanTag = prodName.replace(/[^a-zA-Z0-9]/g, '');

      let headline = '';
      let caption = '';
      let hashtags: string[] = [];

      if (selectedGoal === 'launch') {
        headline = `🚀 Say Hello to ${prodName}: The Upgrade You Have Been Waiting For! ✨`;
        caption = `Level up your experience with ${prodName}. Crafted specifically for ${activeProduct.target_audience}, bringing unmatched quality and peak performance.\n\n` +
          `🌟 Why everyone is talking about it:\n` +
          benefits.slice(0, 3).map((b) => `• ${b}`).join('\n') +
          `\n\n${customAngle ? `💡 Special Note: ${customAngle}\n\n` : ''}` +
          `👉 ${cta}: ${url}`;
        hashtags = [`#${cleanTag}`, `#NewLaunch`, `#${activeProduct.category.replace(/[^a-zA-Z]/g, '')}`, `#Innovation`, `#TrendingNow`];
      } else if (selectedGoal === 'sale') {
        headline = `🔥 LIMITED TIME OFFER: Get Exclusive Deals on ${prodName}! ⚡`;
        caption = `Don't miss out! Upgrade today with ${prodName} and experience superior performance crafted for ${activeProduct.target_audience}.\n\n` +
          `✅ What you get:\n` +
          benefits.slice(0, 3).map((b) => `✓ ${b}`).join('\n') +
          `\n\n⚡ ${customAngle || 'Hurry, stocks are strictly limited for this exclusive run!'}\n\n` +
          `👉 ${cta}: ${url}`;
        hashtags = [`#${cleanTag}`, `#SpecialOffer`, `#FlashSale`, `#LimitedDeal`, `#MustHave`];
      } else if (selectedGoal === 'value') {
        headline = `💡 Stop Settling for Less. Here is Why ${prodName} Changes the Game! 🏆`;
        caption = `Tired of outdated solutions? ${prodName} was engineered to solve real challenges for ${activeProduct.target_audience}.\n\n` +
          `✨ Key advantages you will love:\n` +
          benefits.map((b) => `🔹 ${b}`).join('\n') +
          `\n\n👉 Discover More & ${cta}: ${url}`;
        hashtags = [`#${cleanTag}`, `#GameChanger`, `#QualityFirst`, `#ProblemSolved`, `#Upgrade`];
      } else {
        headline = `✨ Elevate Your Daily Lifestyle with ${prodName} 🌟`;
        caption = `Designed for those who appreciate excellence. ${prodName} blends premium aesthetics with effortless functionality for ${activeProduct.target_audience}.\n\n` +
          benefits.slice(0, 2).map((b) => `✨ ${b}`).join('\n') +
          `\n\n👉 ${cta}: ${url}`;
        hashtags = [`#${cleanTag}`, `#LifestyleGoals`, `#Aesthetic`, `#DailyInspiration`, `#ModernLiving`];
      }

      const newCampaign: Campaign = {
        id: `camp-${Date.now()}`,
        product_id: activeProduct.id,
        product_name: prodName,
        content_type: 'image',
        headline,
        caption,
        hashtags,
        apply_url: url,
        local_image_uri: 'bundled://icon.png',
        status: 'approved',
        platforms: ['instagram', 'facebook', 'whatsapp', 'linkedin'],
        created_at: Date.now(),
      };

      // 100% on-device storage in SQLite
      saveCampaign(newCampaign);
      setGeneratedResult(newCampaign);
      setGenerating(false);
      onCampaignCreated(newCampaign);

      Alert.alert(
        '💾 Campaign Synthesized!',
        `Created for "${prodName}" and stored securely in local device SQLite memory.`,
        [
          { text: 'Review & Broadcast', onPress: () => onNavigate('approval') },
          { text: 'Keep Editing', style: 'cancel' },
        ]
      );
    }, 1100);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      {/* Studio Banner */}
      <ThreeDCard glowColor={Colors.primaryGlow} borderColor="rgba(124, 92, 252, 0.4)">
        <Text style={styles.headerBadge}>MANVIX 3D AI STUDIO</Text>
        <Text style={styles.headerTitle}>Synthesize Viral Campaigns</Text>
        <Text style={styles.headerSubtitle}>
          Generate high-converting multi-platform social posts for any product or service in your on-device portfolio.
        </Text>
      </ThreeDCard>

      {/* Product Selector */}
      <View style={styles.productSelectionBar}>
        <Text style={styles.sectionTitle}>1. Target Product / Brand</Text>
        <Pressable onPress={() => setShowProductModal(true)}>
          <Text style={styles.addNewLink}>+ Add New</Text>
        </Pressable>
      </View>

      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.productPillRow}>
        {products.map((p) => {
          const isSelected = activeProduct?.id === p.id;
          return (
            <Pressable
              key={p.id}
              onPress={() => setActiveProduct(p)}
              style={[
                styles.productSelectCard,
                isSelected && styles.productSelectCardActive,
              ]}
            >
              <Text style={styles.productIcon}>{p.logo_icon || '🚀'}</Text>
              <View>
                <Text
                  style={[
                    styles.productNameText,
                    isSelected && { color: '#FFFFFF', fontWeight: '800' },
                  ]}
                  numberOfLines={1}
                >
                  {p.name}
                </Text>
                <Text style={styles.productCategoryText} numberOfLines={1}>
                  {p.category}
                </Text>
              </View>
            </Pressable>
          );
        })}
      </ScrollView>

      {/* Campaign Goal Selector */}
      <Text style={styles.sectionTitle}>2. Campaign Goal</Text>
      <View style={styles.optionsGrid}>
        {CAMPAIGN_GOALS.map((g) => {
          const isSelected = selectedGoal === g.id;
          return (
            <Pressable
              key={g.id}
              onPress={() => setSelectedGoal(g.id)}
              style={[
                styles.optionCard,
                {
                  borderColor: isSelected ? Colors.cyan : 'rgba(255, 255, 255, 0.1)',
                  backgroundColor: isSelected ? '#141E33' : '#0D1424',
                },
              ]}
            >
              <Text style={styles.optionLabel}>{g.label}</Text>
              <Text style={styles.optionSub}>{g.sub}</Text>
            </Pressable>
          );
        })}
      </View>

      {/* Tone Selector */}
      <Text style={styles.sectionTitle}>3. Tone of Voice</Text>
      <View style={styles.toneRow}>
        {TONES.map((t) => {
          const isSelected = selectedTone === t.id;
          return (
            <Pressable
              key={t.id}
              onPress={() => setSelectedTone(t.id)}
              style={[
                styles.tonePill,
                {
                  borderColor: isSelected ? Colors.primary : 'rgba(255, 255, 255, 0.12)',
                  backgroundColor: isSelected ? 'rgba(124, 92, 252, 0.2)' : '#0D1424',
                },
              ]}
            >
              <Text
                style={[
                  styles.toneText,
                  { color: isSelected ? '#FFFFFF' : Colors.textSecondary },
                ]}
              >
                {t.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {/* Custom Promo Angle / Extra Instructions */}
      <Text style={styles.sectionTitle}>4. Custom Angle / Promo Details (Optional)</Text>
      <View style={styles.inputCard}>
        <TextInput
          style={styles.textInput}
          placeholder="e.g. Free shipping on orders over $50, Weekend 20% discount code, or New summer colors..."
          placeholderTextColor={Colors.textMuted}
          value={customAngle}
          onChangeText={setCustomAngle}
          multiline
          numberOfLines={3}
        />
      </View>

      {/* Generate Button */}
      <ThreeDButton
        title={generating ? 'Synthesizing with AI...' : `✨ Generate Post for ${activeProduct?.name || 'Product'}`}
        onPress={handleGenerate}
        loading={generating}
        gradient={['#7C5CFC', '#00F2FE']}
        glowColor={Colors.cyanGlow}
        bevelColor="#381D9E"
        style={{ marginTop: 16 }}
      />

      {/* Preview Card */}
      {generatedResult && (
        <ThreeDCard glowColor={Colors.emeraldGlow} borderColor="rgba(16, 185, 129, 0.4)">
          <View style={styles.previewHeader}>
            <Text style={styles.previewBadge}>ON-DEVICE GENERATED POST</Text>
            <Text style={styles.previewID}>SAVED IN SQLITE</Text>
          </View>

          <Text style={styles.prevHeadline}>{generatedResult.headline}</Text>
          <Text style={styles.prevCaption}>{generatedResult.caption}</Text>

          <View style={styles.prevTagsRow}>
            {generatedResult.hashtags.map((tag, idx) => (
              <Text key={idx} style={styles.tagPill}>{tag}</Text>
            ))}
          </View>

          <ThreeDButton
            title="Proceed to Broadcast 🚀"
            onPress={() => onNavigate('approval')}
            gradient={['#10B981', '#059669']}
            glowColor={Colors.emeraldGlow}
            bevelColor="#065F46"
            style={{ marginTop: 12 }}
          />
        </ThreeDCard>
      )}

      {/* Add Product Modal */}
      <ProductModal
        visible={showProductModal}
        onClose={() => setShowProductModal(false)}
        onProductSaved={(newProd) => {
          loadProducts();
          setActiveProduct(newProd);
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
  headerBadge: {
    color: Colors.cyan,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '900',
    color: '#FFFFFF',
    marginTop: 4,
  },
  headerSubtitle: {
    color: Colors.textSecondary,
    fontSize: 12,
    lineHeight: 18,
    marginTop: 4,
  },
  productSelectionBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 18,
    marginBottom: 8,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: '800',
    color: '#FFFFFF',
    letterSpacing: 0.3,
  },
  addNewLink: {
    color: Colors.cyan,
    fontSize: 12,
    fontWeight: '800',
  },
  productPillRow: {
    flexDirection: 'row',
    marginBottom: 10,
  },
  productSelectCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0D1424',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    marginRight: 10,
    gap: 8,
  },
  productSelectCardActive: {
    borderColor: Colors.cyan,
    backgroundColor: 'rgba(0, 242, 254, 0.12)',
  },
  productIcon: {
    fontSize: 20,
  },
  productNameText: {
    color: Colors.textSecondary,
    fontSize: 13,
    fontWeight: '600',
  },
  productCategoryText: {
    color: Colors.textMuted,
    fontSize: 10,
  },
  optionsGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 10,
    marginTop: 8,
  },
  optionCard: {
    width: '48%',
    borderRadius: 14,
    padding: 12,
    borderWidth: 1.5,
  },
  optionLabel: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '700',
  },
  optionSub: {
    color: Colors.cyan,
    fontSize: 11,
    marginTop: 4,
  },
  toneRow: {
    flexDirection: 'row',
    gap: 8,
    marginTop: 8,
  },
  tonePill: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 12,
    alignItems: 'center',
    borderWidth: 1.5,
  },
  toneText: {
    fontSize: 11,
    fontWeight: '700',
  },
  inputCard: {
    backgroundColor: '#0D1424',
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    padding: 12,
    marginTop: 8,
  },
  textInput: {
    color: '#FFFFFF',
    fontSize: 13,
    minHeight: 60,
    textAlignVertical: 'top',
  },
  previewHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  previewBadge: {
    color: Colors.emerald,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0.8,
  },
  previewID: {
    color: Colors.textMuted,
    fontSize: 10,
    fontWeight: '700',
  },
  prevHeadline: {
    color: '#FFFFFF',
    fontSize: 15,
    fontWeight: '700',
    marginBottom: 6,
  },
  prevCaption: {
    color: Colors.textSecondary,
    fontSize: 12,
    lineHeight: 18,
  },
  prevTagsRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 10,
  },
  tagPill: {
    color: Colors.cyan,
    fontSize: 11,
    backgroundColor: 'rgba(0, 242, 254, 0.1)',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
});
