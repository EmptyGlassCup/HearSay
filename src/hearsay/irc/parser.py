from dataclasses import dataclass, field

@dataclass
class IRCMessage:
    command: str
    prefix: str | None = None
    tags: dict[str,str] = field(default_factory=dict)
    params: list[str] = field(default_factory=list)


# Converts a IRC message (string) into a IRCMessage dataclass
def parse(line: str) -> IRCMessage:
    line = line.strip('\r\n')
    # Check if message has tags
    tags = {}
    if line.startswith('@'):
        # Get the tags, without the '@', seperated via ';'
        tags_str = line.split(maxsplit=1)[0][1:].split(';')

        for tag in tags_str:
            parts = tag.split('=', maxsplit=1)
            key = parts[0]
            value = parts[1] if len(parts) > 1 else ''
            tags[key] = value
    
        # Strip away the tags
        line = line.split(maxsplit=1)[1]

    # Check if message has prefix
    prefix = None
    if line.startswith(':'):
        prefix = line.split(maxsplit=1)[0][1:]

        # Strip away prefix
        line = line.split(maxsplit=1)[1]

    # Add the command
    parts = line.split(maxsplit=1)
    command = parts[0]
    line = parts[1] if len(parts) > 1 else ''

    # Add the parameter
    params = []
    if len(line) > 0:
        params_str = line.split()
        for i, param in enumerate(params_str):
            if param.startswith(':'):
                params.append(' '.join(params_str[i:])[1:])
                break
            else:
                params.append(param)

    msg = IRCMessage(tags = tags, prefix = prefix, command = command, params = params)

    return msg




def serialize(msg: IRCMessage) -> str:
    # Create Tag string
    tags = []
    for key, value in msg.tags.items():
        if value:
            tags.append(key + '=' + value)
        else:
            tags.append(key)
    
    tag_str = ';'.join(tags)
    if msg.tags:
        tag_str = '@' + tag_str


    # Create Prefix String
    prefix_str = msg.prefix
    if prefix_str:
        prefix_str = ':' + prefix_str

    # Create COmmand String
    command_str = msg.command

    # Creats params string
    params = msg.params
    param_str = ''
    if params:
        *rest, last = params
        if rest:
            param_str = ' '.join(rest) + ' :' + last
        else:
            param_str = ':' + last


    # Create IRC message
    parts = []
    if tag_str:
        parts.append(tag_str)
    if prefix_str:
        parts.append(prefix_str)
    
    parts.append(command_str)

    if param_str:
        parts.append(param_str)

    line = ' '.join(parts) + '\r\n'

    return line




