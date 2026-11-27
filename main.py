"""
スポーツエントリー「第12回 トレニックワールド 100mile＆100km in 彩の国」
100mileソロ(A)の各区分の受付状況を監視し、LINE / ntfy に通知する。

通知は3種類:
  1. 毎日21:00以降の最初の取得時に「定時レポート」
     （各区分の見出しにある 受付終了 / 受付中 などの表記をそのまま送る）
  2. 表記が変わったとき（例: 受付終了 → 受付中）に「変化通知」
  3. 「受付中」になった区分があるときの「空き通知」(緊急)

- ログイン不要の公開ページだけを見る（自動申込みはしない）
- 21:00前後は15秒間隔、それ以外は5分間隔（サーバー負荷への配慮）

使い方:
  pip install requests beautifulsoup4
  LINE_CHANNEL_TOKEN=xxxx LINE_USER_ID=Uxxxx NTFY_TOPIC=your-secret-topic python watch_trainic.py
  （どちらの通知先も片方だけで可）
"""

def now_jst() -> dt.datetime:
    return dt.datetime.now(JST)


def interval() -> int:
    n = now_jst()
    minutes = n.hour * 60 + n.minute
    if REPORT_HOUR * 60 - 2 <= minutes <= REPORT_HOUR * 60 + 10:
        return 15
    return 300


def fetch_items():
    """対象区分を [(状態表記, 区分名), ...] で返す。例: ("受付終了", "A）100mile：男子（40歳代）")"""
    r = requests.get(URL, headers=HEADERS, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []
    for h in soup.find_all(["h3", "h4"]):
        text = " ".join(h.get_text(" ", strip=True).split())
        if TARGET in text and EXTRA_FILTER in text:
            head, _, rest = text.partition(" ")
            if TARGET in head:      # 状態表記が付いていない場合
                head, rest = "(表記なし)", text
            items.append((head, rest))
    return items


def notify(title: str, message: str, urgent: bool = False):
    """設定されている通知先すべてに送る。1つ失敗しても他は送る"""
    if LINE_TOKEN and LINE_USER_ID:
        try:
            requests.post(
                "https://api.line.me/v2/bot/message/push",
                headers={"Authorization": f"Bearer {LINE_TOKEN}"},
                json={
                    "to": LINE_USER_ID,
                    "messages": [{"type": "text", "text": f"{title}\n{message}\n{URL}"}],
                },
                timeout=10,
            )
        except Exception as e:
            print("LINE error:", e)
    if NTFY_TOPIC:
        try:
            requests.post(
                f"https://ntfy.sh/{NTFY_TOPIC}",
                data=message.encode("utf-8"),
                headers={
                    "Title": title,
                    "Priority": "urgent" if urgent else "default",
                    "Click": URL,
                },
                timeout=10,
            )
        except Exception as e:
            print("ntfy error:", e)


def format_report(items) -> str:
    return "\n".join(f"{status}｜{label}" for status, label in items)


def main():
    if not ((LINE_TOKEN and LINE_USER_ID) or NTFY_TOPIC):
        raise SystemExit("通知先が未設定です（LINE_CHANNEL_TOKEN+LINE_USER_ID か NTFY_TOPIC）")
    notify("Watcher started", "監視を開始しました（テスト通知）")

    prev = {}                  # 区分名 -> 前回の状態表記
    last_report_date = None    # 定時レポートを送った日付
    notified_open = set()
    warned_structure = False

    while True:
        try:
            items = fetch_items()
            n = now_jst()
            print(n.strftime("%H:%M:%S"), format_report(items).replace("\n", " / ") or "対象なし")

            if not items and not warned_structure:
                notify("Watcher warning", "対象区分が見つかりません。ページ構造の変更を確認してください")
                warned_structure = True

            # 1. 定時レポート（毎日21:00以降の最初の取得時）
            if items and n.hour >= REPORT_HOUR and last_report_date != n.date():
                notify(f"{n:%m/%d} 21時の受付状況", format_report(items))
                last_report_date = n.date()

            # 2. 表記の変化通知（初回取得時は比較対象がないので送らない）
            cur = {label: status for status, label in items}
            if prev:
                changes = [
                    f"{label}\n  {prev.get(label, '(新規)')} → {status}"
                    for label, status in cur.items()
                    if prev.get(label) != status
                ]
                if changes:
                    notify("受付状況が変わりました", "\n".join(changes))
            prev = cur

            # 3. 「受付中」になった区分の緊急通知
            open_now = {label for status, label in items if status == "受付中"}
            for label in open_now - notified_open:
                notify("100mile slot OPEN", f"{label}\n今すぐ申込みへ", urgent=True)
            notified_open = open_now   # 再び埋まったら、次に空いたときまた通知できる
        except Exception as e:  # ネットワークエラー等は握りつぶして続行
            print("error:", e)
        time.sleep(interval())


if __name__ == "__main__":
    main()
    app.run()
