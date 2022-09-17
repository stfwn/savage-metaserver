from enum import Enum, unique
from functools import cached_property


@unique
class UserClanLinkDeletedReason(str, Enum):
    DECLINED = "declined"
    KICKED = "kicked"
    LEFT = "left"
    RETRACTED = "retracted"


@unique
class UserClanLinkRank(str, Enum):
    # Using IntEnum could have made this class shorter, but it's nice to keep
    # the database readable in isolation by using string values.
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"

    def __gt__(self, other):
        if type(self) is type(other):
            return self.weights[self.value] > self.weights[other.value]
        elif type(other) is str:
            return self > self(other)
        raise NotImplementedError

    def __lt__(self, other):
        if type(self) is type(other):
            return self.weights[self.value] < self.weights[other.value]
        elif type(other) is str:
            return self < self(other)
        raise NotImplementedError

    def __eq__(self, other):
        if type(self) is type(other):
            return self.weights[self.value] == self.weights[other.value]
        elif type(other) is str:
            return self == other
        raise NotImplementedError

    def __geq__(self, other):
        if type(self) is type(other):
            return self.weights[self.value] >= self.weights[other.value]
        elif type(other) is str:
            return self >= self(other)
        raise NotImplementedError

    def __le__(self, other):
        if type(self) is type(other):
            return self.weights[self.value] <= self.weights[other.value]
        elif type(other) is str:
            return self <= self(other)
        raise NotImplementedError

    def __call__(self, value: str):
        return {"owner": self.OWNER, "admin": self.ADMIN, "member": self.MEMBER}[value]

    @cached_property
    def weights(self):
        return {"owner": 3, "admin": 2, "member": 1}
