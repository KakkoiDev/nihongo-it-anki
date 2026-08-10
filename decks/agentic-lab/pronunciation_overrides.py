# surface -> the correct reading; used to override UniDic when building the
# dictionary reading, so an accepted term stops being reported.
#
# Most entries here are not rendaku but context loss: check_pronunciation.py
# re-tags each token's bare surface, and out of its sentence UniDic reads 一つ as
# いちつ, 化 as ばけ and 多 as さわ. The authored reading is the in-context one.
#
# Keys must be surfaces that never appear inside a longer word in this deck:
# the checker splits the sentence on them, so a key like 行 would also cut 実行
# and 進行 in half.
ACCEPTED = {
    "朝会": "あさかい",          # what the team says; UniDic guesses ちょうかい
    "私": "わたし",              # UniDic reads the bare pronoun わたくし
    "今日中": "きょうじゅう",     # UniDic splits it as 今日 + 中 and reads こんにち
    "捏造": "ねつぞう",          # UniDic reads でつぞう
    "日本語": "にほんご",        # UniDic splits it as 日本 + 語 and reads にっぽん
    "一つ": "ひとつ",
    "二つ": "ふたつ",
    "三日": "みっか",
    "半日": "はんにち",
    "自動化": "じどうか",
    "効率化": "こうりつか",
    "可視化": "かしか",
    "属人化": "ぞくじんか",
    "担当者": "たんとうしゃ",
    "進め方": "すすめかた",
    "やり方": "やりかた",
    "一時的": "いちじてき",
    "空いて": "あいて",
    "多すぎ": "おおすぎ",
    "分からない": "わからない",
}
