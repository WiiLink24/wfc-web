db_url = "postgresql://username:password@localhost/nc"

# Used to secure the web panel.
secret_key = "please_change_thank_you"

# Authentik API configuration
authentik_api_url = ""
authentik_service_account_token = ""

# OpenID Connect configuration
oidc_redirect_uri = ""
oidc_client_secrets_json = {
    "web": {
        "client_id": "",
        "client_secret": "",
        "auth_uri": "",
        "token_uri": "",
        "userinfo_uri": "",
        "issuer": "",
        "redirect_uris": "",
    }
}
oidc_logout_url = ""

# Moderator group UUID for access control
moderator_group_uuid = "your-moderator-group-uuid-here"

# API URLs for WFC and Ban Info
wfc_stats_api = "http://localhost:8080/api/dummy_stats"
wfc_groups_api = "https://api.wfc.wiilink.ca/api/groups"
ban_info_api = "http://localhost:8080/api/dummy/baninfo?q={query}"
