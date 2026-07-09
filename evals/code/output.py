from dataclasses import dataclass, field


@dataclass
class CodeEvalOutput:
    diff: str
    modified_files: dict[str, str] = field(default_factory=dict)
