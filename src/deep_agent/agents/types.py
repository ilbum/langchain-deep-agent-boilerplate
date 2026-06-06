from dataclasses import dataclass, field


@dataclass
class SubagentConfig:
    name: str
    description: str
    system_prompt: str
    tools: list
    interrupt_on: dict[str, bool | dict] = field(default_factory=dict)

    def __post_init__(self):
        if not self.name:
            raise ValueError("SubagentConfig.name is required")
        if not self.tools:
            raise ValueError(f"{self.name}: tools list is empty")

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "tools": self.tools,
        }
        if self.interrupt_on:
            d["interrupt_on"] = self.interrupt_on
        return d
