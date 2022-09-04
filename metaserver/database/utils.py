from enum import Enum, unique


@unique
class UserClanLinkDeletedReason(str, Enum):
    DECLINED = "declined"
    KICKED = "kicked"
    LEFT = "left"
    RETRACTED = "retracted"
