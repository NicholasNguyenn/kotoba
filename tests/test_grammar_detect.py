from kotoba.grammar_detect import confirm_candidates, detect, load_catalog, unverified
from kotoba.tokenizer import tokenize


def _patterns(text):
    return [d.pattern for d in detect(tokenize(text))]


def test_catalog_loads():
    assert len(load_catalog()) >= 12


def test_multi_token_patterns_match():
    # のに is two particle tokens; ても is て + も. Surface matching would miss
    # neither, but lemma matching is what survives conjugation.
    assert "のに" in _patterns("勉強したのに不合格だった。")
    assert "ても" in _patterns("雨が降っても行きます。")
    assert "なければならない" in _patterns("明日までに出さなければならない。")


def test_matches_through_conjugation():
    # 食べている -> 食べる + て + いる, so the ている pattern still matches.
    assert "ている" in _patterns("今ご飯を食べている。")
    assert "てしまう" in _patterns("全部食べてしまった。")


def test_particles_are_distinguished():
    got = _patterns("彼はゲームばかりしている。")
    assert "は" in got and "ばかり" in got
    assert "だけ" not in got


def test_pos_constraint_rejects_lookalikes():
    # は as part of a word (発表) must not match the topic-marker entry.
    assert "は" not in _patterns("発表を見た。")


def test_confirm_candidates_rejects_what_catalog_did_not_match():
    tokens = tokenize("水だけ飲んだ。")
    got = {d.pattern: d.confirmed for d in confirm_candidates(["だけ", "ばかり"], tokens)}
    assert got == {"だけ": True, "ばかり": False}


def test_seed_entries_are_flagged_unverified():
    # Guards the resume claim: nothing counts as evidence until checked.
    assert len(unverified()) == len(load_catalog())


def test_voiced_te_form_matches():
    """読んで / 飲んで lemmatize the te-particle as で, not て.

    Missing this silently dropped ても, ている and てしまう for every
    ぶ/む/ぬ/ぐ verb -- a large share of real sentences.
    """
    assert "ても" in _patterns("本を読んでも分からない。")
    assert "ている" in _patterns("本を読んでいる。")
    assert "てしまう" in _patterns("本を読んでしまった。")


def test_tabakari_suppresses_bakari():
    # 着いたばかり is "just arrived", not "nothing but arriving".
    got = _patterns("今着いたばかりです。")
    assert "たばかり" in got and "ばかり" not in got


def test_bakari_still_matches_on_its_own():
    assert "ばかり" in _patterns("彼はゲームばかりしている。")


def test_souda_senses_are_separated_by_pos():
    # Appearance そう is 形状詞, hearsay そう is 名詞.
    assert "そうだ（様態）" in _patterns("雨が降りそうだ。")
    assert "そうだ" in _patterns("彼は来るそうだ。")
    assert "そうだ" not in _patterns("雨が降りそうだ。")


def test_temo_requires_a_preceding_verb():
    """でも as 'but' and いくらでも are not the ても grammar point.

    Regression: accepting で for the voiced te-form made ても over-match
    every でも in the language until the preceding part of speech was checked.
    """
    assert "ても" in _patterns("本を読んでも分からない。")
    assert "ても" in _patterns("尋ねられても分からない。")
    assert "ても" not in _patterns("でも可能性は低そうだね。")
    assert "ても" not in _patterns("時間はいくらでも作れる。")


def test_ga_requires_a_preceding_noun():
    # Conjunctive が ("but") follows a predicate, not a noun.
    assert "が" in _patterns("猫が好きです。")
    assert "が" not in _patterns("明日雨のようだががんばろう。")
    assert "が" not in _patterns("知られているが変えられない。")


def test_polite_nakereba_narimasen_matches():
    assert "なければならない" in _patterns("私は眠らなければなりません。")
    assert "なければならない" in _patterns("明日までに出さなければならない。")
