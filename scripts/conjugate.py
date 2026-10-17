#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""日语动词变形引擎。

输入辞书形（或ます形）与动词类别，输出 9 种活用形。
被 build_workbench.py 调用，也可单独测试：

    python conjugate.py 書く 動Ⅰ
    python conjugate.py 食べる 動Ⅱ
"""

import sys

# 五段动词：词尾假名 → (て形后缀, ない形词干, え段, お段, 使役词干)
GODAN = {
    "う": ("って", "わ", "え", "お", "わ"),
    "く": ("いて", "か", "け", "こ", "か"),
    "ぐ": ("いで", "が", "げ", "ご", "が"),
    "す": ("して", "さ", "せ", "そ", "さ"),
    "つ": ("って", "た", "て", "と", "た"),
    "ぬ": ("んで", "な", "ね", "の", "な"),
    "ぶ": ("んで", "ば", "べ", "ぼ", "ば"),
    "む": ("んで", "ま", "め", "も", "ま"),
    "る": ("って", "ら", "れ", "ろ", "ら"),
}

# 特殊活用（辞书形 → 9 形）。键为辞书形首词（去重前）。
SPECIAL = {
    # ある：否定是「ない」，不是「あらない」
    "ある": dict(te="あって", ta="あった", nai="ない", pot="あり得る",
                 vol="あろう", imp="—", pro="あるな", ba="あれば", cau="—"),
    # くださる／なさる／おっしゃる／いらっしゃる：命令形是「～い」而非「～れ」
    "くださる": dict(te="くださって", ta="くださった", nai="くださらない", pot="くださる",
                    vol="くださろう", imp="ください", pro="くださるな",
                    ba="くだされば", cau="くださらせる"),
    "なさる": dict(te="なさって", ta="なさった", nai="なさらない", pot="なさる",
                  vol="なさろう", imp="なさい", pro="なさるな",
                  ba="なされば", cau="なさらせる"),
    "おっしゃる": dict(te="おっしゃって", ta="おっしゃった", nai="おっしゃらない", pot="おっしゃる",
                      vol="おっしゃろう", imp="おっしゃい", pro="おっしゃるな",
                      ba="おっしゃれば", cau="おっしゃらせる"),
    "いらっしゃる": dict(te="いらっしゃって", ta="いらっしゃった", nai="いらっしゃらない", pot="いらっしゃる",
                        vol="いらっしゃろう", imp="いらっしゃい", pro="いらっしゃるな",
                        ba="いらっしゃれば", cau="いらっしゃらせる"),
    "ござる": dict(te="ござって", ta="ござった", nai="ござらない", pot="ござる",
                  vol="ござろう", imp="ござい", pro="ござるな",
                  ba="ござれば", cau="ござらせる"),
    # くれる：命令形是「くれ」
    "くれる": dict(te="くれて", ta="くれた", nai="くれない", pot="くれられる",
                  vol="くれよう", imp="くれ", pro="くれるな", ba="くれれば", cau="くれさせる"),
    # 行く：て形是「行って」而非「行いて」
    "行く": dict(te="行って", ta="行った", nai="行かない", pot="行ける",
                vol="行こう", imp="行け", pro="行くな", ba="行けば", cau="行かせる"),
    "いく": dict(te="いって", ta="いった", nai="いかない", pot="いける",
                vol="いこう", imp="いけ", pro="いく", ba="いけば", cau="いかせる"),
}


def _first(s):
    """辞书形可能是「見る/診る」这种并列写法，取第一个。"""
    return str(s).split("/")[0].strip()


def conjugate(dic, cls="動Ⅰ"):
    """返回 dict：te, ta, nai, pot(可能), vol(意志), imp(命令),
    pro(禁止), ba(假设), cau(使役)。未识别时返回 None。"""
    d = _first(dic)
    if not d:
        return None

    # 1) 特殊表优先
    if d in SPECIAL:
        return dict(SPECIAL[d])

    # 2) サ変（する / ～する）
    if d.endswith("する"):
        pre = d[:-2]
        return dict(
            te=pre + "して", ta=pre + "した", nai=pre + "しない",
            pot=pre + "できる", vol=pre + "しよう", imp=pre + "しろ",
            pro=pre + "するな", ba=pre + "すれば", cau=pre + "させる",
        )

    # 3) カ変（来る / ～てくる / ～くる）
    if d.endswith("来る"):
        pre = d[:-2]
        return dict(
            te=pre + "来て", ta=pre + "来た", nai=pre + "来ない",
            pot=pre + "来られる", vol=pre + "来よう", imp=pre + "来い",
            pro=pre + "来るな", ba=pre + "来れば", cau=pre + "来させる",
        )
    if d.endswith("くる"):
        pre = d[:-2]
        return dict(
            te=pre + "きて", ta=pre + "きた", nai=pre + "こない",
            pot=pre + "こられる", vol=pre + "こよう", imp=pre + "こい",
            pro=pre + "くるな", ba=pre + "くれば", cau=pre + "こさせる",
        )

    # 4) 一段（動Ⅱ）：去る + 各后缀
    if cls == "動Ⅱ" and d.endswith("る"):
        st = d[:-1]
        return dict(
            te=st + "て", ta=st + "た", nai=st + "ない",
            pot=st + "られる", vol=st + "よう", imp=st + "ろ",
            pro=d + "な", ba=st + "れば", cau=st + "させる",
        )

    # 5) 五段（動Ⅰ）
    if cls == "動Ⅰ":
        last = d[-1]
        if last in GODAN:
            te_suf, nai_k, e_k, o_k, a_k = GODAN[last]
            st = d[:-1]
            te = st + te_suf
            ta = te[:-1] + ("だ" if te.endswith("で") else "た")
            return dict(
                te=te, ta=ta, nai=st + nai_k + "ない",
                pot=st + e_k + "る", vol=st + o_k + "う", imp=st + e_k,
                pro=d + "な", ba=st + e_k + "ば", cau=st + a_k + "せる",
            )

    # 6) 兜底：当作一段处理（若以る结尾）
    if d.endswith("る"):
        st = d[:-1]
        return dict(
            te=st + "て", ta=st + "た", nai=st + "ない",
            pot=st + "られる", vol=st + "よう", imp=st + "ろ",
            pro=d + "な", ba=st + "れば", cau=st + "させる",
        )
    return None


def row(masu, dic, cls):
    """生成 13 列表格的一行：ます形/辞书形/类/て/た/ない/要点/6形"""
    c = conjugate(dic, cls)
    if not c:
        return [masu, dic, cls, "—", "—", "—", "无法识别", "—", "—", "—", "—", "—", "—"]
    note = ""
    d = _first(dic)
    if d in SPECIAL:
        note = "★特殊活用"
    elif d.endswith("する"):
        note = "サ変"
    elif d.endswith("来る") or d.endswith("くる"):
        note = "カ変"
    return [
        masu, dic, cls, c["te"], c["ta"], c["nai"], note,
        c["pot"], c["vol"], c["imp"], c["pro"], c["ba"], c["cau"],
    ]


if __name__ == "__main__":
    tests = [
        ("書きます", "書く", "動Ⅰ"),
        ("食べます", "食べる", "動Ⅱ"),
        ("します", "する", "動Ⅲ"),
        ("来ます", "来る", "動Ⅲ"),
        ("行きます", "行く", "動Ⅰ"),
        ("飲みます", "飲む", "動Ⅰ"),
        ("話します", "話す", "動Ⅰ"),
        ("泳ぎます", "泳ぐ", "動Ⅰ"),
        ("待ちます", "待つ", "動Ⅰ"),
        ("遊びます", "遊ぶ", "動Ⅰ"),
        ("死にます", "死ぬ", "動Ⅰ"),
        ("帰ります", "帰る", "動Ⅰ"),
        ("あります", "ある", "動Ⅰ"),
        ("くださいます", "くださる", "動Ⅰ"),
        ("勉強します", "勉強する", "動Ⅲ"),
        ("持ってきます", "持ってくる", "動Ⅲ"),
    ]
    for masu, dic, cls in tests:
        r = row(masu, dic, cls)
        print(f"{r[0]:<10} {r[2]:<4} て:{r[3]:<8} た:{r[4]:<8} ない:{r[5]:<9} "
              f"可能:{r[7]:<10} 意志:{r[8]:<9} 命令:{r[9]:<8} 禁止:{r[10]:<10} 假设:{r[11]:<9} 使役:{r[12]}")
