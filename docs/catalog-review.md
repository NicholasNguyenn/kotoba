# Catalog review

14 entries, all `verified: false`. Check each against your textbook,
then set `"verified": true` on that line in `data/grammar_catalog.jsonl`.

I wrote these explanations. They are plausible, not authoritative — the
project's credibility rests on this file being right.

## Known gap, not yet fixed

**のに is ambiguous and currently always labeled 'even though'.** 料理を作るのに
時間がかかる is the *purpose* のに ('it takes time to make food'), and the
detector mislabels it. Distinguishing them needs the preceding verb form and
is not reliable mechanically. Leaving it: Phase 4 will measure what it costs.

## Entries

### [ ] は — N5

**topic marker**

Marks the topic: what the sentence is about, usually known information. Contrast with が, which marks the grammatical subject and presents it as new. 私は学生です answers 'what about me?'; 私が学生です answers 'who is the student?'

`id: g-wa-001` · matches: `は(助詞)`

### [ ] が — N5

**subject marker**

Marks the grammatical subject and presents it as new or identifying information. Also used for the object of 好き, 嫌い, 上手, できる and similar. Contrast with は, which marks a known topic.

`id: g-ga-001` · matches: `が(助詞)`

### [ ] ばかり — N3

**nothing but, only**

Limits by implying excess: the speaker often finds the amount unreasonable. ゲームばかりしている = 'does nothing but play games', with a note of criticism. Contrast だけ, which states a neutral limit.

`id: g-bakari-001` · matches: `ばかり(助詞)`

### [ ] だけ — N4

**only, just**

States a plain limit with no judgement attached. 水だけ飲んだ = 'drank only water'. Contrast ばかり, which implies the amount is excessive.

`id: g-dake-001` · matches: `だけ(助詞)`

### [ ] ても — N4

**even if, even though**

Concessive: the following clause holds regardless of the condition. 雨が降っても行きます = 'I will go even if it rains'. Attaches to the て-form, so the て and も are separate tokens.

`id: g-temo-001` · matches: `て|で(助詞) + も(助詞)`

### [ ] のに — N3

**even though, despite**

Marks a result contrary to expectation, usually carrying surprise, regret or complaint. 勉強したのに不合格だった = 'even though I studied, I failed'. Contrast ても, which is hypothetical and carries no complaint.

`id: g-noni-001` · matches: `の(助詞) + に(助詞)`

### [ ] ている — N5

**progressive or resulting state**

Either an action in progress (食べている = 'is eating') or a state resulting from a completed change (結婚している = 'is married', not 'is marrying'). Which reading applies depends on the verb.

`id: g-teiru-001` · matches: `て|で(助詞) + いる(動詞)`

### [ ] てしまう — N4

**completion, or regret**

Marks an action as finished off, often with regret that it cannot be undone. 全部食べてしまった = 'I ate it all (oops)'. Context decides whether completion or regret dominates.

`id: g-teshimau-001` · matches: `て|で(助詞) + しまう(動詞)`

### [ ] なければならない — N4

**must, have to**

Obligation, literally 'if it does not, it will not do'. Tokenizes as four units: ない + ば + なる + ない.

`id: g-nakereba-001` · matches: `ない(助動詞) + ば(助詞) + なる(動詞) + ない(助動詞)`

### [ ] ことができる — N5

**can, be able to**

Potential built from a dictionary-form verb + ことができる. More formal than the potential verb form (話せる).

`id: g-kotogadekiru-001` · matches: `こと(名詞) + が(助詞) + できる(動詞)`

### [ ] そうだ — N4

**I hear that, reportedly**

Hearsay, attaching to a plain form: 来るそうだ = 'I hear he is coming'. Distinct from the そう of 来そうだ ('looks like it will come'), which attaches to the verb stem.

`id: g-souda-hearsay-001` · matches: `そう(名詞) + だ(助動詞)`

### [ ] ようだ — N3

**seems, appears**

The speaker's inference from evidence. 雨が降るようだ = 'it seems it will rain'. Softer and more subjective than らしい.

`id: g-youda-001` · matches: `よう(形状詞) + だ(助動詞)`

### [ ] たばかり — N4

**just did, only just**

Marks an action completed a short time ago, from the speaker's perspective. 着いたばかりです = 'I've just arrived'. Distinct from the ばかり of ゲームばかり ('nothing but'), and the た before it is what tells them apart.

`id: g-tabakari-001` · matches: `た(助動詞) + ばかり(助詞)`

### [ ] そうだ（様態） — N4

**looks like, seems about to**

Appearance inferred from looking at something, attaching to the verb stem: 降りそうだ = 'it looks like it will rain'. The hearsay そうだ attaches to a plain form instead (降るそうだ = 'I hear it will rain'). The tokenizer separates them: appearance そう is 形状詞, hearsay そう is 名詞.

`id: g-souda-appearance-001` · matches: `そう(形状詞) + だ(助動詞)`
