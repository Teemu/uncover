# coding: utf-8
from collections import defaultdict, Counter
from subprocess import Popen, PIPE
import os.path

def tokenize(cmd):
    tokens = []
    buf = ''
    open_string = False
    escape_next = False
    for c in cmd:
        if escape_next:
            escape_next = False
            buf += c
        elif open_string:
            if c == '"':
                buf += '"'
                tokens.append(buf)
                open_string = False
                buf = ''
            else:
                buf += c
        else:
            if c == ' ':
                if buf:
                    tokens.append(buf)
                buf = ''
            elif c == '"':
                buf += '"'
                open_string = True
            elif c == "\\":
                escape_next = True
            else:
                buf += c
    if buf:
        tokens.append(buf)
    while tokens and not tokens[0]:
        tokens.pop(0)
    return tuple(tokens)

class Database(object):
    def __init__(self):
        self.commands = defaultdict(lambda: Counter())
        self.commands_with_args = Counter()
        self.relations = defaultdict(lambda: Counter())

    def add_command(self, cmd):
        tokens = tokenize(cmd)
        if tokens:
            self.commands[tokens[0]]['__usage__'] += 1
            for token in tokens[1:]:
                self.commands[tokens[0]][token] += 1
            partial = ()
            for token in tokens:
                partial += (token,)
                self.commands_with_args[partial] += 1

    def add_command_groups(self, cmds):
        prev = None
        for cmd in cmds:
            if prev:
                self.relations[prev][cmd] += 1
            prev = cmd
        self.relations[prev][cmd] += 1

    def most_used_commands(self):
        return sorted(
            self.commands.items(),
            key=lambda x: x[1]['__usage__'],
            reverse=True
        )

    def most_used_commands_with_args(self):
        return [
            x for x in self.commands_with_args.most_common()
            if len(x[0]) > 1
        ]

    def most_typing_saved(self):
        return filter(
            lambda x: x[1] > 1,
            sorted(
                self.commands_with_args.items(),
                key=lambda x: len(' '.join(x[0])) * x[1],
                reverse=True
            )
        )

def get_history():
    sources = []
    with open(os.path.join(os.path.expanduser('~'), '.zsh_history')) as fp:
        lines = []
        for line in fp:
            if line and ';' in line:
                lines.append(line.strip().split(';')[1])
        sources.append(('zsh', lines))

    with open(os.path.join(os.path.expanduser('~'), '.bash_history')) as fp:
        lines = []
        for line in fp:
            if line:
                lines.append(line.strip())
        sources.append(('bash', lines))
    return sources

def main():
    db = Database()
    for source, history in get_history():
        for command in history:
            db.add_command(command)
        db.add_command_groups(history)

    print "Most used commands by history:"
    for i, add_command in enumerate(db.most_used_commands()[0:10]):
        print "- %d %s" % (add_command[1]['__usage__'], add_command[0])
        most_used_parameters = sorted(
            add_command[1].items(),
            key=lambda x: x[1],
            reverse=True
        )
        for key, used in most_used_parameters[:5]:
            if used > 1 and key != '__usage__':
                print "    %d %s" % (used, key)

    print "Most used commands with arguments:"
    for cmd, usage in db.most_used_commands_with_args()[0:50]:
        print '- %s %s' % (usage, ' '.join(cmd))

    print "Typing saves:"
    for cmd, usage in db.most_typing_saved()[0:50]:
        print '- %s %s' % (usage, ' '.join(cmd))

    print "command groups"
    def print_next_cmd(cmd, depth=0):
        sum_score = sum(db.relations[cmd].values())
        for next_cmd, score in db.relations[cmd].most_common(10):
            if score >= sum_score*0.1 and score > 1 and depth <= 2:
                print u"%s └ %s%% %s" % (
                    "  "*(depth*1),
                    round(100 * (float(score) / sum_score)),
                    next_cmd
                )
                print_next_cmd(next_cmd, depth+1)

    for cmd, next_cmds in sorted(
        db.relations.items(),
        key=lambda x: len(x[0] + x[1].most_common(1)[0][0]) * max(x[1].values()),
        reverse=True
    )[0:30]:
        #  max(x[1].values())
        next_cmd, score = next_cmds.most_common(1)[0]
        print "%s -> %s (%s%%)" % (
            cmd,
            next_cmd,
            round(100 * (float(score) / sum(next_cmds.values())))
        )

if __name__ == '__main__':
    main()