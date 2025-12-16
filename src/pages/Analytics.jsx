import { useState, useEffect, useRef } from "react";
import Card from "../components/ui/Card.jsx";
import Dropdown from "../components/ui/Dropdown.jsx";
import analyticsService from "../services/analyticsService.js";
import { apiFetch } from "../lib/api.js";

// WebSocket real-time updates
const WS_PATH = (typeof window !== 'undefined' && window.location.hostname === 'localhost') ? 'ws://localhost:8000/ws/analytics' : `${(typeof window !== 'undefined' ? window.location.protocol.replace('http', 'ws') : 'ws:')}//${(typeof window !== 'undefined' ? window.location.host : '')}/ws/analytics`;

function Analytics() {
  const [analyticsData, setAnalyticsData] = useState({
    overview: null,
    followers: null,
    demographics: null,
    posts: null,
    bestPost: null,
    worstPost: null,
    status: null
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isConfigured, setIsConfigured] = useState(false);
  const [selectedPlatform, setSelectedPlatform] = useState("all");
  const [selectedCampaign, setSelectedCampaign] = useState("all");

  // Platform options for dropdown
  const platformOptions = [
    { value: "all", label: "All Platforms", icon: (<svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" /></svg>) },
    { value: "facebook", label: "Facebook", icon: (<svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" /></svg>) },
    { value: "instagram", label: "Instagram", icon: (<svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" /></svg>) },
    { value: "twitter", label: "Twitter", icon: (<svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z" /></svg>) },
    { value: "reddit", label: "Reddit", icon: (<svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0zm5.01 4.744c.688 0 1.25.561 1.25 1.249a1.25 1.25 0 0 1-2.498.056l-2.597-.547-.8 3.747c1.824.07 3.48.632 4.674 1.488.308-.309.73-.491 1.207-.491.968 0 1.754.786 1.754 1.754 0 .716-.435 1.333-1.01 1.614a3.111 3.111 0 0 1 .042.52c0 2.694-3.13 4.87-7.004 4.87-3.874 0-7.004-2.176-7.004-4.87 0-.183.015-.366.043-.534A1.748 1.748 0 0 1 4.028 12c0-.968.786-1.754 1.754-1.754.463 0 .898.196 1.207.49 1.207-.883 2.878-1.43 4.744-1.487l.885-4.182a.342.342 0 0 1 .14-.197.35.35 0 0 1 .238-.042l2.906.617a1.214 1.214 0 0 1 1.108-.701z" /></svg>) }
  ];

  // Platform-specific campaign options
  const getCampaignOptions = (platform) => {
    const baseOptions = [
      {
        value: "all",
        label: "All Campaigns",
        icon: (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" />
          </svg>
        )
      }
    ];

    switch (platform) {
      case "facebook":
        return [
          ...baseOptions,
          {
            value: "fifa_world_cup",
            label: "FIFA World Cup 2026",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            )
          },
          {
            value: "office_behind_scenes",
            label: "Office Behind Scenes",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
              </svg>
            )
          }
        ];

      case "instagram":
        return [
          ...baseOptions,
          {
            value: "lifestyle_brand",
            label: "Lifestyle Brand",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
              </svg>
            )
          },
          {
            value: "visual_storytelling",
            label: "Visual Storytelling",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
              </svg>
            )
          }
        ];

      case "twitter":
        return [
          ...baseOptions,
          {
            value: "product_launch",
            label: "Product Launch",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
              </svg>
            )
          },
          {
            value: "startup_lessons",
            label: "Startup Lessons Thread",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 011 1v2a1 1 0 01-1 1H4a1 1 0 01-1-1V4zM3 10a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H4a1 1 0 01-1-1v-6zM14 9a1 1 0 00-1 1v6a1 1 0 001 1h2a1 1 0 001-1v-6a1 1 0 00-1-1h-2z" clipRule="evenodd" />
              </svg>
            )
          }
        ];

      case "reddit":
        return [
          ...baseOptions,
          {
            value: "nike_sale",
            label: "Nike Sale Alert",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-8.293l-3-3a1 1 0 00-1.414 0l-3 3a1 1 0 001.414 1.414L9 9.414V13a1 1 0 102 0V9.414l1.293 1.293a1 1 0 001.414-1.414z" clipRule="evenodd" />
              </svg>
            )
          },
          {
            value: "screen_time_til",
            label: "Screen Time TIL",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
              </svg>
            )
          }
        ];

      case "all":
      default:
        return [
          ...baseOptions,
          {
            value: "cross_platform",
            label: "Cross-Platform Campaign",
            icon: (
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3z" />
              </svg>
            )
          }
        ];
    }
  };

  const campaignOptions = getCampaignOptions(selectedPlatform);

  // Reset campaign selection when platform changes
  useEffect(() => { setSelectedCampaign("all"); }, [selectedPlatform]);

  useEffect(() => { loadAnalyticsData(); }, [selectedPlatform, selectedCampaign]);

  // WebSocket connection for real-time analytics updates
  const wsRef = useRef(null);
  useEffect(() => {
    const ws = new WebSocket(WS_PATH);
    wsRef.current = ws;

    ws.addEventListener('open', () => { try { ws.send('ping'); } catch { } });

    ws.addEventListener('message', (evt) => {
      try {
        const payload = JSON.parse(evt.data);
        if (payload.type === 'snapshot' && payload.overview) {
          setAnalyticsData(prev => ({ ...prev, overview: payload.overview.data || payload.overview }));
        }
      } catch (e) { console.warn('WS analytics parse error', e); }
    });

    ws.addEventListener('close', () => {
      setTimeout(() => { if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) loadAnalyticsData(); }, 2000);
    });

    return () => { try { ws.close(); } catch { } };
  }, [selectedPlatform]);

  // Transform and helper functions (Twitter/Reddit) - reuse from user's design
  const transformTwitterData = (accountInfo, accountAnalytics, myTweets) => {
    // Normalize account payload from multiple shapes
    const accRaw = accountInfo?.account || accountInfo?.user || accountInfo?.data || {};
    const followers = accRaw.followers_count || accRaw.public_metrics?.followers_count || 0;

    // Normalize tweets/posts array from multiple shapes
    const raw = (myTweets && (myTweets.tweets || myTweets.posts || myTweets.data)) || [];
    const tweets = raw.map((t) => {
      const pm = t.public_metrics || {};
      return {
        id: t.id,
        text: t.text || t.message || t.full_text || "",
        created_at: t.created_at || t.created_time || t.timestamp || null,
        like_count: t.like_count ?? pm.like_count ?? t.reactions?.like ?? 0,
        retweet_count: t.retweet_count ?? pm.retweet_count ?? t.reactions?.retweet ?? 0,
        reply_count: t.reply_count ?? pm.reply_count ?? t.reactions?.reply ?? 0,
        impression_count: t.impression_count ?? pm.impression_count ?? t.impressions ?? 0,
        url: t.url || null,
      };
    });

    const totalTweets = tweets.length;
    const totalLikes = tweets.reduce((s, t) => s + (t.like_count || 0), 0);
    const totalRetweets = tweets.reduce((s, t) => s + (t.retweet_count || 0), 0);
    const totalReplies = tweets.reduce((s, t) => s + (t.reply_count || 0), 0);
    const totalImpressions = tweets.reduce((s, t) => s + (t.impression_count || 0), 0);
    const avgImpressions = totalTweets ? Math.round(totalImpressions / totalTweets) : 0;

    const topTweets = [...tweets]
      .sort(
        (a, b) =>
          (b.like_count + b.retweet_count + b.reply_count) -
          (a.like_count + a.retweet_count + a.reply_count)
      )
      .slice(0, 5);

    const formattedTweets = tweets.map((tweet) => ({
      id: tweet.id,
      message: tweet.text,
      created_time: tweet.created_at,
      reach: tweet.impression_count || 0,
      impressions: tweet.impression_count || 0,
      engaged_users:
        (tweet.like_count || 0) + (tweet.retweet_count || 0) + (tweet.reply_count || 0),
      engagement_rate: tweet.impression_count
        ?
        ((tweet.like_count + tweet.retweet_count + tweet.reply_count) /
          tweet.impression_count)
        : 0,
      reactions: {
        like: tweet.like_count || 0,
        retweet: tweet.retweet_count || 0,
        reply: tweet.reply_count || 0,
      },
      url: tweet.url,
    }));

    return {
      overview: {
        totals: {
          followers,
          impressions: totalImpressions,
          reach: totalImpressions,
          engagement_rate: avgImpressions
            ? (totalLikes + totalRetweets + totalReplies) / avgImpressions
            : 0,
          best_post: topTweets[0]?.id || null,
        },
        metrics_available: true,
        configured: !!accountInfo?.success,
      },
      followers: { followers, configured: !!accountInfo?.success },
      demographics: {},
      posts: { posts: formattedTweets, configured: !!myTweets?.success },
      bestPost: {
        post: topTweets[0]
          ? {
            id: topTweets[0].id,
            message: topTweets[0].text,
            reach: topTweets[0].impression_count || 0,
            impressions: topTweets[0].impression_count || 0,
            engaged_users:
              (topTweets[0].like_count || 0) +
              (topTweets[0].retweet_count || 0) +
              (topTweets[0].reply_count || 0),
            engagement_rate: topTweets[0].impression_count
              ?
              ((topTweets[0].like_count +
                topTweets[0].retweet_count +
                topTweets[0].reply_count) /
                topTweets[0].impression_count)
              : 0,
          }
          : {},
        configured: !!myTweets?.success,
      },
      worstPost: {
        post: topTweets[topTweets.length - 1] || {},
        configured: !!myTweets?.success,
      },
      status: { configured: !!accountInfo?.success, account_info: accRaw, summary: accountAnalytics || {} },
    };
  };

  const transformRedditData = (accountInfo, accountAnalytics, myPosts, myComments) => {
    const account = accountInfo.success ? accountInfo.account : {};
    const posts = myPosts.success ? myPosts.posts || [] : [];
    const totalPostScore = posts.reduce((s, p) => s + (p.score || 0), 0);
    const totalPostComments = posts.reduce((s, p) => s + (p.num_comments || 0), 0);
    const mapReddit = (post) => ({
      id: post.id,
      message: post.title || post.selftext || '',
      created_time: post.created_utc ? new Date(post.created_utc * 1000).toISOString() : null,
      reach: post.score || 0,
      impressions: post.score || 0,
      engaged_users: post.num_comments || 0,
      engagement_rate: post.score ? (post.num_comments / post.score) : 0,
      reactions: { upvote: post.score || 0, downvote: 0, comment: post.num_comments || 0 },
      subreddit: post.subreddit,
      permalink: post.permalink,
      url: post.url,
    });
    const formatted = posts.map(mapReddit);
    const best = [...posts].sort((a, b) => (b.score || 0) - (a.score || 0))[0];
    const worst = [...posts].sort((a, b) => (a.score || 0) - (b.score || 0))[0];
    return {
      overview: {
        totals: {
          followers: account.followers_count || 0, // Real Reddit followers from user-subreddit
          impressions: totalPostScore, // Total post score (upvotes)
          reach: totalPostComments, // Total comments received
          engagement_rate: totalPostComments > 0 ? (totalPostComments / Math.max(totalPostScore, 1)) * 100 : 0,
          best_post: best?.id || null,
        },
        metrics_available: true,
        configured: accountInfo.success,
      },
      followers: { followers: account.followers_count || 0, configured: accountInfo.success }, // Real Reddit followers
      demographics: { by_subreddit: posts.reduce((m, p) => ((m[p.subreddit] = (m[p.subreddit] || 0) + 1), m), {}) },
      posts: { posts: formatted, configured: myPosts.success },
      bestPost: { post: best ? mapReddit(best) : {}, configured: myPosts.success },
      worstPost: { post: worst ? mapReddit(worst) : {}, configured: myPosts.success },
      status: { configured: accountInfo.success, account_info: account, summary: accountAnalytics || {} },
    };
  };

  const transformInstagramData = (accountInfo, accountAnalytics, mediaList) => {
    const account = accountInfo.success ? accountInfo.account : {};
    const analytics = accountAnalytics.success ? accountAnalytics : {};
    const media = mediaList.success ? mediaList.media || [] : [];

    const mapInstagram = (post) => ({
      id: post.id,
      message: post.caption || '',
      created_time: post.timestamp || null,
      reach: post.total_engagement || 0,
      impressions: post.total_engagement || 0,
      engaged_users: post.comments_count || 0,
      engagement_rate: post.like_count > 0 ? (post.comments_count / post.like_count) * 100 : 0,
      reactions: { like: post.like_count || 0, comment: post.comments_count || 0 },
      media_type: post.media_type,
      media_url: post.media_url,
      permalink: post.permalink,
    });

    const formatted = media.map(mapInstagram);
    const best = [...media].sort((a, b) => (b.total_engagement || 0) - (a.total_engagement || 0))[0];
    const worst = [...media].sort((a, b) => (a.total_engagement || 0) - (b.total_engagement || 0))[0];

    return {
      overview: {
        totals: {
          followers: account.followers_count || 0,
          impressions: analytics.summary?.total_engagement || 0,
          reach: analytics.summary?.total_engagement || 0,
          engagement_rate: analytics.summary?.avg_engagement || 0,
          best_post: best?.id || null,
        },
        metrics_available: true,
        configured: accountInfo.success,
      },
      followers: { followers: account.followers_count || 0, configured: accountInfo.success },
      demographics: {
        by_media_type: analytics.media_types || {},
        by_engagement: formatted.reduce((m, p) => {
          const range = p.total_engagement > 100 ? 'high' : p.total_engagement > 50 ? 'medium' : 'low';
          m[range] = (m[range] || 0) + 1;
          return m;
        }, {})
      },
      posts: { posts: formatted, configured: mediaList.success },
      bestPost: { post: best ? mapInstagram(best) : {}, configured: mediaList.success },
      worstPost: { post: worst ? mapInstagram(worst) : {}, configured: mediaList.success },
      status: { configured: accountInfo.success, account_info: account, summary: analytics.summary || {} },
    };
  };

  const getInstagramMockData = () => ({
    overview: {
      totals: {
        followers: 1250,
        impressions: 15420,
        reach: 12350,
        engagement_rate: 4.2,
        best_post: "mock_best_post_id",
      },
      metrics_available: true,
      configured: false,
    },
    followers: { followers: 1250, configured: false },
    demographics: {
      by_media_type: { "IMAGE": 15, "VIDEO": 5, "CAROUSEL_ALBUM": 3 },
      by_engagement: { high: 8, medium: 10, low: 5 }
    },
    posts: {
      posts: [
        {
          id: "mock_post_1",
          message: "Beautiful sunset today! 🌅 #nature #photography",
          created_time: new Date().toISOString(),
          reach: 1250,
          impressions: 1250,
          engaged_users: 45,
          engagement_rate: 3.6,
          reactions: { like: 42, comment: 3 },
          media_type: "IMAGE",
          media_url: "https://picsum.photos/400/400",
          permalink: "https://instagram.com/p/mock_post_1/",
        }
      ],
      configured: false
    },
    bestPost: {
      post: {
        id: "mock_best_post",
        message: "This is our best performing post! 🎉",
        created_time: new Date().toISOString(),
        reach: 2500,
        impressions: 2500,
        engaged_users: 125,
        engagement_rate: 5.0,
        reactions: { like: 120, comment: 5 },
        media_type: "IMAGE",
        media_url: "https://picsum.photos/400/400",
        permalink: "https://instagram.com/p/mock_best_post/",
      },
      configured: false
    },
    worstPost: {
      post: {
        id: "mock_worst_post",
        message: "This post didn't perform well...",
        created_time: new Date().toISOString(),
        reach: 150,
        impressions: 150,
        engaged_users: 3,
        engagement_rate: 2.0,
        reactions: { like: 2, comment: 1 },
        media_type: "IMAGE",
        media_url: "https://picsum.photos/400/400",
        permalink: "https://instagram.com/p/mock_worst_post/",
      },
      configured: false
    },
    status: { configured: false, account_info: {}, summary: {} },
  });

  const ensureBestWorst = (data) => {
    try {
      const postsArr = data?.posts?.posts || [];
      const hasBest = data?.bestPost?.post && Object.keys(data.bestPost.post).length > 0;
      const hasWorst = data?.worstPost?.post && Object.keys(data.worstPost.post).length > 0;
      if ((!hasBest || !hasWorst) && postsArr.length > 0) {
        const sorted = [...postsArr].sort((a, b) => {
          const ae = (a.engaged_users || 0) + (a.impressions || a.reach || 0) * 0.001;
          const be = (b.engaged_users || 0) + (b.impressions || b.reach || 0) * 0.001;
          return be - ae;
        });
        const best = sorted[0];
        const worst = sorted[sorted.length - 1];
        return {
          ...data,
          bestPost: { post: hasBest ? data.bestPost.post : (best || {}), configured: data.bestPost?.configured ?? true },
          worstPost: { post: hasWorst ? data.worstPost.post : (worst || {}), configured: data.worstPost?.configured ?? true },
        };
      }
    } catch { }
    return data;
  };

  const loadAnalyticsData = async () => {
    try {
      setLoading(true); setError(null);
      if (selectedPlatform === 'facebook') {
        // Use analyticsService endpoints and helpers
        const [overview, followers, demographics, posts, bestPost, worstPost, status, availableMetrics] = await Promise.all([
          analyticsService.getAnalyticsOverview(),
          analyticsService.getFollowers(),
          analyticsService.getDemographics(),
          analyticsService.getPostsAnalytics(10),
          analyticsService.getBestPost(10),
          analyticsService.getWorstPost(10),
          analyticsService.getAnalyticsStatus(),
          analyticsService.getAvailableMetrics(),
        ]);

        const engagementOverTime = analyticsService.generateEngagementOverTime(posts.posts || []);

        setAnalyticsData(ensureBestWorst({
          overview,
          followers,
          demographics,
          posts,
          bestPost,
          worstPost,
          status,
          availableMetrics,
          engagementOverTime,
        }));
        setIsConfigured(status && status.configured);
      } else if (selectedPlatform === 'instagram') {
        // Instagram analytics using dedicated Instagram endpoints
        try {
          const [accountInfo, accountAnalytics, mediaList] = await Promise.all([
            apiFetch('/api/instagram/account/info').then(r => r.json()),
            apiFetch('/api/instagram/account/analytics').then(r => r.json()),
            apiFetch('/api/instagram/media?limit=25').then(r => r.json())
          ]);

          if (accountInfo.success && accountAnalytics.success) {
            const instagramData = transformInstagramData(accountInfo, accountAnalytics, mediaList);
            setAnalyticsData(ensureBestWorst(instagramData));
            setIsConfigured(true);
          } else {
            setAnalyticsData(getInstagramMockData());
            setIsConfigured(false);
          }
        } catch (e) {
          console.error('Instagram analytics error:', e);
          setAnalyticsData(getInstagramMockData());
          setIsConfigured(false);
        }
      } else if (selectedPlatform === 'reddit') {
        try {
          const [accountInfo, accountAnalytics, myPosts, myComments] = await Promise.all([
            apiFetch('/api/reddit/account/info').then(r => r.json()),
            apiFetch('/api/reddit/account/analytics').then(r => r.json()),
            apiFetch('/api/reddit/posts/my?limit=10').then(r => r.json()),
            apiFetch('/api/reddit/comments/my?limit=10').then(r => r.json())
          ]);
          if (accountInfo.success && accountAnalytics.success) {
            const rd = transformRedditData(accountInfo, accountAnalytics, myPosts, myComments);
            setAnalyticsData(ensureBestWorst(rd)); setIsConfigured(true);
          } else { setAnalyticsData(getRedditMockData()); setIsConfigured(false); }
        } catch (e) { setAnalyticsData(getRedditMockData()); setIsConfigured(false); }
      } else if (selectedPlatform === 'twitter') {
        try {
          const [accountInfo, accountAnalytics, myTweets] = await Promise.all([
            apiFetch('/api/twitter/account/info').then(r => r.json()),
            apiFetch('/api/twitter/account/analytics').then(r => r.json()),
            apiFetch('/api/twitter/posts/my?limit=10').then(r => r.json())
          ]);
          if (accountInfo.success && accountAnalytics.success) {
            const td = transformTwitterData(accountInfo, accountAnalytics, myTweets);
            setAnalyticsData(ensureBestWorst(td)); setIsConfigured(true);
          } else { setAnalyticsData(getTwitterMockData()); setIsConfigured(false); }
        } catch (e) { setAnalyticsData(getTwitterMockData()); setIsConfigured(false); }
      } else {
        setAnalyticsData(getPlatformMockData(selectedPlatform)); setIsConfigured(selectedPlatform !== 'all');
      }
    } catch (err) { console.error('Error loading analytics data:', err); setError(err.message || String(err)); }
    finally { setLoading(false); }
  };

  const refreshData = () => { loadAnalyticsData(); };

  // helpers and mock data omitted for brevity — reuse simple fallbacks
  const formatNumber = (num) => { if (num === null || num === undefined) return '0'; return Number(num).toLocaleString(); };
  const safeGet = (obj, path, fallback = 'N/A') => { try { const v = path.split('.').reduce((o, p) => o && o[p], obj); return v !== null && v !== undefined ? v : fallback; } catch { return fallback; } };

  // Minimal mock helpers
  const getTwitterMockData = () => ({ overview: { totals: { followers: 0, impressions: 0, reach: 0, engagement_rate: 0, best_post: null }, metrics_available: false, configured: true }, followers: { followers: 0, configured: true }, demographics: {}, posts: { posts: [], configured: true }, bestPost: { post: {}, configured: true }, worstPost: { post: {}, configured: true }, status: { configured: true, account_info: { username: 'shephertz' }, summary: {} } });
  const getRedditMockData = () => ({ overview: { totals: { followers: 1250, impressions: 45320, reach: 32100, engagement_rate: 4.2, best_post: 'rd_post_001' }, metrics_available: true, configured: false }, followers: { followers: 1250, configured: false }, demographics: { by_subreddit: {} }, posts: { posts: [], configured: false }, bestPost: { post: {}, configured: false }, worstPost: { post: {}, configured: false }, status: { configured: false } });
  const getPlatformMockData = (p) => ({ overview: { totals: { followers: 0, impressions: 0, reach: 0, engagement_rate: 0, best_post: null } }, followers: { followers: 0, configured: false }, demographics: {}, posts: { posts: [], configured: false }, bestPost: null, worstPost: null, status: { configured: p !== 'all' } });

  // initial load
  useEffect(() => { loadAnalyticsData(); }, []);

  if (loading) return (<div className="space-y-6"><h1 className="text-2xl font-semibold">Analytics</h1><div className="flex justify-center items-center py-12"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div><span className="ml-4 text-gray-600">Loading analytics data...</span></div></div>);

  // Show platform selection if no platform is selected
  if (selectedPlatform === "all") {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <h1 className="text-2xl font-semibold">Analytics</h1>

          {/* Platform dropdown */}
          <Dropdown
            options={platformOptions}
            value={selectedPlatform}
            onChange={setSelectedPlatform}
            placeholder="Select Platform"
          />
        </div>

        {/* Platform Selection Interface */}
        <div className="flex flex-col items-center justify-center py-20">
          <div className="text-center max-w-lg">
            <div className="w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
              <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">Choose a Platform</h2>
            <p className="text-lg text-gray-600 mb-8 leading-relaxed">
              Select a social media platform from the dropdown above to view analytics and performance data.
            </p>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              <button onClick={() => setSelectedPlatform('facebook')} className="flex flex-col items-center p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-all duration-200 cursor-pointer group">
                <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center mb-2 group-hover:scale-110 transition-transform duration-200">
                  <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
                  </svg>
                </div>
                <span className="text-sm font-medium text-gray-700 group-hover:text-blue-700 transition-colors duration-200">Facebook</span>
              </button>

              <button onClick={() => setSelectedPlatform('instagram')} className="flex flex-col items-center p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-pink-300 hover:bg-pink-50 transition-all duration-200 cursor-pointer group">
                <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center mb-2 group-hover:scale-110 transition-transform duration-200">
                  <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zm0-2.163c-3.259 0-3.667.014-4.947.072-4.358.2-6.78 2.618-6.98 6.98-.059 1.281-.073 1.689-.073 4.948 0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98 1.281.058 1.689.072 4.948.072 3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98-1.281-.059-1.69-.073-4.949-.073zm0 5.838c-3.403 0-6.162 2.759-6.162 6.162s2.759 6.163 6.162 6.163 6.162-2.759 6.162-6.163c0-3.403-2.759-6.162-6.162-6.162zm0 10.162c-2.209 0-4-1.79-4-4 0-2.209 1.791-4 4-4s4 1.791 4 4c0 2.21-1.791 4-4 4zm6.406-11.845c-.796 0-1.441.645-1.441 1.44s.645 1.44 1.441 1.44c.795 0 1.439-.645 1.439-1.44s-.644-1.44-1.439-1.44z" />
                  </svg>
                </div>
                <span className="text-sm font-medium text-gray-700 group-hover:text-pink-700 transition-colors duration-200">Instagram</span>
              </button>

              <button onClick={() => setSelectedPlatform('twitter')} className="flex flex-col items-center p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-blue-300 hover:bg-blue-50 transition-all duration-200 cursor-pointer group">
                <div className="w-8 h-8 bg-black rounded-lg flex items-center justify-center mb-2 group-hover:scale-110 transition-transform duration-200">
                  <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M23.953 4.57a10 10 0 01-2.825.775 4.958 4.958 0 002.163-2.723c-.951.555-2.005.959-3.127 1.184a4.92 4.92 0 00-8.384 4.482C7.69 8.095 4.067 6.13 1.64 3.162a4.822 4.822 0 00-.666 2.475c0 1.71.87 3.213 2.188 4.096a4.904 4.904 0 01-2.228-.616v.06a4.923 4.923 0 003.946 4.827 4.996 4.996 0 01-2.212.085 4.936 4.936 0 004.604 3.417 9.867 9.867 0 01-6.102 2.105c-.39 0-.779-.023-1.17-.067a13.995 13.995 0 007.557 2.209c9.053 0 13.998-7.496 13.998-13.985 0-.21 0-.42-.015-.63A9.935 9.935 0 0024 4.59z" />
                  </svg>
                </div>
                <span className="text-sm font-medium text-gray-700 group-hover:text-blue-700 transition-colors duration-200">Twitter</span>
              </button>

              <button onClick={() => setSelectedPlatform('reddit')} className="flex flex-col items-center p-4 bg-gray-50 rounded-lg border border-gray-200 hover:border-orange-300 hover:bg-orange-50 transition-all duration-200 cursor-pointer group">
                <div className="w-8 h-8 bg-orange-600 rounded-lg flex items-center justify-center mb-2 group-hover:scale-110 transition-transform duration-200">
                  <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 0C5.373 0 0 5.373 0 12s5.373 12 12 12 12-5.373 12-12S18.627 0 12 0zm5.568 8.16c-.169 1.858-.896 3.305-2.189 4.34-.98.78-2.267 1.244-3.768 1.244-2.954 0-5.355-2.401-5.355-5.355 0-.42.048-.83.138-1.224.8.09 1.536.22 2.189.39-.8-.48-1.328-1.24-1.328-2.14 0-.48.12-.93.33-1.32.9.11 1.69.35 2.4.7-.75-.8-1.86-1.3-3.07-1.3-2.33 0-4.22 1.89-4.22 4.22 0 .33.04.65.11.96-3.51-.18-6.62-1.86-8.7-4.42-.36.63-.57 1.36-.57 2.14 0 1.47.75 2.77 1.89 3.53-.7-.02-1.36-.21-1.94-.53v.05c0 2.05 1.46 3.76 3.4 4.15-.36.1-.73.15-1.12.15-.27 0-.54-.03-.8-.08.54 1.69 2.11 2.92 3.97 2.95-1.45 1.14-3.28 1.82-5.27 1.82-.34 0-.68-.02-1.02-.06 1.88 1.21 4.12 1.91 6.52 1.91 7.82 0 12.09-6.48 12.09-12.09 0-.18 0-.37-.01-.56.83-.6 1.55-1.35 2.12-2.2z" />
                  </svg>
                </div>
                <span className="text-sm font-medium text-gray-700 group-hover:text-orange-700 transition-colors duration-200">Reddit</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-semibold">Analytics</h1>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2"><div className={`w-3 h-3 rounded-full ${isConfigured ? 'bg-green-500' : 'bg-yellow-500'}`}></div><span className="text-sm text-gray-600">{isConfigured ? 'Live Data' : 'Demo Data'}</span></div>
          <Dropdown options={getCampaignOptions(selectedPlatform)} value={selectedCampaign} onChange={setSelectedCampaign} placeholder="Select Campaign" />
          <Dropdown options={platformOptions} value={selectedPlatform} onChange={setSelectedPlatform} placeholder="Select Platform" />
          <button onClick={refreshData} className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors">Refresh Data</button>
        </div>
      </div>

      {error && (<div className="bg-red-50 border border-red-200 rounded-lg p-4"><div className="text-red-800"><strong>Error loading analytics:</strong> {error}</div></div>)}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {selectedPlatform === "reddit" ? (
          <>
            <Card title="Followers"><div className="text-2xl font-semibold">{formatNumber(safeGet(analyticsData.followers, 'followers', 0))}</div><div className="text-sm text-gray-500">Profile followers</div></Card>
            <Card title="Total Karma"><div className="text-2xl font-semibold">{formatNumber(safeGet(analyticsData.status, 'account_info.total_karma', 0))}</div><div className="text-sm text-gray-500">Account karma</div></Card>
            <Card title="Post Score"><div className="text-2xl font-semibold">{formatNumber(safeGet(analyticsData.overview, 'totals.impressions', 0))}</div><div className="text-sm text-gray-500">Total post score</div></Card>
          </>
        ) : (
          <>
            <Card title="Followers"><div className="text-2xl font-semibold">{formatNumber(safeGet(analyticsData.followers, 'followers', 0))}</div><div className="text-sm text-gray-500">Total page followers</div></Card>
            <Card title="Impressions"><div className="text-2xl font-semibold">{formatNumber(safeGet(analyticsData.overview, 'totals.impressions', 0))}</div><div className="text-sm text-gray-500">Post impressions</div></Card>
            <Card title="Reach"><div className="text-2xl font-semibold">{formatNumber(safeGet(analyticsData.overview, 'totals.reach', 0))}</div><div className="text-sm text-gray-500">Total reach</div></Card>
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title={selectedPlatform === "reddit" ? "Posts by Subreddit" : selectedPlatform === "twitter" ? "Account Statistics" : "Audience by Country"}>
          <div className="space-y-2">
            {selectedPlatform === "reddit" ? (
              analyticsData.demographics?.by_subreddit && Object.keys(analyticsData.demographics.by_subreddit).length > 0 ? (
                Object.entries(analyticsData.demographics.by_subreddit)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 5)
                  .map(([subreddit, count]) => (
                    <div key={subreddit} className="flex justify-between items-center">
                      <span className="text-gray-700">r/{subreddit}</span>
                      <span className="font-semibold">{formatNumber(count)} posts</span>
                    </div>
                  ))
              ) : (
                <div className="text-gray-500 text-center py-4">No subreddit data available</div>
              )
            ) : selectedPlatform === "twitter" ? (
              analyticsData.status?.account_info ? (
                <div className="space-y-3">
                  <div className="flex justify-between items-center"><span className="text-gray-700">Total Tweets</span><span className="font-semibold">{formatNumber(analyticsData.status.account_info.tweet_count || 0)}</span></div>
                  <div className="flex justify-between items-center"><span className="text-gray-700">Following</span><span className="font-semibold">{formatNumber(analyticsData.status.account_info.following_count || 0)}</span></div>
                  <div className="flex justify-between items-center"><span className="text-gray-700">Verified</span><span className="font-semibold">{analyticsData.status.account_info.verified ? 'Yes' : 'No'}</span></div>
                  <div className="flex justify-between items-center"><span className="text-gray-700">Username</span><span className="font-semibold">@{analyticsData.status.account_info.username}</span></div>
                </div>
              ) : (
                <div className="text-gray-500 text-center py-4">No account data available</div>
              )
            ) : (
              analyticsData.demographics?.by_country && Object.keys(analyticsData.demographics.by_country).length > 0 ? (
                Object.entries(analyticsData.demographics.by_country)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 5)
                  .map(([country, count]) => (
                    <div key={country} className="flex justify-between items-center">
                      <span className="text-gray-700">{country}</span>
                      <span className="font-semibold">{formatNumber(count)}</span>
                    </div>
                  ))
              ) : (
                <div className="text-gray-500 text-center py-4">No country data available</div>
              )
            )}
          </div>
        </Card>

        <Card title={selectedPlatform === "reddit" ? "Account Statistics" : selectedPlatform === "twitter" ? "API Access Info" : "Audience by Age & Gender"}>
          <div className="space-y-2">
            {selectedPlatform === "reddit" ? (
              analyticsData.status?.account_info ? (
                <div className="space-y-3">
                  <div className="flex justify-between items-center"><span className="text-gray-700">Total Karma</span><span className="font-semibold">{formatNumber(analyticsData.status.account_info.total_karma || 0)}</span></div>
                  <div className="flex justify-between items-center"><span className="text-gray-700">Link Karma</span><span className="font-semibold">{formatNumber(analyticsData.status.account_info.link_karma || 0)}</span></div>
                  <div className="flex justify-between items-center"><span className="text-gray-700">Comment Karma</span><span className="font-semibold">{formatNumber(analyticsData.status.account_info.comment_karma || 0)}</span></div>
                  <div className="flex justify-between items-center"><span className="text-gray-700">Account Age</span><span className="font-semibold">{analyticsData.status.account_info.created_utc ? Math.floor((Date.now() - analyticsData.status.account_info.created_utc * 1000) / (1000 * 60 * 60 * 24)) + ' days' : 'Unknown'}</span></div>
                </div>
              ) : (
                <div className="text-gray-500 text-center py-4">No account data available</div>
              )
            ) : selectedPlatform === "twitter" ? (
              <div className="space-y-3">
                <div className="flex justify-between items-center"><span className="text-gray-700">API Access Level</span><span className="font-semibold text-yellow-600">Free Tier</span></div>
                <div className="flex justify-between items-center"><span className="text-gray-700">Tweets Access</span><span className="font-semibold text-red-600">Limited</span></div>
                <div className="flex justify-between items-center"><span className="text-gray-700">Analytics Available</span><span className="font-semibold text-green-600">Basic</span></div>
                <div className="text-sm text-gray-500 mt-2"><p>• Account info: ✅ Available</p><p>• Tweet content: ❌ Restricted</p><p>• Engagement metrics: ❌ Restricted</p></div>
              </div>
            ) : (
              analyticsData.demographics?.by_age_gender && Object.keys(analyticsData.demographics.by_age_gender).length > 0 ? (
                Object.entries(analyticsData.demographics.by_age_gender)
                  .sort(([, a], [, b]) => b - a)
                  .slice(0, 6)
                  .map(([segment, count]) => (
                    <div key={segment} className="flex justify-between items-center"><span className="text-gray-700">{segment}</span><span className="font-semibold">{formatNumber(count)}</span></div>
                  ))
              ) : (
                <div className="text-gray-500 text-center py-4">No demographic data available</div>
              )
            )}
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Best Performing Post">{analyticsData.bestPost?.post && Object.keys(analyticsData.bestPost.post).length > 0 ? (<div className="space-y-3"><div className="text-sm text-gray-600 line-clamp-3">{safeGet(analyticsData.bestPost.post, 'message', 'No message available')}</div><div className="grid grid-cols-2 gap-4 text-sm"><div><span className="text-gray-500">Reach:</span><div className="font-semibold">{formatNumber(safeGet(analyticsData.bestPost.post, 'reach', 0))}</div></div><div><span className="text-gray-500">Impressions:</span><div className="font-semibold">{formatNumber(safeGet(analyticsData.bestPost.post, 'impressions', 0))}</div></div><div><span className="text-gray-500">Engaged Users:</span><div className="font-semibold">{formatNumber(safeGet(analyticsData.bestPost.post, 'engaged_users', 0))}</div></div></div></div>) : (<div className="text-gray-500 text-center py-4">No post data available</div>)}</Card>

        <Card title="Worst Performing Post">{analyticsData.worstPost?.post && Object.keys(analyticsData.worstPost.post).length > 0 ? (<div className="space-y-3"><div className="text-sm text-gray-600 line-clamp-3">{safeGet(analyticsData.worstPost.post, 'message', 'No message available')}</div><div className="grid grid-cols-2 gap-4 text-sm"><div><span className="text-gray-500">Reach:</span><div className="font-semibold">{formatNumber(safeGet(analyticsData.worstPost.post, 'reach', 0))}</div></div><div><span className="text-gray-500">Impressions:</span><div className="font-semibold">{formatNumber(safeGet(analyticsData.worstPost.post, 'impressions', 0))}</div></div><div><span className="text-gray-500">Engaged Users:</span><div className="font-semibold">{formatNumber(safeGet(analyticsData.worstPost.post, 'engaged_users', 0))}</div></div></div></div>) : (<div className="text-gray-500 text-center py-4">No post data available</div>)}</Card>
      </div>

      {analyticsData.posts?.posts && analyticsData.posts.posts.length > 0 && (
        <Card title="Recent Posts Performance">
          <div className="space-y-4">
            {analyticsData.posts.posts.slice(0, 5).map((post, index) => {
              let engagementMetrics = [];
              if (selectedPlatform === "twitter") {
                const likes = post.reactions?.like || 0;
                const retweets = post.reactions?.retweet || 0;
                const replies = post.reactions?.reply || 0;
                engagementMetrics = [
                  { label: "Reach", value: post.reach },
                  { label: "Likes", value: likes },
                  { label: "Retweets", value: retweets },
                  { label: "Replies", value: replies },
                ];
              } else if (selectedPlatform === "reddit") {
                const upvotes = post.reactions?.upvote || 0;
                const downvotes = post.reactions?.downvote || 0;
                const comments = post.reactions?.comment || 0;
                engagementMetrics = [
                  { label: "Reach", value: post.reach },
                  { label: "Upvotes", value: upvotes },
                  { label: "Downvotes", value: downvotes },
                  { label: "Comments", value: comments },
                ];
              } else if (selectedPlatform === "facebook") {
                const totalLikes = post.reactions_count || 0;
                const actualComments = post.comments_count || 0;
                const actualShares = post.shares_count || 0;
                engagementMetrics = [
                  { label: "Reach", value: post.reach },
                  { label: "Likes", value: totalLikes },
                  { label: "Comments", value: actualComments },
                  { label: "Shares", value: actualShares },
                ];
              } else {
                const likes = post.reactions?.like || 0;
                const comments = post.reactions?.comment || 0;
                const shares = post.reactions?.share || 0;
                engagementMetrics = [
                  { label: "Reach", value: post.reach },
                  { label: "Likes", value: likes },
                  { label: "Comments", value: comments },
                  { label: "Shares", value: shares },
                ];
              }
              return (
                <div key={post.id || index} className="border-b border-gray-200 pb-3 last:border-b-0">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1 text-sm text-gray-600 line-clamp-2">{post.message || 'No message available'}</div>
                  </div>
                  <div className="grid grid-cols-4 gap-3 text-xs text-gray-500">
                    {engagementMetrics.map((metric, idx) => (
                      <div key={idx}><span>{metric.label}: </span><span className="font-semibold text-gray-700">{formatNumber(metric.value)}</span></div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {!isConfigured && (<div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4"><div className="flex items-center"><div className="flex-shrink-0"><svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg></div><div className="ml-3"><p className="text-sm text-yellow-800"><strong>Demo Mode:</strong> {selectedPlatform === "reddit" ? "Reddit analytics not configured. Showing sample data." : selectedPlatform === "twitter" ? (analyticsData.posts?.cached ? `Twitter analytics showing ${analyticsData.posts.cache_message || "cached data"} due to rate limits.` : "Twitter analytics showing real account data but limited by API access level.") : "Facebook analytics not configured. Showing sample data."} {selectedPlatform === "reddit" ? " Add your REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, and REDDIT_ACCESS_TOKEN to the server/.env file to see real Reddit data." : selectedPlatform === "twitter" ? (analyticsData.posts?.cached ? " Data will refresh automatically when rate limits reset." : " Twitter account data is real, but tweet content requires higher API access level.") : " Add your PAGE_ID and ACCESS_TOKEN to the server/.env file to see real Facebook data."}</p></div></div></div>)}
    </div>
  );
}

export default Analytics;

