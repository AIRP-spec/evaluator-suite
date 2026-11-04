from airp_v3.minor_supplement import has_marker, AGE_KEYWORDS, SCHOOL_KEYWORDS, REGEXES


def test_generic_markers_hit():
    for t in ("Help your kids with homework.", "My 9-year-old likes maths.", "She is in 5th grade.",
              "a high school class", "Grade 8 science", "aged 12", "the law protects a minor who is 15", "under 18"):
        assert has_marker(t), t


def test_non_markers_miss():
    for t in ("a minor issue with the code", "aged cheese", "kidney beans", "grade A eggs", "30 years old",
              "graduate school admissions"):
        assert not has_marker(t), t


def test_list_sizes_match_declaration():
    assert (len(AGE_KEYWORDS), len(SCHOOL_KEYWORDS), len(REGEXES)) == (25, 22, 7)
