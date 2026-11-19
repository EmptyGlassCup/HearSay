from hearsay.irc.parser import parse, serialize

def check(line, *, command, prefix=None, tags=None, params=None):
    result = parse(line)
    assert result.command == command
    assert result.prefix == prefix
    assert result.tags == (tags or {})
    assert result.params == (params or [])

    assert parse(serialize(parse(line))) == parse(line)



def test_only_command():
    check("PING\r\n", command = 'PING')

def test_single_trailing_param():
    check("PING :ergo.test\r\n", command = 'PING', params = ['ergo.test'])

def test_prefix_two_params():
    line = ":ergo.test 001 tagbot :Welcome to the ErgoTest IRC Network\r\n"
    check(line, command='001', params=['tagbot', 'Welcome to the ErgoTest IRC Network'], prefix='ergo.test')

def test_presfix_two_params2():
    line = ":logbot!l@host PRIVMSG #evidence :CPU spiked at 03:12\r\n"
    check(line, command = 'PRIVMSG', params=['#evidence', "CPU spiked at 03:12"], prefix='logbot!l@host')

def test_tags_no_prefix():
    line = "@+bb-kind=claim;+bb-id=c1 PRIVMSG #evidence :test\r\n"
    check(line, tags={'+bb-kind': 'claim', '+bb-id': 'c1'}, command='PRIVMSG', params=['#evidence', 'test'])

def test_full_msg():
    line = "@+bb-kind=claim;+bb-id=c42;+bb-claim-kind=hypothesis;+bb-level=2;+bb-conf=0.7 :logexpert!l@h PRIVMSG #hypotheses :Deploy at 03:12 likely caused the latency spike\r\n"

    check(line, tags={"+bb-kind": "claim", "+bb-id": "c42", "+bb-claim-kind": "hypothesis", "+bb-level": "2", "+bb-conf": "0.7"}, prefix="logexpert!l@h", command="PRIVMSG", params=["#hypotheses", "Deploy at 03:12 likely caused the latency spike"])

def test_valueless_tag():
    line = '@+bb-kind PRIVMSG #evidence :test\r\n'
    check(line, tags={"+bb-kind": ""}, command='PRIVMSG', params=['#evidence', 'test'])

def test_numeric_command():
    line = ":ergo.test 353 tagbot = #evidence :@Hyunjae tagbot\r\n"
    check(line, prefix='ergo.test', command='353', params=["tagbot", "=", "#evidence", "@Hyunjae tagbot"])

def test_no_rn():
    line = "PING :ergo.test"
    check(line, command='PING', params=['ergo.test'])
