from dataclasses import dataclass
import re


# --------------------------------------------------
# Default values 預設值
# --------------------------------------------------

DEFAULT_WORK_TIME = 25
DEFAULT_BREAK_TIME = 5
DEFAULT_ROUNDS = 4
DEFAULT_PREPARE_TIME = 5

MIN_VALUE = 1
MAX_VALUE = 30

DEFAULT_BOT_NAME = "AI_Anchor"


# --------------------------------------------------
# Data model 資料模型
# --------------------------------------------------

@dataclass(frozen=True)
class ActivityConfig:
    """Configuration for one focus activity."""

    work_time: int = DEFAULT_WORK_TIME
    break_time: int = DEFAULT_BREAK_TIME
    rounds: int = DEFAULT_ROUNDS
    prepare_time: int = DEFAULT_PREPARE_TIME


class CommandParseError(ValueError):
    """Raised when a Plurk command cannot be parsed."""


# --------------------------------------------------
# Validation 驗證
# --------------------------------------------------

def _validate_value(name: str, value: int) -> int:
    """Validate that a value is a positive integer from 1 to 30."""

    if not isinstance(value, int):
        raise CommandParseError(f"{name} 必須是正整數。")

    if value < MIN_VALUE or value > MAX_VALUE:
        raise CommandParseError(
            f"{name} 必須是 {MIN_VALUE}～{MAX_VALUE} 的正整數。"
        )

    return value


def _build_config(
    work_time: int,
    break_time: int,
    rounds: int,
    prepare_time: int,
) -> ActivityConfig:
    """Validate and build an ActivityConfig."""

    return ActivityConfig(
        work_time=_validate_value("工作時間", work_time),
        break_time=_validate_value("休息時間", break_time),
        rounds=_validate_value("回合數", rounds),
        prepare_time=_validate_value("開始前等待時間", prepare_time),
    )


# --------------------------------------------------
# Command text handling 命令文字處理
# --------------------------------------------------

def _remove_bot_mention(content_raw: str, bot_name: str) -> str:
    """
    Remove the leading @Bot mention.

    Example:
        @AI_Anchor 開始 25/5/4/5
    becomes:
        開始 25/5/4/5
    """

    pattern = rf"^@{re.escape(bot_name)}\s*"

    result = re.sub(
        pattern,
        "",
        content_raw.strip(),
        count=1,
    )

    if result == content_raw.strip():
        raise CommandParseError(
            f"找不到有效的 @{bot_name} 呼叫。"
        )

    return result.strip()


# --------------------------------------------------
# Compact syntax 簡潔語法
# --------------------------------------------------

def _parse_compact_syntax(text: str) -> ActivityConfig | None:
    """
    Parse compact syntax.

    Supported:
        25/5/4/5
        20/10/6/3

    Order:
        工作時間 / 休息時間 / 回合數 / 開始前等待時間
    """

    match = re.fullmatch(
        r"(\d{1,2})\s*/\s*"
        r"(\d{1,2})\s*/\s*"
        r"(\d{1,2})\s*/\s*"
        r"(\d{1,2})",
        text,
    )

    if not match:
        return None

    work_time, break_time, rounds, prepare_time = map(
        int,
        match.groups(),
    )

    return _build_config(
        work_time,
        break_time,
        rounds,
        prepare_time,
    )


# --------------------------------------------------
# Friendly syntax 友善語法
# --------------------------------------------------

def _extract_value(
    text: str,
    patterns: list[str],
    field_name: str,
) -> int:
    """
    Extract one numeric value from a known friendly-language pattern.
    """

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            return _validate_value(
                field_name,
                int(match.group(1)),
            )

    raise CommandParseError(
        f"無法辨識{field_name}。"
    )


def _parse_friendly_syntax(text: str) -> ActivityConfig | None:
    """
    Parse friendly syntax using predefined phrases.

    Supported examples:

        開始寫作，工作25分鐘，休息5分鐘，4回合，5分鐘後開始

        開始，25分鐘，休息5分鐘，4回合，5分鐘後開始
    """

    # Friendly syntax must contain at least one Chinese
    # punctuation mark separating the instruction and parameters.
    if not re.search(r"[，,]", text):
        return None

    work_time = _extract_value(
        text,
        [
            r"(?:工作|專注|寫作)\s*(?:時間)?\s*(\d{1,2})\s*分鐘",
        ],
        "工作時間",
    )

    break_time = _extract_value(
        text,
        [
            r"休息\s*(?:時間)?\s*(\d{1,2})\s*分鐘",
        ],
        "休息時間",
    )

    rounds = _extract_value(
        text,
        [
            r"(?:共\s*)?(\d{1,2})\s*回合",
            r"回合數\s*(\d{1,2})",
        ],
        "回合數",
    )

    prepare_time = _extract_value(
        text,
        [
            r"(\d{1,2})\s*分鐘後開始",
            r"開始前\s*(?:等待)?\s*(\d{1,2})\s*分鐘",
            r"準備時間\s*(\d{1,2})\s*分鐘",
        ],
        "開始前等待時間",
    )

    return _build_config(
        work_time,
        break_time,
        rounds,
        prepare_time,
    )


# --------------------------------------------------
# Public parser 共同解析器
# --------------------------------------------------

def parse_command(
    content_raw: str,
    bot_name: str = DEFAULT_BOT_NAME,
) -> ActivityConfig:
    """
    Parse a raw Plurk response into an ActivityConfig.

    Supported commands:

        @AI_Anchor 開始

        @AI_Anchor 開始寫作

        @AI_Anchor 開始 20/5/6/3

        @AI_Anchor 開始寫作 20/5/6/3

        @AI_Anchor 開始寫作，工作20分鐘，休息5分鐘，6回合，3分鐘後開始

    Rules:

        - All parameters must be positive integers.
        - Every parameter must be between 1 and 30.
        - No parameter means default values are used.
        - Unsupported or ambiguous commands raise CommandParseError.
    """

    if not isinstance(content_raw, str):
        raise CommandParseError("指令內容必須是文字。")

    text = _remove_bot_mention(
        content_raw,
        bot_name,
    )

    # --------------------------------------------------
    # Basic command 基本指令
    # --------------------------------------------------

    if text in {"開始", "開始寫作"}:
        return ActivityConfig()

    # --------------------------------------------------
    # Remove command prefix 移除命令前綴
    # --------------------------------------------------

    if text.startswith("開始寫作"):
        parameters = text[len("開始寫作"):].strip()
    elif text.startswith("開始"):
        parameters = text[len("開始"):].strip()
    else:
        raise CommandParseError(
            "不是有效的開始指令。"
        )

    if not parameters:
        return ActivityConfig()

    # --------------------------------------------------
    # Compact syntax 簡潔語法
    # --------------------------------------------------

    compact_config = _parse_compact_syntax(parameters)

    if compact_config is not None:
        return compact_config

    # --------------------------------------------------
    # Friendly syntax 友善語法
    # --------------------------------------------------

    friendly_config = _parse_friendly_syntax(
        text
    )

    if friendly_config is not None:
        return friendly_config

    # --------------------------------------------------
    # Unsupported syntax 不支援的語法
    # --------------------------------------------------

    raise CommandParseError(
        "無法辨識活動設定。"
        "\n可使用："
        "\n@AI_Anchor 開始"
        "\n@AI_Anchor 開始 25/5/4/5"
        "\n或使用完整的中文設定格式。"
    )
