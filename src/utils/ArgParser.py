import re
import logging

from utils.exceptions import JalBotError


def format_args(arg_type, text):
    """Format args based on type"""
    if arg_type == 'list':
            args_text = text.strip().split()
    else:
        args_text = text.strip()
    return args_text


def parse_args(cmd_args, text):
    """Parse command arguments"""
    args = {}
    search_args = {
        i: re.compile(f'(?<=-{i} ).*?(?= -\D|\Z)') for i in cmd_args.keys()
    }
    search_short_args = {
        i: re.compile(f'(?<=-{cmd_args[i]["short"]} ).*?(?= -\D|\Z)') for i in cmd_args.keys()
    }
    for k, v in search_args.items():
        if v.search(text):
            arg = v.search(text).group()
            args[k] = format_args(cmd_args[k]["type"], arg)
        elif search_short_args[k].search(text):
            arg = search_short_args[k].search(text).group()
            args[k] = format_args(cmd_args[k]["type"], arg)
        else:
            args[k] = False
    return args


def parse_option(text, command_options):
    """Get option from text"""
    option_fetch = re.match(r'[\w]*? ([a-z]+?)($|\s-.*)', text)
    if not option_fetch:
        return None
    option = option_fetch.groups()[0]
    # option = text.split(' ', 1)[1]
    if option not in command_options:
        raise JalBotError(f'Invalid Option {option}')
    return option


def format_message(message):
    """Format message"""
    message = message.strip()
    replace_chars = {
        '&lt;': '<',
        '&gt;': '>',
        '&amp;': '&'
    }
    for k, v in replace_chars.items():
        message = message.replace(k, v)
    return message
