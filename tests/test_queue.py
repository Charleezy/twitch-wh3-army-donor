def test_parse_reads_tab_separated_lines(game):
    game.run('entries = donation_army_queue.parse("a1\\tBob\\t20.00\\nb2\\tAlice\\t5.50\\n")')
    assert game.eval("#entries") == 2
    assert game.eval("entries[1].id") == "a1"
    assert game.eval("entries[1].donor") == "Bob"
    assert game.eval("entries[1].amount") == 20.0
    assert game.eval("entries[2].amount") == 5.5


def test_parse_skips_malformed_lines_and_handles_crlf(game):
    game.run('entries = donation_army_queue.parse("junk\\r\\na1\\tBob\\tnot_a_number\\r\\nc3\\tCarl\\t7\\r\\n")')
    assert game.eval("#entries") == 1
    assert game.eval("entries[1].id") == "c3"


def test_parse_ignores_partial_trailing_line(game):
    game.run('entries = donation_army_queue.parse("a1\\tBob\\t20.00\\nb2\\tAlice\\t2")')
    assert game.eval("#entries") == 1
    assert game.eval("entries[1].id") == "a1"


def test_read_missing_file_is_empty(game):
    assert game.eval('#donation_army_queue.read("does_not_exist_here.txt")') == 0


def test_read_file(game):
    game.queue("a1\tBob\t20.00")
    game.run(f'entries = donation_army_queue.read([[{game.queue_path}]])')
    assert game.eval("entries[1].donor") == "Bob"


def test_parse_reads_optional_epoch_field(game):
    game.run('entries = donation_army_queue.parse("a1\\tBob\\t20.00\\t1760000000\\nb2\\tAlice\\t5.50\\n")')
    assert game.eval("#entries") == 2
    assert game.eval("entries[1].time") == 1760000000
    assert game.eval("entries[1].amount") == 20.0
    assert game.eval("entries[2].time") is None


def test_parse_four_fields_ignores_bad_epoch_and_extra_fields(game):
    game.run('entries = donation_army_queue.parse("a1\\tBob\\t20.00\\tsoon\\nb2\\tAlice\\t5.50\\t1\\t2\\n")')
    assert game.eval("#entries") == 1
    assert game.eval("entries[1].id") == "a1"
    assert game.eval("entries[1].time") is None


def test_parse_ignores_partial_four_field_line(game):
    game.run('entries = donation_army_queue.parse("a1\\tBob\\t20.00\\t1760000000\\nb2\\tAlice\\t5.50\\t17600")')
    assert game.eval("#entries") == 1
