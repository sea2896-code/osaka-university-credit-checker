from src.ui_helpers import overall_display, remaining_credits, should_show_fourth_year_message


def test_remaining_zero_shows_clear_message():
    display = overall_display(0)
    assert display.title == "卒業要件クリア！🎉"
    assert display.message == "必要単位を満たしています。"


def test_remaining_one_to_ten_shows_near_message():
    assert overall_display(1).title == "あとちょっと！！"
    assert overall_display(10).message == "卒業まであと 10 単位です。"


def test_remaining_over_ten_shows_short_message():
    display = overall_display(11)
    assert display.title == "未達🥹🥹"
    assert display.message == "卒業まであと 11 単位です。"


def test_provisional_clear_message_is_not_definitive():
    assert "確定ではありません" in overall_display(0, provisional=True).message


def test_fourth_year_message_conditions():
    assert should_show_fourth_year_message(4, 1)
    assert not should_show_fourth_year_message(4, 0)
    assert not should_show_fourth_year_message(1, 1)
    assert not should_show_fourth_year_message(2, 1)
    assert not should_show_fourth_year_message(3, 1)
    assert not should_show_fourth_year_message(None, 1)


def test_remaining_credits_is_capped_at_zero():
    assert remaining_credits(119, 130) == 11
    assert remaining_credits(140, 130) == 0
