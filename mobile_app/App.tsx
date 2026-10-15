import React, { useEffect, useState, Component, ErrorInfo, ReactNode } from 'react';
import {
  SafeAreaView,
  StyleSheet,
  View,
  Text,
  Pressable,
  ActivityIndicator,
  ScrollView,
  Platform,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { Colors } from './src/styles/theme';
import { AppHeader } from './src/components/AppHeader';
import { HomeScreen } from './src/screens/HomeScreen';
import { StudioScreen } from './src/screens/StudioScreen';
import { ApprovalScreen } from './src/screens/ApprovalScreen';
import { VaultScreen } from './src/screens/VaultScreen';
import { initDatabase, getAllCampaigns, Campaign, Product } from './src/db/database';

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('MANVIX AI ErrorBoundary caught:', error, errorInfo);
  }

  handleReload = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <SafeAreaView style={styles.errorContainer}>
          <StatusBar style="light" />
          <View style={styles.errorCard}>
            <Text style={styles.errorEmoji}>⚠️</Text>
            <Text style={styles.errorTitle}>MANVIX AI Notice</Text>
            <Text style={styles.errorSubtitle}>
              A runtime event occurred while rendering.
            </Text>
            <ScrollView style={styles.errorBox}>
              <Text style={styles.errorDetails}>
                {this.state.error?.message || 'Unknown error'}
              </Text>
            </ScrollView>
            <Pressable style={styles.errorButton} onPress={this.handleReload}>
              <Text style={styles.errorButtonText}>🔄 Reload MANVIX AI</Text>
            </Pressable>
          </View>
        </SafeAreaView>
      );
    }

    return this.props.children;
  }
}

type TabKey = 'home' | 'studio' | 'approval' | 'vault';

