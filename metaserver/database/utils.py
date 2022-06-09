import re


def validate_tag(cls, v):
    max_colors = 4
    max_letters = 4

    v = v.strip()

    assert v.replace("^", "").isalnum(), "Only ascii letters, numbers and '^' allowed"
    assert re.match(
        r"^(?!.*\^(?![\d]{3})).*$", v
    ), "'^' must always be followed by exactly three numbers"
    assert v.count("^") <= max_colors, "Clan tags can contain at most 4 colors"
    assert (
        len(re.sub(r"\^[\d]{3}", "", v)) <= max_letters
    ), "Clan tags can contain at most 4 letters"
    return v
