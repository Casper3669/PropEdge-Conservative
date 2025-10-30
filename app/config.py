import os
BALLDONTLIE_API_KEY = os.getenv("BALLDONTLIE_API_KEY", "")
TZ_LOCAL = os.getenv("TZ_LOCAL", "America/Chicago")
DEFAULT_BANKROLL = float(os.getenv("DEFAULT_BANKROLL", "50"))
