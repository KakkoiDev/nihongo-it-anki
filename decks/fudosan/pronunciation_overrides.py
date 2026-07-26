"""Readings for the fudosan deck that legitimately differ from UniDic.
Consumed by scripts/check_pronunciation.py (surface -> correct reading).

Real-estate and municipal vocabulary is compound-heavy, and UniDic tokenises
these compounds into their parts and reads each part in isolation: 所有者 comes
back as しょゆうもの, 下水道 as げすいみち, 市街化 as しがいばけ. The authored
furigana is the standard reading in every case below.
"""

ACCEPTED = {
    # 者 / 物 / 人 as compound suffixes — UniDic falls back to もの / ひと
    '所有者': 'しょゆうしゃ',
    '担当者': 'たんとうしゃ',
    '建築物': 'けんちくぶつ',
    '障害物': 'しょうがいぶつ',
    '埋設物': 'まいせつぶつ',
    '名義人': 'めいぎにん',
    # 水道: UniDic reads the 道 alone as みち
    '上下水道': 'じょうげすいどう',
    '上水道': 'じょうすいどう',
    '下水道': 'げすいどう',
    # 化 as a suffix, not 化ける
    '市街化': 'しがいか',
    '義務化': 'ぎむか',
    # 内 as "within", not うち
    '予算内': 'よさんない',
    '区域内': 'くいきない',
    # Dates and counters: 日 is ひ only when it stands alone
    '一月一日': 'いちがつついたち',
    '一月三十一日': 'いちがつさんじゅういちにち',
    '更新日': 'こうしんび',      # rendaku
    '撮影日': 'さつえいび',      # rendaku
    '九十日': 'きゅうじゅうにち',
    '百五十日': 'ひゃくごじゅうにち',
    '四十二分': 'よんじゅうにふん',
    # Terms UniDic reads as the wrong homograph
    # Keyed on the whole phrase, not on 方 / 様 alone: a bare key would also
    # split 方法, 方針 and 態様, which UniDic reads correctly by itself.
    '担当の方': 'たんとうのかた',   # the person in charge, not ほう the direction
    '担当者様': 'たんとうしゃさま',
    '今週末': 'こんしゅうまつ',
    '法上': 'ほうじょう',        # 建築基準法上の道路
    '保安林': 'ほあんりん',
    '事務所': 'じむしょ',
    '引込み': 'ひきこみ',        # utility service connection
    '未': 'み',                  # 未登記, not the zodiac ひつじ
    '入会権': 'いりあいけん',    # common rights, not にゅうかいけん
}
