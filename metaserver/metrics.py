from metaserver import config
from metaserver.database.models import UserStats


def skill_rating(
    current_rating: int,
    mean_team_rating: int,
    mean_opponent_rating: int,
    achieved_score: int,
):
    """Team-adaptation of standard Elo.

    Expected win rate is computed by taking a weighted sum of a player's own
    Elo and their team's mean Elo versus the other team's mean elo.
    """
    team_weighted_rating = (
        config.lambda_ * mean_team_rating + (1 - config.lambda_) * current_rating
    )
    q_player = 10 ** (team_weighted_rating / config.initial_user_skill_rating)
    q_opponent = 10 ** (mean_opponent_rating / config.initial_user_skill_rating)

    expected_score = q_player / (q_player + q_opponent)

    new_rating = current_rating + (
        config.initial_user_skill_rating * config.skill_rating_update_step_size
    ) / current_rating * (achieved_score - expected_score)
    return new_rating


def mean_skill_rating(users_stats: list[UserStats]) -> float:
    """Put this here to make it easier to implement a weighted mean later."""
    return sum([us.skill_rating for us in users_stats]) / len(users_stats)
