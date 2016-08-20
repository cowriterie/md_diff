#!/usr/bin/python3

import os
import contextlib
import re
import argparse

import markdown2
from jinja2 import Environment, FileSystemLoader

from subprocess import Popen, STDOUT, PIPE

PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_ENVIRONMENT = Environment(
    autoescape=False,
    loader=FileSystemLoader(os.path.join(PATH, 'templates')),
    trim_blocks=False)


@contextlib.contextmanager
def temp_chdir(path):
    starting_directory = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(starting_directory)

class ArgumentException (Exception):
    pass

class Application (object):
    def run(self):
        parser = argparse.ArgumentParser(description='Create a human-readable markdown diff.')
        parser.add_argument('--outfile', dest='outfile', help='set the output file path.')
        parser.add_argument('--diff', dest='diff', help='set the input diff path.')
        parser.add_argument('--stdin', dest='stdin', help='set the input diff path.')
        parser.add_argument('--repo', dest='repo', help='set the path of the repository (use with --sha)')
        parser.add_argument('--sha', dest='sha', help='set the change sha (use with --repo)')
        parser.add_argument('--branch', dest='branch', help='get the whole diff of a branch (use with --repo)')
        parser.add_argument('--word-diff', dest='word_diff', help='whether or not the diff is a word-level or line-level diff', action='store_true')
        args = parser.parse_args();

        # Three different ways to get patch data
        #   1. File (via --diff)
        #   2. Standard input (--stdin)
        #   3. Via a repository (using a sha or a branch)
        #
        # None of these may overlap

        ops = [args.diff, args.stdin, args.repo]
        opcount = 0
        for op in ops:
            opcount += 1 if op else 0
        if opcount != 1:
            raise ArgumentException("Must choose between passing a diff file, stdin, or using a repository")

        diff = None
        if args.diff:
            with open(args.diff, 'r') as fd:
                diff = fd.readline()
        elif args.stdin:
            diff = self.diff_from_stdin()
        elif args.repo:
            if args.sha:
                if args.branch:
                    raise ArgumentException("Choose a sha or a branch, not both")
                diff = self.diff_from_sha(args.repo, args.sha, args.word_diff)
            elif args.branch:
                diff = self.diff_from_branch(args.repo, args.branch, args.word_diff)
            else:
                raise ArgumentException("Must use --sha or --branch with --repo")

        if args.outfile:
            out_file = args.outfile
        else:
            out_file = "out.html"

        self.generate_diff_markdown(diff, out_file)


    def diff_from_stdin(self):
        raise NotImplementedError()


    def diff_from_sha(self, working_tree_dir, sha, word_diff=False):
        with temp_chdir(working_tree_dir):
            args = ['git', 'show', sha, '--unified=2000']
            if word_diff:
                args.append('--word-diff')
            p = Popen(args, stdout=PIPE, stderr=STDOUT)
            output, err = p.communicate()
            if err:
                raise Exception("Failed git call: %s" % str(err))
            return output.split("\n")


    def diff_from_branch(self, working_tree_dir, branch, word_diff=False):
        with temp_chdir(working_tree_dir):
            args = ['git', 'diff', '%s' % branch, '--unified=2000']
            if word_diff:
                args.append('--word-diff')
            p = Popen(args, stdout=PIPE, stderr=STDOUT)
            output, err = p.communicate()
            if err:
                raise Exception("Failed git call: %s" % str(err))

            output = output.decode('UTF-8')
            return output.split("\n")



    def render_template(self, template_filename, context):
        return TEMPLATE_ENVIRONMENT.get_template(template_filename).render(context)

    def diff_replace(self, diff):
        outlines = []
        # Read in the lines of the diff and remove the metadata
        for idx, line in enumerate(diff):
            if line.startswith("diff --git"):
                break
        else:
            raise Exception("Invalid diff")
        diff = diff[idx:]

        # Now, find every "diff --git ..." line and replace it (and all others
        # leading to the line that starts with "@@") with a special div that
        # indicates a new file
        regex = re.compile("^diff --git a/(\S+)")
        cur_line = 0
        while cur_line < len(diff):
            m = regex.match(diff[cur_line])
            # We've found a git line.
            if m:
                end_line = cur_line
                while not diff[end_line].startswith("@@ "):
                    end_line += 1
                    if end_line >= len(diff):
                        raise Exception("No end for last diff file")
                print("found %s from lines %d to %d" % (m.group(1), cur_line, end_line))

                # Ugly ugly, but it works. Remove all of the git lines and replace with a div
                if cur_line == 0:
                    diff = diff[end_line+1:]
                else:
                    diff = diff[:cur_line] + diff[end_line+1:]
                diff.insert(cur_line, "<div class=\"file\">File: %s</div>\n" % m.group(1))
            else:
                cur_line += 1

        # Find and replace dif elements with the html span tags
        replacements = {
            "[-": "<span style='background-color: #d88'>",
            "-]": "</span>",
            "{+": "<span style='background-color: #8d8'>",
            "+}": "</span>"
        }

        # For each line, replace and write out
        for line in diff:
            for k, v in replacements.items():
                line = line.replace(k, v)

            if line:
                if line[0] == "-":
                    line = "<span style='background-color: #d88'>%s</span><br>" % line[1:]

                if line[0] == "+":
                    line = "<span style='background-color: #8d8'>%s</span><br>" % line[1:]
            outlines.append(line.strip())

        return outlines

    def generate_diff_markdown(self, diff, outfile, word_diff=False):

        outlines = self.diff_replace(diff)


        # Generate html from the markdown and feed it into the html file template
        with open(outfile, "w") as fd:
            text = "\n".join(outlines)
            markdown_text = markdown2.markdown(text)
            html = self.render_template("diff.html", {"markdown":markdown_text})

            # Condition code to include proper html escapes
            escapes = {
                u"\u2026": "&hellip;",
                u"\u011b": "&#283;",
                u"\xe0":   "&agrave;",
                u"\xf3":   "&oacute;",
                u"\u2012": "&#8210;",
                u"\u2013": "&ndash;",
                u"\u2018": "'"
            }
            for k, v in escapes.items():
                html = html.replace(k, v)

            # Finally, write out the results. We're done!
            fd.write(html)




if __name__ == "__main__":
    Application().run()
