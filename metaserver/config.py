from datetime import timedelta
import os

max_servers_per_user = 5
server_online_cutoff = timedelta(minutes=1)
database_url = os.environ.get("DATABASE_URL", "sqlite://")
dev_mode = True if os.environ.get("DEV") else False

# How long people have to wait between receiving an email token and requesting a new one.
email_token_renew_timeout = timedelta(seconds=30)

# The granularity of this format determines how long a proof is valid
proof_datetime_component_format = "%Y-%m-%dT%H:%M"

#######################
# Skill rating config #
#######################

# When a user first starts playing on a server.
initial_user_skill_rating = 800

# Lambda -> 1: more importance on team rating.
# Lambda -> 0: more importance on individual rating.
lambda_ = 0.8

skill_rating_update_step_size = 64
