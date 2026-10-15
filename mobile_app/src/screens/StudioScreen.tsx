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
import { SocialPreviewMockup } from '../components/SocialPreviewMockup';
import { getAllProducts, saveCampaign, Campaign, Product } from '../db/database';

interface StudioScreenProps {
  onCampaignCreated: (campaign: Campaign) => void;
  onNavigate: (tab: 'home' | 'studio' | 'approval' | 'vault') => void;
  selectedProduct?: Product | null;
}

const AI_ENGINES = [
  { id: 'gemini', name: 'Gemini 1.5', icon: '♊', desc: 'Google AI Multimodal' },
  { id: 'chatgpt', name: 'ChatGPT-4o', icon: '🤖', desc: 'OpenAI Sales Copy' },
];

const CAMPAIGN_GOALS = [
  { id: 'launch', label: '🚀 Product Launch', sub: 'Announce new release' },
  { id: 'sale', label: '🔥 Flash Sale', sub: 'Urgency & conversions' },
  { id: 'value', label: '💡 Problem & Value', sub: 'Highlight benefits' },
  { id: 'lifestyle', label: '✨ Lifestyle Aesthetic', sub: 'Social engagement' },
];

const TONES = [
  { id: 'energetic', label: '🔥 High Energy' },
  { id: 'luxury', label: '💎 Sleek & Luxury' },
  { id: 'trust', label: '🤝 Trusted & Friendly' },
  { id: 'bold', label: '⚡ Bold & Direct' },
];

const QUICK_INSPIRATION = [
  { label: '🔥 40% Off Launch Deal', angle: 'Limited time 40% discount for first 100 buyers' },
  { label: '🚀 New Arrival 2026', angle: 'Engineered with new breakthrough materials and sleek design' },
  { label: '⭐ 5-Star Reviews', angle: 'Join over 10,000+ satisfied customers worldwide' },
  { label: '🎁 Free Priority Shipping', angle: 'Free express shipping on all orders this weekend only' },
];

