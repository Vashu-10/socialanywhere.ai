import { useState, useEffect } from "react";
import Button from "./ui/Button.jsx";
import { toast } from "sonner";
import { apiFetch, apiUrl } from "../lib/api.js";
import apiClient from "../lib/apiClient.js";

const GoogleCalendarIntegration = ({ campaigns = [], onEventCreated }) => {
  const [isConnected, setIsConnected] = useState(false);
  const [loading, setLoading] = useState(false);
  const [creatingEvents, setCreatingEvents] = useState(new Set());

  // Check Google connection status on component mount
  useEffect(() => {
    checkGoogleStatus();
  }, []);

  const checkGoogleStatus = async () => {
    try {
      const data = await apiClient.getGoogleStatus();
      setIsConnected(data && (data.connected || data.success));
    } catch (error) {
      console.error("Failed to check Google status:", error);
      setIsConnected(false);
    }
  };

  const connectToGoogle = async () => {
    try {
      setLoading(true);
      // Open Google OAuth in a new window
      const response = await apiFetch("/google/connect");
      if (response.ok) {
        window.open(apiUrl("/google/connect"), "_blank", "width=500,height=600");
        // Poll for connection status
        const pollInterval = setInterval(async () => {
          await checkGoogleStatus();
          const statusResponse = await apiFetch("/google/status");
          const statusData = await statusResponse.json();
          if (statusData.connected) {
            setIsConnected(true);
            clearInterval(pollInterval);
            toast.success("Successfully connected to Google Calendar!");
          }
        }, 2000);
        
        // Stop polling after 60 seconds
        setTimeout(() => clearInterval(pollInterval), 60000);
      }
    } catch (error) {
      console.error("Failed to connect to Google:", error);
      toast.error("Failed to connect to Google Calendar");
    } finally {
      setLoading(false);
    }
  };

  const createCalendarEvent = async (campaign) => {
    if (!isConnected) {
      toast.error("Please connect to Google Calendar first");
      return;
    }

    if (!campaign.scheduledAt) {
      toast.error("Campaign must be scheduled to create a calendar event");
      return;
    }

    setCreatingEvents(prev => new Set([...prev, campaign.id]));
    
    try {
      const campaignData = {
        id: campaign.id,
        productDescription: campaign.productDescription || campaign.description,
        generatedContent: campaign.generatedContent || campaign.caption,
        scheduledAt: campaign.scheduledAt,
        status: campaign.status,
        imageUrl: campaign.imageUrl,
        driveImageUrl: campaign.driveImageUrl, // Include Google Drive URL for calendar
        activity: campaign.activity || [
          { time: Date.now(), text: "Campaign created" }
        ]
      };

      const response = await apiFetch("/google-calendar/create-event", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(campaignData),
      });

      const data = await response.json();
      
      if (data.success) {
        toast.success(`Calendar event created! View: ${data.eventLink}`);
        if (onEventCreated) {
          onEventCreated(campaign.id, data);
        }
      } else {
        throw new Error(data.error || "Failed to create calendar event");
      }
    } catch (error) {
      console.error("Failed to create calendar event:", error);
      toast.error("Failed to create calendar event");
    } finally {
      setCreatingEvents(prev => {
        const newSet = new Set(prev);
        newSet.delete(campaign.id);
        return newSet;
      });
    }
  };

  const createAllCalendarEvents = async () => {
    if (!isConnected) {
      toast.error("Please connect to Google Calendar first");
      return;
    }

    const scheduledCampaigns = campaigns.filter(c => c.scheduledAt);
    if (scheduledCampaigns.length === 0) {
      toast.error("No scheduled campaigns to create calendar events for");
      return;
    }

    setLoading(true);
    let successCount = 0;
    
    for (const campaign of scheduledCampaigns) {
      try {
        await createCalendarEvent(campaign);
        successCount++;
      } catch (error) {
        console.error(`Failed to create event for campaign ${campaign.id}:`, error);
      }
    }
    
    setLoading(false);
    toast.success(`Created ${successCount} out of ${scheduledCampaigns.length} calendar events`);
  };

  const scheduledCampaigns = campaigns.filter(c => c.scheduledAt);
  const unscheduledCampaigns = campaigns.filter(c => !c.scheduledAt);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
        <div className="flex items-center space-x-3">
          <div className="text-2xl">📅</div>
          <div>
            <h3 className="font-medium text-gray-900">Google Calendar Integration</h3>
            <p className="text-sm text-gray-600">
              {isConnected 
                ? `Create calendar reminders for ${scheduledCampaigns.length} scheduled posts` 
                : "Connect to create calendar events for your scheduled posts"
              }
            </p>
          </div>
        </div>
        
        <div className="flex items-center space-x-2">
          <div className={`${isConnected ? 'bg-green-500' : 'bg-red-500'} w-2 h-2 rounded-full`} />
          <span className="text-sm text-gray-600">
            {isConnected ? "Connected" : "Disconnected"}
          </span>
        </div>
      </div>

      {unscheduledCampaigns.length > 0 && (
        <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex items-center space-x-2">
            <div className="text-yellow-600">⚠️</div>
            <p className="text-sm text-yellow-800">
              {unscheduledCampaigns.length} campaign(s) need to be scheduled before creating calendar events
            </p>
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        {!isConnected ? (
          <Button 
            onClick={connectToGoogle} 
            disabled={loading}
            variant="primary"
          >
            {loading ? "Connecting..." : "Connect Google Calendar"}
          </Button>
        ) : (
          <>
            <Button 
              onClick={createAllCalendarEvents} 
              disabled={loading || scheduledCampaigns.length === 0}
              variant="primary"
            >
              {loading ? "Creating Events..." : `Create All Events (${scheduledCampaigns.length})`}
            </Button>
            <Button 
              onClick={checkGoogleStatus}
              variant="secondary" 
              size="sm"
            >
              Refresh Status
            </Button>
          </>
        )}
      </div>

      {/* Individual campaign event creation */}
      {isConnected && scheduledCampaigns.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium text-gray-900">Individual Campaign Events</h4>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {scheduledCampaigns.map((campaign) => (
              <div key={campaign.id} className="flex items-center justify-between p-2 bg-white border rounded">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">
                    {campaign.productDescription || campaign.description || campaign.id}
                  </div>
                  <div className="text-xs text-gray-500">
                    📅 {new Date(campaign.scheduledAt).toLocaleString()}
                  </div>
                </div>
                <Button
                  size="sm"
                  onClick={() => createCalendarEvent(campaign)}
                  disabled={creatingEvents.has(campaign.id)}
                  variant="secondary"
                >
                  {creatingEvents.has(campaign.id) ? "Creating..." : "Create Event"}
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Unscheduled campaigns info */}
      {isConnected && unscheduledCampaigns.length > 0 && (
        <div className="space-y-2">
          <h4 className="font-medium text-gray-900">Unscheduled Campaigns</h4>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {unscheduledCampaigns.map((campaign) => (
              <div key={campaign.id} className="flex items-center justify-between p-2 bg-gray-50 border rounded">
                <div className="text-sm text-gray-600 truncate">
                  {campaign.productDescription || campaign.description || campaign.id}
                </div>
                <span className="text-xs text-gray-500 px-2 py-1 bg-gray-200 rounded">
                  Not Scheduled
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default GoogleCalendarIntegration;
