import Card from "../components/ui/Card.jsx";
import Button from "../components/ui/Button.jsx";
import { useState, useEffect } from "react";
import { toast } from "sonner";
import { apiFetch, apiUrl } from "../lib/api.js";
import apiClient from "../lib/apiClient.js";
import SocialMediaConnectionModal from "../components/ui/SocialMediaConnectionModal.jsx";
import { Facebook, Twitter, MessageCircle, Instagram, HardDrive, CalendarDays } from "lucide-react";
import { useAuthStore } from "../store/authStore";

// ========== Usage Widget ==========
function UsageWidget() {
  const [usage, setUsage] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchUsageStats();
  }, []);

  const fetchUsageStats = async () => {
    try {
      const response = await apiFetch('/api/usage-stats');
      const data = await response.json();
      console.log('Usage stats response:', data);
      if (data.success) {
        setUsage(data.usage || {});
      }
    } catch (error) {
      console.error('Failed to fetch usage stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="text-sm text-gray-500">Loading usage...</div>;
  }

  const totalTokens = Object.values(usage).reduce((sum, service) => sum + (service.tokens_used || 0), 0);
  const totalCredits = Object.values(usage).reduce((sum, service) => sum + (service.credits_used || 0), 0);

  return (
    <div className="space-y-2 text-sm">
      <div className="flex justify-between">
        <span className="text-gray-600">Total Tokens:</span>
        <span className="font-medium">{totalTokens.toLocaleString()}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-gray-600">Total Credits:</span>
        <span className="font-medium">{totalCredits.toLocaleString()}</span>
      </div>
      {Object.keys(usage).length > 0 && (
        <div className="pt-2 border-t">
          <div className="text-xs text-gray-500 mb-1">By Service:</div>
          {Object.entries(usage).map(([service, stats]) => (
            <div key={service} className="flex justify-between text-xs">
              <span className="capitalize">{service}:</span>
              <span>{stats.tokens_used || 0} tokens, {stats.credits_used || 0} credits</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ========== Settings Page ==========
function Settings() {
  const [driveConnected, setDriveConnected] = useState(false);
  const [calendarConnected, setCalendarConnected] = useState(false);
  const [notifications, setNotifications] = useState(true);
  const [loading, setLoading] = useState(false);
  const [calendarLoading, setCalendarLoading] = useState(false);
  const [checkingStatus, setCheckingStatus] = useState(true);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  const { user, logout } = useAuthStore();

  // Delete account function
  const handleDeleteAccount = async () => {
    setDeleteLoading(true);
    try {
      const response = await apiClient.deleteAccount();

      if (response) {
        toast.success('Account deleted successfully');
        logout();
        window.location.href = '/login';
      } else {
        throw new Error('Failed to delete account');
      }
    } catch (error) {
      console.error('Delete account error:', error);
      toast.error('Failed to delete account. Please try again.');
    } finally {
      setDeleteLoading(false);
      setShowDeleteConfirm(false);
    }
  };

  // Social media connection states
  const [socialMediaModal, setSocialMediaModal] = useState({ open: false, platform: null });
  const [platformStatus, setPlatformStatus] = useState({
    facebook: { connected: false, checking: false },
    instagram: { connected: false, checking: false },
    twitter: { connected: false, checking: false },
    reddit: { connected: false, checking: false }
  });

  // Check Google Drive connection status on page load
  useEffect(() => {
    checkGoogleStatus();
    checkAllSocialMediaStatus();
  }, []);

  const checkGoogleStatus = async () => {
    try {
      setCheckingStatus(true);
      const response = await apiFetch("/google/status");
      const data = await response.json();
      setDriveConnected(data.connected);
      setCalendarConnected(data.connected); // Same OAuth token works for both
    } catch (error) {
      console.error("Failed to check Google status:", error);
      setDriveConnected(false);
      setCalendarConnected(false);
    } finally {
      setCheckingStatus(false);
    }
  };

  const connectToGoogle = async () => {
    try {
      setLoading(true);
      // Open Google OAuth in a new window
      const authWindow = window.open(
        apiUrl("/google/connect"),
        "GoogleAuth",
        "width=500,height=600,scrollbars=yes,resizable=yes"
      );

      // Poll for connection status
      const pollInterval = setInterval(async () => {
        if (authWindow.closed) {
          clearInterval(pollInterval);
          await checkGoogleStatus();
          if (driveConnected) {
            toast.success("Successfully connected to Google Drive!");
          }
          setLoading(false);
          return;
        }

        try {
          const statusResponse = await apiFetch("/google/status");
          const statusData = await statusResponse.json();
          if (statusData.connected) {
            setDriveConnected(true);
            clearInterval(pollInterval);
            authWindow.close();
            toast.success("Successfully connected to Google Drive!");
            setLoading(false);
          }
        } catch (error) {
          // Continue polling
        }
      }, 2000);

      // Stop polling after 60 seconds
      setTimeout(() => {
        clearInterval(pollInterval);
        if (!authWindow.closed) {
          authWindow.close();
        }
        setLoading(false);
      }, 60000);
    } catch (error) {
      console.error("Failed to connect to Google:", error);
      toast.error("Failed to connect to Google Drive");
      setLoading(false);
    }
  };

  const disconnectGoogle = async () => {
    try {
      setLoading(true);
      const response = await apiFetch("/google/disconnect", { method: "POST" });

      if (response.ok) {
        setDriveConnected(false);
        setCalendarConnected(false);
        toast.success("Successfully disconnected from Google services");
      } else {
        throw new Error("Failed to disconnect");
      }
    } catch (error) {
      console.error("Failed to disconnect from Google:", error);
      toast.error("Failed to disconnect from Google services");
    } finally {
      setLoading(false);
    }
  };

  // Social media platform management functions
  const checkAllSocialMediaStatus = async () => {
    const platforms = ['facebook', 'instagram', 'twitter', 'reddit'];

    for (const platform of platforms) {
      setPlatformStatus(prev => ({ ...prev, [platform]: { ...prev[platform], checking: true } }));

      try {
        const response = await apiFetch(`/social-media/${platform}/status`);
        const data = await response.json();
        setPlatformStatus(prev => ({
          ...prev,
          [platform]: { connected: data.connected, checking: false }
        }));
      } catch (error) {
        console.error(`Failed to check ${platform} status:`, error);
        setPlatformStatus(prev => ({
          ...prev,
          [platform]: { connected: false, checking: false }
        }));
      }
    }
  };

  const handleSocialMediaConnect = async (platform) => {
    try {
      setLoading(true);

      // For Facebook and Reddit, use OAuth2 flow
      if (platform === 'facebook' || platform === 'reddit') {
        // Make API call to initiate OAuth2 flow
        const response = await apiFetch(`/social-media/${platform}/connect`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' }
        });

        if (response.ok) {
          // The backend returns JSON with auth_url
          const data = await response.json();
          const authUrl = data.auth_url;
          const authWindow = window.open(
            authUrl,
            `${platform}Auth`,
            "width=500,height=600,scrollbars=yes,resizable=yes"
          );

          // Poll for connection status
          const pollInterval = setInterval(async () => {
            if (authWindow.closed) {
              clearInterval(pollInterval);
              await checkAllSocialMediaStatus();
              setLoading(false);
              return;
            }

            try {
              const statusResponse = await apiFetch(`/social-media/${platform}/status`);
              const statusData = await statusResponse.json();
              if (statusData.connected) {
                setPlatformStatus(prev => ({
                  ...prev,
                  [platform]: { connected: true, checking: false }
                }));
                clearInterval(pollInterval);
                authWindow.close();
                toast.success(`Successfully connected to ${platform.charAt(0).toUpperCase() + platform.slice(1)}!`);
                setLoading(false);
              }
            } catch (error) {
              // Continue polling
            }
          }, 2000);

          // Stop polling after 60 seconds
          setTimeout(() => {
            clearInterval(pollInterval);
            if (!authWindow.closed) {
              authWindow.close();
            }
            setLoading(false);
          }, 60000);
        } else {
          throw new Error('Failed to initiate OAuth flow');
        }
      } else {
        // For other platforms (Twitter, Instagram), use the modal approach
        setSocialMediaModal({ open: true, platform });
      }
    } catch (error) {
      console.error(`Failed to connect to ${platform}:`, error);
      toast.error(`Failed to connect to ${platform}: ${error.message}`);
      setLoading(false);
    }
  };

  const handleSocialMediaDisconnect = async (platform) => {
    try {
      const response = await apiFetch(`/social-media/${platform}/disconnect`, { method: "POST" });
      if (response.ok) {
        setPlatformStatus(prev => ({
          ...prev,
          [platform]: { ...prev[platform], connected: false }
        }));
        toast.success(`Successfully disconnected from ${platform.charAt(0).toUpperCase() + platform.slice(1)}`);
      }
    } catch (error) {
      console.error(`Failed to disconnect from ${platform}:`, error);
      toast.error(`Failed to disconnect from ${platform}`);
    }
  };

  const handleSaveCredentials = async (platform, credentials) => {
    try {
      const response = await apiFetch(`/social-media/${platform}/connect`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(credentials)
      });

      const result = await response.json();

      if (response.ok && result.success) {
        setPlatformStatus(prev => ({
          ...prev,
          [platform]: { ...prev[platform], connected: true }
        }));
        toast.success(`Successfully connected to ${platform.charAt(0).toUpperCase() + platform.slice(1)}!`);
      } else {
        throw new Error(result.error || 'Connection failed');
      }
    } catch (error) {
      console.error(`Failed to connect to ${platform}:`, error);
      toast.error(`Failed to connect to ${platform}: ${error.message}`);
      throw error;
    }
  };

  const getSocialMediaPlatformConfig = (platform) => {
    const configs = {
      facebook: {
        name: 'Facebook',
        icon: Facebook,
        color: 'bg-blue-600',
        description: 'Connect your Facebook page to post content automatically'
      },
      instagram: {
        name: 'Instagram',
        icon: Instagram,
        color: 'bg-gradient-to-r from-purple-500 to-pink-500',
        description: 'Connect your Instagram account to post content automatically'
      },
      twitter: {
        name: 'Twitter',
        icon: Twitter,
        color: 'bg-black',
        description: 'Connect your Twitter account to post tweets automatically'
      },
      reddit: {
        name: 'Reddit',
        icon: MessageCircle,
        color: 'bg-orange-600',
        description: 'Connect your Reddit account to post to subreddits automatically'
      }
    };
    return configs[platform];
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Settings</h1>

      {/* Social Media Connections Section */}
      <div className="space-y-4">
        <h2 className="text-lg font-medium text-gray-900">Social Media Connections</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {['facebook', 'instagram', 'twitter', 'reddit'].map((platform) => {
            const cfg = getSocialMediaPlatformConfig(platform);
            const st = platformStatus[platform];
            const Icon = cfg.icon;

            // Platform stats + background images (hero area)
            const platformStats = {
              facebook: { users: '3.0B+ users', note: 'High engagement', handle: '@yourbusiness' },
              instagram: { users: '2.4B+ users', note: 'Visual content', handle: '@yourbrand' },
              twitter: { users: '550M+ users', note: 'Real-time updates', handle: '@yourhandle' },
              reddit: { users: '430M+ users', note: 'Community driven', handle: 'r/yourcommunity' },
            }[platform];

            const platformBg = {
              facebook: 'https://images.unsplash.com/photo-1729860648432-723ae383cad9?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxmYWNlYm9vayUyMG1vYmlsZSUyMGFwcHxlbnwxfHx8fDE3NjE3MjQ2NDh8MA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
              instagram: 'https://images.unsplash.com/photo-1759912255512-c5e56b4e5e82?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxpbnN0YWdyYW0lMjBhcHAlMjBpbnRlcmZhY2V8ZW58MXx8fHwxNzYxNzI0NjQ4fDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
              twitter: 'https://images.unsplash.com/photo-1743582733049-dcb16521f6fd?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHx0d2l0dGVyJTIwc29jaWFsJTIwbWVkaWF8ZW58MXx8fHwxNzYxNzI0NjQ4fDA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
              reddit: 'https://images.unsplash.com/photo-1734004691776-d7f04732c174?crop=entropy&cs=tinysrgb&fit=max&fm=jpg&ixid=M3w3Nzg4Nzd8MHwxfHNlYXJjaHwxfHxzb2NpYWwlMjBtZWRpYSUyMHdvcmtzcGFjZSUyMG1vZGVybnxlbnwxfHx8fDE3NjE3MjQ2NDd8MA&ixlib=rb-4.1.0&q=80&w=1080&utm_source=figma&utm_medium=referral',
            }[platform];

            return (
              <div
                key={platform}
                className={`relative rounded-2xl overflow-hidden border-2 bg-white shadow-sm ${st.connected ? 'border-green-400 ring-1 ring-green-300' : 'border-gray-200'}`}
              >
                {/* Hero background */}
                <div className="relative h-36 md:h-40">
                  <div
                    className="absolute inset-0 bg-center bg-cover"
                    style={{ backgroundImage: `url('${platformBg}')` }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-b from-black/15 via-white/10 to-white" />

                  {/* Platform icon */}
                  <div className={`absolute top-3 left-3 w-11 h-11 ${cfg.color} rounded-xl flex items-center justify-center shadow-md`}>
                    <Icon className="w-6 h-6 text-white" />
                  </div>

                  {/* Status badge */}
                  <span className={`absolute top-3 right-3 inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ${st.connected ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
                    <span className={`w-2 h-2 rounded-full ${st.connected ? 'bg-green-500' : 'bg-red-500'}`} />
                    {st.connected ? 'Active' : 'Disconnected'}
                  </span>
                </div>

                {/* Body */}
                <div className="p-5">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="text-lg font-semibold">{cfg.name}</div>
                      <p className="text-sm text-gray-600 max-w-md">{cfg.description}</p>
                    </div>
                  </div>

                  <div className="mt-3 grid grid-cols-1 gap-3 text-sm text-gray-700">
                    <div className="flex items-center gap-3">
                      <span className="text-gray-600">{platformStats.users}</span>
                      <span className="text-gray-400">•</span>
                      <span className="text-gray-600">{platformStats.note}</span>
                    </div>
                    <div>
                      <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-lg text-xs border ${st.connected ? 'bg-green-50 border-green-200 text-green-700' : 'bg-gray-50 border-gray-200 text-gray-600'}`}>
                        ✓ {platformStats.handle}
                      </span>
                    </div>
                  </div>

                  <div className="mt-4 flex items-center gap-3">
                    {st.connected ? (
                      <button
                        onClick={() => handleSocialMediaDisconnect(platform)}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50"
                        disabled={st.checking}
                      >
                        <span className="text-lg leading-none">✖</span> Disconnect
                      </button>
                    ) : (
                      <button
                        onClick={() => handleSocialMediaConnect(platform)}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-white bg-gradient-to-r from-fuchsia-600 to-purple-600 hover:opacity-90"
                        disabled={st.checking}
                      >
                        Connect Now
                      </button>
                    )}
                    <button
                      onClick={() => {
                        setPlatformStatus(prev => ({ ...prev, [platform]: { ...prev[platform], checking: true } }));
                        checkAllSocialMediaStatus();
                      }}
                      className="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-700 hover:bg-gray-50"
                      disabled={st.checking}
                    >
                      {st.checking ? 'Checking...' : 'Refresh'}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
      </div>

      {/* Google Integrations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          {/* Hero background */}
          <div className="relative -mx-5 -mt-5 h-32 md:h-36 overflow-hidden rounded-t-xl">
            <div className="absolute inset-0 bg-center bg-cover" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1504384308090-c894fdcc538d?q=80&w=1600&auto=format&fit=crop')" }} />
            <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-white/10 to-white" />
            {/* Icon */}
            <div className="absolute top-3 left-3 w-11 h-11 bg-emerald-600 rounded-xl flex items-center justify-center shadow-md">
              <HardDrive className="w-6 h-6 text-white" />
            </div>
            {/* Status */}
            <span className={`absolute top-3 right-3 inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ${driveConnected ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
              <span className={`w-2 h-2 rounded-full ${driveConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              {driveConnected ? 'Active' : 'Disconnected'}
            </span>
          </div>

          {/* Body */}
          <div className="p-0 space-y-3">
            <div>
              <div className="text-lg font-semibold">Google Drive</div>
              <p className="text-sm text-gray-600">Save your campaigns and images to Google Drive in JSON format</p>
            </div>
            <div className="flex items-center gap-3 text-sm text-gray-700">
              <span className="text-gray-600">Cloud storage</span>
              <span className="text-gray-400">•</span>
              <span className="text-gray-600">JSON exports</span>
            </div>
            <div className="mt-2 flex items-center gap-3">
              {driveConnected ? (
                <button onClick={disconnectGoogle} disabled={loading} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50">
                  <span className="text-lg leading-none">✖</span> Disconnect
                </button>
              ) : (
                <button onClick={connectToGoogle} disabled={loading} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-white bg-gradient-to-r from-fuchsia-600 to-purple-600 hover:opacity-90">
                  Connect Now
                </button>
              )}
              <button onClick={checkGoogleStatus} disabled={checkingStatus} className="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-700 hover:bg-gray-50">
                {checkingStatus ? 'Checking...' : 'Refresh'}
              </button>
            </div>
          </div>
        </Card>

        <Card>
          {/* Hero background */}
          <div className="relative -mx-5 -mt-5 h-32 md:h-36 overflow-hidden rounded-t-xl">
            <div className="absolute inset-0 bg-center bg-cover" style={{ backgroundImage: "url('https://images.unsplash.com/photo-1506784983877-45594efa4cbe?q=80&w=1600&auto=format&fit=crop')" }} />
            <div className="absolute inset-0 bg-gradient-to-b from-black/20 via-white/10 to-white" />
            {/* Icon */}
            <div className="absolute top-3 left-3 w-11 h-11 bg-indigo-600 rounded-xl flex items-center justify-center shadow-md">
              <CalendarDays className="w-6 h-6 text-white" />
            </div>
            {/* Status */}
            <span className={`absolute top-3 right-3 inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ${calendarConnected ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'}`}>
              <span className={`w-2 h-2 rounded-full ${calendarConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              {calendarConnected ? 'Active' : 'Disconnected'}
            </span>
          </div>

          {/* Body */}
          <div className="p-0 space-y-3">
            <div>
              <div className="text-lg font-semibold">Google Calendar</div>
              <p className="text-sm text-gray-600">Create calendar events for scheduled social media posts with reminders</p>
            </div>
            <div className="flex items-center gap-3 text-sm text-gray-700">
              <span className="text-gray-600">Reminders</span>
              <span className="text-gray-400">•</span>
              <span className="text-gray-600">Calendar sync</span>
            </div>
            <div className="mt-2 flex items-center gap-3">
              {calendarConnected ? (
                <button onClick={disconnectGoogle} disabled={loading} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-red-300 text-red-600 hover:bg-red-50">
                  <span className="text-lg leading-none">✖</span> Disconnect
                </button>
              ) : (
                <button onClick={connectToGoogle} disabled={calendarLoading || loading} className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-white bg-gradient-to-r from-fuchsia-600 to-purple-600 hover:opacity-90">
                  Connect Now
                </button>
              )}
              <button onClick={checkGoogleStatus} disabled={checkingStatus} className="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-700 hover:bg-gray-50">
                {checkingStatus ? 'Checking...' : 'Refresh'}
              </button>
            </div>
          </div>
        </Card>

        <Card title="Notifications">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-medium">Enable notifications</div>
              <div className="text-sm text-gray-600">
                Receive updates about campaign status
              </div>
            </div>
            <button
              role="switch"
              aria-checked={notifications}
              onClick={() => setNotifications((v) => !v)}
              className={
                (notifications ? "bg-blue-600" : "bg-gray-300") +
                " relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
              }
            >
              <span
                className={
                  (notifications ? "translate-x-6" : "translate-x-1") +
                  " inline-block h-4 w-4 transform rounded-full bg-white transition-transform"
                }
              />
            </button>
          </div>
        </Card>

        <Card title="API Usage">
          <UsageWidget />
        </Card>

        <Card title="Account">
          <div className="space-y-3">
            <div className="text-sm text-gray-600">
              User: {user?.name || 'User'} ({user?.email || 'user@example.com'})
            </div>
            <Button
              variant="danger"
              onClick={() => setShowDeleteConfirm(true)}
              disabled={deleteLoading}
            >
              {deleteLoading ? 'Deleting...' : 'Delete account'}
            </Button>
          </div>
        </Card>
      </div>
      </div>

      {/* Social Media Connection Modal */}
      <SocialMediaConnectionModal
        open={socialMediaModal.open}
        onOpenChange={(open) => setSocialMediaModal({ open, platform: socialMediaModal.platform })}
        platform={socialMediaModal.platform}
        onSave={handleSaveCredentials}
      />

      {/* Delete Account Confirmation Modal */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Delete Account
            </h3>
            <p className="text-gray-600 mb-6">
              Are you sure you want to delete your account? This action cannot be undone.
              All your data, campaigns, and posts will be permanently deleted.
            </p>
            <div className="flex space-x-3 justify-end">
              <Button
                variant="secondary"
                onClick={() => setShowDeleteConfirm(false)}
                disabled={deleteLoading}
              >
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={handleDeleteAccount}
                disabled={deleteLoading}
              >
                {deleteLoading ? 'Deleting...' : 'Yes, Delete Account'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Settings;
