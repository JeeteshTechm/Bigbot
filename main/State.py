import json
from typing import Any, Dict, Optional


class ChannelState:
    """Represents the state of a conversation channel."""

    def __init__(
        self,
        user_id: str,
        operator_id: str,
        channel_id: str,
        skill: Optional[Any] = None,
        block_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        """Initialize a new ChannelState object with the given properties and any additional kwargs."""
        self.user_id = user_id
        self.operator_id = operator_id
        self.channel_id = channel_id
        self.skill = skill
        self.block_id = block_id
        self.data = data or {}
        self.extra = extra or {}
        self.kwargs = kwargs

    def has_skill(self) -> bool:
        """Return True if this ChannelState object has a skill associated with it."""
        return self.skill is not None

    def update_data(self, key: str, value: Any) -> None:
        """Update the data attribute with a new key-value pair."""
        self.data[key] = value

    def update_extra(self, key: str, value: Any) -> None:
        """Update the extra attribute with a new key-value pair."""
        self.extra[key] = value

    def serialize(self) -> Dict[str, Any]:
        """Return a dictionary representation of this ChannelState object."""
        return {
            "user_id": self.user_id,
            "operator_id": self.operator_id,
            "channel_id": self.channel_id,
            "skill": self.skill,
            "block_id": self.block_id,
            "data": self.data,
            "extra": self.extra,
            **self.kwargs,
        }

    @classmethod
    def from_dict(cls, state_dict: Dict[str, Any]) -> "ChannelState":
        """Create a new ChannelState object from a dictionary."""
        return cls(**state_dict)

    def to_json(self) -> str:
        """Return a JSON representation of this ChannelState object."""
        return json.dumps(self.serialize())

    @classmethod
    def from_json(cls, json_str: str) -> "ChannelState":
        """Create a new ChannelState object from a JSON string."""
        state_dict = json.loads(json_str)
        return cls(**state_dict)
