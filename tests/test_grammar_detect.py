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
