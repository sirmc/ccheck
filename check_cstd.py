#! /usr/bin/env python3
# This is a Python 3 script - tested with 3.3 or later
# To use, run it from the directory containing the source files to check.
import re
import glob
import sys
import subprocess

error = 0
def die(*msg):
    global error
    print(*msg, file=sys.stderr)
    error = 1

spacing = {}
for i in subprocess.check_output(["find", ".", "-name", "*.[ch]"]).decode('utf-8').split('\n'):
    if len(i) is 0: continue

    try:
        if i.endswith('.h'):
            fn = i.split('/')[-1].replace('.', '_').upper()
            c = subprocess.check_output("cpp -P -dM '" + i + "'", shell=True).decode('utf-8')
            if ("#define " + fn + " \n") not in c:
                die(i + ": preprocessor fence not defined or with wrong name")

            else:
                c = subprocess.check_output("cat '"+ i + "' '" + i +
                                            "' | cpp -P -D" + fn + " 2>&1", shell = True).decode('utf-8')
                if re.search(r'[^\s]', c):
                    die(i + ": fence not protecting double inclusion")

    except subprocess.CalledProcessError:
        die(i + ": error while calling preprocessor")

    f = open(i)
    contents = f.read()
    f.close()

    for n, line in enumerate(contents.split('\n'), start=1):
        if len(line) > 80:
            die(i + ":" + str(n) + ": line exceeding 80 characters")

        if re.search('[\v\r\t\f]', contents):
            die(i + ":" + str(n) + ": invalid whitespace character in source")

        if re.search('[^\n\x20-\x7e]', contents):
            die(i + ":" + str(n) + ": non-printable character in source")

        if re.search(' $', contents, re.M):
            die(i + ":" + str(n) + ": trailing whitespace")

    # remove comments and replace strings/characters
    canon = re.sub(r'/\*([^*]|\*[^/])*\*/', '', contents)
    canon = re.sub(r'//[^\n]\n', '\n', canon)
    canon = re.sub(r'"([^\\]|\\.)*"', 'str', canon)
    canon = re.sub(r"(')(?:(?=(\\?))\2.)*?\1", 'chr', canon)

    for n, line in enumerate(canon.split('\n'), start=1):
        for m in re.finditer(r'^ *# *define +([a-zA-Z_][a-zA-Z0-9_]*)', canon, re.M):
            if re.search('[a-z]', m.group(1)):
                die(i + ":" + str(n) + ": macro name is not all caps")

        for m in re.finditer(r'^ *# *define +[^ (]+\(([^)]*)\)', canon, re.M):
            for a in (s.strip() for s in m.group(1).split(',')):
                if a != a.capitalize():
                    die(i + ":" + str(n) + ": macro argument is not capitalized")

        for m in re.finditer(r'^ *(typedef +)?(struct|enum|union) +(?P<id>[a-zA-Z_][a-zA-Z0-9_]*)', canon, re.M):
            if re.search('[A-Z]', m.group('id')):
                die(i + ":" + str(n) + ": bad struct, enum or union name")

        if re.search(r'\b(if|for|while|do|(__)?asm(__)?|return|continue|break|sizeof)\b([^ ;]|  +)', canon, re.M):
            die(i + ":" + str(n) + ": keyword not followed by single space or semicolon")

        if re.search(';([^ \n]|  +)', canon, re.M):
            die(i + ":" + str(n) + ": semicolon not at end of line and not followed by exactly one space")

        if re.search(r'[^ ] +[];)]', canon):
            die(i + ":" + str(n) + ": semicolon or closing )/] separated from previous token with a space")

        if re.search(r'[[(] +', canon):
            die(i + ":" + str(n) + ": opening (/[ separated from next token with a space")

        if re.search(r'( (\+\+|--|[~!]) )|([^ ([](\+\+|--|[~!])[^] ;)])|(= +\* +)|([^ ([&]&[^] &)])', canon):
            die(i + ":" + str(n) + ": improperly spaced operator")

        if re.match(r' *# *include', line): continue

        m = re.search(r'([]a-zA-Z0-9_]+) +\(', line)
        if m and m.group(1) not in ["if", "for", "while", "do", "return", "continue", "break", "sizeof"] \
           and not re.match(r' *# *define', line):
               die(i + ":" + str(n) + ": incorrect space between cast or function and opening '('")

        if re.search(r'[^ !+*\/%^&=<>|-](!=|&=|\*=|-=|\+=|-=|\+=|&&|\||\|\||[\/%:?^=]|[<>=]=|<<?|>>?|^)', line):
            die(i + ":" + str(n) +  ": missing space before operator")

        if re.search(r'[^-](&&|\||\|\||[/%:?^=]|[<>=]=|<<?|>>?)[^ /%:?^=><|]', line):
            die(i +  ":" + str(n) + ": missing space after operator")

        if re.search(r'(,)[^ ]', line):
            die(i + ":" + str(n) + ": missing space after comma")

        if re.search(r'-> | ->', line):
            die(i + ":" + str(n) + ": invalid space around ->")


    for m in re.finditer(r'^( +)', canon, re.M):
        w = m.group(1)
        l = spacing.get(w, set())
        l.add(i)
        spacing[w] = l

    # brace alignment
    dstack = []
    for row, line in enumerate(canon.split('\n'), start=1):
        for col, c in enumerate(line):
            if c == '{': dstack.append(col)
            if c == '}':
                if len(dstack) is 0:
                    die(i + ":" + str(row) +": closing } without opening {")
                elif col != dstack.pop():
                    die(i + ":" + str(row) + ": closing } not aligned with opening {")

# check spacing across all files
if spacing:
    spaces = list(spacing.keys())
    spaces.sort()
    unit = len(spaces[0])
    for rest in spaces[1:]:
        lrest = len(rest)
        if (lrest // unit) * unit != lrest:
            die(' '.join(spacing[rest]) + ": space width " + str(lrest) +
                " inconsistent with minimum " + str(unit) + " found in other file(s)")

sys.exit(error)
