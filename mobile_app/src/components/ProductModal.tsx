import React, { useState } from 'react';
import {
  Modal,
  View,
  Text,
  StyleSheet,
  ScrollView,
  TextInput,
  Pressable,
  Alert,
} from 'react-native';
import { Colors } from '../styles/theme';
import { ThreeDButton } from './ThreeDButton';
import { Product, saveProduct } from '../db/database';

interface ProductModalProps {
  visible: boolean;
  onClose: () => void;
  onProductSaved: (newProduct: Product) => void;
}

const CATEGORIES = [
  'E-Commerce & Retail',
  'Technology & Software',
  'Fashion & Apparel',
  'Food & Restaurant',
  'Health & Fitness',
  'Professional Services',
  'Real Estate & Interior',
  'Education & Coaching',
  'Finance & FinTech',
  'Entertainment & Media',
];

const ICONS = ['🚀', '⌚', '🛍️', '👗', '🍔', '💪', '🏢', '🎓', '💎', '💻', '🚗', '☕'];

export const ProductModal: React.FC<ProductModalProps> = ({
  visible,
  onClose,
  onProductSaved,
}) => {
  const [name, setName] = useState('');
  const [category, setCategory] = useState(CATEGORIES[0]);
  const [description, setDescription] = useState('');
  const [targetAudience, setTargetAudience] = useState('');
  const [keyBenefits, setKeyBenefits] = useState('');
  const [ctaText, setCtaText] = useState('Shop Now');
  const [ctaUrl, setCtaUrl] = useState('');
  const [selectedIcon, setSelectedIcon] = useState(ICONS[0]);

  const handleSave = () => {
    if (!name.trim()) {
      Alert.alert('Missing Name', 'Please enter your product or brand name.');
      return;
    }

    const benefitsArray = keyBenefits
      .split('\n')
      .map((b) => b.trim())
      .filter((b) => b.length > 0);

    const newProduct: Product = {
      id: `prod-${Date.now()}`,
      name: name.trim(),
      category: category,
      description: description.trim() || 'Premium quality product tailored for outstanding performance.',
      target_audience: targetAudience.trim() || 'Modern consumers and social media audiences.',
      key_benefits: benefitsArray.length > 0 ? benefitsArray : ['Superior quality & craftsmanship', 'Fast shipping & dedicated support'],
      cta_text: ctaText.trim() || 'Shop Now',
      cta_url: ctaUrl.trim() || 'https://mybrand.com',
      brand_colors: { primary: Colors.primary, secondary: Colors.cyan, accent: Colors.gold },
      logo_icon: selectedIcon,
      created_at: Date.now(),
    };

    saveProduct(newProduct);
    onProductSaved(newProduct);
    onClose();

    // Reset inputs
    setName('');
    setDescription('');
    setTargetAudience('');
    setKeyBenefits('');
    setCtaText('Shop Now');
    setCtaUrl('');
    Alert.alert('✅ Product Added!', `"${newProduct.name}" has been saved to your internal device memory.`);
  };

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={styles.overlay}>
        <View style={styles.modalCard}>
          {/* Header */}
          <View style={styles.modalHeader}>
            <View>
              <Text style={styles.modalBadge}>UNIVERSAL PRODUCT ENGINE</Text>
              <Text style={styles.modalTitle}>Add Your Product / Brand</Text>
            </View>
            <Pressable onPress={onClose} style={styles.closeButton}>
              <Text style={styles.closeText}>✕</Text>
            </Pressable>
          </View>

          <ScrollView style={styles.formScroll} showsVerticalScrollIndicator={false}>
            {/* Brand / Product Name */}
            <Text style={styles.fieldLabel}>Product or Business Name *</Text>
            <TextInput
              style={styles.textInput}
              placeholder="e.g. Apex Sportswear, Cafe Mocha, Zenith CRM"
              placeholderTextColor={Colors.textMuted}
              value={name}
              onChangeText={setName}
            />

            {/* Icon Picker */}
            <Text style={styles.fieldLabel}>Brand Avatar Emoji</Text>
            <View style={styles.iconRow}>
              {ICONS.map((icon) => (
                <Pressable
                  key={icon}
                  onPress={() => setSelectedIcon(icon)}
                  style={[
                    styles.iconBox,
                    selectedIcon === icon && styles.selectedIconBox,
                  ]}
                >
                  <Text style={styles.iconText}>{icon}</Text>
                </Pressable>
              ))}
            </View>

            {/* Category Selector */}
            <Text style={styles.fieldLabel}>Category / Industry</Text>
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.categoryScroll}>
              {CATEGORIES.map((cat) => (
                <Pressable
                  key={cat}
                  onPress={() => setCategory(cat)}
                  style={[
                    styles.categoryPill,
                    category === cat && styles.selectedCategoryPill,
                  ]}
                >
                  <Text
                    style={[
                      styles.categoryText,
                      category === cat && styles.selectedCategoryText,
                    ]}
                  >
                    {cat}
                  </Text>
                </Pressable>
              ))}
            </ScrollView>

            {/* Product Description */}
            <Text style={styles.fieldLabel}>What does this product do? (Description)</Text>
            <TextInput
              style={[styles.textInput, styles.multilineInput]}
              placeholder="Explain features, what makes it special, and why customers love it..."
              placeholderTextColor={Colors.textMuted}
              value={description}
              onChangeText={setDescription}
              multiline
              numberOfLines={3}
            />

            {/* Target Audience */}
            <Text style={styles.fieldLabel}>Target Audience / Ideal Buyer</Text>
            <TextInput
              style={styles.textInput}
              placeholder="e.g. College students, young professionals, gamers, gym-goers..."
              placeholderTextColor={Colors.textMuted}
              value={targetAudience}
              onChangeText={setTargetAudience}
            />

            {/* Key Benefits */}
            <Text style={styles.fieldLabel}>Key Benefits (1 per line)</Text>
            <TextInput
              style={[styles.textInput, styles.multilineInput]}
              placeholder="e.g.&#10;Instant 1-day delivery&#10;Eco-friendly organic materials&#10;50% cheaper than competitors"
              placeholderTextColor={Colors.textMuted}
              value={keyBenefits}
              onChangeText={setKeyBenefits}
              multiline
              numberOfLines={3}
            />

            {/* CTA & Link */}
            <View style={styles.ctaRow}>
              <View style={{ flex: 1 }}>
                <Text style={styles.fieldLabel}>Button CTA</Text>
                <TextInput
                  style={styles.textInput}
                  placeholder="Shop Now"
                  placeholderTextColor={Colors.textMuted}
                  value={ctaText}
                  onChangeText={setCtaText}
                />
              </View>
              <View style={{ flex: 2, marginLeft: 10 }}>
                <Text style={styles.fieldLabel}>Store / Website URL</Text>
                <TextInput
                  style={styles.textInput}
                  placeholder="https://..."
                  placeholderTextColor={Colors.textMuted}
                  value={ctaUrl}
                  onChangeText={setCtaUrl}
                  autoCapitalize="none"
                />
              </View>
            </View>

            {/* Save Button */}
            <ThreeDButton
              title="💾 Save Product to Device"
              onPress={handleSave}
              gradient={['#00F2FE', '#7C5CFC']}
              glowColor={Colors.cyanGlow}
              bevelColor="#2B1A80"
              style={{ marginTop: 20, marginBottom: 30 }}
            />
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.85)',
    justifyContent: 'flex-end',
  },
  modalCard: {
    backgroundColor: '#0D1424',
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    borderWidth: 1.5,
    borderColor: 'rgba(0, 242, 254, 0.3)',
    maxHeight: '90%',
    padding: 20,
    shadowColor: Colors.cyanGlow,
    shadowOffset: { width: 0, height: -10 },
    shadowOpacity: 0.5,
    shadowRadius: 16,
    elevation: 20,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.08)',
  },
  modalBadge: {
    color: Colors.cyan,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 1,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '900',
    color: '#FFFFFF',
    marginTop: 2,
  },
  closeButton: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  closeText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
  formScroll: {
    maxHeight: 520,
  },
  fieldLabel: {
    color: '#E2E8F0',
    fontSize: 13,
    fontWeight: '700',
    marginTop: 12,
    marginBottom: 6,
  },
  textInput: {
    backgroundColor: '#070A12',
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.1)',
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 10,
    color: '#FFFFFF',
    fontSize: 14,
  },
  multilineInput: {
    minHeight: 70,
    textAlignVertical: 'top',
  },
  iconRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginVertical: 4,
  },
  iconBox: {
    width: 40,
    height: 40,
    borderRadius: 10,
    backgroundColor: '#070A12',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  selectedIconBox: {
    borderColor: Colors.cyan,
    backgroundColor: 'rgba(0, 242, 254, 0.15)',
  },
  iconText: {
    fontSize: 20,
  },
  categoryScroll: {
    flexDirection: 'row',
    marginVertical: 4,
  },
  categoryPill: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
    backgroundColor: '#070A12',
    marginRight: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.1)',
  },
  selectedCategoryPill: {
    backgroundColor: 'rgba(124, 92, 252, 0.25)',
    borderColor: Colors.primary,
  },
  categoryText: {
    color: Colors.textSecondary,
    fontSize: 12,
    fontWeight: '600',
  },
  selectedCategoryText: {
    color: '#FFFFFF',
    fontWeight: '800',
  },
  ctaRow: {
    flexDirection: 'row',
  },
});