export const StudioScreen: React.FC<StudioScreenProps> = ({
  onCampaignCreated,
  onNavigate,
  selectedProduct: propProduct,
}) => {
  const [products, setProducts] = useState<Product[]>([]);
  const [activeProduct, setActiveProduct] = useState<Product | null>(null);
  const [selectedEngine, setSelectedEngine] = useState('gemini');
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

  const applyInspiration = (item: { label: string; angle: string }) => {
    setCustomAngle(item.angle);
  };

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
        headline = `🔥 LIMITED TIME OFFER: Exclusive Deal on ${prodName}! ⚡`;
        caption = `Don't miss out! Upgrade today with ${prodName} and experience superior performance crafted for ${activeProduct.target_audience}.\n\n` +
          `✅ Highlights:\n` +
          benefits.slice(0, 3).map((b) => `✓ ${b}`).join('\n') +
          `\n\n⚡ ${customAngle || 'Hurry, stocks are strictly limited for this exclusive run!'}\n\n` +
          `👉 ${cta}: ${url}`;
        hashtags = [`#${cleanTag}`, `#SpecialOffer`, `#FlashSale`, `#LimitedDeal`, `#MustHave`];
      } else if (selectedGoal === 'value') {
        headline = `💡 Stop Settling for Less. Why ${prodName} Changes the Game! 🏆`;
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
        '💾 Post Synthesized!',
        `Generated with ${selectedEngine.toUpperCase()} for "${prodName}". Stored in device memory.`,
        [
          { text: 'Review & Broadcast', onPress: () => onNavigate('approval') },
          { text: 'Preview Below', style: 'cancel' },
        ]
      );
    }, 1100);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
      {/* Studio Header Card */}
      <ThreeDCard glowColor={Colors.primaryGlow} borderColor="rgba(139, 92, 246, 0.4)">
        <Text style={styles.headerBadge}>MANVIX 3D AI STUDIO</Text>
        <Text style={styles.headerTitle}>Synthesize Viral Social Content</Text>
        <Text style={styles.headerSubtitle}>
          Select your AI engine, target brand, and marketing goals to generate high-converting copy.
        </Text>
      </ThreeDCard>

      {/* AI Model Selector */}
      <Text style={styles.sectionTitle}>1. Choose AI Generation Engine</Text>
      <View style={styles.engineRow}>
        {AI_ENGINES.map((eng) => {
          const isSelected = selectedEngine === eng.id;
          return (
            <Pressable
              key={eng.id}
              onPress={() => setSelectedEngine(eng.id)}
              style={[
                styles.engineCard,
                isSelected && styles.engineCardActive,
              ]}
            >
              <View style={styles.engineIconBox}>
                <Text style={styles.engineIcon}>{eng.icon}</Text>
              </View>
              <View style={styles.engineTextBox}>
                <Text
                  style={[
                    styles.engineName,
                    isSelected && { color: Colors.cyan, fontWeight: '800' },
                  ]}
                >
                  {eng.name}
                </Text>
                <Text style={styles.engineDesc}>{eng.desc}</Text>
              </View>
              {isSelected && <View style={styles.engineActiveDot} />}
            </Pressable>
          );
        })}
      </View>

      {/* Product Selector */}
      <View style={styles.productSelectionBar}>
        <Text style={styles.sectionTitle}>2. Target Product / Brand</Text>
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
      <Text style={styles.sectionTitle}>3. Campaign Objective</Text>
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
                  borderColor: isSelected ? Colors.cyan : 'rgba(255, 255, 255, 0.08)',
                  backgroundColor: isSelected ? 'rgba(0, 242, 254, 0.12)' : '#0A0F1D',
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
      <Text style={styles.sectionTitle}>4. Tone of Voice</Text>
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
                  borderColor: isSelected ? Colors.primary : 'rgba(255, 255, 255, 0.08)',
                  backgroundColor: isSelected ? 'rgba(139, 92, 246, 0.25)' : '#0A0F1D',
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

      {/* Quick Inspiration Hooks */}
      <Text style={styles.sectionTitle}>5. Quick Inspiration Hooks</Text>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.quickInspoRow}>
        {QUICK_INSPIRATION.map((item, idx) => (
          <Pressable
            key={idx}
            onPress={() => applyInspiration(item)}
            style={styles.inspoChip}
          >
            <Text style={styles.inspoChipText}>{item.label}</Text>
          </Pressable>
        ))}
      </ScrollView>

      {/* Custom Angle Details Input */}
      <Text style={styles.sectionTitle}>6. Specific Discount / Hook (Optional)</Text>
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
        {customAngle.length > 0 && (
          <Pressable onPress={() => setCustomAngle('')} style={styles.clearAngleBtn}>
            <Text style={styles.clearAngleText}>Clear</Text>
          </Pressable>
        )}
      </View>

      {/* 3D Generate Button */}
      <ThreeDButton
        title={generating ? `Synthesizing with ${selectedEngine.toUpperCase()}...` : `✨ Synthesize Post with ${selectedEngine.toUpperCase()}`}
        onPress={handleGenerate}
        loading={generating}
        gradient={Colors.gradientCosmic}
        glowColor={Colors.cyanGlow}
        bevelColor="#381D9E"
        style={{ marginTop: 16 }}
      />

      {/* Live Social Post Mockup Preview */}
      {generatedResult && (
        <View style={styles.previewSection}>
          <View style={styles.previewTitleRow}>
            <Text style={styles.previewSectionTitle}>LIVE FEED POST PREVIEW</Text>
            <View style={styles.savedPill}>
              <Text style={styles.savedPillText}>💾 SAVED IN SQLITE</Text>
            </View>
          </View>

          <SocialPreviewMockup
            productName={activeProduct?.name || generatedResult.product_name}
            avatarIcon={activeProduct?.logo_icon || '🚀'}
            headline={generatedResult.headline}
            caption={generatedResult.caption}
            hashtags={generatedResult.hashtags}
            applyUrl={generatedResult.apply_url}
            ctaText={activeProduct?.cta_text || 'Shop Now'}
          />

          <ThreeDButton
            title="Proceed to Multi-App Broadcast 🚀"
            onPress={() => onNavigate('approval')}
            gradient={Colors.gradientSuccess}
            glowColor={Colors.emeraldGlow}
            bevelColor="#065F46"
            style={{ marginTop: 8 }}
          />
        </View>
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
    paddingBottom: 40,
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
  sectionTitle: {
    fontSize: 12,
    fontWeight: '800',
    color: Colors.cyan,
    marginTop: 18,
    marginBottom: 8,
    letterSpacing: 0.6,
    textTransform: 'uppercase',
  },
  engineRow: {
    flexDirection: 'row',
    gap: 10,
  },
  engineCard: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0A0F1D',
    borderRadius: 14,
    padding: 12,
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    position: 'relative',
  },
  engineCardActive: {
    borderColor: Colors.cyan,
    backgroundColor: 'rgba(0, 242, 254, 0.1)',
  },
  engineIconBox: {
    marginRight: 8,
  },
  engineIcon: {
    fontSize: 20,
  },
  engineTextBox: {
    flex: 1,
  },
  engineName: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '700',
  },
  engineDesc: {
    color: Colors.textMuted,
    fontSize: 10,
    marginTop: 1,
  },
  engineActiveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: Colors.cyan,
    position: 'absolute',
    top: 6,
    right: 8,
  },
  productSelectionBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 18,
    marginBottom: 8,
  },
  addNewLink: {
    color: Colors.cyan,
    fontSize: 11,
    fontWeight: '800',
  },
  productPillRow: {
    flexDirection: 'row',
  },
  productSelectCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#0A0F1D',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.08)',
    marginRight: 10,
    gap: 8,
    minWidth: 150,
  },
  productSelectCardActive: {
    borderColor: Colors.cyan,
    backgroundColor: 'rgba(0, 242, 254, 0.1)',
  },
  productIcon: {
    fontSize: 18,
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
    fontSize: 10,
    marginTop: 3,
  },
  toneRow: {
    flexDirection: 'row',
    gap: 8,
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
  quickInspoRow: {
    flexDirection: 'row',
  },
  inspoChip: {
    backgroundColor: '#0F172A',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.12)',
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 10,
    marginRight: 8,
  },
  inspoChipText: {
    color: '#E2E8F0',
    fontSize: 11,
    fontWeight: '600',
  },
  inputCard: {
    backgroundColor: '#0A0F1D',
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    padding: 12,
    position: 'relative',
  },
  textInput: {
    color: '#FFFFFF',
    fontSize: 13,
    minHeight: 60,
    textAlignVertical: 'top',
  },
  clearAngleBtn: {
    position: 'absolute',
    top: 8,
    right: 10,
  },
  clearAngleText: {
    color: Colors.textMuted,
    fontSize: 11,
    fontWeight: '600',
  },
  previewSection: {
    marginTop: 20,
  },
  previewTitleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 6,
  },
  previewSectionTitle: {
    color: Colors.cyan,
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.8,
  },
  savedPill: {
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(16, 185, 129, 0.35)',
  },
  savedPillText: {
    color: Colors.emerald,
    fontSize: 9,
    fontWeight: '800',
  },
});
