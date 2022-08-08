from datetime import timedelta
import os

max_servers_per_user = 5
server_online_cutoff = timedelta(minutes=1)
database_url = os.environ.get("DATABASE_URL", "sqlite://")
dev_mode = True if os.environ.get("DEV") else False

# The granularity of this format determines how long a proof is valid
proof_datetime_component_format = "%Y-%m-%dT%H:%M"
