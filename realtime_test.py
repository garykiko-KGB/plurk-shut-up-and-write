from services.plurk_api import PlurkAPI, PlurkAPIError
from services.plurk_realtime import PlurkRealtime, PlurkRealtimeError


def main() -> None:
    print("=== Shut Up & Write! Plurk Realtime Test ===")

    try:
        # 建立 Plurk API client
        api = PlurkAPI()

        # 確認目前使用的 Plurk 帳號
        profile = api.get_own_profile()

        print(
            f"已連線至 Plurk："
            f"@{profile.get('nick_name', 'UNKNOWN')}"
        )

        # 取得 Realtime Channel
        channel = api.get_user_channel()

        comet_server = channel.get("comet_server")
        channel_name = channel.get("channel_name")

        if not comet_server or not channel_name:
            raise RuntimeError(
                "Plurk 沒有回傳有效的 Realtime Channel。"
            )

        print(f"Realtime Channel：{channel_name}")
        print("等待 Plurk 事件中……")
        print("請在 Plurk 上對 AI_Anchor 做一則回覆。")
        print("按 Ctrl+C 可以停止測試。")
        print()

        # 建立 Realtime listener
        realtime = PlurkRealtime(
            comet_server=comet_server,
            channel_name=channel_name,
        )

        # 持續等待事件
        for event in realtime.listen():
            print("----- 收到 Plurk 事件 -----")
            print(event)
            print()

    except KeyboardInterrupt:
        print("\n測試已停止。")

    except (PlurkAPIError, PlurkRealtimeError) as exc:
        print(f"\nPlurk API 錯誤：{exc}")

    except Exception as exc:
        print(f"\n發生未預期錯誤：{exc}")


if __name__ == "__main__":
    main()
