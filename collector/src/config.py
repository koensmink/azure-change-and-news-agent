import os

def env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")

PORT = int(os.getenv("PORT", "8088"))
RUN_SCHEDULE_CRON = os.getenv("RUN_SCHEDULE_CRON", "0 7 * * *")

INCLUDE_SOURCES = [s.strip() for s in os.getenv("INCLUDE_SOURCES", "graph_message_center,m365_roadmap,intune_whatsnew,defender_whatsnew,entra_whatsnew,azure_updates,microsoft_security_blog,third_party_rss").split(",") if s.strip()]

DEFAULT_GA_ONLY = env_bool("DEFAULT_GA_ONLY", True)

SECURITY_KEYWORDS = [k.strip() for k in os.getenv("SECURITY_KEYWORDS", "").split(",") if k.strip()]

SOURCE_LOOKBACK_DAYS = int(os.getenv("SOURCE_LOOKBACK_DAYS", "14"))

GRAPH_TENANT_ID = os.getenv("GRAPH_TENANT_ID", "")
GRAPH_CLIENT_ID = os.getenv("GRAPH_CLIENT_ID", "")
GRAPH_CLIENT_SECRET = os.getenv("GRAPH_CLIENT_SECRET", "")
GRAPH_ENDPOINT = os.getenv("GRAPH_ENDPOINT", "https://graph.microsoft.com/v1.0")
