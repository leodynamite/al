-- AL Bot Database Schema for Supabase
-- This file contains the SQL schema for analytics and user data

-- Analytics events table
CREATE TABLE IF NOT EXISTS analytics_events (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    user_id BIGINT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB,
    session_id VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for efficient queries
CREATE INDEX IF NOT EXISTS idx_analytics_events_user_id ON analytics_events(user_id);
CREATE INDEX IF NOT EXISTS idx_analytics_events_timestamp ON analytics_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_analytics_events_type ON analytics_events(event_type);

-- User subscriptions table
CREATE TABLE IF NOT EXISTS user_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL UNIQUE,
    tier VARCHAR(20) NOT NULL DEFAULT 'trial',
    status VARCHAR(20) NOT NULL DEFAULT 'trial',
    trial_start TIMESTAMP WITH TIME ZONE,
    trial_end TIMESTAMP WITH TIME ZONE,
    dialogs_used INTEGER DEFAULT 0,
    dialogs_limit INTEGER DEFAULT 50,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    custom_bot_name VARCHAR(100),
    custom_logo_url TEXT,
    is_read_only BOOLEAN DEFAULT FALSE
);

-- Create index for user subscriptions
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_user_id ON user_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_subscriptions_status ON user_subscriptions(status);

-- Scripts table
CREATE TABLE IF NOT EXISTS scripts (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    created_by BIGINT NOT NULL,
    questions JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for scripts
CREATE INDEX IF NOT EXISTS idx_scripts_created_by ON scripts(created_by);

-- Leads table
CREATE TABLE IF NOT EXISTS leads (
    id VARCHAR(100) PRIMARY KEY,
    source VARCHAR(20) NOT NULL,
    script_id VARCHAR(100) NOT NULL,
    answers JSONB NOT NULL,
    lead_score INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'new',
    assigned_to VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    calendar_event_id VARCHAR(100),
    crm_id VARCHAR(100),
    user_id BIGINT NOT NULL
);

-- Create indexes for leads
CREATE INDEX IF NOT EXISTS idx_leads_user_id ON leads(user_id);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(lead_score);
CREATE INDEX IF NOT EXISTS idx_leads_created_at ON leads(created_at);

-- Hot leads notifications table
CREATE TABLE IF NOT EXISTS hot_leads_notifications (
    id SERIAL PRIMARY KEY,
    lead_id VARCHAR(100) NOT NULL,
    user_id BIGINT NOT NULL,
    channel_id VARCHAR(100),
    sent_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'sent'
);

-- Create index for hot leads notifications
CREATE INDEX IF NOT EXISTS idx_hot_leads_lead_id ON hot_leads_notifications(lead_id);
CREATE INDEX IF NOT EXISTS idx_hot_leads_user_id ON hot_leads_notifications(user_id);

-- System alerts table
CREATE TABLE IF NOT EXISTS system_alerts (
    id SERIAL PRIMARY KEY,
    level VARCHAR(20) NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    metadata JSONB,
    resolved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

-- Create index for system alerts
CREATE INDEX IF NOT EXISTS idx_system_alerts_resolved ON system_alerts(resolved);
CREATE INDEX IF NOT EXISTS idx_system_alerts_level ON system_alerts(level);

-- Views for analytics
CREATE OR REPLACE VIEW user_metrics AS
SELECT 
    u.user_id,
    u.tier,
    u.status,
    u.dialogs_used,
    u.dialogs_limit,
    u.is_read_only,
    -- Dialog metrics
    COALESCE(dialogs_today.count, 0) as dialogs_today,
    COALESCE(dialogs_week.count, 0) as dialogs_week,
    -- Lead metrics
    COALESCE(leads_created.count, 0) as leads_created,
    COALESCE(hot_leads.count, 0) as hot_leads,
    COALESCE(meetings_scheduled.count, 0) as meetings_scheduled,
    -- Conversion rate
    CASE 
        WHEN COALESCE(dialogs_week.count, 0) > 0 
        THEN COALESCE(leads_created.count, 0)::FLOAT / dialogs_week.count
        ELSE 0 
    END as conversion_rate,
    -- Average lead score
    COALESCE(avg_score.avg_score, 0) as avg_lead_score
FROM user_subscriptions u
LEFT JOIN (
    SELECT user_id, COUNT(*) as count
    FROM analytics_events 
    WHERE event_type = 'dialog_completed' 
    AND DATE(timestamp) = CURRENT_DATE
    GROUP BY user_id
) dialogs_today ON u.user_id = dialogs_today.user_id
LEFT JOIN (
    SELECT user_id, COUNT(*) as count
    FROM analytics_events 
    WHERE event_type = 'dialog_completed' 
    AND timestamp >= NOW() - INTERVAL '7 days'
    GROUP BY user_id
) dialogs_week ON u.user_id = dialogs_week.user_id
LEFT JOIN (
    SELECT user_id, COUNT(*) as count
    FROM analytics_events 
    WHERE event_type = 'lead_created'
    GROUP BY user_id
) leads_created ON u.user_id = leads_created.user_id
LEFT JOIN (
    SELECT user_id, COUNT(*) as count
    FROM analytics_events 
    WHERE event_type = 'lead_scored' 
    AND metadata->>'status' = 'hot'
    GROUP BY user_id
) hot_leads ON u.user_id = hot_leads.user_id
LEFT JOIN (
    SELECT user_id, COUNT(*) as count
    FROM analytics_events 
    WHERE event_type = 'lead_booked'
    GROUP BY user_id
) meetings_scheduled ON u.user_id = meetings_scheduled.user_id
LEFT JOIN (
    SELECT user_id, AVG((metadata->>'score')::INTEGER) as avg_score
    FROM analytics_events 
    WHERE event_type = 'lead_scored'
    GROUP BY user_id
) avg_score ON u.user_id = avg_score.user_id;

-- Function to get user metrics
CREATE OR REPLACE FUNCTION get_user_metrics(p_user_id BIGINT)
RETURNS TABLE (
    dialogs_today INTEGER,
    dialogs_week INTEGER,
    hot_leads INTEGER,
    meetings_scheduled INTEGER,
    leads_created INTEGER,
    conversion_rate FLOAT,
    avg_lead_score FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COALESCE(um.dialogs_today, 0),
        COALESCE(um.dialogs_week, 0),
        COALESCE(um.hot_leads, 0),
        COALESCE(um.meetings_scheduled, 0),
        COALESCE(um.leads_created, 0),
        COALESCE(um.conversion_rate, 0),
        COALESCE(um.avg_lead_score, 0)
    FROM user_metrics um
    WHERE um.user_id = p_user_id;
END;
$$ LANGUAGE plpgsql;

-- Function to track analytics event
CREATE OR REPLACE FUNCTION track_analytics_event(
    p_event_type VARCHAR(50),
    p_user_id BIGINT,
    p_metadata JSONB DEFAULT NULL,
    p_session_id VARCHAR(100) DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    INSERT INTO analytics_events (event_type, user_id, metadata, session_id)
    VALUES (p_event_type, p_user_id, p_metadata, p_session_id);
END;
$$ LANGUAGE plpgsql;

-- Function to get global metrics
CREATE OR REPLACE FUNCTION get_global_metrics()
RETURNS TABLE (
    total_users INTEGER,
    active_users INTEGER,
    total_dialogs_today INTEGER,
    total_leads_today INTEGER,
    total_hot_leads_today INTEGER,
    avg_conversion_rate FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        (SELECT COUNT(*) FROM user_subscriptions)::INTEGER as total_users,
        (SELECT COUNT(*) FROM user_subscriptions WHERE status = 'active')::INTEGER as active_users,
        (SELECT COUNT(*) FROM analytics_events WHERE event_type = 'dialog_completed' AND DATE(timestamp) = CURRENT_DATE)::INTEGER as total_dialogs_today,
        (SELECT COUNT(*) FROM analytics_events WHERE event_type = 'lead_created' AND DATE(timestamp) = CURRENT_DATE)::INTEGER as total_leads_today,
        (SELECT COUNT(*) FROM analytics_events WHERE event_type = 'lead_scored' AND metadata->>'status' = 'hot' AND DATE(timestamp) = CURRENT_DATE)::INTEGER as total_hot_leads_today,
        (SELECT AVG(conversion_rate) FROM user_metrics WHERE conversion_rate > 0) as avg_conversion_rate;
END;
$$ LANGUAGE plpgsql;