function MainApp() {
  const [activeTab, setActiveTab] = useState<TabKey>('home');
  const [loading, setLoading] = useState(true);
  const [activeCampaign, setActiveCampaign] = useState<Campaign | null>(null);
  const [studioProduct, setStudioProduct] = useState<Product | null>(null);
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    async function setup() {
      try {
        await initDatabase();
        const campaigns = getAllCampaigns();
        setTotalCount(campaigns.length);
        if (campaigns.length > 0) {
          setActiveCampaign(campaigns[0]);
        }
      } catch (err) {
        console.error('Failed to initialize on-device database:', err);
      } finally {
        setLoading(false);
      }
    }
    setup();
  }, []);

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <StatusBar style="light" />
        <ActivityIndicator size="large" color={Colors.cyan} />
        <Text style={styles.loadingText}>Initializing MANVIX AI...</Text>
        <Text style={styles.loadingSub}>Your Social Media, Supercharged by AI</Text>
        <Text style={styles.loadingDetail}>Mounting 100% On-Device SQLite Vault</Text>
      </View>
    );
  }

  return (
    <SafeAreaView style={styles.safeArea}>
      <StatusBar style="light" />

      {/* Top 3D Branding & Storage Status */}
      <AppHeader
        memoryUsage="100% On-Device"
        totalCampaigns={totalCount}
      />

      {/* Main Active Screen */}
      <View style={styles.body}>
        {activeTab === 'home' && (
          <HomeScreen
            onNavigate={setActiveTab}
            onSelectCampaignForBroadcast={(c) => setActiveCampaign(c)}
            onSelectProductForStudio={(p) => setStudioProduct(p)}
          />
        )}

        {activeTab === 'studio' && (
          <StudioScreen
            onNavigate={setActiveTab}
            selectedProduct={studioProduct}
            onCampaignCreated={(c) => {
              setActiveCampaign(c);
              setTotalCount((prev) => prev + 1);
            }}
          />
        )}

        {activeTab === 'approval' && activeCampaign && (
          <ApprovalScreen
            campaign={activeCampaign}
            onCampaignUpdated={(updated) => setActiveCampaign(updated)}
            onNavigateToVault={() => setActiveTab('vault')}
          />
        )}

        {activeTab === 'approval' && !activeCampaign && (
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No active campaign selected for broadcast.</Text>
            <Pressable
              style={styles.pillAction}
              onPress={() => setActiveTab('studio')}
            >
              <Text style={styles.pillActionText}>Generate One in 3D Studio</Text>
            </Pressable>
          </View>
        )}

        {activeTab === 'vault' && (
          <VaultScreen
            onNavigate={setActiveTab}
            onSelectCampaignForBroadcast={(c) => setActiveCampaign(c)}
          />
        )}
      </View>

      {/* 3D Glass Tab Bar */}
      <View style={styles.tabBar}>
        <Pressable
          onPress={() => setActiveTab('home')}
          style={[
            styles.tabItem,
            activeTab === 'home' && styles.activeTabItem,
          ]}
        >
          <Text style={styles.tabIcon}>⚡</Text>
          <Text
            style={[
              styles.tabLabel,
              activeTab === 'home' && styles.activeTabLabel,
            ]}
          >
            Dashboard
          </Text>
          {activeTab === 'home' && <View style={styles.activeGlowDot} />}
        </Pressable>

        <Pressable
          onPress={() => setActiveTab('studio')}
          style={[
            styles.tabItem,
            activeTab === 'studio' && styles.activeTabItem,
          ]}
        >
          <Text style={styles.tabIcon}>🎨</Text>
          <Text
            style={[
              styles.tabLabel,
              activeTab === 'studio' && styles.activeTabLabel,
            ]}
          >
            3D Studio
          </Text>
          {activeTab === 'studio' && <View style={styles.activeGlowDot} />}
        </Pressable>

        <Pressable
          onPress={() => setActiveTab('approval')}
          style={[
            styles.tabItem,
            activeTab === 'approval' && styles.activeTabItem,
          ]}
        >
          <Text style={styles.tabIcon}>🚀</Text>
          <Text
            style={[
              styles.tabLabel,
              activeTab === 'approval' && styles.activeTabLabel,
            ]}
          >
            Broadcast
          </Text>
          {activeTab === 'approval' && <View style={styles.activeGlowDot} />}
        </Pressable>

        <Pressable
          onPress={() => setActiveTab('vault')}
          style={[
            styles.tabItem,
            activeTab === 'vault' && styles.activeTabItem,
          ]}
        >
          <Text style={styles.tabIcon}>💾</Text>
          <Text
            style={[
              styles.tabLabel,
              activeTab === 'vault' && styles.activeTabLabel,
            ]}
          >
            Vault
          </Text>
          {activeTab === 'vault' && <View style={styles.activeGlowDot} />}
        </Pressable>
      </View>
    </SafeAreaView>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <MainApp />
    </ErrorBoundary>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: Colors.background,
  },
  loadingContainer: {
    flex: 1,
    backgroundColor: Colors.background,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  loadingText: {
    color: '#FFFFFF',
    fontSize: 22,
    fontWeight: '900',
    marginTop: 18,
    letterSpacing: 1,
  },
  loadingSub: {
    color: Colors.cyan,
    fontSize: 13,
    marginTop: 6,
    fontWeight: '700',
  },
  loadingDetail: {
    color: Colors.textMuted,
    fontSize: 11,
    marginTop: 8,
  },
  body: {
    flex: 1,
  },
  tabBar: {
    flexDirection: 'row',
    height: Platform.OS === 'ios' ? 84 : 70,
    paddingBottom: Platform.OS === 'ios' ? 18 : 6,
    backgroundColor: '#070C1A',
    borderTopWidth: 1.5,
    borderTopColor: 'rgba(255, 255, 255, 0.08)',
    paddingHorizontal: 8,
    alignItems: 'center',
    justifyContent: 'space-around',
    shadowColor: Colors.cyanGlow,
    shadowOffset: { width: 0, height: -6 },
    shadowOpacity: 0.35,
    shadowRadius: 10,
    elevation: 12,
  },
  tabItem: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 6,
    paddingHorizontal: 14,
    borderRadius: 14,
    position: 'relative',
  },
  activeTabItem: {
    backgroundColor: 'rgba(0, 242, 254, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(0, 242, 254, 0.3)',
  },
  tabIcon: {
    fontSize: 18,
    marginBottom: 2,
  },
  tabLabel: {
    color: Colors.textMuted,
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  activeTabLabel: {
    color: Colors.cyan,
    fontWeight: '900',
  },
  activeGlowDot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: Colors.cyan,
    position: 'absolute',
    bottom: 2,
  },
  emptyContainer: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  emptyText: {
    color: Colors.textSecondary,
    fontSize: 15,
    marginBottom: 16,
  },
  pillAction: {
    backgroundColor: Colors.primary,
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 14,
  },
  pillActionText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '800',
  },
  errorContainer: {
    flex: 1,
    backgroundColor: '#070A12',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorCard: {
    backgroundColor: '#0D1424',
    borderRadius: 20,
    padding: 24,
    width: '100%',
    alignItems: 'center',
    borderWidth: 1.5,
    borderColor: 'rgba(244, 63, 94, 0.4)',
  },
  errorEmoji: {
    fontSize: 36,
    marginBottom: 12,
  },
  errorTitle: {
    color: '#FFFFFF',
    fontSize: 20,
    fontWeight: '900',
  },
  errorSubtitle: {
    color: Colors.textSecondary,
    fontSize: 13,
    marginTop: 4,
    textAlign: 'center',
  },
  errorBox: {
    backgroundColor: '#070A12',
    borderRadius: 10,
    padding: 12,
    marginVertical: 16,
    maxHeight: 140,
    width: '100%',
  },
  errorDetails: {
    color: '#F43F5E',
    fontSize: 12,
    fontFamily: 'monospace',
  },
  errorButton: {
    backgroundColor: Colors.primary,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 14,
  },
  errorButtonText: {
    color: '#FFFFFF',
    fontWeight: '800',
    fontSize: 14,
  },
});
